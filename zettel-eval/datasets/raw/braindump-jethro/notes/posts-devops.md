## Kubernetes

[Open Containers Initiative](https://www.opencontainers.org/)

### Features of a COE

1. clustering
2. scheduling
3. scaling
4. load balancing (pets to cattle)
	- monitoring services vs monitoring
5. fault tolerance
6. app deployment

### Why use kubernetes

### Downsides to kubernetes

| Feature | Concept |
| --- | --- |
| Colocation | Pods |
| Scaling/Fault Tolerance | Replication controllers, replica sets |
| Load Balancing | Services |
| App Deployment | Rolling-updates |

### Architecture

kubectl <— scheduler (which node is used for container launch etc.) api server controllers manager (replication controller etc.) etcd (service discovery)

MASTER

### Replication controller vs set

| Controller | Set |
| --- | --- |
| old way | new way |
| works with rolling updates | supports sets based selectors |
| imperative | part of deployments |
|  | declarative |

### Selectors

eg. I want to select these pods, add it to replication sets

### Kubernetes Schema

| Api Version | v1 |
| --- | --- |
| Kind | Pod/ReplicaSet/ReplicaController |
| Metadata | name/labels |
| Spec | Containers |

[School of Dev Ops](https://github.com/schoolofdevops/course-outlines) [KataCoda](https://katacoda.com/)

### Articles on Kubernetes

[http://www.doxsey.net/blog/kubernetes--the-surprisingly-affordable-platform-for-personal-projects](http://www.doxsey.net/blog/kubernetes--the-surprisingly-affordable-platform-for-personal-projects)

Argues that Kubernetes is affordable and worth the try for personal projects.

The main arguments are:

1. Kubernetes is reliable and scalable.
2. It’s cheap to run: run HTTP proxy for each node, instead of using Google’s HTTP load balancer.
3. Kubernetes makes rollback deployments trivial, since everything is containerised.

[http://carlosrdrz.es/kubernetes-for-small-projects/](http://carlosrdrz.es/kubernetes-for-small-projects)

A response to the above article. Basically arguing that Kubernetes is very complex and has a lot of moving parts, which is wholly unnecessary for side projects.

## Mesos

Mesos is responsible for managing cluster resources (CPU, RAM, disk, etc) and the allocation of applications into those resources.

[Dominant Resource Fairness](https://people.eecs.berkeley.edu/~alig/papers/drf.pdf)

Two-level scheduler, compared to k8s one-level scheduler.

Scheduler scales a lot better than k8s (earlier).

<biblio.bib>

#### Links to this note

- [[posts-docker|Docker 101]]
