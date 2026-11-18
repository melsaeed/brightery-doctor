#!/bin/sh
set -eu
umask 022
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(sed -n 's/^VERSION = "\([0-9][^"]*\)"$/\1/p' "$ROOT/brightery_doctor/cli.py" | head -1)
: "${APT_GPG_KEY_ID:?Set APT_GPG_KEY_ID to your private signing-key fingerprint (key remains outside the repository)}"
for tool in dpkg-scanpackages gpg gzip sha256sum; do command -v "$tool" >/dev/null 2>&1 || { echo "Missing $tool" >&2; exit 1; }; done
DEB="$ROOT/dist/brightery-doctor_${VERSION}_all.deb"
[ -r "$DEB" ] || { echo 'Build the .deb first' >&2; exit 1; }
OUT="$ROOT/docs/apt"
install -d -m 0755 "$OUT/pool/main/b/brightery-doctor" "$OUT/dists/stable/main/binary-all"
cp "$DEB" "$OUT/pool/main/b/brightery-doctor/"
(cd "$OUT" && dpkg-scanpackages -m pool /dev/null > dists/stable/main/binary-all/Packages)
gzip -n -9 -c "$OUT/dists/stable/main/binary-all/Packages" > "$OUT/dists/stable/main/binary-all/Packages.gz"
cd "$OUT"
{
  printf 'Origin: Brightery Doctor\nLabel: Brightery Doctor\nSuite: stable\nCodename: stable\nArchitectures: all\nComponents: main\nDescription: Signed Brightery Doctor APT archive\n'
  printf 'Date: %s\n' "$(LC_ALL=C date -Ru)"
  printf 'SHA256:\n'
  for file in dists/stable/main/binary-all/Packages dists/stable/main/binary-all/Packages.gz; do
    checksum=$(sha256sum "$file" | cut -d ' ' -f 1)
    size=$(wc -c < "$file" | tr -d ' ')
    relative=$(printf '%s' "$file" | sed 's|^dists/stable/||')
    printf ' %s %s %s\n' "$checksum" "$size" "$relative"
  done
} > dists/stable/Release
gpg --batch --yes --local-user "$APT_GPG_KEY_ID" --clearsign --output dists/stable/InRelease dists/stable/Release
gpg --batch --yes --local-user "$APT_GPG_KEY_ID" --armor --detach-sign --output dists/stable/Release.gpg dists/stable/Release
gpg --batch --export "$APT_GPG_KEY_ID" > brightery-doctor-archive-keyring.gpg
[ -s brightery-doctor-archive-keyring.gpg ] || { echo 'Unable to export public key' >&2; exit 1; }
echo 'Signed public APT archive created in docs/apt'
