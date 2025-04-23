import igraph
import logging
import numpy as np

logging.basicConfig(handlers=[
        logging.FileHandler("log.log",mode='a'),
        logging.StreamHandler()
    ],
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
    level=logging.INFO)
logger = logging.getLogger()

try:
    graph = igraph.load('C:\\SHB\\FOK!\\FOK!_users.graphml')
    #graph = igraph.load('C:\\SHB\\Kindertelefoon\\De_Kindertelefoon_users.graphml')
except FileNotFoundError:
    logger.critical('Graph file not found!')

key_users_graph = igraph.Graph().as_directed()

most_active = sorted(graph.vs, key=lambda x: x.outdegree(), reverse=True)

def get_key_user_by_id(v):
    try:
        return key_users_graph.vs.select(id=v.attributes()['id'])[0]
    except (KeyError, IndexError):
        return key_users_graph.add_vertex(**v.attributes())

def add_edges_to_key_users(v):
    source = get_key_user_by_id(v)
    for e in v.out_edges():
        key_users_graph.add_edge(source,get_key_user_by_id(e.target_vertex))
    

ku=[]
added = []

for v in most_active:
    before = len(key_users_graph.vs)
    add_edges_to_key_users(v)
    after = len(key_users_graph.vs)
    ku.append(v)
    if len(ku) > 127 and len(ku) <= 254:
        added.append(after-before)
    logger.info('Key user %s with out-degree %d brings %d more new users. The amount of key users is now %d, who target %0.4f%% of the network', v.attributes()['id'], v.outdegree(), after-before,len(ku),(after/len(graph.vs))*100)