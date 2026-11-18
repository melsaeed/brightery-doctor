# Signed APT repository

Published files: `docs/apt/`, including the signed `InRelease`, public archive key, `Packages.gz` and `.deb`. **Never commit signing private keys, secrets or passphrases.**

## Repository signing fingerprint

`E63D3954E4532650A0DA2865070CB56B2FF393C7`

Verify the fingerprint independently against a maintainer announcement. The archive signing key must remain on a trusted, offline or secured maintainer workstation, not a production VPS or GitHub Actions. Anyone with the private key can publish trusted updates.

## One-time Ubuntu installation

```bash
set -e
BASE=https://raw.githubusercontent.com/melsaeed/brightery-doctor/main/docs/apt
EXPECTED=E63D3954E4532650A0DA2865070CB56B2FF393C7
curl -fsSL "$BASE/brightery-doctor-archive-keyring.gpg" -o /tmp/brightery-doctor-keyring.gpg
ACTUAL=$(gpg --batch --with-colons --show-keys /tmp/brightery-doctor-keyring.gpg | awk -F: '$1 == "fpr" {print $10; exit}')
[ "$EXPECTED" = "$ACTUAL" ] || { echo "Signing fingerprint mismatch" >&2; exit 1; }
sudo install -d -m 0755 /etc/apt/keyrings
sudo install -m 0644 /tmp/brightery-doctor-keyring.gpg /etc/apt/keyrings/brightery-doctor.gpg
printf 'deb [arch=all signed-by=/etc/apt/keyrings/brightery-doctor.gpg] %s stable main\n' "$BASE" | sudo tee /etc/apt/sources.list.d/brightery-doctor.list
sudo apt update
sudo apt install brightery-doctor
```

Subsequent versions use ordinary `sudo apt update && sudo apt upgrade`.

## Maintainer release process

1. Test and review the complete source; bump `VERSION` in `brightery_doctor/cli.py`.
2. On a **trusted build machine**, run `python3 -m unittest discover -s tests -v` and `./scripts/build-deb.sh`.
3. Ensure your **private signing key** is loaded in a separate, protected GnuPG home. Then run `APT_GPG_KEY_ID=E63D3954E4532650A0DA2865070CB56B2FF393C7 ./scripts/build-apt-repo.sh`.
4. Verify signatures, hashes and package contents, and test in a clean APT sandbox before publishing.
5. Commit public `docs/apt/` metadata and package bytes to `main`. Preserve old archive objects for rollbacks where desired.
6. Keep the encrypted private-key backup protected separately from its decryption passphrase, and never include either in repository files.

GitHub Pages can optionally serve the same archive from `https://melsaeed.github.io/brightery-doctor/apt`, once enabled in repository settings. The direct raw.githubusercontent.com address works without Pages.

Do not bypass signature verification with `trusted=yes` or `allow-insecure=yes`.
