# Evaluation

Run the deterministic labelled set, including the skincare offer-consistency, unsupported-claim and adversarial-document examples:

```powershell
api\.venv\Scripts\python.exe api\scripts\run_evals.py
```

The runner reports exact finding-type precision and recall, cited-excerpt validity and high-severity false-breach rate. The mock judgement client intentionally returns human-verification outcomes for unsupported claims. A perfect score on this small set is not evidence of general model accuracy.

The current set is `evals/brandlens.json`. Extend it with approved passages, expected finding types, asset text and the expected high-severity outcome. Keep evidence passage text exact so citation verification is measurable. CI runs this set with the mock client.

There is no real LLM adapter in this repository. To evaluate a future provider, implement the existing `LLMClient` contract, keep the provider disabled by default, use a dedicated test organisation with explicit processing consent, protect credentials through CI secrets, and report provider/model/version and latency. Add adversarial inputs and human-labeled expected outcomes before enabling user workflows. Do not report model performance from the mock-only run.
