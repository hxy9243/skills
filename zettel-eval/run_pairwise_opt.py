import sys
import os
os.environ["PYTHONUNBUFFERED"] = "1"
import csv
csv.field_size_limit(sys.maxsize)
from pathlib import Path
import dspy
import random
from datetime import datetime

sys.path.insert(0, "/home/kevin/Workspace/skills/zettel-eval/src")
from zettel_eval.pipeline.dspy_program import BrainstormPipeline, SynthesizeBrainstorm, format_retrieved_notes
from zettel_eval.pipeline.elo_judge import PairwiseEloJudge
from zettel_eval.pipeline.optimize import discover_retrieval_metrics, load_phase2_examples

class ProposeInstruction(dspy.Signature):
    """Propose a new, improved system prompt instruction for an LLM agent that synthesizes brainstorms from Zettelkasten notes.
    The instruction must enforce groundedness, explicitly cite evidence quotes, and maintain logical coherence."""
    current_instruction = dspy.InputField()
    feedback = dspy.InputField(desc="Feedback from the judge on why the previous version lost matches. Address these weaknesses.")
    proposed_instruction = dspy.OutputField(desc="The new proposed instruction (plain text, no markdown blocks).")

def run_pairwise_optimization():
    print("Setting up Pairwise Optimizer LMs...", flush=True)
    task_lm = dspy.LM(model="openai/gpt-5.1-codex-mini", temperature=1.0, max_tokens=16000, cache=False)
    judge_lm = dspy.LM(model="openai/gpt-5.4", temperature=1.0, max_tokens=16000, cache=False)
    dspy.configure(lm=task_lm)

    print("Loading benchmark corpus...", flush=True)
    output_root = Path("/home/kevin/Workspace/skills/zettel-eval/output")
    processed_root = Path("/home/kevin/Workspace/skills/zettel-eval/datasets/processed")
    metrics_path = discover_retrieval_metrics(output_root)
    examples = load_phase2_examples(metrics_path=metrics_path, processed_root=processed_root, max_examples=100)
    
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / "runs" / f"pairwise_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    judge_log = run_dir / "pairwise_eval.csv"
    judge = PairwiseEloJudge(judge_lm=judge_lm, log_file=judge_log)
    proposer = dspy.Predict(ProposeInstruction)
    
    # Start with the baseline instruction
    champ_instruction = "Write a brainstorm essay that synthesizes the seed note and the retrieved notes into a coherent argument."
    
    history_log = run_dir / "optimization_history.log"
    with open(history_log, "w") as f:
        f.write(f"Starting Pairwise Optimization\nInitial Champion Instruction:\n{champ_instruction}\n\n")

    print("Starting Pairwise Optimization Loop (10 Iterations)...", flush=True)
    feedback_accumulator = "We want to improve Innovation, Groundedness, and Coherence. The prompt must explicitly cite sources."

    for i in range(1, 11):
        print(f"\n--- Iteration {i}/10 ---", flush=True)
        
        # 1. Propose new instruction using the smarter Judge LM
        print("Proposing new Challenger instruction...", flush=True)
        with dspy.context(lm=judge_lm):
            proposal = proposer(current_instruction=champ_instruction, feedback=feedback_accumulator)
        
        challenger_instruction = proposal.proposed_instruction.strip()
        print(f"Challenger Proposed:\n{challenger_instruction}\n", flush=True)
        
        # 2. Setup Pipelines
        champ_pipeline = BrainstormPipeline()
        class ChampSynth(SynthesizeBrainstorm):
            __doc__ = champ_instruction
        champ_pipeline.synthesize = dspy.Predict(ChampSynth)
        
        chall_pipeline = BrainstormPipeline()
        class ChallSynth(SynthesizeBrainstorm):
            __doc__ = challenger_instruction
        chall_pipeline.synthesize = dspy.Predict(ChallSynth)
        
        # 3. Evaluate on a batch
        # To keep it reasonably fast, we evaluate on 5 random examples per iteration
        batch = random.sample(examples, min(5, len(examples)))
        
        wins = 0
        losses = 0
        ties = 0
        match_rationales = []
        
        for j, ex in enumerate(batch, 1):
            formatted_notes = format_retrieved_notes(ex.retrieved_notes)
            
            res_champ = champ_pipeline(seed_note=ex.seed_note, retrieved_notes=formatted_notes)
            res_chall = chall_pipeline(seed_note=ex.seed_note, retrieved_notes=formatted_notes)
            
            essay_champ = res_champ.brainstorm_essay
            essay_chall = res_chall.brainstorm_essay
            
            # Blind A/B
            is_chall_a = random.choice([True, False])
            if is_chall_a:
                winner, rationale = judge.compare(
                    seed_note=ex.seed_note, retrieved_notes=formatted_notes,
                    essay_a=essay_chall, essay_b=essay_champ
                )
                if winner == "A":
                    wins += 1
                    match_rationales.append(f"Challenger Won: {rationale}")
                elif winner == "B":
                    losses += 1
                    match_rationales.append(f"Champion Won: {rationale}")
                else:
                    ties += 1
                    match_rationales.append(f"Tie: {rationale}")
            else:
                winner, rationale = judge.compare(
                    seed_note=ex.seed_note, retrieved_notes=formatted_notes,
                    essay_a=essay_champ, essay_b=essay_chall
                )
                if winner == "B":
                    wins += 1
                    match_rationales.append(f"Challenger Won: {rationale}")
                elif winner == "A":
                    losses += 1
                    match_rationales.append(f"Champion Won: {rationale}")
                else:
                    ties += 1
                    match_rationales.append(f"Tie: {rationale}")

        print(f"Result: Challenger {wins} Wins, {losses} Losses, {ties} Ties", flush=True)
        
        with open(history_log, "a") as f:
            f.write(f"Iteration {i} Results: W:{wins} L:{losses} T:{ties}\n")
            f.write(f"Challenger Prompt:\n{challenger_instruction}\n")
            f.write("Rationales:\n" + "\n".join(match_rationales) + "\n\n")
        
        if wins > losses:
            print("🏆 Challenger dethrones Champion! Updating baseline.", flush=True)
            champ_instruction = challenger_instruction
            feedback_accumulator = "The new prompt won! Previous feedback to keep strengthening: " + " ".join(match_rationales)
        else:
            print("🛡️ Champion defends its title. Discarding Challenger.", flush=True)
            feedback_accumulator = "The proposed prompt lost. It failed because: " + " ".join(match_rationales)

        # Save current best prompt
        with open(run_dir / "best_synthesis_prompt.txt", "w") as f:
            f.write(champ_instruction)
            
    print("\nPairwise Optimization Complete!", flush=True)
    print(f"Final prompt saved to {run_dir / 'best_synthesis_prompt.txt'}", flush=True)

if __name__ == "__main__":
    run_pairwise_optimization()
