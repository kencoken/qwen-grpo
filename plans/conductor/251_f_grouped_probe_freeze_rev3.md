# 251_f — Step-6 grouped-probe freeze REV3 (response to 250_s)

The single P1 (external root of trust) and the nonblocking telemetry
tightening are both repaired. Full CPU suite: **982 passed under
`-W error`, TRUE exit 0** (66 in the routing battery). No Step-6 run
root exists — the repair remains pre-outcome.

## 1. P1 — the verifier is anchored to the reviewed identities

`verify_probe_run(run_root, expected_identity_sha256,
expected_environment_sha256)` now REQUIRES the two reviewed launch
identities as arguments (the reviewer's first, simpler option) and
anchors the archive to them:

- `identity_manifest["manifest_sha256"]` (already required to rehash
  and to bind to the record) must equal
  `expected_identity_sha256`;
- `record["attested_environment_sha256"]` (already required to equal
  the attested hash of the archived, self-hash-valid environment)
  must equal `expected_environment_sha256`.

Internal coherence is no longer accepted as identity: the reviewer's
coordinated-relabelling reproduction — alter the manifests, REHASH
them, and update the record pointers — is now a pair of regressions
in `test_probe_archive_verifier_lifecycle` (a rehashed identity
manifest with an updated record pointer, and a rehashed environment
manifest with BOTH record hashes updated), and both refuse at the
external anchor ("not the REVIEWED one (250_s P1)"). The prior
corruption regressions (tamper without rehash) are retained.

`execute_probe()` passes its own reviewed
`expected_identity_sha256` / `expected_environment_sha256` into the
verifier before the complete closeout, so the in-run verification is
anchored to the same externally reviewed values as the post-hoc one.

## 2. Nonblocking — complete execution-telemetry schema

The verifier now validates the full `execution_telemetry` schema:
exact key set; `group_accounting == record["counters"]` (which must
themselves equal the design-derived 432/432/432/3456); embedded
`session_preflight` equal to the archived preflight;
`deadline_seconds` equal to the frozen ceiling (3.0 GPU-h = 10,800
s); `wall_seconds` finite and non-negative;
`peak_reserved_vram_mib` a non-negative int. A wrong deadline is a
regression and refuses.

## 3. Frozen identities (FULL — the launch arguments)

The config is untouched this round, so config and freeze are
UNCHANGED from 249_f; the identity manifest moves because it binds
the probe-runner source bytes (`routing_source_sha256`).

- Config (unchanged):
  `4acf08f3f34acf7f46236b29259a5a0cabaa2b20e4a2169c3fcd68ca9ecc3b53`
- Freeze (unchanged):
  `88fee9217e79ef261468387f1bcafc7b2a50f07eccbd04ebc4abf86f7e0fae6b`
- Static execution-identity manifest (MOVED):
  `2155a8bf46c87f5288b5e8e9e76d86ae5d146f9c502bed26f381d5d93b817dd6`
- Attested environment (unchanged host):
  `372f958f5e5aa30805222d338f2e90d665cf8188a7c2ac8d559d231b3f53cd42`
- Ledger head (unchanged):
  `1a8d41fde4ffb64a9d9d9886f8fbcf9dc20578ab33c3c0d72a44fa8ea9b6a44a`
- Bound cohort (unchanged):
  `7f31bd091aaa97664e71ecb86b17078861b4e28af284162ee6ac50338d661e3b`
- Probe rule (unchanged):
  `0b616b8863bf73263c11c63cd8cc1572b880e6586f15059bde642c2a397c9f7b`

Launch: `execute_probe(expected_freeze_sha256,
expected_identity_sha256, expected_environment_sha256,
expected_head_sha256)`; post-hoc:
`verify_probe_run(run_root, expected_identity_sha256,
expected_environment_sha256)` with the same reviewed values.

## 4. Next

Narrow changed-lines and hash check (250_s closing paragraph), then
launch OK → the GPU run with the §3 hashes → close-out + report
review → P0 designed from MEASURED exposure. Registered-measurement
discipline unchanged (denominators 432/216/24 = opportunities).
