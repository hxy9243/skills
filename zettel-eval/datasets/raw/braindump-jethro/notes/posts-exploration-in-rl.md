In [Reinforcement Learning ⭐](https://braindump.jethro.dev/posts/reinforcement_learning), exploration is important where rewards are sparse, and not a direct indication of how good an action is. Some environments where good exploration is necessary is Montezuma’s revenge, where finishing a game only weakly correlates with rewarding events.

Key Questions:

1. How can an agent discover high-reward strategies that require a temporally-extended sequence of complex behaviours that, individually, are not rewarding?
2. How can an agent decide whether to attempt new behaviours or continue to do the best thing it knows so far?
3. Is there an *optimal* exploration strategy?

In order of theoretical tractability (tractable to intractable):

1. multi-armed bandits (1-step stateless RL problems): can be formailized as POMDP identification
2. contextual bandits (1-step RL problems): policy learning is trivial even with POMDP
3. small, finite MDPs (tractable planning, model-based RL setting): can frame as Bayesian model identification, reason explicitly about value of information
4. large, infinite MDPs, continuous spaces: optimal methods don’t work

## General Themes in Exploration

- Requires some form of uncertainty
- Assumes:
	- Unknown is good (optimism)
		- Sample = Truth
		- information gain is good

## Exploration in Bandits

### Optimistic Exploration

Keep track of average reward \\(\\hat{\\mu}\_a\\) for each action \\(a\\), and choose $a = \\mathrm{argmax} \\hat{\\mu}\_a + Cσ\_a$for some variance estimate \\(\\sigma\_a\\). This method is model-free.

### Posterior/Thompson Sampling

Here, we assume $r(a\_i) ∼ p <sub>θ_i</sub> (r\_i), defining a POMDP with \\(s = \\left\[\\theta\_1, \\dots, \\theta\_n \\right\]\\), and we have a belief over the states.

Thompson sampling does this:

1. sample \\(\\theta\_1, \\dots, \\theta\_n \\sim \\hat{p}(\\theta\_1, \\dots, \\theta\_n)\\)
2. pretend the model \\(\\theta\_1, \\dots, \\theta\_n\\) is correct
3. take the optimal action
4. update the model

Thompson sampling is hard to analyze theoretically, but can work well empirically.

### Information Gain

\\begin{equation} IG(z, y|a) = E\_y\\left\[ \\mathcal{H}(\\hat{p}(z)) - \\mathcal{H}(\\hat{p}(z)|y)|a \\right\] \\end{equation}

is how much we learn about \\(z\\) from action \\(a\\), given current beliefs

If we have \\(\\Delta(a) = E\[r(a^\\star) - r(a)\]\\), the expected suboptimality of \\(a\\), and \\(g(a) = IG(\\theta\_a, r\_a | a)\\), then we can choose \\(a\\) according to \\(\\mathrm{argmin}\_a \\frac{\\Delta(a)^2}{g(a)}\\).

### Upper Confidence Bound

\\begin{equation} a = \\mathrm{argmax} \\hat{\\mu}\_a + \\sqrt{\\frac{2 \\ln T}{N(a)}} \\end{equation}

## Extending Exploration to RL

### Count-based exploration ()

Use pseudo-counts:

\\begin{equation} r\_i^+ = r\_i + \\mathcal{B}(\\hat{N}(s)) \\end{equation}

There are many choices for the bonus.

## Bibliography

Bellemare, Marc, Sriram Srinivasan, Georg Ostrovski, Tom Schaul, David Saxton, and Remi Munos. n.d. “Unifying Count-Based Exploration and Intrinsic Motivation.” In *Advances in Neural Information Processing Systems 29*, edited by D. D. Lee, M. Sugiyama, U. V. Luxburg, I. Guyon, and R. Garnett, 1471–79. Curran Associates, Inc. [http://papers.nips.cc/paper/6383-unifying-count-based-exploration-and-intrinsic-motivation.pdf](http://papers.nips.cc/paper/6383-unifying-count-based-exploration-and-intrinsic-motivation.pdf).
