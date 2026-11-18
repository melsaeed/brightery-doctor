# Brightery Doctor

Read-only Linux/Ubuntu server diagnosis, using only Python 3's standard library. Designed to surface I/O saturation, blocked `D`-state tasks, high CPU wait, memory pressure, and recursive permission jobs with their parent service.

## Safety model

- **No network access**, no subprocess execution, no service restarts, no cleanup, no installation of dependencies while scanning.
- Process **command-line arguments and environment variables are never recorded**. Hostname is excluded by default. Output contains process and service names/PIDs, which can still be identifying; review reports before sharing.
- `--save` is the only scan option that writes a file. It creates a fresh report with mode `0600`, refuses existing files and final-component symlinks. Use a trusted directory; do not write as root into a directory controlled by other users.
- Bounded sampling: 120-second limit, at most 8,192 process entries per sample and 241 samples. Best-effort attribution—not proof of causation. The tool does not require root; non-root users may see less detail.
- No persistent agent, server, open port, remote API, or auto-update feature.

## Usage from source

```bash
python3 brightery-doctor --seconds 6
python3 brightery-doctor --seconds 15 --json
python3 brightery-doctor --seconds 10 --save /root/doctor-report.json
```

## Build and install a local Debian package

On Debian/Ubuntu with `dpkg-deb` installed:

```bash
python3 -m unittest discover -s tests -v
./scripts/build-deb.sh
sudo apt install ./dist/brightery-doctor_1.1.0_all.deb
brightery-doctor --seconds 6
```

**`apt install brightery-doctor` without `./...` requires a configured APT repository.** Merely publishing code to GitHub does not register a package in Ubuntu/Debian's official repositories. We provide a script to generate a **signed** static repository on GitHub Pages; see [APT_REPOSITORY.md](APT_REPOSITORY.md). It must be published by the repository maintainer with an independently managed GPG signing key before the remote APT installation works.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile brightery_doctor/cli.py
```

Issues and security reports: see [SECURITY.md](SECURITY.md). Licensed under MIT.
