# SkyT Workflow Evaluation Set

`tasks.json` is the fixed offline benchmark set for code, research, analysis and documentation workflows.

Run `python evals/workflows/evaluate_workflows.py` to validate the task set and emit a machine-readable summary. The evaluator does not call a model or production database by default; live runs should be submitted through the workflow API and measured with the returned run records.
