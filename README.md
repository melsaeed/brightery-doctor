# Brightery Doctor

**Read-only, dependency-free Linux server health dashboard.** Ubuntu/Debian, Python 3 standard library, no web service or open ports, no third-party Python dependencies. Public MIT-licensed source.

## Example

```text
╭─────────────────────────────────────────────────────────────────────────╮
│ BRIGHTERY DOCTOR  v1.2.0  |  READ-ONLY HEALTH REPORT                    │
│ ● HEALTHY   No significant bottleneck detected in this sample           │
├─────────────────────────────────────────────────────────────────────────┤
│ SERVER OVERVIEW                                                         │
│   ●  CPU I/O wait     1.5%                                              │
│   ●  Available RAM    16.8 GiB                                          │
│   ●  I/O pressure     0.0%                                              │
│   ●  Disk bottleneck  sda · 3.5 ms                                      │
╰─────────────────────────────────────────────────────────────────────────╯
```

Colors are green for healthy, amber for warnings, red for critical. Colors are enabled for interactive terminals and disabled for pipes, `NO_COLOR`, or `--no-color`. `--color` forces ANSI coloring. `--ascii` uses ASCII borders.

## Install via signed APT

See [APT_REPOSITORY.md](APT_REPOSITORY.md). The repository uses an explicitly scoped signing key; verify fingerprint `E63D3954E4532650A0DA2865070CB56B2FF393C7` out of band. Once the repository is configured:

```bash
sudo apt update
sudo apt install brightery-doctor
```

## Run

```bash
brightery-doctor                          # color dashboard on SSH/TTY
brightery-doctor --seconds 15             # longer sample (max 120s)
brightery-doctor --no-color --ascii       # no ANSI or Unicode box drawing
brightery-doctor --plain                  # legacy text report
brightery-doctor --json                   # machine-readable report
brightery-doctor --save /root/check.json  # private JSON report (0600)
brightery-doctor --report /root/check.txt # private text report (0600)
brightery-doctor --html-report /root/check.html # offline HTML dashboard (0600)
```

Open the HTML file on a trusted computer to view cards, warnings and status colors. The report requires **no network**, JavaScript, fonts, images, backend, or browser plugins; Content Security Policy blocks external resources. Share reports only after reviewing process/service identifiers.

### Interpretation

* **HEALTHY (green)** — current scan finds no significant bottleneck.
* **WARNING (amber)** — elevated latency/pressure, suspicious recursive permission operations, or missing telemetry.
* **CRITICAL (red)** — severe disk latency/queue, I/O wait, memory pressure, or stall pressure.

Thresholds are heuristics, not guarantees. `write_await_ms` measures observed device latency; it does not mean every 1-second spike is caused by a single process. One snapshot cannot diagnose past incidents after they end. High `busy_pct` alone does not prove saturation.

### Security model

* Does not execute commands, contact the network, alter services, open ports, or restart anything.
* Process arguments and environments are never included in reports. For `chmod`, `chown`, and `chgrp`, only a limited read of `/proc/PID/cmdline` checks for the recursive flag and is never retained or displayed.
* No hostname by default; `--include-hostname` explicitly opts in.
* Report writes use mode `0600`, refuse existing destinations and final-component symlinks. Save reports only inside a trusted directory.
* Max 120-second scan, 41 samples, 4,096 process entries per sample. Non-root is preferable where sufficient.

## Build and test

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q brightery_doctor
./scripts/build-deb.sh
sudo apt install ./dist/brightery-doctor_1.2.0_all.deb
```

Signing and publishing a new package requires the **dedicated private APT key**, kept off GitHub; see [APT_REPOSITORY.md](APT_REPOSITORY.md). No GitHub Actions workflows are required.

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Official Debian and Ubuntu archive submission

Debian-standard source packaging is in `debian/`, with a source-only build helper and a submission guide in [DEBIAN_MENTORS.md](DEBIAN_MENTORS.md). **Not yet accepted into Debian or Ubuntu.** A real maintainer identity, ITP bug, clean build/lintian checks, personal OpenPGP key, and sponsoring Debian Developer are still required. The existing signed APT repository uses a **different archive key**.

### Debian Maintainer identity

Official-archive packaging lists **Brightery <support@brightery.com>** as the Maintainer, and lists **Muhammad Elsaeed <m.elsaeed@brightery.com>** as the human `Uploaders` identity required for team-maintained packages. See [DEBIAN_MENTORS.md](DEBIAN_MENTORS.md) for the remaining signing and submission steps. This does not affect the existing signed APT package.
