"""Accessible, dependency-free, read-only terminal health dashboard.

All output is generated from sanitized metrics, never raw process arguments.
ANSI styling is automatically disabled for redirected output or NO_COLOR.
"""
import os
import re
import shutil
import sys

RESET = "\x1b[0m"
PALETTE = {
    "healthy": "\x1b[32m",
    "warning": "\x1b[33m",
    "critical": "\x1b[31m",
    "muted": "\x1b[90m",
    "heading": "\x1b[1;36m",
    "bold": "\x1b[1m",
}
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ORDER = {"healthy": 0, "warning": 1, "critical": 2}


def classify(result):
    """Assign the same traffic-light statuses to terminal and machine reports."""
    findings = result.get("findings", [])
    if any(f.startswith("CRITICAL:") for f in findings):
        return "critical"
    if any(f.startswith(("WARNING:", "SUSPECT:")) for f in findings):
        return "warning"
    return "healthy"


def metric_checks(result):
    """Transparent thresholds; measurement absence is not reported as healthy."""
    cpu = result.get("cpu", {})
    available = result.get("memory_available_bytes", 0)
    total = result.get("memory_total_bytes", 0)
    psi = result.get("io_pressure", {})
    disk = result.get("disks", [])
    checks = []
    def add(name, value, severity, detail):
        checks.append(dict(name=name, value=value, severity=severity, detail=detail))
    wait = cpu.get("iowait_pct")
    if isinstance(wait, (int, float)):
        level = "critical" if wait >= 20 else "warning" if wait >= 8 else "healthy"
        add("CPU I/O wait", "%.1f%%" % wait, level, "High I/O wait can signal storage contention")
    else:
        add("CPU I/O wait", "N/A", "warning", "CPU counters unavailable")
    if total:
        ratio = available / total
        level = "critical" if ratio < .1 else "warning" if ratio < .2 else "healthy"
        add("Available RAM", "%.1f GiB" % (available / 1073741824), level,
            "%.0f%% of total RAM available" % (100 * ratio))
    else:
        add("Available RAM", "N/A", "warning", "Memory counters unavailable")
    full = psi.get("full", {}).get("avg10")
    if isinstance(full, (int, float)):
        level = "critical" if full >= 10 else "warning" if full >= 3 else "healthy"
        add("I/O pressure", "%.1f%%" % full, level, "10-second full-stall average")
    else:
        add("I/O pressure", "N/A", "warning", "PSI unavailable on this system")
    if disk:
        worst = max(disk, key=lambda d: (d.get("queue_depth", 0), d.get("write_await_ms", 0)))
        latency = worst.get("write_await_ms", 0)
        queue = worst.get("queue_depth", 0)
        writes = worst.get("writes_per_s", 0)
        level = ("critical" if queue >= 20 or (writes >= 30 and latency >= 30) else
                 "warning" if queue >= 10 or (writes >= 30 and latency >= 15) else "healthy")
        add("Disk bottleneck", "%s · %.1f ms" % (worst["device"], latency), level,
            "Queue %.1f · %.0f writes/s" % (queue, writes))
    else:
        add("Disk bottleneck", "N/A", "warning", "No block device sample available")
    return checks


def enrich(result):
    """Use severity consistently in dashboard and JSON without mutating input."""
    data = dict(result)
    data["checks"] = metric_checks(result)
    findings_level = classify(result)
    metrics_level = max((c["severity"] for c in data["checks"]), key=lambda s: ORDER[s], default="healthy")
    data["health"] = max((findings_level, metrics_level), key=lambda s: ORDER[s])
    data["health_summary"] = {"healthy": "No significant bottleneck detected in this sample",
                             "warning": "Potential issue needs attention",
                             "critical": "Severe bottleneck detected"}[data["health"]]
    return data


def use_color(force=None, stream=None):
    if force is not None:
        return bool(force)
    output = stream if stream is not None else sys.stdout
    return bool(getattr(output, "isatty", lambda: False)() and
                "NO_COLOR" not in os.environ and os.environ.get("TERM", "") != "dumb")


def shade(value, level, enabled):
    if not enabled or level not in PALETTE:
        return value
    return PALETTE[level] + value + RESET


def shorten(value, width):
    if width <= 0:
        return ""
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[:width - 3] + "..."


