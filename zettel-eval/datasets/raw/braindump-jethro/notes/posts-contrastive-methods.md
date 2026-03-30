Contrastive methods learn representations by contrasting positive and negative examples. This is one of methods used in [Self-supervised Learning](https://braindump.jethro.dev/posts/self_supervised_learning).

The goal is to learn an encoder \\(f\\) such that:

\\begin{equation} \\text{score}(f(x), f(x^{+})) » \\text{score}(f(x), f(x^{-})) \\end{equation}

where \\(x^{+}\\) is a positive example, and \\(x^{-}\\) is a negative example.

#### Links to this note

- [[posts-chen20-simpl-framew-contr-learn-visual-repres|chen20\_simpl\_framew\_contr\_learn\_visual\_repres: A simple framework for contrastive learning of visual representations]]
