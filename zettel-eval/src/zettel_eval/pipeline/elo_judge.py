from __future__ import annotations

import json
import csv
from dataclasses import dataclass
from typing import Any
from pathlib import Path

import dspy

from zettel_eval.pipeline.dspy_program import _coerce_json_payload

class CompareBrainstorms(dspy.Signature):
    """Compare two brainstorm essays against the source material and declare a winner based on Innovation, Groundedness, and Coherence. Return strict JSON."""

    seed_note = dspy.InputField(desc="The original seed note.")
    retrieved_notes = dspy.InputField(desc="The retrieved source notes that the essay is allowed to rely on.")
    essay_a = dspy.InputField(desc="Brainstorm Essay A to evaluate.")
    essay_b = dspy.InputField(desc="Brainstorm Essay B to evaluate.")
    
    score_json = dspy.OutputField(
        desc=(
            "A JSON object with exactly two keys: 'winner' (which MUST be either 'A', 'B', or 'TIE'), "
            "and 'justification' (a 1-sentence explanation of why the winner was chosen)."
        )
    )

class PairwiseEloJudge:
    def __init__(self, judge_lm: Any | None = None, log_file: Path | None = None) -> None:
        self.judge_lm = judge_lm
        self._judge = dspy.Predict(CompareBrainstorms)
        self.log_file = log_file
        
        if self.log_file and not self.log_file.exists():
            with self.log_file.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "seed_note", 
                    "essay_a", 
                    "essay_b",
                    "winner", 
                    "justification"
                ])

    def compare(
        self,
        *,
        seed_note: str,
        retrieved_notes: str,
        essay_a: str,
        essay_b: str,
    ) -> tuple[str, str]:
        
        if self.judge_lm is None:
            prediction = self._judge(
                seed_note=seed_note,
                retrieved_notes=retrieved_notes,
                essay_a=essay_a,
                essay_b=essay_b,
            )
        else:
            with dspy.context(lm=self.judge_lm):
                prediction = self._judge(
                    seed_note=seed_note,
                    retrieved_notes=retrieved_notes,
                    essay_a=essay_a,
                    essay_b=essay_b,
                )
                
        payload = _coerce_json_payload(prediction.score_json, default={})
        if not isinstance(payload, dict):
            payload = {}
            
        winner = str(payload.get("winner", "TIE")).strip().upper()
        if winner not in {"A", "B", "TIE"}:
            winner = "TIE"
            
        justification = str(payload.get("justification", "")).strip()

        if self.log_file:
            with self.log_file.open("a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    seed_note[:200].replace("\n", " "),
                    essay_a[:200].replace("\n", " "),
                    essay_b[:200].replace("\n", " "),
                    winner,
                    justification.replace("\n", " ")
                ])
                
        return winner, justification