class Panel:
    """Width-aware border renderer; ANSI never affects padding."""
    def __init__(self, width=94, color=False, ascii_only=False):
        self.width = max(42, min(112, width))
        self.inner = self.width - 4
        self.color = color
        self.ascii_only = ascii_only
        if ascii_only:
            self.edge, self.horizontal = "|", "-"
            self.top = self.mid = self.bottom = "+"
        else:
            self.edge, self.horizontal = "│", "─"
            self.top, self.mid, self.bottom = "╭", "├", "╰"
        self.lines = []

    def line(self, kind="mid"):
        a = getattr(self, kind)
        b = {"top": "+" if self.ascii_only else "╮",
             "mid": "+" if self.ascii_only else "┤",
             "bottom": "+" if self.ascii_only else "╯"}[kind]
        self.lines.append(a + self.horizontal * (self.width - 2) + b)

    def row(self, *segments):
        parts = []
        size = 0
        for segment in segments:
            if isinstance(segment, tuple):
                label, color = segment
            else:
                label, color = segment, None
            text = str(label)
            remaining = self.inner - size
            if remaining <= 0:
                break
            text = shorten(text, remaining)
            parts.append(shade(text, color, self.color))
            size += len(text)
        self.lines.append(self.edge + " " + "".join(parts) + (" " * (self.inner - size)) + " " + self.edge)

    def section(self, title):
        self.line()
        self.row((title.upper(), "heading"))

    def finish(self):
        self.line("bottom")
        return "\n".join(self.lines)


def severity_label(level, ascii_only=False):
    dot = "!" if ascii_only and level != "healthy" else "+" if ascii_only else "●"
    return "%s %s" % (dot, {"healthy": "HEALTHY", "warning": "WARNING", "critical": "CRITICAL"}[level])


def render(data, color=None, width=None, ascii_only=False):
    """Render a single snapshot; never alters the terminal or clears its screen."""
    data = enrich(data) if "checks" not in data else data
    columns = width or shutil.get_terminal_size(fallback=(94, 24)).columns
    p = Panel(columns, use_color(color), ascii_only)
    status = data["health"]
    p.line("top")
    p.row(("BRIGHTERY DOCTOR", "heading"), "  v" + data.get("version", "?"),
          "  |  READ-ONLY HEALTH REPORT")
    p.row((severity_label(status, ascii_only), status), "  " + data["health_summary"])
    p.row(("Sample: %.1f s" % data.get("sample_seconds", 0), "muted"),
          ("   Time (UTC): " + data.get("timestamp_utc", "unknown")[:19], "muted"))
    p.section("Server overview")
    load = data.get("load_1_5_15", [0, 0, 0])
    cores = data.get("logical_cpus", 0)
    p.row("LOAD  1m %.1f  /  5m %.1f  /  15m %.1f" % tuple((load + [0, 0, 0])[:3]),
          "    %s logical CPUs" % cores if cores else "")
    p.row("SWAP  %.1f GiB used" % (data.get("swap_used_bytes", 0) / 1073741824))
    for check in data["checks"]:
        label = "%-17s" % shorten(check["name"], 17)
        value = shorten(str(check["value"]), max(13, p.inner - 40))
        p.row("  ", (severity_label(check["severity"], ascii_only)[:1], check["severity"]),
              "  " + label, (value, check["severity"]))
        if p.inner >= 75:
            p.row("       ", (shorten(check["detail"], p.inner - 7), "muted"))
    p.section("Disk activity")
    if not data.get("disks"):
        p.row("No disk counters available for this sample")
    else:
        for disk in data["disks"][:5]:
            severity = next((c["severity"] for c in data["checks"]
                            if c["name"] == "Disk bottleneck" and str(c["value"]).startswith(disk["device"] + " ·")), "healthy")
            p.row(("%-10s" % shorten(disk["device"], 10), severity),
                  "  %5.0f writes/s   %5.1f ms await   queue %5.1f" %
                  (disk["writes_per_s"], disk["write_await_ms"], disk["queue_depth"]))
    p.section("Findings & recommended attention")
    findings = data.get("findings", [])
    for item in findings[:8]:
        level = "critical" if item.startswith("CRITICAL:") else "warning" if item.startswith(("WARNING:", "SUSPECT:")) else "healthy"
        marker = "!" if ascii_only else "●"
        p.row("  ", (marker, level), " ", (shorten(item, p.inner - 5), level))
    if not findings:
        p.row("  No findings in this scan")
    p.section("Notable processes (arguments hidden)")
    shown = 0
    for proc in data.get("suspects", []):
        if not (proc["recursive_permissions"] or proc["blocked_samples"] or proc["cpu_pct_one_core"] >= 10):
            continue
        warn = proc["recursive_permissions"] or proc["blocked_samples"] >= 2
        severity = "warning" if warn else "muted"
        p.row(("PID %-8d" % proc["pid"], severity),
              " ", ("%-15s" % shorten(proc["name"], 15), severity),
              " CPU %5.1f%%  D %d/%d" % (proc["cpu_pct_one_core"], proc["blocked_samples"], proc["seen_samples"]))
        service = proc.get("service") or proc.get("parent_service") or "unknown"
        p.row("  service: " + shorten(service, p.inner - 12))
        shown += 1
        if shown >= 4:
            break
    if not shown:
        p.row("No unusually active or blocked processes in this sample")
    p.line()
    p.row(("Snapshot only; findings are not proof of root cause. No changes made.", "muted"))
    return p.finish()
