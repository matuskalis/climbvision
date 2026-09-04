# CLAUDE.md

The operating rules for coding agents in this repository live in `AGENTS.md`. They are binding,
and they are identical for every agent and every tool. Read that file first, before the code and
before the plan.

@AGENTS.md

## Claude Code specifics

Delegate code to an `implementer` subagent and documentation to a `docs-writer` subagent. Run the
`reviewer` subagent after **any** code change, and do not report done until it approves. Report
only the reviewer's verdict, the `docs/status.md` diff, the verification commands with their
output, and whatever could not be measured. Stop after every stage and wait for the owner's
decision.
