# Stage 1: Build stage (compile ModSecurity and Nginx dynamic module)
FROM debian:bookworm-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git g++ flex bison curl doxygen libyajl-dev libgeoip-dev libtool dh-autoreconf \
    libcurl4-gnutls-dev libxml2 libxml2-dev libpcre3-dev liblmdb-dev pkgconf zlib1g-dev libssl-dev make wget

# Compile ModSecurity Core (libmodsecurity3)
WORKDIR /opt
RUN git clone --depth 1 -b v3.0.10 https://github.com/SpiderLabs/ModSecurity.git && \
    cd ModSecurity && \
    git submodule init && \
    git submodule update && \
    ./build.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install

# Compile ModSecurity Nginx Connector dynamic module
# We compile it against Nginx 1.24.0 to match the production stage
RUN wget http://nginx.org/download/nginx-1.24.0.tar.gz && \
    tar -xzf nginx-1.24.0.tar.gz && \
    git clone --depth 1 https://github.com/SpiderLabs/ModSecurity-nginx.git && \
    cd nginx-1.24.0 && \
    ./configure --with-compat --add-dynamic-module=../ModSecurity-nginx && \
    make modules

# Stage 2: Production stage (lean WAF Nginx runtime)
FROM nginx:1.24.0

# Upgrade all system packages to patch OS-level CVEs and secure the WAF runtime
RUN apt-get update && apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy ModSecurity compiled core library
COPY --from=builder /usr/local/modsecurity /usr/local/modsecurity
RUN ln -s /usr/local/modsecurity/lib/libmodsecurity.so.3 /usr/lib/libmodsecurity.so.3

# Copy the dynamic Nginx ModSecurity module
COPY --from=builder /opt/nginx-1.24.0/objs/ngx_http_modsecurity_module.so /etc/nginx/modules/ngx_http_modsecurity_module.so

# Prepare ModSecurity configuration folders
RUN mkdir -p /etc/nginx/modsec/rules
