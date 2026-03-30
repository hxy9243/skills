PROPERTIES::ID: 79ec0a7b-258d-49c6-b159-afcb2917e219

:END:

tags

[Linux](https://braindump.jethro.dev/posts/linux), [Operating Systems](https://braindump.jethro.dev/posts/operating_systems)

## Why Containers

### Containers are Cheap

![](https://braindump.jethro.dev/ox-hugo/container_vm.png)

#### Containers are Cheap

- Docker provides lightweight virtualization with almost zero overhead.
- Start and stop containers within seconds.

### Containers are Portable

Containers contain all the required software dependencies to run your application.

Once a container is built, you can be sure it runs “the same way” on any host operating system with the same Linux kernel.

## Containers in OSes

| Year |  |
| --- | --- |
| 2006 | Process Containers, later renamed to cgroups |
| 2008 | LXC: implemented using cgroups and kernel namespaces |
| 2013 | Docker: initially built on LXC, but now runs on `libcontainer` |

### 2006: Process Containers

![](https://braindump.jethro.dev/ox-hugo/cgroups.png)

### 2008: LXC Containers, and 2013: Docker

![](https://braindump.jethro.dev/ox-hugo/lxc_docker.png)

## What is Docker?

Docker is a toolchain for managing containers.

![](https://braindump.jethro.dev/ox-hugo/docker_architecture.png)

## What You’ll Do Today

You’ll be packaging a simple application with Docker.

If time permits, we’ll cover additional things, such as passing environment variables.

## Docker Basics

### Pulling images

```sh
docker pull alpine
```

#### Alpine?

`alpine` is an image for a tiny Linux distribution, used by Docker for most of its official images.

A container image is a lightweight, stand-alone, executable package of a piece of software that includes everything needed to run it: code, runtime, system tools, system libraries, settings.

`alpine` is pulled from the Docker Registry, where hundreds of thousands of images are hosted.

### Starting a container

```sh
docker run alpine
```

What is happening here?

### Running a command

```sh
docker run alpine echo "Hello from alpine!"
```

### Docker Status

List all docker images:

```sh
docker images
```

List all running docker containers:

```sh
docker ps
```

List all docker containers (including stopped containers):

```sh
docker ps -a
```

### Entering a Container Interactively

```sh
docker run -it alpine sh
```
```sh
uname -r                        # 4.9.41-moby
  hostname                        # container_id
  whoami                          # root
  id                              # uid=0(root) gid=0(root) groups=0(root),1(bin)...
```

## Inside alpine

Docker images consist of multiple layers:

![](https://braindump.jethro.dev/ox-hugo/container-layers.jpg)

### Layers for the ubuntu image

Observe the output for the following:

```sh
docker pull ubuntu:15.04
   docker history ubuntu
```

### Declare layers with a Dockerfile

```docker-file
FROM ubuntu
  MAINTAINER Kimbro Staken

  RUN apt-get install -y software-properties-common python
  RUN add-apt-repository ppa:chris-lea/node.js
  RUN echo "deb http://us.archive.ubuntu.com/ubuntu/ precise universe" >> /etc/apt/sources.list
  RUN apt-get update
  RUN apt-get install -y nodejs
  #RUN apt-get install -y nodejs=0.6.12~dfsg1-1ubuntu1
  RUN mkdir /var/www

  ADD app.js /var/www/app.js

  CMD ["/usr/bin/node", "/var/www/app.js"]
```

### Dockerfile Cheatsheet

| Command | Info |
| --- | --- |
| FROM | Sets the Base Image for subsequent instructions. |
| RUN | execute any commands in a new layer on top of the current image and commit the results. |
| CMD | provide defaults for an executing container. |
| EXPOSE | informs Docker that the container listens on the specified network ports at runtime. |
| ENV | sets environment variable. |
| COPY | copies new files or directories to container. |
| ENTRYPOINT | configures a container that will run as an executable. |
| VOLUME | creates a mount point for externally mounted volumes or other containers. |
| WORKDIR | sets the working directory. |
| ARG | defines a build-time variable. |
| LABEL | apply key/value metadata to your images, containers, or daemons. |

## Docker Networking

Docker creates three networks by default. We’re mostly concerned with `bridge`.

```text
$ docker network ls

  NETWORK ID          NAME                DRIVER
  7fca4eb8c647        bridge              bridge
  9f904ee27bf5        none                null
  cf03ee007fb4        host                host
```

### How bridge works

Unless specified otherwise, the docker container will connect to this default `bridge` network. This provides a means of Docker containers to access the outside world. This is achieved through rules on the kernel’s `iptable`.

By default, none of the ports are published and the outside world has no access to the docker containers.

### Running a Simple Webserver

```sh
nc -ll -p 8080 -e /bin/echo -e "HTTP/1.1 200 OK\n\n$(date)\n"
```

### Allowing Ingress

```sh
docker run -p 5001:8080 alpine \
          nc -ll -p 8080 -e /bin/echo -e "HTTP/1.1 200 OK\n\n$(date)\n"
```

As a daemon:

```sh
docker run -p 5001:8080 -d alpine \
          nc -ll -p 8080 -e /bin/echo -e "HTTP/1.1 200 OK\n\n$(date)\n"
```

## Exercise: package a Node.js Server with Docker

```sh
curl -i http://localhost:5001/
```
```text
HTTP/1.1 200 OK
  X-Powered-By: Express
  Content-Type: text/html; charset=utf-8
  Content-Length: 14
  ETag: W/"e-ZohVPp9YwmNT/yh3111KJ3ZG6Uk"
  Date: Fri, 13 Oct 2017 18:34:46 GMT
  Connection: keep-alive

  Hello world!!
```

### Server code

```text
https://git.io/vdXLC
```

### General Instructions

1. Install the Node.js runtime (use Ubuntu)
2. Copy the files into the container
3. Get the node package manager `npm`
4. Run `npm install`
5. Run `npm start` to start server

## But… I want to change my files!

```sh
docker run -d my/webserver
  # Create file locally
  docker exec -it container_name sh
  ls #WAT
```

### Mounting Volumes

There are three types of mounts:

1. **Volumes** are managed by docker. Volumes also support the use of volume drivers, which allow you to store your data on remote hosts or cloud providers, among other possibilities.
2. **Bind Mounts** may be stored anywhere on the host filesystem.
3. **tmpfs mounts** are stored in the host system’s memory only.

### Mounting the /src directory

```sh
docker run -p 5000:8080 -v ~/path/to/directory:/usr/src/app/src my/webserver
```

## Beyond Docker

Docker is the building block for many devops solutions.

1. Container Orchestration: Kubernetes, Cloud Foundry etc.
2. Monitoring: cAdvisor, InfluxDB etc.
3. Reverse Proxies and Load Balancers: fabio etc.

Docker makes microservices manageable and scalable.
