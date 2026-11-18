#!/bin/sh
# Create signed public archive metadata; private GPG keys must stay off-repository.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APT_GPG_KEY_ID=$(printenv APT_GPG_KEY_ID || true)
[ -n "$APT_GPG_KEY_ID" ] || { echo 'Set APT_GPG_KEY_ID to your dedicated signing key fingerprint' >&2; exit 1; }
for binary in dpkg-scanpackages gpg gzip sha256sum; do command -v "$binary" >/dev/null; done
DEB="$ROOT/dist/brightery-doctor_1.1.1_all.deb"
[ -r "$DEB" ] || { echo 'Run scripts/build-deb.sh first' >&2; exit 1; }
OUT="$ROOT/docs/apt"
mkdir -p "$OUT/pool/main/b/brightery-doctor" "$OUT/dists/stable/main/binary-all"
cp "$DEB" "$OUT/pool/main/b/brightery-doctor/"
(cd "$OUT" && dpkg-scanpackages -m pool /dev/null > dists/stable/main/binary-all/Packages)
gzip -n -9 -c "$OUT/dists/stable/main/binary-all/Packages" > "$OUT/dists/stable/main/binary-all/Packages.gz"
cd "$OUT"
{
  printf 'Origin: Brightery Doctor\nLabel: Brightery Doctor\nSuite: stable\nCodename: stable\nArchitectures: all\nComponents: main\nDescription: Signed Brightery Doctor APT archive\n'
  printf 'Date: %s\n' "$(LC_ALL=C date -Ru)"
  printf 'SHA256:\n'
  for p in dists/stable/main/binary-all/Packages dists/stable/main/binary-all/Packages.gz; do
    checksum=$(sha256sum "$p" | cut -d ' ' -f 1)
    size=$(wc -c < "$p" | tr -d ' ')
    relative=$(printf '%s' "$p" | sed 's|^dists/stable/||')
    printf ' %s %s %s\n' "$checksum" "$size" "$relative"
  done
} > dists/stable/Release
gpg --batch --yes --local-user "$APT_GPG_KEY_ID" --clearsign --output dists/stable/InRelease dists/stable/Release
gpg --batch --yes --local-user "$APT_GPG_KEY_ID" --armor --detach-sign --output dists/stable/Release.gpg dists/stable/Release
gpg --batch --export "$APT_GPG_KEY_ID" > brightery-doctor-archive-keyring.gpg
[ -s brightery-doctor-archive-keyring.gpg ] || { echo 'Public key export failed' >&2; exit 1; }
echo 'Signed APT archive generated in docs/apt; verify and publish public files only.'
