# metrics Package

The metrics package standardizes experiment scoring and output.

## Files and roles

| File | Purpose |
| --- | --- |
| metrics/asr.py | Attack Success Rate metric logic. |
| metrics/tir.py | Tool Invocation Rate metric logic. |
| metrics/dbr.py | Defense Bypass Rate metric logic. |
| metrics/qtj.py | Query-To-Jailbreak metric logic. |
| metrics/collector.py | ExperimentRecord model, aggregation, and CSV/JSON export. |
| metrics/__init__.py | Package exports. |

## Export behavior

collector.to_csv writes flat records.
collector.to_json writes summary, category breakdown, and clean records.
