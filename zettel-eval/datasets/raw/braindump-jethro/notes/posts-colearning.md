Co-learning is the technique of aiding of modeling of a (resource-poor) modality by exploiting knowledge from another (resource-rich) modality. The helper modality is only used in model training, and is not used during test-time. ([[posts-colearning|Baltrušaitis, Ahuja, and Morency, n.d.]])

Parallel-data approaches require the data to be directly linked to observations in other modalites. Non-parallel approaches do not require these direct links between modalities. Hybrid-data approaches bridge the modalities through a shared modality, or a dataset.

## Parallel data

Co-training is the process of creating more labeled training samples when we have few labeled samples in a multi-modal problem. Weak classifiers are built for each modality to bootstrap each other with labels for the unlabeled data.

[Transfer learning](https://braindump.jethro.dev/posts/transfer_learning) exploits co-learning with parallel data, by building [multi-modal representations](https://braindump.jethro.dev/posts/multimodal_representation) with only some modalities used during test time. Approaches like these include multimodal [[posts-deep-boltzmann-machines|Deep Boltzmann Machines]] and [Multi-modal Autoencoders](https://braindump.jethro.dev/posts/multimodal_autoencoders).

## Non-parallel data

Non-parallel methods only require that different modalities share similar categories or concepts. Methods include [transfer learning](https://braindump.jethro.dev/posts/transfer_learning) using coordinated multimodal representations, or [[posts-concept-grounding|Concept Grounding]] via word similarity, or [zero-shot learning](https://braindump.jethro.dev/posts/zeroshot_learning).

## Bibliography

Baltrušaitis, Tadas, Chaitanya Ahuja, and Louis-Philippe Morency. n.d. “Multimodal Machine Learning: A Survey and Taxonomy.” [http://arxiv.org/abs/1705.09406v2](http://arxiv.org/abs/1705.09406v2).

#### Links to this note

- [Multi-modal Machine Learning](https://braindump.jethro.dev/posts/multimodal_machine_learning)
