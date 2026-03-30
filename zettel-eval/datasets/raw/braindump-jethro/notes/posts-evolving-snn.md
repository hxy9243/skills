Early evolving [Spiking Neural Networks](https://braindump.jethro.dev/posts/spiking_neurons_lit_review) architectures use the [Leaky Integrate-And-Fire](https://braindump.jethro.dev/posts/leaky_integrate_and_fire) model, and rank-order encoding. eSNNs can be used for classification. Given an input sample, the spike train is propagated through the SNN, resulting in the firing of output neurons. If no output neuron is activated, the classification result is undetermined. If one or more output neurons emit a spike, the label of the neuron with the shortest response time represents the classification result.

## Training an eSNN

For each class label an individual repository is evolved. A new output neuron is created and fully connected to the previous layer of neurons. Input spikes are propagated through the network, and the weight vector for the neuron is computed, along with its firing threshold. This weight vector is compared to existing neurons in the repository. If neurons are too similar (e.g. small Euclidean distance between weight vectors), they are merged.

See ([[posts-evolving-snn|Schliebs and Kasabov, n.d.]]) for a comprehensive review.

## Bibliography

Schliebs, Stefan, and Nikola Kasabov. n.d. “Evolving Spiking Neural Network-a Survey” 4 (2):87–98. [https://doi.org/10.1007/s12530-013-9074-9](https://doi.org/10.1007/s12530-013-9074-9).

#### Links to this note

- [[posts-evolving-connectionist-systems|Evolving Connectionist Systems]]
