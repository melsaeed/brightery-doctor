"""Offline HTML status report. No JavaScript, remote assets or server."""
import html
from .dashboard import enrich


STYLES = """
:root {color-scheme:light; --bg:#f5f7fb; --ink:#1b2638; --muted:#617083; --edge:#dce3ed;
--good:#147b52; --warn:#a86407; --bad:#b32632; --card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Arial,sans-serif}
main{max-width:1100px;margin:auto;padding:38px 24px 70px}header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:20px;margin-bottom:26px}
h1{font-size:30px;letter-spacing:-.7px;margin:0}.lead{color:var(--muted);margin:4px 0}.tag{font-weight:800;border-radius:999px;padding:9px 15px;border:1px solid currentColor}
.healthy{color:var(--good)}.warning{color:var(--warn)}.critical{color:var(--bad)}.tag.healthy{background:#e9f8f0}.tag.warning{background:#fff3df}.tag.critical{background:#ffebef}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:14px}.card,section{background:var(--card);border:1px solid var(--edge);border-radius:18px;padding:22px;box-shadow:0 4px 16px #26364d08}
.metric{font-size:29px;font-weight:800;letter-spacing:-.7px;margin:8px 0 3px}.label{font-size:13px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.desc{color:var(--muted);font-size:13px}section{margin-top:22px}h2{font-size:19px;margin:0 0 16px}table{border-collapse:collapse;width:100%;text-align:left}th,td{padding:11px 10px;border-bottom:1px solid #edf0f5}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.4px}tbody tr:last-child td{border-bottom:0}
.finding{margin:8px 0;border-left:4px solid var(--edge);padding:11px 13px;background:#f8fafc;border-radius:8px;overflow-wrap:anywhere}.finding.warning{border-color:#df980d}.finding.critical{border-color:#c33a43}.finding.healthy{border-color:#249666}
footer{margin-top:20px;color:var(--muted);font-size:13px}code{font-family:ui-monospace,Consolas,monospace} .scroll{overflow-x:auto}td{overflow-wrap:anywhere}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#101721;--ink:#ecf1f7;--muted:#a3b0c0;--edge:#344357;--card:#182333;--good:#71dca4;--warn:#ffc06c;--bad:#ff8793}
.tag.healthy{background:#15382c}.tag.warning{background:#4a3318}.tag.critical{background:#4b212a}th,td{border-bottom-color:#344357}.finding{background:#212f40}}
@media print{main{padding:10px}body{background:white}section,.card{box-shadow:none;break-inside:avoid}}"""


def e(value):
    return html.escape(str(value), quote=True)


def level_for(finding):
    return "critical" if finding.startswith("CRITICAL:") else "warning" if finding.startswith(("WARNING:", "SUSPECT:")) else "healthy"


def html_report(result):
    data = result if "checks" in result else enrich(result)
    level = data["health"]
    checks = "".join(
        '<article class="card"><div class="label">{name}</div><div class="metric {level}">{value}</div><div class="desc">{detail}</div></article>'.format(
            name=e(c["name"]), level=e(c["severity"]), value=e(c["value"]), detail=e(c["detail"]))
        for c in data.get("checks", []))
    load = data.get("load_1_5_15", [0,0,0])
    extra = '<article class="card"><div class="label">System load (1 / 5 / 15 min)</div><div class="metric">{load}</div><div class="desc">{cores} logical CPUs</div></article>'.format(
        load=" / ".join("%.1f" % v for v in load), cores=e(data.get("logical_cpus", "N/A")))
    disk_rows = "".join(
        '<tr><td><code>{device}</code></td><td>{writes:.0f}</td><td>{latency:.1f} ms</td><td>{queue:.1f}</td><td>{busy:.1f}%</td></tr>'.format(
            device=e(d["device"]),writes=d["writes_per_s"],latency=d["write_await_ms"],queue=d["queue_depth"],busy=d["busy_pct"])
        for d in data.get("disks", [])[:12]) or '<tr><td colspan="5">No block-device data available</td></tr>'
    findings = "".join('<p class="finding {level}">{message}</p>'.format(level=level_for(f), message=e(f)) for f in data.get("findings", []))
    procs = [p for p in data.get("suspects", []) if p["recursive_permissions"] or p["blocked_samples"] or p["cpu_pct_one_core"] >= 10][:12]
    proc_rows = "".join('<tr><td>{pid}</td><td><code>{name}</code></td><td>{cpu:.1f}%</td><td>{blocked}/{seen}</td><td><code>{service}</code></td></tr>'.format(
        pid=int(p["pid"]), name=e(p["name"]), cpu=float(p["cpu_pct_one_core"]),
        blocked=int(p["blocked_samples"]), seen=int(p["seen_samples"]), service=e(p.get("service") or p.get("parent_service") or "unknown")) for p in procs)
    if not proc_rows:
        proc_rows = '<tr><td colspan="5">No unusually active or blocked processes in this sample</td></tr>'
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>Brightery Doctor — Read-only Health Report</title><style>{css}</style></head><body><main>
<header><div><h1>Brightery Doctor <small>v{version}</small></h1><p class="lead">Server health · {time} UTC · {duration:.1f}-second sample</p></div>
<div class="tag {status}">{status_text}</div></header>
<div class="grid">{extra}{checks}</div>
<section><h2>Findings</h2>{findings}</section>
<section><h2>Disk activity</h2><div class="scroll"><table><thead><tr><th>Device</th><th>Writes/s</th><th>Write latency</th><th>Queue depth</th><th>Busy</th></tr></thead><tbody>{disks}</tbody></table></div></section>
<section><h2>Notable processes (arguments hidden)</h2><div class="scroll"><table><thead><tr><th>PID</th><th>Process</th><th>CPU (one core)</th><th>Blocked samples</th><th>Service</th></tr></thead><tbody>{procs}</tbody></table></div></section>
<footer>Read-only point-in-time diagnosis. Correlation does not establish root cause. No files, services, packages, or permissions were modified by the scan. Review reports before sharing.</footer>
</main></body></html>""".format(css=STYLES,version=e(data.get("version", "")),time=e(data.get("timestamp_utc", "")),
                       duration=data.get("sample_seconds", 0), status=e(level),status_text=e(level.upper()),
                       extra=extra,checks=checks,findings=findings,disks=disk_rows,procs=proc_rows)
