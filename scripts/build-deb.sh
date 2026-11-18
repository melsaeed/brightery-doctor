#!/bin/sh
set -eu
umask 022
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(sed -n 's/^VERSION = "\([0-9][^"]*\)"$/\1/p' "$ROOT/brightery_doctor/cli.py" | head -1)
[ -n "$VERSION" ] || { echo 'Cannot determine version' >&2; exit 1; }
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
Description: Read-only Linux health dashboard and server diagnostics
 Displays color-coded server health and detects storage saturation,
 memory pressure, and recursive permission operations. Produces
 offline HTML, text and JSON reports with no background agent.
EOF
install -m 755 "$ROOT/brightery-doctor" "$TMP/usr/bin/brightery-doctor"
sed -i '1c\#!/usr/bin/python3' "$TMP/usr/bin/brightery-doctor"
for name in cli.py dashboard.py report.py __init__.py; do
  install -m 644 "$ROOT/brightery_doctor/$name" "$TMP/usr/lib/python3/dist-packages/brightery_doctor/$name"
done
install -m 644 "$ROOT/README.md" "$TMP/usr/share/doc/brightery-doctor/README.md"
install -m 644 "$ROOT/LICENSE" "$TMP/usr/share/doc/brightery-doctor/copyright"
dpkg-deb --build --root-owner-group "$TMP" "$OUT/brightery-doctor_${VERSION}_all.deb"
echo "Built $OUT/brightery-doctor_${VERSION}_all.deb"
