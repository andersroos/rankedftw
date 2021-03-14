# Dockerfile for running tests with travis. 

FROM ubuntu:18.04

RUN apt-get update -y

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get install -y \
    g++ \
    libboost-python-dev \
    libboost-system-dev \
    libboost-serialization-dev \
    libboost-iostreams-dev \
    libboost-thread-dev \
    libboost-program-options-dev \
    python3 \
    python3-pip \
    libpq-dev \
    libjsoncpp-dev \
    libpcre3 \
    libpcre3-dev \
    npm \
    nodejs
 
WORKDIR /src
 
COPY build/requirements.txt .
RUN pip3 install --upgrade -r requirements.txt

COPY build/package.json .
RUN npm install

COPY build .

RUN make -j

