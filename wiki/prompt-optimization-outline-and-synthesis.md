# Prompt Optimization: Outline and Synthesis

This synthesis was compiled from the notebook at `/home/kevin/Documents/kevinhusnotes` using the workflow in [`wiki/SKILL.md`](/home/kevin/Workspace/skills/wiki/SKILL.md) and the search guidance in [`wiki/agents/search.md`](/home/kevin/Workspace/skills/wiki/agents/search.md).

## Scope

Across these notes, `prompt engineering` is the broad craft of getting a model to do useful work, `prompt optimization` is the systematic search and evaluation of better prompts or harnesses, and `prompt tuning` is the narrower gradient-based or parameterized optimization family. The notebook also extends the topic beyond prompt text into full `agent harness` optimization: system prompts, tool schemas, retrieval logic, and workflow constraints.

## Most Relevant Notes

- `10_Projects/Notes on DSPy Agentic Research.md`
- `20_Subjects/Computer Science/Machine Learning/GEPA - Reflective Prompt Evolution.md`
- `20_Subjects/Computer Science/Machine Learning/GEPA Automatically Learning Skills for Coding Agents.md`
- `10_Projects/Zettel_Eval_Experiment_Log.md`
- `10_Projects/Zettel_Brainstormer_Roadmap.md`
- `20_Subjects/Computer Science/Artificial Intelligence/AI Agents/Optimization/Meta-Harness.md`
- `20_Subjects/Computer Science/Machine Learning/NLP and LLM/Welcome  Learn Prompting.md`
- `20_Subjects/Computer Science/Machine Learning/NLP and LLM/Prompt Engineering Guide  Prompt Engineering Guide.md`
- `20_Subjects/Computer Science/Papers/Large Language Models as Optimizers.md`
- `20_Subjects/Computer Science/Artificial Intelligence/AI Agents/Frameworks/Building Effective AI Agents.md`
- `20_Subjects/Computer Science/Artificial Intelligence/AI Agents/Research/CS294194-196 Large Language Model Agents.md`

## Outline

1. Definitions and boundaries
   - Prompt engineering as the general interaction craft
   - Prompt optimization as search, evaluation, and iteration
   - Prompt tuning as the more algorithmic or gradient-based subset
   - Harness optimization as the broader agent-system view
2. Main method families
   - Manual prompt design and iterative refinement
   - OPRO-style optimization by prompting
   - DSPy and MIPRO-style compilation of instructions and demonstrations
   - GEPA-style reflective evolution with richer diagnostics
   - Gradient-based prompt tuning
3. What gets optimized in practice
   - System prompts
   - Few-shot examples and demonstrations
   - Tool definitions and tool documentation
   - Retrieval and context construction
   - Skill instructions, checklists, and workflow constraints
4. Evaluation patterns
   - Absolute scoring versus pairwise comparison
   - Trace-based diagnosis over scalar-only rewards
   - Cost, latency, and token budget as first-class constraints
   - Robustness and hallucination resistance as optimization targets
5. Operational doctrine
   - Start simple
   - Add optimization when it clearly improves results
   - Optimize the whole harness, not just one prompt string
   - Use fine-tuning and prompt optimization as complementary tools

## Synthesis

### 1. The notebook’s center of gravity is agentic prompt optimization, not beginner prompt writing

The most developed cluster is not general prompt-engineering advice. It is the use of optimization methods to improve agent workflows, especially in DSPy- and GEPA-adjacent systems. The strongest notes focus on measurable improvements to agent behavior, synthesis quality, and repository-level coding performance.

`GEPA - Reflective Prompt Evolution.md` frames GEPA as a method for "optimizing LLM prompts and agent behaviors through reflective evolution" and emphasizes that it uses actionable side information such as error messages, profiling data, and reasoning logs instead of only success/fail rewards.

`Notes on DSPy Agentic Research.md` centers DSPy, MIPROv2, and the idea that "Fine-tuning and Prompt Optimization works better together," which positions prompt optimization as part of a larger systems toolkit rather than a standalone trick.

### 2. Rich feedback beats scalar-only optimization

The clearest recurring pattern is that the notebook prefers optimization methods that can inspect failures in detail. GEPA is presented as superior to methods that rely on a single scalar reward because it can read richer traces and make targeted changes. `Meta-Harness.md` pushes this further by arguing that the right object of optimization is the full harness and that the optimizer should have access to source code, traces, and prior candidates, not just compressed summaries.

This is the main conceptual shift in the note set:

- weak approach: score prompt candidates with a single number and search blindly
- stronger approach: inspect failures, logs, traces, retrieval choices, and tool behavior
- strongest approach in the notebook: optimize the full agent harness with detailed execution context

### 3. Pairwise optimization is treated as more reliable than absolute scoring

The most grounded practical lesson comes from `Zettel_Eval_Experiment_Log.md`. That note describes an attempted DSPy MIPROv2 optimization loop using absolute essay scores. The result was high measured performance, but the prompt became too large and expensive because it depended heavily on injected examples. The note explicitly says the prompt "quickly bloated" past 4K tokens and was "too expensive and slow for a subagent loop."

