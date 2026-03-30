## Formula

**Forgetting curve** describes the decline in the probability of [recall](https://supermemo.guru/wiki/Recall "Recall") over time (source: [Wozniak, Gorzelanczyk, Murakowski, 1995](http://www.super-memory.com/english/2vm.htm)):

**R=exp <sup>(-t/S)</sup>**

where:

- **R** - probability of recall ([retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability") of memory)
- **S** - *strength* of a memory trace ([stability](https://supermemo.guru/wiki/Stability "Stability") of memory)
- t - time

  

## Explanation

In a mass of remembered details, the shape of the forgetting curve will depend on (1) [memory complexity](https://supermemo.guru/wiki/Memory_complexity "Memory complexity") (i.e. how difficult it is to uniformly bring individual knowledge details from memory), and (2) [memory stability](https://supermemo.guru/wiki/Stability "Stability") (i.e. how well individual details have been established in memory). For example, a set of easy French words, memorized on the same day, may align into a curve that meets the above formula. Those French words will have low complexity (because they are easy), and low stability (because they have just been learned). Those French words will be lost to memory, one by one, at equal probability over time. The chance of recalling a given word will be R ([retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability")) after time t. With time going to infinity, the [recall](https://supermemo.guru/wiki/Recall "Recall") will approach zero. However, if all words are reviewed again, their stability will increase and [retention](https://supermemo.guru/wiki/Retention "Retention") time will be extended. This is used in [spaced repetition](https://supermemo.guru/wiki/Spaced_repetition "Spaced repetition") to minimize the cost of an indefinite retention of memories.

## Power or Exponential?

Forgetting is exponential, however, superposition of forgetting rates for different [stabilities](https://supermemo.guru/wiki/Stability "Stability") will make forgetting follow the power law. In other words, when memories of different [complexity](https://supermemo.guru/wiki/Memory_complexity "Memory complexity") are mixed, the forgetting curve will change its shape, and may be better approximated with a negative power function (as originally [discovered by Hermann Ebbinghaus in 1885](https://supermemo.guru/wiki/Error_of_Ebbinghaus_forgetting_curve "Error of Ebbinghaus forgetting curve")). Plotting the forgetting curve for memories of different stability is of less interest. It can be compared to establishing a single expiration date for products of different shelf life produced at different times. Power approximations face the problem of t=0 point. On the other hand, exponential forgetting may seem devastating in its power. Luckily, for [well-formulated material](https://supermemo.guru/wiki/20_rules "20 rules"), decay constants are very low due to high [memory stabilities](https://supermemo.guru/wiki/Stability "Stability") developed after just a few reviews.

**Forgetting is exponential** due to the random nature of memory [interference](https://supermemo.guru/wiki/Interference "Interference")

For more see: [Exponential nature of forgetting](https://supermemo.guru/wiki/Exponential_nature_of_forgetting "Exponential nature of forgetting")

## Data

[Spaced repetition](https://supermemo.guru/wiki/Spaced_repetition "Spaced repetition") software [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo") routinely collects data and displays a set of forgetting curves that depend on memory [stability](https://supermemo.guru/wiki/Stability "Stability") and [knowledge complexity](https://supermemo.guru/wiki/Memory_complexity "Memory complexity"). Each user and each knowledge [collection](https://supermemo.guru/wiki/Collection "Collection") are assigned a set of 400 forgetting curves for different combinations of [stability](https://supermemo.guru/wiki/Stability "Stability") and [complexity](https://supermemo.guru/wiki/Complexity "Complexity") levels. In addition, newer SuperMemos keep 400 curves where time is expressed by memory [retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability") estimate. This rich dataset helps [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo") keep an accurate model of each student's memory.

Examples of curves collected with SuperMemo:

- [Power curve for the first review of heterogeneous knowledge](http://help.supermemo.org/wiki/File:First_forgetting_curve.jpg)
- [Exponential curve for the second review of homogeneous knowledge](http://help.supermemo.org/wiki/File:Forgetting_curves.jpg)
- [Cumulative normalized curve for different levels of stability and memory complexity](http://help.supermemo.org/wiki/File:Cumulative_forgetting_curve.jpg) (over 214,000 data points taken from over 380,000 repetitions)
- [3D curve for various levels of stability](http://help.supermemo.org/wiki/File:Recall.jpg) ([retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability") log axis reversed in reference to time)

See also:

- [Error of Ebbinghaus forgetting curve](https://supermemo.guru/wiki/Error_of_Ebbinghaus_forgetting_curve "Error of Ebbinghaus forgetting curve")
- [Stabilization curve](https://supermemo.guru/wiki/Stabilization_curve "Stabilization curve")
- [Bad forgetting curves](https://supermemo.guru/wiki/Bad_forgetting_curves "Bad forgetting curves")
- [Two component model of long-term memory](https://supermemo.guru/wiki/Two_component_model_of_long-term_memory "Two component model of long-term memory")

This text is a part of a series of articles about [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo"), a pioneer of [spaced repetition](https://supermemo.guru/wiki/Spaced_repetition "Spaced repetition") software since [1987](https://supermemo.guru/wiki/History_of_spaced_repetition_\(print\) "History of spaced repetition (print)")

## Examples

![](https://supermemo.guru/images/thumb/2/26/First_forgetting_curve_in_Algorithm_SM-19_%28SuperMemo%29.jpg/600px-First_forgetting_curve_in_Algorithm_SM-19_%28SuperMemo%29.jpg)

Forgetting curve collected with SuperMemo 17

> ***Figure:** The [first forgetting curve](https://supermemo.guru/wiki/First_forgetting_curve "First forgetting curve") for newly learned knowledge collected with [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo"). Power approximation is used in this case due to the heterogeneity of the learning material freshly introduced in the learning process. Lack of separation by [memory complexity](https://supermemo.guru/wiki/Memory_complexity "Memory complexity") results in superposition of exponential forgetting with different decay constants. On a semi-log graph, the power regression curve is logarithmic (in yellow), and appearing almost straight. The curve shows that in the presented case recall drops merely to 58% in four years, which can be explained by a high reuse of memorized knowledge in real life. The first [optimum interval](https://supermemo.guru/wiki/Optimum_interval "Optimum interval") for review at [retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability") of 90% is 3.96 days. The forgetting curve can be described with the formula R=0.9906\*power(interval,-0.07), where 0.9906 is the recall after one day, while -0.07 is the decay constant. In this is case, the formula yields 90% recall after 4 days. 80,399 repetition cases were used to plot the presented graph. Steeper drop in recall will occur if the material contains a higher proportion of [difficult](https://supermemo.guru/wiki/Memory_complexity "Memory complexity") knowledge (esp. [poorly formulated knowledge](https://supermemo.guru/wiki/20_rules "20 rules")), or in new students with lesser mnemonic skills. Curve irregularity at intervals 15-20 comes from a smaller sample of repetitions (later interval categories on a log scale encompass a wider range of intervals)*

![](https://supermemo.guru/images/thumb/6/69/Exponential_forgetting_curve.jpg/600px-Exponential_forgetting_curve.jpg)

Exponential forgetting curve collected with SuperMemo 17

> ***Figure:** Exponential forgetting curve for [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo") learning material after an equivalent of 6th [optimum interval](https://supermemo.guru/wiki/Optimum_interval "Optimum interval") review. 14,550 repetitions have been used to plot the presented graph*

![](https://supermemo.guru/images/thumb/2/21/Cumulative_forgetting_curve.jpg/600px-Cumulative_forgetting_curve.jpg)

Cumulative forgetting curve collected with SuperMemo 17

> **Figure:** *Cumulative forgetting curve for learning material of mixed [complexity](https://supermemo.guru/wiki/Complexity "Complexity"), and mixed [stability](https://supermemo.guru/wiki/Stability "Stability"). The graph is obtained by superposition of 400 forgetting curves normalized for the decay constant of 0.003567, which corresponds with recall of 70% at 100% of the presented time span (i.e. [R](https://supermemo.guru/wiki/Retrievability "Retrievability") =70% on the right edge of the graph). 401,828 repetition cases have been included in the graph. Individual curves are represented by yellow data points. Cumulative curve is represented by blue data points that show the average recall for all 400 curves. The size of circles corresponds with the size of data samples.*

![A forgetting curve from a preschooler's SuperMemo collection](https://supermemo.guru/images/thumb/5/56/Forgetting_curve_from_preschoolers_SuperMemo_collection.jpg/600px-Forgetting_curve_from_preschoolers_SuperMemo_collection.jpg)

A forgetting curve from a preschooler's SuperMemo collection

> ***Figure:** A forgetting curve from a preschooler's [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo") [collection](https://supermemo.guru/wiki/Collection "Collection"). The absence of [forgetting](https://supermemo.guru/wiki/Forgetting "Forgetting") indicates the absence of intentional [declarative learning](https://supermemo.guru/wiki/Declarative_learning "Declarative learning"). The decay constant is nearly zero which makes [optimum interval](https://supermemo.guru/wiki/Optimum_interval "Optimum interval") meaningless. 1706 repetition cases have been recorded. This flat forgetting curve would go unnoticed in older versions of SuperMemo due to the adult-centric assumption that on Day=0, [retrievability](https://supermemo.guru/wiki/Retrievability "Retrievability") is 100%. Overtime, this forgetting curve will lean down to produce a graph typical of adult learning. This process may take a few years and should not be artificially accelerated, e.g. by means of [coercion](https://supermemo.guru/wiki/Coercion "Coercion"). This curve is a hypothetical expression of the [semantic brain](https://supermemo.guru/wiki/Semantic_brain "Semantic brain")*

![](https://supermemo.guru/images/thumb/f/f1/Forgetting_curve_in_coercive_learning.png/600px-Forgetting_curve_in_coercive_learning.png)

> ***Figure:** Good educators know that [you cannot motivate a child extrinsically](https://supermemo.guru/wiki/You_cannot_motivate_a_child_extrinsically "You cannot motivate a child extrinsically"). Poor [intrinsic motivation](https://supermemo.guru/wiki/Intrinsic_motivation "Intrinsic motivation"), and poor mnemonic skills make [SuperMemo unsuitable for children](https://supermemo.guru/wiki/SuperMemo_does_not_work_for_kids "SuperMemo does not work for kids"). In the presented case, a forgetting curve shows a catastrophically poor performance in a 7-year-old child coerced to learn vocabulary of a foreign language. This is a classic case of [asemantic learning](https://supermemo.guru/wiki/Asemantic_learning "Asemantic learning"). The curve bears no relevance to a child's IQ. At this age, some kids may already show some success, as long as the use of [SuperMemo](https://supermemo.guru/wiki/SuperMemo "SuperMemo") is entirely voluntary*
