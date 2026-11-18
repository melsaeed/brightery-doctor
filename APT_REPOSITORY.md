# Signed APT repository deployment

**Current status:** Packaging and signed-repository generation tools are provided. A public APT endpoint does **not** exist until a maintainer creates a signing key, generates archive metadata, publishes the resulting `docs/apt` directory, and enables GitHub Pages. Never use `trusted=yes` or `[allow-insecure=yes]` as a shortcut.

1. On a **maintainer-controlled offline or secured workstation**, generate a dedicated signing key (never on a public server or in this repository):

   ```bash
   gpg --quick-generate-key 'Brightery Doctor Archive' ed25519 sign 1y
   gpg --list-keys --fingerprint
   ```

2. Verify the key fingerprint. Backup the **private key** separately in encrypted offline storage. Do **not** commit private keys, GNUPGHOME, credentials, or passphrases.
3. Build and sign the archive from a reviewed, tagged release:

   ```bash
   ./scripts/build-deb.sh
   APT_GPG_KEY_ID=YOUR_40_HEX_FINGERPRINT ./scripts/build-apt-repo.sh
   gpg --verify docs/apt/dists/stable/InRelease
   ```

   The script writes only public signed metadata, package bytes and the **public** key into `docs/apt`. Review these files and the signing fingerprint before committing.
4. Enable GitHub Pages for the repository with source `main` and folder `/docs`; allow time for the Pages endpoint to publish. The desired APT base URL is `https://melsaeed.github.io/brightery-doctor/apt/`. Confirm that HTTPS, the Packages file, InRelease and key all return valid content.
5. On an Ubuntu machine, **independently verify** the public key's full fingerprint against a maintainer-announced value, and install it with restrictive permissions:

   ```bash
   curl -fL https://melsaeed.github.io/brightery-doctor/apt/brightery-doctor-archive-keyring.gpg -o /tmp/brightery-doctor-archive-keyring.gpg
   gpg --show-keys --with-fingerprint /tmp/brightery-doctor-archive-keyring.gpg
   sudo install -m 644 /tmp/brightery-doctor-archive-keyring.gpg /usr/share/keyrings/brightery-doctor-archive-keyring.gpg
   echo 'deb [arch=all signed-by=/usr/share/keyrings/brightery-doctor-archive-keyring.gpg] https://melsaeed.github.io/brightery-doctor/apt stable main' | sudo tee /etc/apt/sources.list.d/brightery-doctor.list
   sudo apt update
   sudo apt install brightery-doctor
   ```

Do not perform these installation commands until the maintainer has verified and published the archive and fingerprint. The public key fetched from the same site is **not** a sufficient independent trust anchor; confirm its fingerprint out of band. Keep the signing private key off the webserver and rotate it carefully, with advance notice to users.

**No GitHub Actions workflows are needed**. Publication can be performed manually from a trusted maintainer workstation.
