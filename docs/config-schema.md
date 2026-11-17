# Harness configuration design (not executable yet)

A versioned manifest will identify the model, prompt-template hash, tool allowlist,
step/token/wall-time limits, fixed task revision and protected-verifier hash.
Secrets are referenced by environment-variable name, never stored in manifests or
traces. No model is preselected without a verified no-cost access route.

The current implementation analyzes already-scored JSONL outcomes only. The
Inspect integration is currently a fixed-response mock contract check. Neither
is a container runner or a real coding-agent evaluation.

Proposed run identity: suite hash + task ID/revision + verifier hash + harness
configuration hash + model identifier + trial + seed + execution/evidence class.
Both sides of a paired comparison must share task and verifier identities.

A pilot must not be treated as the final benchmark. Repeat counts, non-inferiority
margin and task split must be specified before the measured comparison, with
held-out tasks kept separate from harness development.
