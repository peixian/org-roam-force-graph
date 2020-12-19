#!/usr/bin/env python3
import networkx as nx
import sqlite3
import logging
import json
import argparse
from pathlib import Path
from cdlib.algorithms import leiden

def load_from_db(path):
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

def generate_url(file_name, replace_dict):
    new_url = file_name
    for key, val in replace_dict.items():
        if val == "NONE":
            val = ""
        new_url = new_url.replace(key, val)
    return new_url

def parse_links(links, titles, replace_dict={}):
    logging.info(f"Parsing links")
    l = []
    for file1, file2, kind, _ in links:
        if 'private' in file2 or 'private' in file2:
            continue
        file1_name = titles.get(file1)
        file2_name = titles.get(file2)
        if file1_name and file2_name:
            l.append({
                "source": file1_name,
                "source_url": generate_url(file1, replace_dict),
                "target": file2_name,
                "target_url": generate_url(file2, replace_dict),
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

def dump(nodes, links, name):
    logging.info(f"Writing json to {name}")
    output = {}
    output['links'] = links
    output['nodes'] = list(nodes.values())
    with open(name, 'w') as f:
        json.dump(output, f)



if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Generates a json file from your org-roam DB")
    parser.add_argument("--org-db-location",  help="Location of org-roam.db file. Defaults to $HOME/.emacs.d/org-roam.db", type=str, default=f"{Path.home()}/.emacs.d/org-roam.db", dest="db_location")
    parser.add_argument("--output", "-o", help="File to output as. Defaults to './org-data.json'", type=str, default="./org-data.json", dest="output_location")
    parser.add_argument("--replace", dest="replacements", nargs="+", help="Replacement to generate urls. Takes in <FILE_PATH> <REPLACEMENT_VALUE>")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("debug.log"),
            logging.StreamHandler()
        ]
    )

    if len(args.replacements) % 2 != 0:
        print("Replacements must be in pairs")
        exit(1)

    titles, links = load_from_db(path=args.db_location)
    replacements = {args.replacements[i]: args.replacements[i+1] for i in range(0, len(args.replacements), 2)}
    logging.info(f"Replacing according to {replacements}")
    links = parse_links(links, titles, replacements)
    nodes = generate_community_colors(links)
    dump(nodes, links, name=args.output_location)
