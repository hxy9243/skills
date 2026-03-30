[[zjowjeprvrjnm2zl3gdxbjg|The mnemonic medium can help readers apply what they’ve learned through simple application prompts]]. With such prompts implemented, to what extent does one also need traditional atomic recall prompts?

Imagine that we’re in a high school calculus course, and you’ve just learned that `e` is the function whose derivative is itself. If that lesson were written in the [[zkpv6qkserdrgqyryvgs2ws|Mnemonic medium]], we might ask these recall prompts:

> Q. What function is its own derivative?  
> A. `e`  
> Q. What is the derivative of `f(x) = e^x`?  
> A. `e^x`

But we could also imagine framing this as an application prompt.

> Q. What’s the derivative of `e^8x`?  
> A. `8e^8x` Explanation: the derivative of e^x is itself

If we gave them just this one question, I wouldn’t necessarily expect their declarative knowledge of `e` to end up solid: they’d likely end up memorizing the answer to this question. [Application prompts should vary when repeated](https://notes.andymatuschak.org/zSisETSpZBCgZH4rFNHRcnC), so imagine that instead we also ask a bunch of variants like:

> Q. Let `f(x) = 14e^[x]`. What is `df/dx`?  
> A. `14e^[x]` Explanation: the derivative of e^x is itself

Imagine that the reader can solve this problem and also half a dozen other variants, and now a month has passed since the original lesson. Let’s return to the recall prompts we proposed. Would we expect the reader to recall: “What function is its own derivative?” I think it’s reasonably likely… but I suspect the variants’ accuracies would correlate more highly with each other than with the accuracy on that recall prompt.

Understanding `e` in terms of its conceptual properties is different from understanding `e` in procedural terms. I suspect that including both types of questions will probably lead to richer elaborative encodings.

Now, would we expect the reader to be able to answer the proposed recall prompt: “What is the derivative of `f(x) = e^x`?” I’d expect so, with high likelihood: that question can be interpreted as a trivial application prompt, after all, and the reader already solved harder variants.

Does this mean that this recall prompt is unnecessary in the presence of those application prompts? Consider: what if the reader *hadn’t* been able to answer those application prompts consistently? The first variant required also applying the chain rule (and the knowledge that `d[kx]/dx = kx`). The second variant required also understanding the syntax `df/dx`. These are more complex problems.

When a reader forgets the answer to a recall prompt, they look at the answer and try to remember it for next time. If the questions are atomic and the schedule well-calibrated, this will usually work! But if a reader can’t answer an application prompt, they can’t just look at the answer and try to remember it for next time: [Answers to application prompts shouldn’t be drawn from memory](https://notes.andymatuschak.org/zXAYq9zGTGq99CqwBtLwyGq). They have to analyze the answer (possibly including its explanation), discern what they didn’t remember, and try to recall that piece next time. This is much more difficult than what’s needed for a recall prompt. A reader who was still shaky on the chain rule might pay little attention to their inability to recall the derivative of `e^x`. Without separate recall-oriented prompts, their answers on this application prompt might remain unreliable for quite some time.

It would be very interesting to run empirical experiments on this topic! How are readers’ application prompt accuracies impacted when the related recall prompts are held out?

One interesting empirical example is [Execute Program](https://notes.andymatuschak.org/zSsjk5UvNPGrYp8B6DEFCMS): [Execute Program’s prompts act both as application prompts and recall prompts](https://notes.andymatuschak.org/zUoZHzEPeQFKaUTYctg9fqq).
