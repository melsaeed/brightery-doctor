# Brightery Doctor signed APT repository

**Status:** Version 1.1.1 repository files are signed and published under `docs/apt`. GitHub Pages activation may require the repository owner to enable `Settings → Pages → Deploy from a branch → main /docs`.

**Signing key fingerprint:** `E63D3954E4532650A0DA2865070CB56B2FF393C7`

The private archive signing key must **never** be committed, placed on a production server, or made publicly accessible. Safeguard your encrypted backup offline. Confirm the full fingerprint from a trusted maintainer announcement independent of the downloaded key.

## Install (GitHub raw endpoint)

GitHub raw hosting provides a direct URL even before GitHub Pages is configured. On Ubuntu or Debian:

```bash
set -e
BASE=https://raw.githubusercontent.com/melsaeed/brightery-doctor/main/docs/apt
curl -fsSL "$BASE/brightery-doctor-archive-keyring.gpg" -o /tmp/brightery-doctor-keyring.gpg
gpg --show-keys --with-fingerprint /tmp/brightery-doctor-keyring.gpg
# STOP: compare the displayed fingerprint with the trusted fingerprint above before continuing.
sudo install -d -m 0755 /etc/apt/keyrings
sudo install -m 0644 /tmp/brightery-doctor-keyring.gpg /etc/apt/keyrings/brightery-doctor.gpg
printf 'deb [arch=all signed-by=/etc/apt/keyrings/brightery-doctor.gpg] %s stable main\n' "$BASE" | sudo tee /etc/apt/sources.list.d/brightery-doctor.list
sudo apt update
sudo apt install brightery-doctor
```

This configures the third-party APT source once. Subsequent updates use `sudo apt update && sudo apt install --only-upgrade brightery-doctor`. Do not use `trusted=yes` or `allow-insecure=yes`.

## GitHub Pages (preferred for production)

1. In the repository settings, select **Pages → Deploy from a branch**, branch `main`, folder `/docs`.
2. Verify `https://melsaeed.github.io/brightery-doctor/apt/dists/stable/InRelease` and `https://melsaeed.github.io/brightery-doctor/apt/brightery-doctor-archive-keyring.gpg`.
3. Replace the source URL in `/etc/apt/sources.list.d/brightery-doctor.list` with `https://melsaeed.github.io/brightery-doctor/apt`. Keep the same `signed-by` setting.

## Maintainer releases

On a trusted maintainer workstation that holds the signing key **outside the repo**:

```bash
python3 -m unittest discover -s tests -v
./scripts/build-deb.sh
APT_GPG_KEY_ID=YOUR_40_CHARACTER_FINGERPRINT ./scripts/build-apt-repo.sh
gpg --verify docs/apt/dists/stable/InRelease
dpkg-deb --contents dist/brightery-doctor_1.1.1_all.deb
git add docs/apt
git diff --cached --stat
git commit -m 'Publish signed APT archive'
git push origin main
```

Increase `VERSION` in `brightery_doctor/cli.py` and package version constants in both build scripts for each upgrade; remove obsolete packages from the pool before regeneration as needed. Never store the private key in GitHub, GitHub Actions, or an untrusted VPS. Use manual release signing without GitHub Actions.

Signing is a supply-chain control, not a promise that software contains no vulnerabilities. Review changes and tests before signing.
