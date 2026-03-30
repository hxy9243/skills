In using a [[z2d1qpwddpktbjpnuwyfvva|Spaced repetition memory system]], you’ll fill it with notes on what you’re learning, observing, and thinking. Unfortunately, [Existing spaced repetition systems discourage evergreen notes](https://notes.andymatuschak.org/zMXZQANJPzCDUFPrUAYAFrn). A memory system will help you retain and continuously engage with what you write, but it won’t much help you build on those ideas over time. An [[z5e5qawixcmbtntupvxeoex|Evergreen notes]] system will help you build on your ideas over time, but it won’t help you retain and continuously engage with those notes (outside of [[zwbmsefw9ld4vsovhadcf4u|Evergreen note maintenance approximates spaced repetition]]). So you’re stuck either duplicating your efforts messily in two separate systems, or giving up one system’s benefits.

The [[zkpv6qkserdrgqyryvgs2ws|Mnemonic medium]] solved a similar problem for published prose: [[z8e98xn7t5qnhr5cf8oqjbj|The mnemonic medium gives structure to normally-atomized spaced repetition memory prompts]]. One can use the same approach to give structure to one’s personal spaced repetition prompts, within one’s personal notes. We can call this a { **personal mnemonic medium** }.

For example, one could imagine creating a {cloze deletion} prompt within one’s personal notes by {wrapping it in curly braces}.

And one might create a traditional two-sided prompt like this:  
Q. If one only took notes in Anki, what key limitations might one experience?  
A. (e.g. no serendipitous note-finding when note-writing, no way to easily evolve notes over time, limited connections between notes, difficult to “read through” one’s notes on a subject, etc)

- [Anki seems to make it harder to “sketch” and revise prompts](https://notes.andymatuschak.org/zXiWsZY761uNMUKeMEqNVqi)

## Implementations

There are a few other implementations of something like this idea:

- Importers into external SRS
	- [My implementation of a personal mnemonic medium](https://notes.andymatuschak.org/z6sX7ZcYdPiya3SzQ5segaq)
		- [Obisidan *to* Anki](https://github.com/Pseudonium/Obsidian_to_Anki). Requires some manual steps.
		- [Ankify](https://github.com/kangruixiang/Ankify), which requires manual steps—not meant to run automatically in the background.
- Uses integrated SRS
	- [RemNote](https://notes.andymatuschak.org/zvZiz35n9aN8RJSEoa4yE5), an increasingly polished webapp implementation
		- [Mochi](https://notes.andymatuschak.org/zMxXQHmTuLN9mKA46RPpqJs), whose interactions de-emphasize writing prose notes
		- [org-fc](https://www.leonrische.me/fc/index.html), a polished implementation for org-mode
		- [TiddlyRemember](https://github.com/sobjornstad/TiddlyRemember), syncs with TiddlyWiki using some custom markup; requires a manual sync step, by [Soren Bjornstad](https://notes.andymatuschak.org/zB2cf1tzHqvLRg5Px4rBNbq)
		- [Fishing — v2.0.2](https://oflg.github.io/fishing) another TiddlyWiki-based implementation

---

## References

Nielsen, M. (2018). *Augmenting Long-term Memory*. [http://augmentingcognition.com/ltm.html](http://augmentingcognition.com/ltm.html)

> I start to identify open problems, questions that I’d personally like answered, but which don’t yet seem to have been answered. I identify tricks, observations that seem pregnant with possibility, but whose import I don’t yet know. And, sometimes, I identify what seem to me to be field-wide blind spots. I add questions about all these to Anki as well. In this way, Anki is a medium supporting my creative research. It has some shortcomings as such a medium, since it’s not designed with supporting creative work in mind – it’s not, for instance, equipped for lengthy, free-form exploration inside a scratch space.
