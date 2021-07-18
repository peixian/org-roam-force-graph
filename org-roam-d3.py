#!/usr/bin/env python3
import networkx as nx
import sqlite3
import logging
import json
import argparse
import pandas as pd
from pathlib import Path
from cdlib.algorithms import leiden

import networkx as nx
import sqlite3
import logging
import json
import argparse
import pandas as pd
from pathlib import Path
from cdlib.algorithms import leiden

def load_from_db(path):
    logging.info(f"Loading from {path}")
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('SELECT file, title, id FROM nodes')
    titles = c.fetchall()

    c.execute('SELECT source, dest FROM links')
    links = c.fetchall()

    t = {}
    id_to_file = {}
    for file, title, or_id in titles:
        if 'private' in file:
            continue
        if title:
            title = title[1:-1]
            t[file] = title
        else:
            t[file] = file
        id_to_file[or_id] = file

    final_links = []
    for source, dest in links:
        if id_to_file.get(source, None) is None or id_to_file.get(dest, None) is None:
            continue
        final_links.append((id_to_file[source], id_to_file[dest]))
    return t, final_links

def generate_url(file_name, replace_dict):
    new_url = file_name
    for key, val in replace_dict.items():
        if val == "NONE":
            val = ""
        new_url = new_url.replace(key, val)
    return new_url.replace('"', '')

def parse_links(links, titles, top=None, replace_dict={}):
    logging.info(f"Parsing links")
    l = []
    for file1, file2  in links:
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
            })
    #if top:
        #df = pd.DataFrame(l)
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
    return nodes, G

def dump(nodes, links, name):
    logging.info(f"Writing json to {name}")
    output = {}

    for cur_link in links:
        cur_link["x1"] = nodes[cur_link["source"]]['x']
        cur_link["y1"] = nodes[cur_link["source"]]['y']
        cur_link["x2"] = nodes[cur_link["target"]]['x']
        cur_link["y2"] = nodes[cur_link["target"]]['y']

    output['links'] = links

    output['nodes'] = list(nodes.values())
    with open(name, 'w') as f:
        json.dump(output, f)


def generate_positions(G, nodes, iterations=50):
    logging.info(f"Generating and iterating through spring layout with iterations {iterations}")
    pos = nx.spring_layout(G, iterations=iterations)
    for key, value in pos.items():
        if key in nodes:
            nodes[key]["x"] = value[0]
            nodes[key]["y"] = value[1]
    return nodes

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Generates a json file from your org-roam DB")
    parser.add_argument("--org-db-location",  help="Location of org-roam.db file. Defaults to $HOME/.emacs.d/org-roam.db", type=str, default=f"{Path.home()}/.emacs.d/org-roam.db", dest="db_location")
    parser.add_argument("--output", "-o", help="File to output as. Defaults to './org-data.json'", type=str, default="./org-data.json", dest="output_location")
    parser.add_argument("--replace", dest="replacements", nargs="+", help="Replacement to generate urls. Takes in <FILE_PATH> <REPLACEMENT_VALUE>")
    parser.add_argument("--top", default=None, dest="top", help="Number of nodes to cut off by. Default is to generate all nodes")

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
    logging.info(f"Loading db from {args.db_location}")
    titles, links = load_from_db(path=args.db_location)
    replacements = {args.replacements[i]: args.replacements[i+1] for i in range(0, len(args.replacements), 2)}
    logging.info(f"Replacing according to {replacements}")
    links = parse_links(links, titles, args.top, replacements)
    nodes, G = generate_community_colors(links)
    nodes = generate_positions(G, nodes, iterations=200)
    dump(nodes, links, name=args.output_location)
