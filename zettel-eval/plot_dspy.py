import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('/home/kevin/Workspace/skills/zettel-eval/output/runs/20260329-124458/filter_eval.csv', names=[
    'seed', 'essay', 'innovation', 'groundedness', 'coherence', 'normalized_score', 'summary'
], skiprows=1)

df['innovation'] = pd.to_numeric(df['innovation'], errors='coerce')
df['groundedness'] = pd.to_numeric(df['groundedness'], errors='coerce')
df['coherence'] = pd.to_numeric(df['coherence'], errors='coerce')
df['normalized_score'] = pd.to_numeric(df['normalized_score'], errors='coerce')

df['Trial'] = (df.index // 4)

trial_scores = df.groupby('Trial')[['innovation', 'groundedness', 'coherence', 'normalized_score']].mean().reset_index()

plt.figure(figsize=(12, 7))
sns.lineplot(data=trial_scores, x='Trial', y='normalized_score', marker='o', color='#4c72b0', label='Total Normalized Score (0-1)')
sns.lineplot(data=trial_scores, x='Trial', y='innovation', marker='s', color='#dd8452', label='Innovation (0-5)')
sns.lineplot(data=trial_scores, x='Trial', y='groundedness', marker='^', color='#55a868', label='Groundedness (0-5)')
sns.lineplot(data=trial_scores, x='Trial', y='coherence', marker='x', color='#c44e52', label='Coherence (0-5)')

plt.title('DSPy End-to-End Optimization Trajectory (20 Trials)', fontsize=16, fontweight='bold')
plt.xlabel('Optimization Trial', fontsize=12)
plt.ylabel('Average Score', fontsize=12)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.ylim(0, 5.5)
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/home/kevin/.openclaw/media/dspy_optimization.jpg', dpi=300)
