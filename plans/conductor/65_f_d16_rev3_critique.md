# D16 rev3 critique — stop spending on Math; recover Code by layout

Input: `64_f_d16_rev3.md`, probes therein, `runs/d16-rev3-eval/traces/`.

## Assessment

Rev3 closed the Math investigation the right way: two probes, one
falsifying prompt-content sensitivity (three maximally different prompts,
0/20 each), one localizing the defect to the endpoint model (base
Instruct, same prompt, same requests: 20/20). That is the evidence
package the D16/spec review needs; further Math prompt iterations would
be motion without information.

Rev3's Code cost was real: adding material mid-prompt demoted the
handle contrast and regressed count-shape compliance that rev2 had won.
The accumulated Code evidence supports a specific theory of this model:
**examples teach structure; layout position teaches priority; prose
rules teach little.** Lookup — 15/15 for three straight revisions —
has exactly the layout Code lacks: the identifier rule in the first
sentence, one example, contract at the end, nothing else.

## Levers for rev4 (ranked)

1. **Code: restructure to Lookup's winning layout, keeping all three
   examples.** First sentence carries the identifier rule ("the sequence
   argument is always the word `resource` — never a name like R-8C3");
   examples follow (count, step_k, select — each already
   machine-verified); the final line repeats the identifier rule
   *and* the envelope contract, restoring recency for the rule that
   regressed. Cut: "given the same resource" repetitions (rename to
   plain "the task …" phrasing), the separate scope-discipline sentences
   (fold "whitelist calls only" into the first paragraph; drop "ignore
   other arithmetic" — the `* 12` case vanished at rev3 and the sentence
   is a suspect in the regression).
2. **Math: freeze the rev3 text as the best-effort candidate.** No
   further content changes; the prompt is adequate (probe 2 proves a
   compliant model follows it). Mark the endpoint-model decision as the
   blocking question for the review in the D16 evidence summary.
3. **Confirmatory scale, not new content, for rev5.** If rev4 recovers
   Code, spend the final iteration re-running the paired evaluation at
   larger `--per-cell` (e.g. 15 → ~30 code calls, ~45 lookup calls) so
   the review sees the stable configuration at less noisy counts,
   rather than introducing new prompt text in the same breath as the
   confirmation run.

## For the eventual D16 review (accumulating summary)

- Lookup: solved at rev1; stable since.
- Code: solved failure modes = envelope (rev1), count-shape identifier
  (rev2), select nesting + arithmetic contamination (rev3); open =
  identifier recency (rev4 target).
- Math: prompt-side exhausted with a falsification trail; blocking
  question = §1.6 endpoint model (evidence: probe 1 + probe 2, 64_f).
  Options for the reviewer: endpoint swap to base Instruct (versioned
  experiment change), or accept Math-cell qualification failure as an
  outcome. Note the payoff-structure implication: if Math-routed steps
  cannot produce legal artifacts, `math_atomic` and every math-sink
  composite cell lose their reference path, which guts four of six
  cells — this is why the endpoint question deserves review time before
  the construction screen.
