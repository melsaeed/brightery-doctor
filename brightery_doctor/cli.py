#!/usr/bin/env python3
"""Brightery Doctor: bounded, read-only Linux performance triage.

No network calls, shell commands, or automatic remediation. Process arguments,
environment variables, hostname and file paths are not collected in reports.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

from .dashboard import enrich, render
from .report import html_report

VERSION = "1.2.0"
MAX_PROCESSES = 4096
MAX_SAMPLES = 41
SERVICE_RE = re.compile(r"(?:^|/)([A-Za-z0-9_.@-]{1,88}\.service)(?:/|$)")


def read(path, size=8192, binary=False):
    try:
        with open(path, "rb") as handle:
            raw = handle.read(size)
        return raw if binary else raw.decode("utf-8", "replace")
    except (OSError, ValueError):
        return b"" if binary else ""


def clean(s, limit=90):
    """Remove terminals' control characters and bound untrusted kernel names."""
    return "".join(c if 32 <= ord(c) <= 126 else "?" for c in s)[:limit]


def parse_cpu(raw):
    for line in raw.splitlines():
        bits = line.split()
        if bits and bits[0] == "cpu":
            try:
                values = [int(x) for x in bits[1:9]]
                if len(values) != 8:
                    break
                return {"total": sum(values), "user": sum(values[0:2]),
                        "system": sum(values[x] for x in (2, 5, 6)),
                        "idle": values[3], "iowait": values[4]}
            except ValueError:
                break
    return {k: 0 for k in ("total", "user", "system", "idle", "iowait")}


def parse_mem(raw):
    data = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                data[parts[0].rstrip(":")] = int(parts[1]) * 1024
            except ValueError:
                continue
    return data


def parse_pressure(raw):
    result = {}
    for line in raw.splitlines():
        bits = line.split()
        if not bits or bits[0] not in ("some", "full"):
            continue
        values = {}
        for item in bits[1:]:
            key, _, val = item.partition("=")
            if key in ("avg10", "avg60", "avg300", "total"):
                try:
                    values[key] = float(val)
                except ValueError:
                    continue
        result[bits[0]] = values
    return result


def parse_disks(raw, names):
    data = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) < 14 or parts[2] not in names:
            continue
        name = parts[2]
        if name.startswith(("loop", "ram", "sr", "zram")):
            continue
        try:
            n = list(map(int, parts[3:14]))
        except ValueError:
            continue
        data[clean(name, 40)] = dict(read_ops=n[0], read_sectors=n[2], read_ms=n[3],
                                     write_ops=n[4], write_sectors=n[6], write_ms=n[7],
                                     weighted_ms=n[10], io_ms=n[9])
    return data


def parse_process(pid):
    stat = read("/proc/%d/stat" % pid, 8192)
    pivot = stat.rfind(")")
    if pivot < 0:
        return None
    try:
        bits = stat[pivot + 2:].split()
        ppid = int(bits[1]); start = int(bits[19]); ticks = int(bits[11]) + int(bits[12])
        state = bits[0]
    except (ValueError, IndexError):
        return None
    name = clean(stat[stat.find("(") + 1:pivot], 60)
    # Raw command line is inspected only for -R; it is never stored or printed.
    recursive = False
    if name in ("chmod", "chown", "chgrp"):
        raw = read("/proc/%d/cmdline" % pid, 4096, binary=True)
        args = raw.split(b"\0")
        recursive = any(a == b"--recursive" or
                        (a.startswith(b"-") and b"R" in a[1:] and a != b"--")
                        for a in args[1:])
    cgroup = read("/proc/%d/cgroup" % pid, 2048)
    match = SERVICE_RE.search(cgroup)
    service = match.group(1) if match else ""
    io = {}
    for line in read("/proc/%d/io" % pid, 2048).splitlines():
        key, sep, val = line.partition(":")
        if sep and key in ("read_bytes", "write_bytes"):
            try:
                io[key] = int(val.strip())
            except ValueError:
                continue
    return dict(pid=pid, ppid=ppid, start=start, ticks=ticks, state=state,
                name=name, service=service, recursive_permissions=recursive,
                wchan=clean(read("/proc/%d/wchan" % pid, 128).strip(), 60), io=io)


