from __future__ import annotations

import json
import csv
from dataclasses import dataclass
from typing import Any
from pathlib import Path

import dspy

from zettel_eval.pipeline.dspy_program import _coerce_json_payload


@dataclass(slots=True)
class JudgeScore:
    innovation_insight: float
    groundedness: float
    logical_coherence: float
    summary: str

    @property
    def total(self) -> float:
        return self.innovation_insight + self.groundedness + self.logical_coherence

    @property
    def normalized(self) -> float:
        return self.total / 15.0

    def to_json(self) -> str:
        return json.dumps(
            {
                "innovation_insight": self.innovation_insight,
                "groundedness": self.groundedness,
                "logical_coherence": self.logical_coherence,
                "summary": self.summary,
                "normalized": self.normalized,
            },
            indent=2,
            ensure_ascii=True,
        )


class JudgeBrainstorm(dspy.Signature):
    """Score the brainstorm essay rigorously against the provided source notes and return strict JSON."""

    seed_note = dspy.InputField(desc="The original seed note.")
    retrieved_notes = dspy.InputField(desc="The retrieved source notes that the essay is allowed to rely on.")
    brainstorm_essay = dspy.InputField(desc="The final brainstorm essay to evaluate.")
    score_json = dspy.OutputField(
        desc=(
            "A JSON object with innovation_insight, groundedness, logical_coherence as integers 0-5, "
            "plus a short summary."
        )
    )


def parse_judge_score(raw_text: str) -> JudgeScore:
    payload = _coerce_json_payload(raw_text, default={})
    if not isinstance(payload, dict):
        payload = {}

    def _score(name: str) -> float:
        raw_value = payload.get(name, 0)
        try:
            return max(0.0, min(5.0, float(raw_value)))
        except (TypeError, ValueError):
            return 0.0

    return JudgeScore(
        innovation_insight=_score("innovation_insight"),
        groundedness=_score("groundedness"),
        logical_coherence=_score("logical_coherence"),
        summary=str(payload.get("summary", "")).strip(),
    )


class LLMJudgeMetric:
    def __init__(self, judge_lm: Any | None = None, log_file: Path | None = None) -> None:
        self.judge_lm = judge_lm
        self._judge = dspy.Predict(JudgeBrainstorm)
        self.log_file = log_file
        
        if self.log_file and not self.log_file.exists():
            with self.log_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "seed_note", 
                    "brainstorm_essay", 
                    "innovation_insight", 
                    "groundedness", 
                    "logical_coherence", 
                    "normalized_score", 
                    "judge_summary"
                ])

    def score_prediction(
        self,
        *,
        seed_note: str,
        retrieved_notes: str,
        brainstorm_essay: str,
    ) -> JudgeScore:
        if self.judge_lm is None:
            prediction = self._judge(
                seed_note=seed_note,
                retrieved_notes=retrieved_notes,
                brainstorm_essay=brainstorm_essay,
            )
        else:
            with dspy.context(lm=self.judge_lm):
                prediction = self._judge(
                    seed_note=seed_note,
                    retrieved_notes=retrieved_notes,
                    brainstorm_essay=brainstorm_essay,
                )
        score = parse_judge_score(prediction.score_json)
        
        if self.log_file:
            with self.log_file.open("a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    seed_note[:200].replace("\n", " "),
                    brainstorm_essay[:200].replace("\n", " "),
                    score.innovation_insight,
                    score.groundedness,
                    score.logical_coherence,
                    score.normalized,
                    score.summary.replace("\n", " ")
                ])
                
        return score

    def __call__(self, example: Any, prediction: Any, trace: Any | None = None) -> float:
        score = self.score_prediction(
            seed_note=str(example.seed_note),
            retrieved_notes=str(example.retrieved_notes),
            brainstorm_essay=str(prediction.brainstorm_essay),
        )
        return score.normalized
