tags

[[posts-data-science|Data Science]]

Challenges:

1. Limited Resource
2. Fragmented solutions

[https://github.com/Microsoft/recommenders](https://github.com/Microsoft/recommenders) contains modular functions for model creation, data manipulation, evaluation etc.

- SVD, SAR, ALS, NCF, Wide&Deep, xDeepFM, DKN etc.

### Collaborative Filtering

Memory based method:

1. Microsoft Smart Adaptive Recommendation (SAR) algorithm

Model based methods

1. Matrix factorization methods
2. Neural network-based methods
	1. Restricted Boltzmann Machine (RBM)
		2. Neural Collaborative Filtering (NCF)

### SAR (ipynb)

- Item-to-item similarity matrix via co-occurence
- User-to-item affinity matrix via co-occurence of user-item interactions
	- weighted by interaction type and time decay:

\\begin{equation}

\\end{equation}

- Free from machine learning and feature collection
- Explainable results

### Neural Collaborative Filtering (NCF)

- Neural network based architecture to model latent features
- Generalization of MF based method

### Content-based Filtering

- “Content” can be user/item features, review comments, knowledge graph etc.
- Mitigates cold-start issue
- Feature vector can be highly sparse

e.g. Factorization machines

\\begin{equation} \\hat{y}(\\mathbf{x}) = w\_0 + \\sum\_{i=1}^{n} w\_i x\_i + \\sum\_{i=1}^{n}\\sum\_{j=i+1}^n \\langle v\_i, v\_j \\rangle x\_i x\_j \\end{equation}

#### TODO xDeepFM

, Guo et al., n.d., @lian18

### TODO Deep Knowledge-aware Network

Multi-channel word-entity aligned knowledge aware CNN

- containerize model serving, use Kubernetes to autoscale
- 9-year longitudinal study of scaling data science at Twitter

2 models of DS teams in engineering-driven organizations:

embedded model

data scientists part of a smaller team, with other engineers
- Pros:
	- Dedicated data science resourcing
		- Alignment between DS and the rest of the team
		- One roadmap, fewer dependencies
		- Data science has a more natural “seat at the table”
- Cons:
	- Rigid resourcing (harder to move DS between teams)
		- Barriers for collaboration between data scientists
		- Manager may not have domain knowledge (typically an EM)
		- Risk of Data Science being a support or service to eng. team

centralized model

data scientists manageed by a data science manager, supporting the product teams
- Pros:
	- Data scientists working together (collaboration and knowledge sharing)
		- DS manager has domain knowledge (between career dev)
		- Resources can be rebalanced to meet customer demand
		- Advocacy for better and consistent tech (tooling, datasets, etc.)
- Cons:
	- Coordiantion between teams (DS and stakeholder) becomes more complicated
		- In eng. centric orgs the DS teams need to influence org roadmap
		- Risk of data science work not being aligned with product
		- Company needs to support one more function

Best of both worlds: centralized org with embedded teams

E.g.

- Growth Eng (with centralized DS)
- Product Eng (with centralized DS)
- Health Eng (with centralized DS)
- Centralized proceses, common resources

Challenges:

1. Everyone has at least 2 teams - centralized DS team, and part of the product team
	1. Risk of meeting and planning overload
		2. Which is their main team?
2. Risk of mismatch of expectation between DS leadership and product leadership

How to scale this hybrid org structure to ~100 Data Scientists?

~ Create more layers of abstraction:

- Split teams into pillars

“A product as a system”:

```text
Growth DS -> Product DS -> Revenue Science
                ^^^
Insights, metrics, data enigneering, data visualization
```

Twitter organizes into:

- Growth
- Product
- Health
- Foundational DS

team charters Swimlanes - clear differentiation between teams Working agreement - what to expect from other teams? (e.g. interactions between data engineering & notifications ds team)

- How does the data eng team receive requests?
- What is the SLA of a dataset request?
- What would be the ownership structure for the request?
- On what basis this request will be prioritized?

**Create clear communication channels**

- Have team meetings at all levels
- Have recurrent sessions to review ongoing projects
- Have fun with each other - quarterly offsites and other activities

**Build and strengthen your leadership team**

- Leadership team is their **first team**
- Have staff meeting, and keep an open standing agenda
- Do leadership offsites and working sessions (twitter does it monthly on a specific topic)
- Make this reponsible for managing your org’s relationship with stakeholders

TLDR: align teams with objectives, build structures of your teams: team charters, working agreements, swimlanes, and strong leadership team

### Questions: Thoughts on self-servicing (end-to-end) data scientists

- Moving away from end-to-end

### Question: How to bridge gap in understanding between data eng and data scientists

- strong overlap in skill set between data eng and scientists e.g. engineers are taught to build data pipelines early when joining Twitter
- job of the DS manager

## Argo: Kubernetes Native Workflows and Pipelines - Greg Roodt, Canva

[Github project](https://github.com/argoproj/argo)

- Similar to airflow
- runs on top of kubernetes

[Machine Learning as Code - Youtube](https://www.youtube.com/watch) - How Kubeflow uses Argo Workflows as its core workflow engine and Argo CD to declaratively deploy ML pipelines and models.

Argo’s DAG UI looks nice!

![](https://braindump.jethro.dev/ox-hugo/screenshot_2019-07-17_12-06-32.png)

- How to handle unclean data?
- How quick will the transforms be?
- Transitioning into a data-driven company
	- Centralized existing datasets

### Data Collection

- ownership and access of data
- near-real time raw data: access to unfiltered data in minutes
- no data sampling: ensure access to full dataset
- ad blockers: responsible for many lost events
- personal identification information: turn off PII scraping
- data model: custom events can be sent in nested format
- SDKs with persistent layer: collected logs stored on the offline device

### Storage and Flow

- schedulable pipelines with dependencies
	- notifications, SLAs, extendibility
- Collected data transformation
- Raw-level data stored on the storage, accessible on query engine

### Database Query Engine

- read benchmarks
- look at distributed query engines
- star schema better for analytics
- flat truth tables
- store aggregations as cubes

### Visualization

- self-hosted vs hosted
- native SQL execution
- interactive query builder

E.g. stack Kinesis Data Firehose, S3, Airflow, EMR-Presto (Athena for large jobs), [Apache Superset](https://superset.incubator.apache.org/)

## Bibliography

\[wang18\_dkn\] Wang, Zhang, Xie & Guo, Dkn: Deep Knowledge-Aware Network for News Recommendation, *CoRR*,. [link](http://arxiv.org/abs/1801.08284v2). [[posts-data-council|↩]]
