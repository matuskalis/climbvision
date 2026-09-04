# Verification Commands

Run this table after every stage, before committing, from the repository root
(`~/projects/climbvision`). What to do when a check fails:
[`00-operating-manual.md`](00-operating-manual.md) Section 7.

| # | Check | Command or file | Good result | Bad result |
| --- | --- | --- | --- | --- |
| 1 | Full test run | `uv run pytest -q` | no fewer passed than the count `docs/status.md` records for the previous stage (423 today), 0 failed, 0 skipped | fewer passed than that count; any skipped; any failed |
| 2 | Lint | `uv run ruff check .` | `All checks passed` | any diagnostic |
| 3 | Probe tool version | `ffprobe -version` | a version line prints; `docs/status.md` records 8.0 | `command not found`, which means any skip in row 1 is environmental and not a code defect |
| 4 | Working tree scope | `git status --porcelain` | empty, or only the files the brief named | any path the brief did not name |
| 5 | No data or media in the tree | `git status --porcelain -- data '*.mp4' '*.mov' '*.mkv' '*.jpg' '*.png' '*.pt' '*.onnx' '*.safetensors'` | no output | any output |
| 6 | Change scope against the previous commit | `git diff --stat HEAD` | every path listed is one the brief named | a path no brief named |
| 7 | Contract untouched in a code-only change | `git diff --name-only HEAD -- docs/mvp-contract.md` | no output | any output, with no decision record in the same change set |
| 8 | Configs and `[FIXED]` thresholds untouched | `git diff --name-only HEAD -- configs` | no output | any output, with no decision record in the same change set |
| 9 | Dependency drift | `git diff HEAD -- pyproject.toml uv.lock` | no output, unless the brief named the dependency | a dependency no brief named |
| 10 | Guard pins not edited to make a change pass | `git diff HEAD -- tests/unit/test_scope_guard.py` | no output, unless the brief authorised a new module or dependency | a pin edited in a change set that authorised neither |
| 11 | No absolute path in a written artifact | `grep -rIn -e "/Users/" -e "/home/" docs README.md AGENTS.md src configs` | no output, other than the contract's own illustration of the rule in `docs/mvp-contract.md` Section 7 | any other hit |
| 12 | `[VAL]` still unused | `grep -rn -F "[VAL]" docs configs src README.md AGENTS.md` | every hit defines or discusses the tag; no hit attaches it to a number | a number carrying `[VAL]` |
| 13 | Every number in the status diff carries a tag | `git diff -- docs/status.md` | every added number is either an observation in a measured-evidence column or carries exactly one tag | an added number that is neither |
| 14 | Gate evidence names a command and a dataset | file `docs/status.md`, column **Gate evidence** | each cell names the command that produced the number and the data it ran on | the word "passes" with no number; "should", "presumably", "typically" |
| 15 | Gate evidence does not cite the fixtures | `grep -n -i fixture docs/status.md` | hits appear only in the Stage 1 supporting facts about ingest determinism | a fixture cited as evidence for an accuracy-shaped gate, Stages 2 through 7 |
| 16 | Test-set evaluations logged with dates | `grep -n -i "test set" docs/status.md` | every test-set evaluation carries a date and a reason | an undated or unlogged test-set run |
| 17 | Ingest still idempotent | block V17 below | see block V17 | see block V17 |
| 18 | README status table agrees with the ledger | files `README.md` (Stage / State table) and `docs/status.md` (Stage ledger) | the same state word in both, for every stage row | a stage that is `complete` in one and `not started` in the other |
| 19 | Commit message describes the actual diff | `git diff --stat HEAD`, read beside the proposed message | every path in the diff is accounted for by the message | a message narrower than the diff |

---

## Block V17 — ingest the same clip twice

```bash
uv run climbvision ingest ~/climbvision-data/sessions/<session-id>/raw/<clip>.mov --out artifacts
shasum -a 256 artifacts/recordings/<asset_id>/recording.json
ls artifacts/recordings/<asset_id>/runs/

uv run climbvision ingest ~/climbvision-data/sessions/<session-id>/raw/<clip>.mov --out artifacts
shasum -a 256 artifacts/recordings/<asset_id>/recording.json
ls artifacts/recordings/<asset_id>/runs/
```

**Good:** both ingests exit 0; the same `<asset_id>` directory both times; the two digests are
identical; the second listing contains a new run record beside the first, and nothing from the
first run is missing or altered.

**Bad:** a second `<asset_id>` directory; a changed digest; `MANIFEST_CONFLICT`.

---

## Stop immediately

Three signals. Do not investigate first, and do not commit.

1. The test count went down.
2. A gate is marked passed with no number.
3. The contract changed inside a change set that also measured a gate.
