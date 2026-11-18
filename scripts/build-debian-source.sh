#!/bin/sh
# Create unsigned Debian source packages without prebuilt binaries or APT keys.
set -eu
umask 077
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
UPSTREAM_VERSION=1.2.0
SOURCE_VERSION=1.2.0+ds
UPSTREAM_REF=$(printenv UPSTREAM_REF || true)
[ -n "$UPSTREAM_REF" ] || UPSTREAM_REF=b16f442d65add29a5aa094ef9e8eaf6e51f9eebf
if [ "$#" -gt 0 ]; then OUT=$1; else OUT="$ROOT/../debian-build"; fi
for tool in git tar dpkg-buildpackage python3; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing build tool: $tool" >&2; exit 1; }
done
if grep -q 'your-email@example.invalid' "$ROOT/debian/control" "$ROOT/debian/changelog"; then
    echo 'Replace placeholder Maintainer identity in debian/control and debian/changelog before building.' >&2
    exit 1
fi
if ! git -C "$ROOT" cat-file -e "$UPSTREAM_REF^{commit}" 2>/dev/null; then
    echo "Missing upstream Git commit/tag: $UPSTREAM_REF" >&2
    exit 1
fi
(cd "$ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
BASE="brightery-doctor-$SOURCE_VERSION"
git -C "$ROOT" archive --format=tar --prefix="$BASE/" "$UPSTREAM_REF" | tar -xf - -C "$WORK"
test -r "$WORK/$BASE/brightery_doctor/cli.py"
rm -rf "$WORK/$BASE/debian" "$WORK/$BASE/docs/apt" "$WORK/$BASE/dist"
EPOCH=$(git -C "$ROOT" log -1 --format=%ct "$UPSTREAM_REF")
tar -C "$WORK" --sort=name --mtime="@$EPOCH" --owner=0 --group=0 --numeric-owner \
    -cJf "$WORK/brightery-doctor_$SOURCE_VERSION.orig.tar.xz" "$BASE"
cp -R "$ROOT/debian" "$WORK/$BASE/debian"
(cd "$WORK/$BASE" && dpkg-buildpackage -S -sa -us -uc)
mkdir -p "$OUT"
find "$WORK" -maxdepth 1 -type f -name "brightery-doctor_$SOURCE_VERSION*" \
    -exec cp -v {} "$OUT/" \;
printf '\nUnsigned source package saved to: %s\n' "$OUT"
echo 'Review lintian and a clean Debian unstable build before signing.'
echo 'Sign using your personal key: debsign -k YOUR_PERSONAL_KEY_FINGERPRINT <source.changes>'
