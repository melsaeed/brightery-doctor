# Brightery Doctor — Debian Mentors packaging and submission

**Status:** Packaging is prepared in `debian/`, but the package has **not** been accepted into Debian or Ubuntu. Debian acknowledged [ITP #1154410](https://bugs.debian.org/1154410) on 18 November 2026. Local Ubuntu source/binary builds, 16 unit tests, and lintian checks passed before the ITP reference was added. The signed initial source upload is listed on Mentors and the v1.2.0 tag has been verified. The following packaging-only improvements respond to Mentors QA; a replacement upload, clean Debian unstable testing and sponsor review remain pending.

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
sudo apt install git devscripts build-essential debhelper dh-python python3 lintian dput reportbug dpkg-dev xz-utils
git clone https://github.com/melsaeed/brightery-doctor.git
cd brightery-doctor
```

The source **Maintainer** is `Brightery <support@brightery.com>` and **Uploaders** is `Muhammad Elsaeed <m.elsaeed@brightery.com>`. The Debian changelog trailer also names Muhammad Elsaeed as the release preparer (`Changed-By`), as Debian Policy expects. Confirm that the personal OpenPGP key registered on Debian Mentors has an appropriate UID for `m.elsaeed@brightery.com`. Never substitute the dedicated archive signing key for the personal key.

## Registered ITP and upstream release

**Already filed: [Debian ITP #1154410](https://bugs.debian.org/1154410).** Do not file a duplicate. The initial changelog now contains `(Closes: #1154410)`. The following reportbug instructions are retained for reference only.

Check https://www.debian.org/devel/wnpp/ and the Debian package tracker for an existing package. If none exists, file an **ITP** for upstream version 1.2.0, the Expat/MIT license, https://github.com/melsaeed/brightery-doctor and the Linux diagnostic purpose.

**On Ubuntu hosts**, `reportbug` defaults to the Ubuntu bug system, which is unsupported by this tool. Explicitly direct it to Debian with `-B debian`. In novice mode, querying WNPP may enumerate thousands of unrelated reports; after checking that no ITP for `brightery-doctor` already exists, pass `--no-query-bts` to skip that enormous interactive listing:

```sh
reportbug -B debian --no-query-bts \
  --realname "Muhammad Elsaeed" \
  --email m.elsaeed@brightery.com wnpp
```

Do not run the reporting tool as `root` on a production server if a regular user or trusted development workstation is available. The `--realname` flag also avoids an incorrect `root <m.elsaeed@brightery.com>` From identity.

Select **ITP (Intent to Package)** and fill the prompts with the data from [packaging/ITP_DRAFT.txt](packaging/ITP_DRAFT.txt). The command only submits the ITP if email delivery is configured and you explicitly send the report. Configure a trusted SMTP relay or mail transport if needed; otherwise send a correctly formatted ITP email from the legitimate Brightery mailbox to `submit@bugs.debian.org`. Debian will email a bug number after accepting the report. Do not assume a number until Debian confirms it.

The confirmed bug number has been added to `debian/changelog`; rebuild before signing.

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

## One-command review and final signature

After confirming the real personal Uploaders identity and filing an ITP, run a local source/binary packaging preflight (uses lintian and Debian build tools; requires a Debian development machine):

```bash
./scripts/check-debian-source.sh
./scripts/build-debian-source.sh
```

The initial changelog already closes ITP #1154410. Rebuild and review the new source package before signing.

To perform the remaining signer-controlled upload using your personal private key:

```bash
./scripts/sign-upload-mentors.sh YOUR_PERSONAL_GPG_FINGERPRINT
```

The script checks your personal secret key is available, requests confirmation, invokes `debsign`, then uploads with `dput mentors` if signing succeeds. It does not run in the APT package or in a scheduled job. Do not run this until the source has passed clean-room review, and the registered ITP is included. Seek a sponsor after the Mentors upload.

ITP and RFS drafts are under [packaging/ITP_DRAFT.txt](packaging/ITP_DRAFT.txt) and [packaging/RFS_GUIDE.md](packaging/RFS_GUIDE.md).

## Troubleshooting missing build tools on Ubuntu

The following errors are missing **development-machine packages**, not Brightery Doctor application test failures:

| Error | Install |
| --- | --- |
| `Required build tool missing: lintian` | `lintian` |
| `unmet build dependencies: dh-sequence-python3` | `dh-python` (provides that virtual dependency) |
| `Missing required program: debsign` | `devscripts` |

On a **dedicated build machine**, install:

```sh
sudo apt update
sudo apt install -y build-essential debhelper dh-python devscripts lintian dpkg-dev dput gnupg python3 git xz-utils
```

To verify the environment before rebuilding:

```sh
command -v lintian
command -v debsign
command -v dh_python3
dpkg-checkbuilddeps debian/control
```

**Do not upload merely because the 16 upstream unit tests pass.** Complete the source/binary checks, file the ITP, and put its bug number in `debian/changelog` before signing. Your key fingerprint is not a private key. The signing machine needs the private key; keep it on your trusted workstation, not a production VPS. The signed source must be uploaded from that trusted machine.

## Results from Ubuntu 26.04 packaging preflight (18 November 2026)

All 16 upstream tests passed and the Debian source/binary builds completed. The observed lintian findings were:

- `redundant-priority-optional-field` and `redundant-rules-requires-root-no-field`: fields removed from `debian/control`.
- `no-manual-page`: resolved by adding an upstream `man/brightery-doctor.1` and installing it with `debian/brightery-doctor.manpages`. For the v1.2.0 source tarball, Debian applies this upstream-forwarded manual page through `debian/patches/0001-add-upstream-manual.patch`.
- `initial-upload-closes-no-bugs`: addressed by `(Closes: #1154410)` in the initial changelog entry. **Rebuild both source and binary packages** before signing to verify the fix.

The public key on the server has primary UID `Brightery <support@brightery.com>`; the Debian uploader is `Muhammad Elsaeed <m.elsaeed@brightery.com>`. To associate the existing signing key with the named uploader, on the **trusted key-owning machine** run:

```sh
gpg --quick-add-uid C850B1AB24FE1C31CFAAE3036F7DF6E2768F6B20 'Muhammad Elsaeed <m.elsaeed@brightery.com>'
gpg --list-keys --with-fingerprint C850B1AB24FE1C31CFAAE3036F7DF6E2768F6B20
gpg --armor --export C850B1AB24FE1C31CFAAE3036F7DF6E2768F6B20 > brightery-mentors-public.asc
```

Upload the **updated public** key to the Debian Mentors profile, ensuring the new UID is included. Never upload the private key. The private key currently appears to be held by `root` on the `shad` production server; move signing operations to a trusted dedicated signing computer and protect/backup the secret key. Avoid deleting the only key copy.

Run builds as an **unprivileged user** (not `root`) in a clean Debian unstable build environment to avoid lintian root-privilege warnings and production-server risk.

## Mentors QA follow-up (19 November 2026)

The initial 1.2.0+ds-1 upload exposed older Lintian's recommended Priority field, nocheck handling, superficial tests and watch metadata findings. The packaging now declares optional priority (newer Lintian may call this redundant), respects DEB_BUILD_OPTIONS=nocheck, exercises installed modules and report creation in autopkgtest, adds upstream metadata, and tracks Git tags directly instead of relying on GitHub HTML. The verified v1.2.0 tag is not OpenPGP-signed; pgpmode=none explicitly records this limitation. A signed Debian upload does not authenticate an upstream tarball independently.

Because the package has not entered Debian, retain the initial Debian revision and ITP reference for the corrected Mentors submission. Confirm the package has not actually been uploaded by a sponsor before replacing it; do not mark it uploaded to Debian yourself. Use the same pinned orig archive. Check the new source with `uscan --report-status --verbose`, the existing preflight scripts, and a clean Debian unstable build plus autopkgtest. If all pass, sign and re-upload, then enable Needs a Sponsor and use the RFS template. If dput refuses due to an earlier local upload log, use `dput -f mentors ../debian-build/brightery-doctor_1.2.0+ds-1_source.changes` only after verifying the replacement files and their signatures.
