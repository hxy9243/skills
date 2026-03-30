SimCLR is a simple framework for [[posts-contrastive-methods|Contrastive Methods]] of visual representations.

## A simple framework for contrastive learning of visual representations

### We do not train the model with a memory bank

Rather than train with a memory bank, they use a large batch size, and the [LARS Optimizer](https://braindump.jethro.dev/posts/lars_optimizer) to stabilize training.

## Key Contributions

- Composition of data augmentation to form positive pairs
- introduce a learnable non-linear transformation between the representation and the contrastive loss substantially improves the quality of the learned representations
- Contrastive learning benefits from larger batch sizes and more training steps compared to supervised learning

## Data Augmentation

A stochastic data augmentation module is introduced to produce two correlated views of the same example, denoted \\(\\tilde{x}\_i\\) and \\(\\tilde{x}\_j\\), which is considered a positive pair. Some of these augmentations include:

- random cropping
- random color distortions
- random Gaussian blur

A neural network encoder \\(f(\\cdot)\\) extracts representation vectors from augmented data examples.

A small network projection head \\(g(\\cdot)\\) maps representations to the space where contrastive loss is applied.

The loss function (normalized temperature-scaled cross entropy loss) is applied on the output of \\(g(\\cdot)\\).

A minibatch of N examples is sampled, resulting in \\(2N\\) data-points. The other 2(N-1) augmented examples within the minibatch is used as negative examples.

\\begin{equation} \\ell\_{i, j}=-\\log \\frac{\\exp \\left(\\operatorname{sim}\\left(\\boldsymbol{z}\_{i}, \\boldsymbol{z}\_{j}\\right) / \\tau\\right)}{\\sum\_{k=1}^{2 N} \\mathbb{1}\_{\[k \\neq i\]} \\exp \\left(\\operatorname{sim}\\left(\\boldsymbol{z}\_{i}, \\boldsymbol{z}\_{k}\\right) / \\tau\\right)} \\end{equation}

## The Importance of the Projection Head

It is conjectured that the projection head \\(g(\\cdot)\\) is important due to loss of information induced by the contrastive loss. \\(z = g(h)\\) is trained to be invariant to the data transformation. Thus \\(g\\) can remove information that may be useful for the downstream task, such as color or orientation of objects.

<biblio.bib>

#### Links to this note

- [[posts-chen-big-2020|chen\_big\_2020: Big Self-Supervised Models are Strong Semi-Supervised Learners]]
