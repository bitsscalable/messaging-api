## Prerequisites

Ensure you have the following installed on your system:

- [Docker](https://www.docker.com/) (for containerization)

- Create a local docker network

```
docker network create mynetwork

```

- Run the mongodb as a container
```
docker run --name mongo-db -p 27017:27017 -d mongo:latest
```

- Run the rabbitmq as a container
```
podman run -d --name rabbitmq  -p 5672:5672  -p 15672:15672 rabbitmq:management

```

## Getting Started

### Step 1: Clone the Repository

```bash
git clone https://github.com/bitsscalable/messaging-api.git
cd messaging-api 
```

### Step 2: Build the Docker image

docker build -t messaging-api .

### Step 3: Run the container

docker run -d --name messaging-api --network mynetwork -p 5000:5000 messaging-api
