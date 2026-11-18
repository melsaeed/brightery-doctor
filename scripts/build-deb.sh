#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=1.1.1
OUT="$ROOT/dist"
mkdir -p "$OUT"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
install -d -m 0755 "$TMP/DEBIAN" "$TMP/usr/bin" "$TMP/usr/lib/python3/dist-packages/brightery_doctor" "$TMP/usr/share/doc/brightery-doctor"
chmod 0755 "$TMP" "$TMP/usr" "$TMP/usr/lib" "$TMP/usr/lib/python3" "$TMP/usr/lib/python3/dist-packages" "$TMP/usr/share" "$TMP/usr/share/doc"
cat > "$TMP/DEBIAN/control" <<EOF
Package: brightery-doctor
Version: $VERSION
Section: admin
Priority: optional
Architecture: all
Maintainer: Brightery Doctor contributors
Depends: python3 (>= 3.8)
Description: Read-only Linux server performance triage
 Diagnose high disk I/O, memory pressure, and suspicious recursive permissions
 operations using only standard Linux procfs and sysfs interfaces.
EOF
install -m 755 "$ROOT/brightery-doctor" "$TMP/usr/bin/brightery-doctor"
sed -i '1c\#!/usr/bin/python3' "$TMP/usr/bin/brightery-doctor"
install -m 644 "$ROOT/brightery_doctor/cli.py" "$TMP/usr/lib/python3/dist-packages/brightery_doctor/cli.py"
install -m 644 "$ROOT/brightery_doctor/__init__.py" "$TMP/usr/lib/python3/dist-packages/brightery_doctor/__init__.py"
install -m 644 "$ROOT/README.md" "$TMP/usr/share/doc/brightery-doctor/README.md"
install -m 644 "$ROOT/LICENSE" "$TMP/usr/share/doc/brightery-doctor/copyright"
dpkg-deb --build --root-owner-group "$TMP" "$OUT/brightery-doctor_${VERSION}_all.deb"
echo "Built $OUT/brightery-doctor_${VERSION}_all.deb"
