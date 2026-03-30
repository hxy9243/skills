You’ll remember material more reliably if you study it on separate occasions, with some space in between—rather than if you spend the same amount of time cramming it all in one evening.

To put this another way, successive reinforcements flatten the [Forgetting curve](https://notes.andymatuschak.org/z26AXzY1oNUMSENevADMhGV), so you can wait longer and longer between each review. Well-timed spacings flatten that curve to a greater degree.

[[z2d1qpwddpktbjpnuwyfvva|Spaced repetition memory system]] algorithms taken advantage of this to implement efficient learning systems.

## Optimal spacing

The intersession intervals shouldn’t be increased without bound, since that decreases the likelihood that you’ll remember the material when reviewing, which in turn diminishes the reinforcement effect on your memory. The optimal ISI depends on the retention interval (RI)—the time between the final study session and the test.

Mozer and Lindsey (2016) derive this power-law relationship for individual study sessions from various empirical data sets:  
Optimal ISI = 0.097 \* RI^0.812  
Which has this shape:  
![](https://notes.andymatuschak.org/BearImages/8E197D4A-1C00-4782-8E0D-C2779925029F/16CD74F1-BD28-485D-9BAE-A4C240829927.png)  
It looks roughly linear to me, honestly. Their data sets don’t include anything outside of a 1 year RI, so we shouldn’t trust the function beyond this range.

Also, this function doesn’t seem to fit Cepeda et al 2008’s data very well:  
![](https://notes.andymatuschak.org/BearImages/6A55CB9C-3345-418B-A170-52F4FF8C4FE1/9966CFC2-C6BF-4A9E-A7C2-6282AADB8EA7.png)  
e.g. they found that OISI ~= 5 for RI = 35, but the power law fit finds OISI = 1.8, which empirically performed much worse in that study.

## Collected empirical evidence

Kornel (2009), in an experiment involving GRE-type vocabulary:

> Combining the three experiments, 90% of participants learned more in the spaced conditions than the massed conditions, whereas only 6% of participants showed the reverse pattern.

## Possible explanatory theories for the spacing effect

1. “Encoding variability”: spacing varies the context, which leads to richer, more diverse encodings representing those contexts
2. Spacing demands less concentrated effort and focus than massed study.
3. [Less accessible memories are more reinforced by retrieval](https://notes.andymatuschak.org/zCyRxeMEg53C6mMfXYH2gxn), which may enhance learning via [Two-component model of memory](https://notes.andymatuschak.org/zCgYSHF9xQSEe71x9ML1NLB)
4. “Predictive-utility”: if an item is typically retrieved on a short interval, your mind assumes it’s no longer needed after that interval elapses; longer intervals establish longer periods of need.

---

Q. What term is used in spacing effect studies to refer to the time between sessions?  
A. Intersession interval (ISI)

Q. What does ISI stand for in spacing effect papers?  
A. Intersession interval.

Q. What term is used in spacing effect studies to refer to the time between the final study session and the test?  
A. Retention interval (RI)

Q. Distinguish “intersession interval” and “retention interval” in spacing effect studies.  
A. The former refers to time between study sessions and the latter to the time between the last study session and the test.

Q. What’s the “spacing function” refer to in spacing effect literature?  
A. Recall accuracy as a function of intersession interval

Q. What’s the characteristic shape of the spacing function?  
A. A hill: a relatively sharp initial increase in accuracy followed by a slow decline.

Q. What’s the “optimal ISI” refer to relative to the spacing effect?  
A. The peak of the spacing function: the ISI which produces the highest recall accuracy.

Q. The optimal ISI depends strongly on what other interval?  
A. The retention interval (Cepeda et al, 2006; via Mozer et al, 2009)

Q. What’s the central claim of encoding variability theories for the spacing effect?  
A. Spacing produces better recall because it encodes memory traces with a wider variety of psychological contexts, providing more opportunities for overlap with recall contexts.

Q. Why would having memory traces involving a wider variety of psychological contexts lead to more reliable recall?  
A. Encoding specificity principle

Q. In encoding variability theory, why not increase the ISI without bound to get maximum context variability?  
A. As ISI increases, retrieval becomes lossier because each study context overlaps less with the next.

Q. What’s the central claim of predictive utility theories for the spacing effect?  
A. The mind “learns” how long memories are needed according to their access patterns; longer study intervals encourage longer storage.

---

## References

Branwen, G. (2009). Spaced Repetition for Efficient Learning. Retrieved December 16, 2019, from [https://www.gwern.net/Spaced-repetition](https://www.gwern.net/Spaced-repetition)

Kornell, N. (2009). Optimising learning using flashcards: Spacing is more effective than cramming. Applied Cognitive Psychology, 23(9), 1297–1317. [https://doi.org/10.1002/acp.1537](https://doi.org/10.1002/acp.1537)

[Mozer, M. C., & Lindsey, R. V. (2016). Predicting and Improving Memory Retention: Psychological Theory Matters in the Big Data Era. In M. N. Jones (Ed.), Big data in cognitive science (pp. 34–64).](https://notes.andymatuschak.org/zGXgn3UjMpmMiTtFBxAa8GQ)
