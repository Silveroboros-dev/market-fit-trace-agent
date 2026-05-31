# Trace Repair V1

This pack proves the Arize/Phoenix correction loop. It is not a strict
correctness-golden pack.

Trace-repair cases assert a transition:

```text
first run overstates fit
-> Phoenix/OpenInference trace contains fit_eval_run mismatch signals
-> Phoenix MCP retrieves the failed trace/eval context
-> deterministic trace_informed_false_strong_cap downgrades the rerun
```

The first run is expected to fail in a specific way. The second run may repair
only when Phoenix MCP succeeds; local fallback must not silently pass this pack.

Run:

```bash
make trace-repair
```

The command writes `run_results/trace_repair_result.json`.
