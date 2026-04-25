# API Payload Examples

## 11. Environment Summary Payload
```json
[
  {"name": "df", "type": "data.frame", "details": "150 rows, 5 cols"},
  {"name": "model_fit", "type": "lm", "details": "Linear model"},
  {"name": "avg_height", "type": "numeric", "details": "172.4"}
]
```

## 12. Execute Response Payload
```json
{
  "status": "success",
  "stdout": "Call: lm(formula = Sepal.Length ~ Sepal.Width, data = iris)\nCoefficients: ...",
  "stderr": null,
  "plots": ["https://storage.googleapis.com/air-sessions/sessions/id/artifacts/plot_1.png?X-Goog-Algorithm=..."],
  "environment": [
    {"name": "iris", "type": "data.frame", "details": "150 rows, 5 cols"}
  ],
  "snapshot_uri": "gs://air-sessions/sessions/abc/snapshots/state.RData"
}
```
