# Security policy

Please report vulnerabilities privately using GitHub's **Report a vulnerability** feature for this repository if enabled, or contact the repository owner privately. Do not post exploit details or secrets in public issues.

Supported version: 1.1.x. The tool runs locally, has no network interfaces, executes no subprocesses and does not alter services. Treat it as a diagnostic aid, not a security boundary. Follow least privilege; running without `sudo` is preferred where it provides enough information. `--save` creates a report and should point into a trusted directory.

Release checklist: run tests, review all source changes, check for embedded secrets, build the package locally, inspect `dpkg-deb --contents`, check signatures and fingerprint for APT archive, and never commit private signing keys.
