import pandas as pd
import igraph
import logging
from dateparser import parse


logging.basicConfig(handlers=[
        logging.FileHandler("log.log",mode='a'),
        logging.StreamHandler()
    ],
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
    level=logging.INFO)
logger = logging.getLogger()

users = pd.read_csv('C:\\SHB\\FOK!\\users_list.csv', index_col='nick_name')
graph = igraph.load('C:\\SHB\\FOK!\\FOK!_users.graphml')

def get_vertex_by_name(graph,name):
    try:
        return graph.vs.find(name)
    except ValueError:
        logger.error('Vertex ' + name + ' not found!')
try:
    for i, row in users.iterrows():
        v = get_vertex_by_name(graph,row['code'])
        # v['id'] = 'n' + str(int(v['name']))
        if row['birth_date'] == '00-00-0000' or pd.isna(row['birth_date']):
            v['birth_date'] = ''
        elif '00-00' in row['birth_date']:
            v['birth_date'] = row['birth_date'].split('-')[2] + '-01-01'
        elif '-00-' in row['birth_date']:
            v['birth_date'] = row['birth_date'].split('-')[2] + '-01-' + row['birth_date'].split('-')[0]
        else:
            v['birth_date'] = parse(row['birth_date']).strftime('%Y-%m-%d')
        # if pd.isna(row['registered']):
        #     v['registered'] = None
        # else:
        #     v['registered'] = row['registered']
        logger.info('Vertex %s have been processed', row['code'])

except Exception as e:
    logger.exception(e)

#del(graph.vs['name'])

graph.save('C:\\SHB\\FOK!\\FOK!_users_final.graphml')
logger.info('Graph saved!')