def processes():
    try:
        pids = sorted((int(n) for n in os.listdir("/proc") if n.isdecimal()))[:MAX_PROCESSES]
    except OSError:
        return {}
    result = {}
    for pid in pids:
        p = parse_process(pid)
        if p:
            result[(pid, p["start"])] = p
    return result


def snapshot():
    try:
        names = set(os.listdir("/sys/block"))
    except OSError:
        names = set()
    return dict(t=time.monotonic(), cpu=parse_cpu(read("/proc/stat")),
                mem=parse_mem(read("/proc/meminfo")),
                psi=parse_pressure(read("/proc/pressure/io")),
                disks=parse_disks(read("/proc/diskstats", 65536), names),
                procs=processes())


def delta(a, b):
    return max(0, b - a)


def summarize(first, last, samples, hostname=False):
    duration = max(0.001, last["t"] - first["t"])
    c0, c1 = first["cpu"], last["cpu"]
    total = max(1, delta(c0["total"], c1["total"]))
    cpu = {key + "_pct": round(100 * delta(c0[key], c1[key]) / total, 1)
           for key in ("user", "system", "idle", "iowait")}
    disks = []
    for name, end in last["disks"].items():
        start = first["disks"].get(name)
        if not start:
            continue
        w = delta(start["write_ops"], end["write_ops"])
        r = delta(start["read_ops"], end["read_ops"])
        disks.append(dict(device=name, writes_per_s=round(w / duration, 1),
                          reads_per_s=round(r / duration, 1),
                          write_kib_per_s=round(delta(start["write_sectors"], end["write_sectors"]) / 2 / duration, 1),
                          write_await_ms=round(delta(start["write_ms"], end["write_ms"]) / w, 1) if w else 0,
                          read_await_ms=round(delta(start["read_ms"], end["read_ms"]) / r, 1) if r else 0,
                          queue_depth=round(delta(start["weighted_ms"], end["weighted_ms"]) / (1000 * duration), 1),
                          busy_pct=round(delta(start["io_ms"], end["io_ms"]) / (10 * duration), 1)))
    disks.sort(key=lambda d: (d["queue_depth"], d["writes_per_s"]), reverse=True)
    records = {}
    for sample in samples:
        for key, proc in sample["procs"].items():
            item = records.setdefault(key, dict(last=proc, d=0, seen=0, lo_cpu=proc["ticks"],
                                                hi_cpu=proc["ticks"], lo_io={}, hi_io={}))
            item["last"] = proc
            item["seen"] += 1
            item["d"] += proc["state"] == "D"
            item["lo_cpu"] = min(item["lo_cpu"], proc["ticks"])
            item["hi_cpu"] = max(item["hi_cpu"], proc["ticks"])
            for field in ("write_bytes", "read_bytes"):
                v = proc["io"].get(field)
                if v is not None:
                    item["lo_io"][field] = min(item["lo_io"].get(field, v), v)
                    item["hi_io"][field] = max(item["hi_io"].get(field, v), v)
    hz = os.sysconf("SC_CLK_TCK")
    latest_by_pid = {p["pid"]: p for s in samples for p in s["procs"].values()}
    procs = []
    for item in records.values():
        p = item["last"]
        cpu_pct = round(100 * (item["hi_cpu"] - item["lo_cpu"]) / hz / duration, 1)
        write_bps = round((item["hi_io"].get("write_bytes", 0) - item["lo_io"].get("write_bytes", 0)) / duration)
        parent = latest_by_pid.get(p["ppid"])
        entry = dict(pid=p["pid"], ppid=p["ppid"], name=p["name"], service=p["service"],
                     state=p["state"], blocked_samples=item["d"], seen_samples=item["seen"],
                     cpu_pct_one_core=cpu_pct, write_kib_per_s=round(write_bps / 1024, 1),
                     recursive_permissions=p["recursive_permissions"], wchan=p["wchan"],
                     parent_name=parent["name"] if parent else "",
                     parent_service=parent["service"] if parent else "")
        entry["_rank"] = (500 if entry["recursive_permissions"] else 0) + item["d"] * 25 + min(cpu_pct, 300) + min(write_bps / 1048576, 200) * 4
        procs.append(entry)
    procs.sort(key=lambda p: p["_rank"], reverse=True)
    for p in procs:
        del p["_rank"]
    mem = last["mem"]
    findings = []
    if cpu["iowait_pct"] >= 20:
        findings.append("CRITICAL: High CPU I/O wait (%.1f%%)" % cpu["iowait_pct"])
    elif cpu["iowait_pct"] >= 8:
        findings.append("WARNING: Elevated CPU I/O wait (%.1f%%)" % cpu["iowait_pct"])
    full = last["psi"].get("full", {}).get("avg10", 0)
    if full >= 10:
        findings.append("CRITICAL: I/O full pressure %.1f%% (10s average)" % full)
    elif full >= 3:
        findings.append("WARNING: Elevated I/O full pressure %.1f%% (10s average)" % full)
    if "full" not in last["psi"]:
        findings.append("WARNING: I/O pressure data unavailable on this system")
    if not disks:
        findings.append("WARNING: No block-device samples available")
    for disk in disks:
        if disk["queue_depth"] >= 20 or (disk["writes_per_s"] >= 30 and disk["write_await_ms"] >= 30):
            findings.append("CRITICAL: %s write bottleneck, %.0f writes/s, %.1fms latency, queue %.1f" %
                            (disk["device"], disk["writes_per_s"], disk["write_await_ms"], disk["queue_depth"]))
        elif disk["queue_depth"] >= 10 or (disk["writes_per_s"] >= 30 and disk["write_await_ms"] >= 15):
            findings.append("WARNING: %s elevated disk writes, %.0f writes/s, %.1fms latency, queue %.1f" %
                            (disk["device"], disk["writes_per_s"], disk["write_await_ms"], disk["queue_depth"]))
    for p in procs:
        if p["recursive_permissions"]:
            findings.append("SUSPECT: Recursive permissions process PID %d (%s), parent %s, service %s" %
                            (p["pid"], p["name"], p["parent_name"] or "unknown", p["service"] or p["parent_service"] or "unknown"))
            if sum("SUSPECT:" in x for x in findings) >= 3:
                break
    if mem.get("MemTotal", 0):
        memory_ratio = mem.get("MemAvailable", 0) / mem["MemTotal"]
        if memory_ratio < 0.1:
            findings.append("CRITICAL: Available memory below 10%")
        elif memory_ratio < 0.2:
            findings.append("WARNING: Available memory below 20%")
    if not findings:
        findings.append("OK: No obvious bottleneck detected in this short sample")
    result = dict(name="Brightery Server Doctor", version=VERSION,
                  timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                  sample_seconds=round(duration, 2), sample_count=len(samples),
                  logical_cpus=os.cpu_count() or 0, cpu=cpu, load_1_5_15=list(os.getloadavg()),
                  memory_total_bytes=mem.get("MemTotal", 0),
                  memory_available_bytes=mem.get("MemAvailable", 0),
                  swap_used_bytes=max(0, mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)),
                  io_pressure=last["psi"], disks=disks[:12], findings=findings,
                  suspects=procs[:20],
                  note="Snapshot indicates correlation, not definitive causation. No commands or secrets are collected.")
    if hostname:
        result["hostname"] = clean(os.uname().nodename)
    return enrich(result)


