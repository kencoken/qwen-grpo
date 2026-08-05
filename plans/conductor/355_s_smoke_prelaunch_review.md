Do not launch `execute_smoke_run` yet. I need to withdraw the earlier launch sign-off because the prelaunch check exposed one genuine frozen-contract regression.

Blocking finding: `tasks/routing/p0_smoke.py` no longer checks the deadline at the training reward entry. `on_step_begin` is useful but not equivalent: generation can begin before the deadline, cross it, and still be scored and followed by an optimizer update before the next check.

The narrow repair is:

```python
def reward(completions=None, **kwargs):
    _check_deadline(deadline, "training reward entry")
    instrumentation.on_reward_entry()
    return base_reward(completions, **kwargs)
```

Retain the existing `on_step_begin` check. Add a regression covering “step begins before deadline, generation finishes after it,” verifying that scoring and consumption do not occur.

Everything else validated:

- All prelaunch hashes and identities rederive.
- Ledger head is correctly `6fea9e3b…`.
- No same-freeze launch or execution output exists.
- Environment attestation and budget admission pass.
- The run root contains exactly the three prepared files.

Because the repair changes the routing-source digest, manifest `685200a5…` must be recorded as superseded and regenerated under a documented successor prelaunch identity. The freeze/configuration need not change, and the ledger parent remains valid. After that, only another narrow hash/head/root check is required.