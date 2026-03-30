from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime
from pathlib import Path

from zettel_eval.pipeline.optimize import discover_retrieval_metrics, load_phase2_examples

csv.field_size_limit(sys.maxsize)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def build_pairwise_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--retrieval-metrics", type=Path, default=None, help="Optional Phase 2 retrieval_metrics.csv path.")
    parser.add_argument("--processed-root", type=Path, default=PROJECT_ROOT / "datasets/processed")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "output")
    parser.add_argument("--task-model", default="openai/gpt-5.1-codex-mini")
    parser.add_argument("--judge-model", default="openai/gpt-5.4")
    parser.add_argument("--iterations", type=int, default=10, help="Number of hill-climb iterations to run.")
    parser.add_argument("--batch-size", type=int, default=5, help="Examples to judge per iteration.")
    parser.add_argument("--max-examples", type=int, default=100, help="Maximum Phase 2 examples to load.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--baseline-instruction",
        default="Write a brainstorm essay that synthesizes the seed note and the retrieved notes into a coherent argument.",
        help="Starting synthesis instruction for the champion prompt.",
    )
    return parser


def run_pairwise_optimization_from_args(args: argparse.Namespace) -> Path:
    import dspy

    from zettel_eval.pipeline.dspy_program import BrainstormPipeline, SynthesizeBrainstorm, format_retrieved_notes
    from zettel_eval.pipeline.elo_judge import PairwiseEloJudge

    class ProposeInstruction(dspy.Signature):
        """Propose a stronger synthesis prompt for grounded brainstorm writing."""

        current_instruction = dspy.InputField()
        feedback = dspy.InputField(
            desc="Feedback from the judge on why the previous version lost matches."
        )
        proposed_instruction = dspy.OutputField(
            desc="A plain-text replacement instruction without markdown fences."
        )

    random.seed(args.seed)

    print("Setting up pairwise optimizer LMs...", flush=True)
    task_lm = dspy.LM(model=args.task_model, temperature=1.0, max_tokens=16000, cache=False)
    judge_lm = dspy.LM(model=args.judge_model, temperature=1.0, max_tokens=16000, cache=False)
    dspy.configure(lm=task_lm)

    print("Loading benchmark corpus...", flush=True)
    metrics_path = args.retrieval_metrics or discover_retrieval_metrics(args.output_root)
    examples = load_phase2_examples(
        metrics_path=metrics_path,
        processed_root=args.processed_root,
        max_examples=args.max_examples,
    )
    if not examples:
        msg = "No Phase 2 examples available for pairwise optimization."
        raise ValueError(msg)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = args.output_root / "runs" / f"pairwise_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    judge = PairwiseEloJudge(judge_lm=judge_lm, log_file=run_dir / "pairwise_eval.csv")
    proposer = dspy.Predict(ProposeInstruction)
    champ_instruction = args.baseline_instruction
    history_log = run_dir / "optimization_history.log"
    history_log.write_text(
        "Starting Pairwise Optimization\n"
        f"Initial Champion Instruction:\n{champ_instruction}\n\n",
        encoding="utf-8",
    )

    print(f"Starting Pairwise Optimization Loop ({args.iterations} iterations)...", flush=True)
    feedback_accumulator = (
        "We want to improve Innovation, Groundedness, and Coherence. "
        "The prompt must explicitly cite sources."
    )

    for iteration in range(1, args.iterations + 1):
        print(f"\n--- Iteration {iteration}/{args.iterations} ---", flush=True)
        print("Proposing new challenger instruction...", flush=True)
        with dspy.context(lm=judge_lm):
            proposal = proposer(
                current_instruction=champ_instruction,
                feedback=feedback_accumulator,
            )

        challenger_instruction = proposal.proposed_instruction.strip()
        print(f"Challenger proposed:\n{challenger_instruction}\n", flush=True)

        champ_pipeline = BrainstormPipeline()

        class ChampSynth(SynthesizeBrainstorm):
            __doc__ = champ_instruction

        champ_pipeline.synthesize = dspy.Predict(ChampSynth)

        chall_pipeline = BrainstormPipeline()

        class ChallSynth(SynthesizeBrainstorm):
            __doc__ = challenger_instruction

        chall_pipeline.synthesize = dspy.Predict(ChallSynth)

        batch = random.sample(examples, min(args.batch_size, len(examples)))
        wins = 0
        losses = 0
        ties = 0
        match_rationales: list[str] = []

        for example in batch:
            formatted_notes = format_retrieved_notes(example.retrieved_notes)
            res_champ = champ_pipeline(seed_note=example.seed_note, retrieved_notes=formatted_notes)
            res_chall = chall_pipeline(seed_note=example.seed_note, retrieved_notes=formatted_notes)

            is_challenger_a = random.choice([True, False])
            if is_challenger_a:
                winner, rationale = judge.compare(
                    seed_note=example.seed_note,
                    retrieved_notes=formatted_notes,
                    essay_a=res_chall.brainstorm_essay,
                    essay_b=res_champ.brainstorm_essay,
                )
                if winner == "A":
                    wins += 1
                    match_rationales.append(f"Challenger won: {rationale}")
                elif winner == "B":
                    losses += 1
                    match_rationales.append(f"Champion won: {rationale}")
                else:
                    ties += 1
                    match_rationales.append(f"Tie: {rationale}")
                continue

            winner, rationale = judge.compare(
                seed_note=example.seed_note,
                retrieved_notes=formatted_notes,
                essay_a=res_champ.brainstorm_essay,
                essay_b=res_chall.brainstorm_essay,
            )
            if winner == "B":
                wins += 1
                match_rationales.append(f"Challenger won: {rationale}")
            elif winner == "A":
                losses += 1
                match_rationales.append(f"Champion won: {rationale}")
            else:
                ties += 1
                match_rationales.append(f"Tie: {rationale}")

        print(f"Result: Challenger {wins} wins, {losses} losses, {ties} ties", flush=True)

        with history_log.open("a", encoding="utf-8") as handle:
            handle.write(f"Iteration {iteration} Results: W:{wins} L:{losses} T:{ties}\n")
            handle.write(f"Challenger Prompt:\n{challenger_instruction}\n")
            handle.write("Rationales:\n" + "\n".join(match_rationales) + "\n\n")

        if wins > losses:
            print("Challenger dethrones champion. Updating baseline.", flush=True)
            champ_instruction = challenger_instruction
            feedback_accumulator = (
                "The new prompt won. Previous feedback to keep strengthening: "
                + " ".join(match_rationales)
            )
        else:
            print("Champion defends its title. Discarding challenger.", flush=True)
            feedback_accumulator = "The proposed prompt lost. It failed because: " + " ".join(match_rationales)

        (run_dir / "best_synthesis_prompt.txt").write_text(champ_instruction, encoding="utf-8")

    print("\nPairwise optimization complete.", flush=True)
    print(f"Final prompt saved to {run_dir / 'best_synthesis_prompt.txt'}", flush=True)
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pairwise prompt optimization.",
        parents=[build_pairwise_parser()],
    )
    args = parser.parse_args()
    run_pairwise_optimization_from_args(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