def display(result):
    print("Brightery Server Doctor %s | read-only %ss" % (VERSION, result["sample_seconds"]))
    print("Load: %s | CPU I/O wait: %s%% | RAM available: %.1f GiB" %
          (" / ".join("%.1f" % x for x in result["load_1_5_15"]),
           result["cpu"]["iowait_pct"], result["memory_available_bytes"] / 1073741824))
    print("\nFindings:")
    for item in result["findings"]:
        print("  " + item)
    print("\nDisks:")
    for d in result["disks"][:8]:
        print("  %-12s %8.0f writes/s %8.1fms await %6.1f queue %6.1f%% busy" %
              (d["device"], d["writes_per_s"], d["write_await_ms"], d["queue_depth"], d["busy_pct"]))
    print("\nSuspect processes (arguments hidden):")
    for p in result["suspects"][:12]:
        if p["recursive_permissions"] or p["blocked_samples"] or p["cpu_pct_one_core"] >= 10:
            print("  PID %-8s %-17s D=%d/%d CPU=%5.1f%% parent=%s service=%s %s" %
                  (p["pid"], p["name"], p["blocked_samples"], p["seen_samples"],
                   p["cpu_pct_one_core"], p["parent_name"] or "-", p["service"] or p["parent_service"] or "-",
                   "recursive-permissions" if p["recursive_permissions"] else ""))
    print("\nNote: no services, packages, or filesystem permissions changed.")


