# Dockerfile for running tests with travis. 

FROM ubuntu:18.04
# 
# RUN echo "deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu trusty main" > /etc/apt/sources.list.d/ubuntu-toolchain-r-test-trusty.list
# 
# RUN echo "-----BEGIN PGP PUBLIC KEY BLOCK-----\nVersion: GnuPG v1\n\nmI0ESuBvRwEEAMi4cDba7xlKaaoXjO1n1HX8RKrkW+HEIl79nSOSJyvzysajs7zU\now/OzCQp9NswqrDmNuH1+lPTTRNAGtK8r2ouq2rnXT1mTl23dpgHZ9spseR73s4Z\nBGw/ag4bpU5dNUStvfmHhIjVCuiSpNn7cyy1JSSvSs3N2mxteKjXLBf7ABEBAAG0\nGkxhdW5jaHBhZCBUb29sY2hhaW4gYnVpbGRziLYEEwECACAFAkrgb0cCGwMGCwkI\nBwMCBBUCCAMEFgIDAQIeAQIXgAAKCRAek3eiup7yfzGKA/4xzUqNACSlB+k+DxFF\nHqkwKa/ziFiAlkLQyyhm+iqz80htRZr7Ls/ZRYZl0aSU56/hLe0V+TviJ1s8qdN2\nlamkKdXIAFfavA04nOnTzyIBJ82EAUT3Nh45skMxo4z4iZMNmsyaQpNl/m/lNtOL\nhR64v5ZybofB2EWkMxUzX8D/FQ==\n=LcUQ\n-----END PGP PUBLIC KEY BLOCK-----\n" > /tmp/key
# 
# RUN apt-key add /tmp/key
# 
RUN apt-get update && apt-get install -y \
    g++ \
    less \
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
    libpython3-dev \
    libpcre3 \
    libpcre3-dev \
    node-less \
    npm \
    nodejs
 
# RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-5 60 --slave /usr/bin/g++ g++ /usr/bin/g++-5
# 
# RUN pip3 install --upgrade pip
# 
# RUN apt-get install -y \
#     libpcre3 \
#     libpcre3-dev \
#     node-less \
#     npm \
#     nodejs
# 
# RUN ln -s /usr/bin/nodejs /usr/bin/node
 
WORKDIR /src
         
# RUN apt-get remove -y python3-urllib3
 
COPY build/requirements.txt .
RUN pip3 install --upgrade -r requirements.txt

COPY build/package.json .
RUN npm install

COPY build .

RUN make -j

