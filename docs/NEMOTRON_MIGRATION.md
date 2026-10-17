# Nemotron model migration

Crusoe's authenticated live catalog on 2026-10-17 returned the exact ID
`nvidia/NVIDIA-Nemotron-3-Super-120B-A12B`, with tool support and a
262,144-token context. This is now the default and the prepared workspace's
local selection for both investigation and isolated repair. Explicit model
overrides remain supported. No key is included in source.

## Validation

- Existing non-browser suite: 45 passed, 14 browser tests deselected.
- Live readiness tool call and tool-result round trip: passed.
  Response IDs: `chatcmpl-a13a866653508c67`, `chatcmpl-8059b2e98f701fbb`.
- Fresh VIP20 control `0a3e38a2-0209-4429-8a57-1f0c7d705fbe`:
  blocked by HTTP 429 after two successful completions, 6 requests including
  bounded retries, 6,496 reported tokens, 28.38 seconds, zero browser actions.
- Fresh recovery report `abdd8974-9bd1-4d72-874e-25317d904822`:
  blocked by HTTP 429, 4 requests including discovery/retries, zero completions
  and zero browser actions, 5.22 seconds.

These results establish provider compatibility, not a completed Nemotron
investigation or repair. Resolve Crusoe's rate limit before rerunning. Creating
a new key does not guarantee a different account quota. Prior DeepSeek runs,
the recorded video, and delivery artifacts retain their original provenance.

## Saving a replacement key

On the prepared Windows workspace, double-click `Configure_Repro.cmd`. Paste
the new Crusoe Intelligence API key into the hidden prompt and press Enter.
The helper changes only the ignored local `.env` key. Alternatively run
`.\.venv\Scripts\python.exe -m scripts.configure` in the project directory.
Key selection and model selection are separate. New attempts read the file
again; previously saved results keep their original model.

NVIDIA describes Super's agentic coding and tool use:
https://docs.nvidia.com/nemotron/latest/usage-cookbook/Nemotron-3-Super/OpenScaffoldingResources/README.html
