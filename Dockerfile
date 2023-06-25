FROM ubuntu:23.10

RUN apt-get update && \
    apt-get install -y python3 python3-venv python3-pip fish cmake gcc

RUN python3 -m venv /venv
RUN source /venv/bin/activate && pip install networkx numpy pandas cdlib igraph leidenalg scikit-learn umap-learn numba

COPY . /workspace

WORKDIR /workspace

RUN cd /workspace/vendor/snap/examples/node2vec; make; cp node2vec /usr/local/bin

#RUN node2vec -i:/workspace/org-data.edgelist  -o:/workspace/org-data.emb  -d:64 -l:40 -q:0.5
ENTRYPOINT ["/bin/bash"]