## Verdict

Almost, but one narrow P1 remains before Unit 5.

A genuine plan fails after the repository’s normal sorted-key JSON round-trip because `require_launchable()` treats input-key order as significant:

```python
json.loads(json.dumps(plan, sort_keys=True))
```

This is then rejected at `tuple(plan["inputs"]) != REGISTERED_CAPACITY_INPUTS`. Since Unit 5 will persist this record and the repository commonly uses sorted-key JSON, this breaks the intended workflow.

::code-comment{title="[P1] Persisted valid plan is rejected" body="Input identity is checked by dictionary iteration order. Canonical sorted-key JSON persistence reorders these keys, causing a genuine launch plan to fail admission. Compare exact key membership without considering order, retain the existing type-sensitive full-plan rederivation, and add sorted-key round-trip acceptance plus missing/extra-key rejection tests." file="/home/ken/qwen-grpo/tasks/routing/p0_cap.py" start=192 end=197 priority=1}

Everything else is satisfactorily closed:

- Forged branch, epoch, Boolean, NaN, and ceiling values are rejected.
- Genuine stop/under-target/spare branches behave correctly.
- The signed traceability matrix and complete sentinel obligations are present.
- CRLF tampering is rejected and the byte count is correct at 11,187.
- Focused tests and the independent 25/25 C2 equivalence check pass.
- Worktree and diff checks are clean.

After the small key-membership fix and its JSON round-trip regression test, I would sign off Unit 4 and proceed directly to Unit 5.