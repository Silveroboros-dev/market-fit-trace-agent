# Market Fit v4 Live-Promoted Goldens

This pack contains reviewed live PolyData retrieval candidates promoted into strict frozen goldens. It is intentionally separate from `market_fit_v1`, which remains the stable Phoenix proof pack.

The pack freezes the agent-run market set, market rules, retrieval IDs, run IDs, and trace IDs for two reviewed geopolitical cases:

- `demo-hormuz-candidate`: `indirect`, best market `2155023`.
- `live-iran-sanctions-relief-package`: `weak_proxy`, no clean best market; `2155023` is a tempting adjacent market only.

Run with:

```bash
make evals-v4-live-promoted
```

Promotion rule: these are strict goldens only because the market snapshots and resolution rules are frozen locally. Live PolyData retrieval is not called by this eval pack.
