import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set seaborn style for better visuals
sns.set_theme(style="whitegrid")

# Data extracted from summary.md
data = []
# (dataset, method, MAP, Hit@5, Hit@10, MRR)
records = [
    ("andy-matuschak", "bm25", 0.2965, 0.7500, 0.8800, 0.5760),
    ("andy-matuschak", "dense (openai)", 0.3706, 0.7800, 0.9300, 0.6301),
    ("andy-matuschak", "dense (nomic)", 0.1705, 0.5100, 0.6700, 0.3672),
    ("andy-matuschak", "hybrid (openai)", 0.3600, 0.8400, 0.9700, 0.6421),
    ("andy-matuschak", "hybrid (nomic)", 0.3063, 0.7800, 0.8800, 0.5793),
    
    ("braindump-jethro", "bm25", 0.0659, 0.1200, 0.3500, 0.0708),
    ("braindump-jethro", "dense (openai)", 0.3383, 0.5100, 0.5600, 0.3824),
    ("braindump-jethro", "dense (nomic)", 0.1430, 0.2300, 0.2800, 0.1695),
    ("braindump-jethro", "hybrid (openai)", 0.3533, 0.5300, 0.5800, 0.4029),
    ("braindump-jethro", "hybrid (nomic)", 0.2340, 0.4100, 0.4200, 0.2765),

    ("steph-ango", "bm25", 0.1096, 0.2600, 0.3700, 0.1366),
    ("steph-ango", "dense (openai)", 0.2094, 0.3800, 0.4400, 0.2483),
    ("steph-ango", "dense (nomic)", 0.1912, 0.3500, 0.4100, 0.2635),
    ("steph-ango", "hybrid (openai)", 0.2099, 0.3600, 0.4300, 0.2507),
    ("steph-ango", "hybrid (nomic)", 0.2262, 0.3500, 0.4500, 0.2867)
]

for ds, m, m_ap, h5, h10, mrr in records:
    data.append({"Dataset": ds, "Method": m, "Metric": "Hit@10", "Score": h10})
    data.append({"Dataset": ds, "Method": m, "Metric": "MAP", "Score": m_ap})
    data.append({"Dataset": ds, "Method": m, "Metric": "MRR", "Score": mrr})

df = pd.DataFrame(data)

fig, axes = plt.subplots(3, 1, figsize=(10, 15), sharex=False)

metrics = ["Hit@10", "MAP", "MRR"]
titles = ["Hit@10 (Did it find a link in Top 10?)", 
          "Mean Average Precision (Rank-aware Accuracy)", 
          "Mean Reciprocal Rank (Rank of first hit)"]

colors = ["#4c72b0", "#dd8452", "#c44e52", "#55a868", "#8c564b"]

for ax, metric, title in zip(axes, metrics, titles):
    sns.barplot(
        data=df[df["Metric"] == metric],
        x="Dataset", y="Score", hue="Method", ax=ax,
        palette=colors,
        edgecolor=".2"
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_xlabel("")
    
    # Position the legend outside the plot for the first one, hide for others
    if metric == "Hit@10":
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="Retrieval Method")
    else:
        ax.legend().remove()
        
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(f"{height:.2f}", 
                        (p.get_x() + p.get_width() / 2., height),
                        ha='center', va='bottom', 
                        fontsize=9, color='black', xytext=(0, 2),
                        textcoords='offset points')

plt.tight_layout()
plt.savefig("/home/kevin/.openclaw/media/zettel_eval_results.jpg", dpi=300, bbox_inches='tight', format='jpg')