The same note reports better results from a GEPA-style pairwise loop:

- a challenger prompt competes directly against a champion
- a judge model chooses the better output side by side
- optimization pressure shifts toward groundedness and hallucination resistance

The resulting lesson is not just "GEPA is better." It is more specific: when the target behavior is nuanced, pairwise judgment with concrete traces is often easier to calibrate than assigning an absolute score.

### 4. The real optimization target is the whole harness

`Meta-Harness.md` is important because it broadens the scope from prompt strings to harnesses: "system prompts, tool definitions, retrieval logic." This theme also appears in `Building Effective AI Agents.md`, which stresses that tool definitions deserve as much prompt-engineering attention as the main prompt.

That changes the practical best-practices stack:

- improve tool schemas and descriptions
- improve retrieval payloads and query construction
- improve filtering prompts separately from synthesis prompts
- improve workflow checklists and guardrails
- only then judge whether the remaining failure is really a prompt-text problem

### 5. Prompt optimization is valuable, but not free

Several notes treat optimization as costly and situational. The `Zettel` experiment notes highlight token cost, latency, and fragility. The notebook is not advocating that every prompt should be optimized with a heavy search loop. The pattern is more disciplined:

- start with a simple baseline
- define an evaluation target
- optimize only when the baseline is a bottleneck
- stop if the optimized prompt becomes too slow, too brittle, or too expensive

This is reinforced by `Building Effective AI Agents.md`, which effectively argues for adding complexity only when it demonstrably improves outcomes.

### 6. Prompt optimization and fine-tuning are framed as complements

The notes do not present prompt optimization and fine-tuning as rivals. `Notes on DSPy Agentic Research.md` and the linked research framing both suggest that the best pattern is staged:

- use prompt optimization to shape behavior, structure tasks, and discover effective constraints
- use fine-tuning when you need a stronger base capability or a more stable behavior profile

That is a mature view. It treats prompt optimization as a fast, external control surface and fine-tuning as a deeper model adaptation.

## Practical Best Practices From the Notes

- Optimize against a real task with a real judge, not intuition alone.
- Prefer pairwise evaluation when absolute scoring is noisy or poorly calibrated.
- Keep token cost and latency in the objective; a better prompt that is too expensive is often not better in practice.
- Use traces, error messages, and execution logs as optimization inputs whenever possible.
- Optimize retrieval, tool definitions, and workflow instructions together with the main prompt.
- Separate optimization problems when credit assignment is unclear. The roadmap notes explicitly distinguish synthesis-prompt optimization from filter-prompt optimization.
- Favor prompts that improve groundedness and reduce hallucination before chasing creativity or stylistic gains.
- Use prompt optimization and fine-tuning together when the problem warrants both.
- Start from a simple baseline and add optimization only after proving that the baseline fails on a meaningful benchmark.

## Tensions and Tradeoffs

- Absolute-scoring optimizers can look good on paper while hiding prompt bloat and operational cost.
- Safer prompts may win evaluations by sacrificing some creativity or novelty.
- Rich-context optimizers are more powerful but require better instrumentation and evaluation infrastructure.
- Retrieval quality and metadata quality can dominate prompt quality when the task is context-heavy.

## Gaps in Coverage

- There is little direct notebook coverage for `teleprompt` as a term.
- Prompt tuning is mentioned, but not deeply developed as an applied practice in this notebook.
- DSPy and MIPRO mechanics are discussed more by reference than by detailed internal notes.
- The taxonomy is still somewhat distributed across agent, evaluation, and retrieval notes rather than concentrated in one canonical note.

## Source Evidence

- `10_Projects/Notes on DSPy Agentic Research.md`
  - `MIPROv2`
  - `Fine-tuning and Prompt Optimization works better together`
  - `How to create personalized agent with user interaction and prompt optimization`
- `20_Subjects/Computer Science/Machine Learning/GEPA - Reflective Prompt Evolution.md`
  - `optimizing LLM prompts and agent behaviors through reflective evolution`
  - `GEPA uses ASI`
  - `Works with as few as 3 examples`
- `10_Projects/Zettel_Eval_Experiment_Log.md`
  - `quickly bloated the prompt to over 4K tokens`
  - `too expensive and slow for a subagent loop`
  - `Pairwise Hill-Climbing Optimizer`
  - `The evolutionary prompt traded away some Innovation in exchange for absolutely bulletproof Groundedness`
- `10_Projects/Zettel_Brainstormer_Roadmap.md`
  - `Evolutionary Pairwise Optimization (GEPA) creates much safer, robust prompts than absolute-scoring optimizers`
  - `Defensive Prompting`
- `20_Subjects/Computer Science/Artificial Intelligence/AI Agents/Optimization/Meta-Harness.md`
  - `optimizing model harnesses (system prompts, tool definitions, retrieval logic)`
  - `full filesystem containing the source code, execution traces, and scores of all prior candidates`
- `20_Subjects/Computer Science/Papers/Large Language Models as Optimizers.md`
  - `Optimization by PROmpting (OPRO)`
  - `the goal is to find instructions that maximize the task accuracy`
