#!/usr/bin/env python3
import networkx as nx
import sqlite3
import logging
import json
from cdlib.algorithms import leiden

def load_from_db(path="/Users/peixian/.emacs.d/org-roam.db"):
    logging.info(f"Loading from {path}")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('SELECT * FROM titles')
    titles = c.fetchall()

    c.execute('SELECT * FROM links')
    links = c.fetchall()


    t = {}
    for file, title in titles:
        if 'private' in file:
            continue
        if title:
            title = title[1:-1]
            t[file] = title
        else:
            t[file] = file

    return t, links

def generate_url(file_name):
    return file_name.replace("/Users/peixian/code/org/", "https://wiki.space.af/posts/").replace(".org", "")[1:-1]

def parse_links(links, titles):
    logging.info(f"Parsing links")
    l = []
    for file1, file2, kind, _ in links:
        print(file1)
        print(file2)

        if 'private' in file2 or 'private' in file2:
            continue
        file1_name = titles.get(file1)
        file2_name = titles.get(file2)
        if file1_name and file2_name:
            l.append({
                "source": file1_name,
                "source_url": generate_url(file1),
                "target": file2_name,
                "target_url": generate_url(file2),
                "type": kind[1:-1]
            })
    return l

def color_nodes(community_dictionary, links):
    # community_dictionary is a mapping of 'title' -> 'community'
    nodes = {}
    for link in links:
        source = link['source']
        target = link['target']
        if source not in nodes:
            nodes[source] = {
                'id': source,
                'url': link['source_url'],
                'group': community_dictionary[source]
            }
        if target not in nodes:
            nodes[target] = {
                'id': target,
                'url': link['target_url'],
                'group': community_dictionary[target]
            }
    return nodes

def generate_community_colors(links, community_algo=leiden):
    logging.info(f"Generating community colors with algorithm {community_algo}")
    G = nx.Graph()
    for link in links:
        source = link['source']
        target = link['target']
        if source not in G:
            G.add_node(source)
            if target not in G:
                G.add_node(target)

        G.add_edge(source, target)

    community_sets = {}
    community_list = community_algo(G).communities
    for i, com in enumerate(community_list):
        for note_name in com:
            community_sets[note_name] = i

    nodes = color_nodes(community_sets, links)
    return nodes

def dump(nodes, links, name='./org-data.json'):
    logging.info(f"Writing json to {name}")
    output = {}
    output['links'] = links
    output['nodes'] = list(nodes.values())
    with open(name, 'w') as f:
        json.dump(output, f)

if __name__=="__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )
    titles, links = load_from_db()
    links = parse_links(links, titles)
    nodes = generate_community_colors(links)
    dump(nodes, links)
