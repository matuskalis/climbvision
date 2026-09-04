# Prompt Templates

Copy a block verbatim and fill the `<...>` placeholders. Which template applies to which
situation: [`00-operating-manual.md`](00-operating-manual.md) Section 13.

---

## T1 — stage kickoff

Use when: opening a stage, in a fresh session, with every precondition in that stage's brief ticked.

```
Read these, in this order, before doing anything else:

  1. docs/agents/00-operating-manual.md, Sections 7 and 8
  2. docs/mvp-contract.md
  3. docs/evaluation.md
  4. docs/status.md
  5. docs/agents/briefs/stage-<N>-<slug>.md, the brief for this stage and no other

Then work Stage <N> exactly as that brief specifies.

Session rules:

  - Delegate code to an implementer subagent and documentation to a docs-writer subagent.
  - Run the reviewer after any code change. Do not report done until the reviewer approves.
  - Add no dependency the brief does not name.
  - Do not modify the contract, the configs, or any [FIXED] threshold.
  - Every number written into the documentation carries exactly one status tag.
  - Gate numbers come from real annotated data, never from tests/fixtures/. If the data does
    not exist yet, stop and say so. Do not substitute synthetic data or assumed values.

Report exactly four things:

  1. The reviewer's verdict, verbatim.
  2. The diff of docs/status.md.
  3. The exact commands to verify, with their expected output.
  4. Anything that could not be measured, and why.

Then stop. Do not start the next stage.
```

---

## T2 — reviewer challenge

Use when: one specific claim in a report looks unverified. Send it to the reviewer, not to the implementer.

```
Claim under challenge:

  File and line: <path>:<line>
  Sentence:      "<paste the exact sentence>"

Verify this claim by independent measurement. Do not verify it by reading the implementation's
report, its docstrings, or its test names.

Return:

  1. The exact command you ran.
  2. Its raw output, pasted, not paraphrased.
  3. VERIFIED or NOT VERIFIED.

If the claim cannot be reproduced by a command I can run on my own machine, mark it
NOT VERIFIED and state exactly what is missing.
```

---

## T3 — gate report request

Use when: asking for a stage gate result.

```
Report the Stage <N> gate as a table, one row per gate clause:

  | Clause | How it was measured (exact command) | Measured value | Pass or fail | Data it ran on |

Rules for that table:

  - Only values observed on this machine today.
  - A clause that was not measured reads "pending measurement" and names the data that is missing.
  - No number carried over from a previous run on a different dataset.
  - No number derived from tests/fixtures/ reported as gate evidence.
```

---

## T4 — failure escalation

Use when: a gate clause was measured and failed.

```
Gate clause:     <clause>
Measured value:  <value>
Threshold:       <threshold>

Do not change the threshold. Do not change the test set. Do not re-run the test set.

Return:

  1. The gap, with its number.
  2. The failing slices: by problem, by session, and hands versus feet.
  3. Three smallest experiments that could close the gap. For each, the data or the labelling
     it needs from me.
  4. One recommendation, and what it is expected to change.

Then stop. I choose.
```

---

## T5 — data arrival

Use when: footage has been filmed, logged and copied off the phone.

```
New recordings, outside the repository:

  Session id: <session-id>
  Path:       ~/climbvision-data/sessions/<session-id>/raw/
  Files:      <list the filenames>

Ingest each one. Report a table with one row per recording:

  | Asset id (abbreviated) | resolution_below_min | frame_rate_below_min | variable_frame_rate | timestamps_absent | audio_stream_count |

Then say which recordings fall outside the envelope, and why.

Exclude nothing on your own. Exclusion is my decision and is recorded in the session log.
```

---

## T6 — standing status challenge

Use when: resuming after a gap, or when an agent's summary reads better than the evidence behind it.

```
State the project's status without using any summary written earlier by you or by another agent.

Use only these three sources:

  1. docs/status.md
  2. The git log
  3. The output of the test command and the lint command, run now

If those three sources disagree with each other, stop and show me the disagreement.
```
