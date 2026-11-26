# e-lamp release security gate

Source gate: `python3 .security-ci/check.py source . --report /tmp/elamp-security/source.json`
Exact image gate: `docker save -o /tmp/elamp-candidate.tar IMAGE` then `python3 .security-ci/check.py image /tmp/elamp-candidate.tar --report /tmp/elamp-security/image.json`.

Docker (Linux containers) and Python 3 are required. No cloud credentials are passed to the scanner. Pinned Semgrep 1.187.0 and Trivy 0.76.1 run locally; application code is not executed during source scanning. Raw findings/snippets/secret values are never published; reports contain only locations and rule identifiers. Temporary scanner images are removed by the wrapper.

Blocking policy: all detected secrets, bundled Python/JavaScript/TypeScript security rules, vulnerabilities with a fixed version at any severity, HIGH/CRITICAL even without a fix, end-of-life image OS, unresolved dependency declarations, scanner/parser failures. No baseline/ignore/automatic risk acceptance. This initial SAST rule set does not cover every language or vulnerability class.

Cloud Build: source gate before application build, exact built image gate before automatic image push. Firebase: predeploy hooks run the source gate, preserving existing hooks. Never use `--ignore-scripts` or remove hooks to bypass the gate. A failed scan stops a new release; it does not stop the currently running service.

Limitations: the current private-repository GitHub plan rejects branch protection/rulesets (HTTP 403). Status checks alone cannot enforce merge protection, and direct `gcloud run deploy`, a different Cloud Build config or modified Firebase config can bypass repository hooks. IAM/contract changes and source-to-production mapping are outside this change. Once a supported GitHub plan is available, require the `Security gate` check, protect CI/deploy files, and restrict direct release permissions separately. An owner can deliberately override controls; this is not an organization-wide deployment admission controller.

No application release, dependency upgrade, credential rotation or Slack notification is performed by installing this gate. Resolve existing findings before the next release; do not mark a failing scan successful to finish installation.
