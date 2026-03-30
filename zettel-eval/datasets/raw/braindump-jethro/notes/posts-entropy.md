tags

[Information Theory](https://braindump.jethro.dev/posts/information_theory), [Gibbs’ Inequality](https://braindump.jethro.dev/posts/gibbs_inequality)

## Definitions

The Shannon information content of an outcome \\(x\\), measured in bits, is defined to be:

\\begin{equation} h(x) = \\log\_2 \\frac{1}{P(x)} \\end{equation}

The entropy of an ensemble \\(X\\) is defined to be the average Shannon information content of an outcome:

\\begin{equation} H(X)\\equiv \\sum\_{x \\in \\mathcal{A}\_X} P(x) \\log \\frac{1}{P(x)} \\end{equation}

Entropy is 0 when the outcome is deterministic, and maximized with value \\(\\log(|\\mathcal{A}\_X|)\\) when the outcomes are uniformly distributed.

The *joint entropy* of two ensembles \\(X, Y\\) is:

\\begin{equation} H(X,Y) \\equiv \\sum\_{x,y \\in \\mathcal{A}\_x \\mathcal{A}\_y} P(x,y) \\log \\frac{1}{P(x,y)} \\end{equation}

Entropy is additive if the ensembles are independent:

\\begin{equation} H(X,Y) = H(X) + H(Y) \\end{equation}

Entropy is *decomposable*.

#### Links to this note

- [[posts-actor-critic|Actor-Critic]]
- [[posts-artificial-intelligence|Artificial Intelligence]]
- [[posts-bayesian-deep-learning|Bayesian Deep Learning]]
- [[posts-chen20-simpl-framew-contr-learn-visual-repres|chen20\_simpl\_framew\_contr\_learn\_visual\_repres: A simple framework for contrastive learning of visual representations]]
- [[posts-deep-learning|Deep Learning]]
- [[posts-dl-tools|Deep Learning Tools]]
- [[posts-emti-dl-with-bayesian-principles|Deep Learning With Bayesian Principles - Emtiyaz Khan]]
- [Gibbs' Inequality](https://braindump.jethro.dev/posts/gibbs_inequality)
- [Information Theory](https://braindump.jethro.dev/posts/information_theory)
- [Information-Theoretic Reinforcement Learning](https://braindump.jethro.dev/posts/information_theoretic_reinforcement_learning)
- [Inverse Reinforcement Learning](https://braindump.jethro.dev/posts/inverse_rl)
- [Machine Learning](https://braindump.jethro.dev/posts/machine_learning)
- [Model-Based Reinforcement Learning](https://braindump.jethro.dev/posts/model_based_rl)
- [Natural Language Processing](https://braindump.jethro.dev/posts/nlp)
- [Optimal Control and Planning](https://braindump.jethro.dev/posts/optimal_control)
- [Probabilistic Graph Models](https://braindump.jethro.dev/posts/pgm)
- [Q-Learning](https://braindump.jethro.dev/posts/q_learning)
- [Temp Coding with Alpha Synaptic Function](https://braindump.jethro.dev/posts/comsa2019_temp_coding)
- [Transfer Learning](https://braindump.jethro.dev/posts/transfer_learning)
- [Transformer Models](https://braindump.jethro.dev/posts/transformer_models)
