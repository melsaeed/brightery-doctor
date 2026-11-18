#!/bin/sh
# Build/test a Debian source package locally. No uploads or signing.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=1.2.0+ds-1
for program in git python3 dpkg-buildpackage dpkg-source dpkg-deb dpkg-checkbuilddeps lintian dh dh_python3; do
    command -v "$program" >/dev/null 2>&1 || {
        echo "Required build tool missing: $program" >&2
        echo "On a development VM, run: sudo apt install build-essential debhelper dh-python devscripts lintian dpkg-dev dput gnupg python3 git xz-utils" >&2
        exit 1
    }
done
if ! dpkg-checkbuilddeps "$ROOT/debian/control"; then
    echo "Missing build dependencies. Ubuntu/Debian package dh-python provides virtual dh-sequence-python3." >&2
    exit 1
fi
if grep -Eq 'uploader@example.invalid|YOUR PERSONAL NAME' "$ROOT/debian/control"; then
    echo 'Debian Uploaders human name and email must be supplied first.' >&2
    exit 1
fi
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir "$WORK/out"
"$ROOT/scripts/build-debian-source.sh" "$WORK/out"
DSC="$WORK/out/brightery-doctor_$VERSION.dsc"
[ -s "$DSC" ] || { echo "Missing Debian source package" >&2; exit 1; }
ORIG="$WORK/out/brightery-doctor_1.2.0+ds.orig.tar.xz"
if tar -tf "$ORIG" | grep -E '/(docs/apt/|dist/)|\.(deb|gpg|key|pem)$'; then
    echo "Unexpected binary or signing artifact in Debian upstream source" >&2
    exit 1
fi
lintian --pedantic "$DSC"
dpkg-source -x "$DSC" "$WORK/extracted"
(cd "$WORK/extracted" && dpkg-buildpackage --build=binary -us -uc)
BIN="$WORK/brightery-doctor_${VERSION}_all.deb"
[ -s "$BIN" ] || { echo "Missing binary Debian package" >&2; exit 1; }
lintian --pedantic "$BIN"
dpkg-deb --contents "$BIN" | grep -Fq 'usr/bin/brightery-doctor'
dpkg-deb --contents "$BIN" | grep -Fq 'usr/share/man/man1/brightery-doctor.1.gz'
dpkg-deb --contents "$BIN" | grep -Fq 'usr/lib/python3/dist-packages/brightery_doctor/cli.py'
if ! grep -Eq '\(Closes: #[0-9]+\)' "$ROOT/debian/changelog"; then
    echo 'NOTICE: initial-upload-closes-no-bugs remains until Debian assigns an ITP number. Update changelog and rebuild before upload.' >&2
fi
echo "Passed local source and binary checks. Next: clean Debian unstable sbuild, autopkgtest, and human review."
