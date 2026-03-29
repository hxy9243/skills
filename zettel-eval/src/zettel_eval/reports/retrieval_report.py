from __future__ import annotations


def build_summary_report(summary_rows: list[dict], dataset_scores: dict[str, dict[str, float]]) -> str:
    lines = ["# Retrieval Benchmark Summary", ""]
    if not summary_rows:
        lines.append("No processed datasets were available for benchmarking.")
        return "\n".join(lines) + "\n"

    lines.extend(["## Best Method Per Dataset", ""])
    for row in summary_rows:
        lines.append(
            f"- `{row['dataset_slug']}` / `{row['method']}`:"
            f" R@5={row['recall_at_5']}, R@10={row['recall_at_10']}, MRR={row['mrr']}, params={row['params']}"
        )

    lines.extend(["", "## Aggregate Diagnostics", ""])
    for dataset_slug, scores in dataset_scores.items():
        if not scores:
            lines.append(f"- `{dataset_slug}`: no successful retrieval runs")
            continue
        rendered = ", ".join(f"{method}={score:.4f}" for method, score in sorted(scores.items()))
        lines.append(f"- `{dataset_slug}`: {rendered}")

    return "\n".join(lines) + "\n"