def save_new_file(path, text):
    # Refuse to overwrite existing files and reject final-component symlinks.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text + "\n")
    except BaseException:
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Privacy-first read-only Linux health dashboard")
    parser.add_argument("--seconds", type=float, default=6, help="duration in seconds (1–120)")
    parser.add_argument("--interval", type=float, default=1, help="sample interval (0.5–5 seconds)")
    views = parser.add_mutually_exclusive_group()
    views.add_argument("--json", action="store_true", help="print structured JSON instead of dashboard")
    views.add_argument("--plain", action="store_true", help="use legacy plain-text output")
    colors = parser.add_mutually_exclusive_group()
    colors.add_argument("--color", action="store_true", help="force ANSI colors (only for dashboard)")
    colors.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--ascii", action="store_true", help="use ASCII borders for limited terminals")
    parser.add_argument("--save", metavar="FILE", help="create a private JSON report (0600; no overwrites)")
    parser.add_argument("--report", metavar="FILE", help="create a private color-free text report (0600)")
    parser.add_argument("--html-report", metavar="FILE", help="create a private offline HTML report (0600)")
    parser.add_argument("--include-hostname", action="store_true", help="include hostname in reports (privacy opt-in)")
    parser.add_argument("--version", action="version", version="brightery-doctor " + VERSION)
    args = parser.parse_args(argv)
    if sys.platform != "linux" or not os.path.exists("/proc/stat"):
        parser.error("Linux with /proc is required")
    if not 1 <= args.seconds <= 120 or not 0.5 <= args.interval <= 5:
        parser.error("--seconds must be 1–120; --interval must be 0.5–5")
    paths = [os.path.abspath(p) for p in (args.save, args.report, args.html_report) if p]
    if len(paths) != len(set(paths)):
        parser.error("Report destinations must use different paths")
    first = snapshot()
    samples = [first]
    finish = first["t"] + args.seconds
    while len(samples) < MAX_SAMPLES:
        remaining = finish - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(max(args.interval, args.seconds / (MAX_SAMPLES - 1)), remaining))
        samples.append(snapshot())
    result = summarize(first, samples[-1], samples, args.include_hostname)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.plain:
        display(result)
    else:
        flag = True if args.color else False if args.no_color else None
        print(render(result, color=flag, ascii_only=args.ascii))
    for path, contents, label in ((args.save, json.dumps(result, indent=2, sort_keys=True), "JSON"),
                                  (args.report, render(result, color=False, ascii_only=args.ascii), "Text"),
                                  (args.html_report, html_report(result), "HTML")):
        if not path:
            continue
        try:
            save_new_file(path, contents)
        except OSError as exc:
            parser.exit(2, "Cannot create report: %s\n" % clean(str(exc), 250))
        print("Private %s report created: %s" % (label, clean(path, 250)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
