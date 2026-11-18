#!/bin/sh
# Upload a vetted source-only Debian package to Debian Mentors.
# Run only from your trusted workstation, with your personal OpenPGP key.
# This intentionally stops before uploading if signing fails.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
KEY_ID=$(printf '%s' "${1-}")
if [ -z "$KEY_ID" ]; then
    echo 'Usage: scripts/sign-upload-mentors.sh PERSONAL_GPG_FINGERPRINT' >&2
    exit 2
fi
case "$KEY_ID" in
    *[!a-fA-F0-9]*)
        echo 'Expected a hexadecimal OpenPGP fingerprint (no spaces)' >&2
        exit 2 ;;
esac
case "$KEY_ID" in
    ????????????????????????????????????????) ;;
    *) echo 'Expected the full 40-character personal OpenPGP fingerprint' >&2; exit 2 ;;
esac
if grep -Eq 'uploader@example.invalid|YOUR PERSONAL NAME' "$ROOT/debian/control"; then
    echo 'Set a real human Uploaders identity first (Debian Policy §5.6.3)' >&2
    exit 2
fi
if ! grep -Eq '\(Closes: #[0-9]+\)' "$ROOT/debian/changelog"; then
    echo 'An initial Debian upload must close a real ITP bug: add (Closes: #NUMBER) to debian/changelog, rebuild and revalidate before signing.' >&2
    exit 2
fi
for tool in debsign dput gpg; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "Missing required program: $tool" >&2
        exit 2
    }
done
CHANGES="$ROOT/../debian-build/brightery-doctor_1.2.0+ds-1_source.changes"
[ -r "$CHANGES" ] || {
    echo 'Build and validate the source package first with scripts/build-debian-source.sh' >&2
    exit 2
}
if ! gpg --batch --list-secret-keys "$KEY_ID" >/dev/null 2>&1; then
    echo 'Personal OpenPGP private key not found. Do not use the public-only key or the APT archive key.' >&2
    exit 2
fi

echo 'Confirm you have reviewed the source package and ITP/changelog before upload.'
echo 'This will SIGN and UPLOAD the source package to Debian Mentors.'
echo 'Press Ctrl+C to cancel, or Enter to continue.'
read -r confirmation
debsign -k "$KEY_ID" "$CHANGES"
dput mentors "$CHANGES"
echo 'Upload requested. Check Debian Mentors for acceptance and request a sponsor.'
