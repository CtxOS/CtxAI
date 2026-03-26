# Use the pre-built base image for CTX0
# FROM ctxai-base:local
# FROM ctxos/ctxai-base:testing
FROM ctxos/ctxai-base:latest

# Check if the argument is provided, else throw an error
ARG BRANCH
RUN if [ -z "$BRANCH" ]; then echo "ERROR: BRANCH is not set!" >&2; exit 1; fi
ENV BRANCH=$BRANCH

# Copy filesystem files to root
COPY ./fs/ /

# pre installation steps
RUN bash /ins/pre_install.sh $BRANCH

# install CTX0
RUN bash /ins/install_CTX0.sh $BRANCH

# install additional software
RUN bash /ins/install_additional.sh $BRANCH

# cleanup repo and install CTX0 without caching, this speeds up builds
ARG CACHE_DATE=none
RUN echo "cache buster $CACHE_DATE" && bash /ins/install_CTX02.sh $BRANCH

# post installation steps
RUN bash /ins/post_install.sh $BRANCH

# Expose ports
EXPOSE 22 80 9000-9009

RUN chmod +x /exe/initialize.sh /exe/run_CTX0.sh /exe/run_searxng.sh /exe/run_tunnel_api.sh /exe/trigger_self_update.sh

# initialize runtime and switch to supervisord
CMD ["/exe/initialize.sh", "$BRANCH"]
