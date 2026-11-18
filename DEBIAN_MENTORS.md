# Brightery Doctor — Debian Mentors packaging and submission

**Status:** Packaging is prepared in `debian/`, but the package has **not** been accepted into Debian or Ubuntu. A real maintainer identity, an ITP bug number, a signed upload, and sponsor review are still required. The package has not yet been checked by lintian or a clean Debian unstable sbuild.

## Personal OpenPGP key

Create a personal key using the email registered with Debian Mentors. This is **not** the Brightery Doctor APT archive signing key.

```bash
gpg --full-generate-key
gpg --list-secret-keys --keyid-format LONG --with-fingerprint
gpg --armor --export YOUR_PERSONAL_KEY_FINGERPRINT > debian-mentors-public.asc
```

Paste the complete **public** key into https://mentors.debian.net/accounts/profile/. Never publish your private key.

## Prepare a development machine

Use a clean Debian unstable VM or container; do not build or sign on a production VPS.

```bash
sudo apt update
sudo apt install git devscripts build-essential debhelper dh-sequence-python3 python3 lintian dput reportbug dpkg-dev
git clone https://github.com/melsaeed/brightery-doctor.git
cd brightery-doctor
```

Replace the placeholder `YOUR REAL NAME <your-email@example.invalid>` **in both** `debian/control` and `debian/changelog` with your actual name and reachable, key-associated email. Do not upload packages with placeholders.

## File an ITP and tag the upstream release

Check https://www.debian.org/devel/wnpp/ and the Debian package tracker for an existing package. If none exists, run `reportbug wnpp`, select **ITP**, and describe the upstream version 1.2.0, the Expat/MIT license, https://github.com/melsaeed/brightery-doctor and the Linux diagnostic purpose.

Once assigned an ITP bug number, add `(Closes: #NUMBER)` to the initial entry in `debian/changelog`.

The upstream GitHub release tag `v1.2.0` should point at the audited upstream commit **b16f442d65add29a5aa094ef9e8eaf6e51f9eebf**, not a later commit containing Debian packaging changes:

```bash
git tag -a v1.2.0 b16f442d65add29a5aa094ef9e8eaf6e51f9eebf -m 'Brightery Doctor 1.2.0'
git push origin v1.2.0
```

## Build and validate a source package

Debian Policy version targeted: 4.7.4; source format: `3.0 (quilt)`; Debian revision: `1.2.0+ds-1`. The `+ds` signifies that APT repository metadata, binary packages, and public archive signing materials are excluded from the source tarball.

```bash
./scripts/build-debian-source.sh
cd ../debian-build
dpkg-source -x brightery-doctor_1.2.0+ds-1.dsc
cd brightery-doctor-1.2.0+ds
dpkg-buildpackage -us -uc -b
cd ..
lintian --pedantic --display-info brightery-doctor_1.2.0+ds-1_*.changes
```

Also validate with sbuild or pbuilder against Debian unstable, run an autopkgtest, inspect the Debian binary contents, and review lintian errors or warnings. The source-only build script runs upstream unit tests but **does not** replace clean binary-build testing.

## Sign and upload to Mentors

Sign with the personal key registered on mentors.debian.net, never the APT archive key:

```bash
debsign -k YOUR_PERSONAL_KEY_FINGERPRINT ../debian-build/brightery-doctor_1.2.0+ds-1_source.changes
```

Configure `~/.dput.cf`:

```ini
[mentors]
fqdn = mentors.debian.net
incoming = /upload
method = https
allow_unsigned_uploads = 0
progress_indicator = 2
allowed_distributions = .*
```

```bash
dput mentors ../debian-build/brightery-doctor_1.2.0+ds-1_source.changes
```

After the upload appears on Debian Mentors, enable **Needs a Sponsor**, use the site's RFS template to file a `sponsorship-requests` bug, and resolve sponsor feedback. New packages also require Debian archive NEW-queue review.

Official instructions: https://mentors.debian.net/intro-maintainers/
Debian Policy: https://www.debian.org/doc/debian-policy/
Copyright format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
