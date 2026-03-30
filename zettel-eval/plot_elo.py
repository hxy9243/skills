import matplotlib.pyplot as plt
import seaborn as sns

# Elo ratings parsed from tournament.log
elo_opt = [1200]
elo_base = [1200]

with open("/home/kevin/Workspace/skills/zettel-eval/tournament.log", "r") as f:
    for line in f:
        if "Current Elo" in line:
            parts = line.strip().split("|")
            opt_val = int(parts[0].split(":")[1].strip())
            base_val = int(parts[1].split(":")[1].strip())
            elo_opt.append(opt_val)
            elo_base.append(base_val)

matches = list(range(len(elo_opt)))

plt.figure(figsize=(10, 6))
sns.set_theme(style="whitegrid")

plt.plot(matches, elo_opt, marker='o', label='Optimized Prompt', color='#2ca02c', linewidth=2.5, markersize=8)
plt.plot(matches, elo_base, marker='X', label='Baseline Prompt', color='#d62728', linewidth=2.5, markersize=8)

plt.axhline(1200, color='gray', linestyle='--', alpha=0.5, label="Starting Elo (1200)")

plt.title('Elo Tournament Trajectory (Optimized vs Baseline)', fontsize=16, fontweight='bold')
plt.xlabel('Match Number', fontsize=12)
plt.ylabel('Elo Rating', fontsize=12)
plt.xticks(matches)
plt.legend(loc='upper left', fontsize=11)

# Annotate final points
plt.annotate(f"{elo_opt[-1]}", (matches[-1], elo_opt[-1]), textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#2ca02c')
plt.annotate(f"{elo_base[-1]}", (matches[-1], elo_base[-1]), textcoords="offset points", xytext=(0,-15), ha='center', fontweight='bold', color='#d62728')

plt.tight_layout()
plt.savefig('/home/kevin/.openclaw/media/elo_trajectory.jpg', dpi=300)
