import re
import matplotlib.pyplot as plt
import seaborn as sns

scores = []
with open("/home/kevin/Workspace/skills/zettel-eval/output/pipeline.log", "r") as f:
    for line in f:
        if "Scores so far:" in line:
            m = re.search(r"\[(.*?)\]", line)
            if m:
                scores = [float(x) for x in m.group(1).split(",")]

if not scores:
    print("Could not find scores in log.")
else:
    best_scores = []
    current_best = 0.0
    for s in scores:
        if s > current_best:
            current_best = s
        best_scores.append(current_best)

    trials = list(range(len(scores)))

    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    plt.plot(trials, scores, marker='o', label='Trial Score (0-100)', color='#1f77b4', linestyle=':', alpha=0.6)
    plt.plot(trials, best_scores, marker='s', label='Cumulative Best Score', color='#ff7f0e', linewidth=3)
    
    plt.title('DSPy LLM Optimization: Best Score Progression', fontsize=16, fontweight='bold')
    plt.xlabel('Optimization Trial', fontsize=12)
    plt.ylabel('Score (Percent)', fontsize=12)
    plt.xticks(trials)
    plt.legend(loc='lower right', fontsize=11)
    
    plt.annotate(f"{best_scores[-1]:.1f}%", (trials[-1], best_scores[-1]), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#ff7f0e')

    plt.tight_layout()
    plt.savefig('/home/kevin/.openclaw/media/dspy_best_score.jpg', dpi=300)
