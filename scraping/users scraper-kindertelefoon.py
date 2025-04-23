import pandas as pd
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
from urllib.parse import urlparse
import igraph
import logging
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateparser import parse

logging.basicConfig(handlers=[
        logging.FileHandler("log.log",mode='a'),
        logging.StreamHandler()
    ],
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
    level=logging.INFO)
logger = logging.getLogger()

driver = None

quote_pattern = re.compile("^Op\s(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s\d{1,2}\s(januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\s\d{4}\s\d{2}\:\d{2}\sschreef\s(?P<nick>\S+)\shet\svolgende:$")
comments = pd.read_csv('C:\\SHB\\Kindertelefoon\\20210530_comment_list.csv', index_col='Index', dtype={'TopicID':'Int32', 'Author_code':str})
topics = pd.read_csv('C:\\SHB\\Kindertelefoon\\20210530_topic_list.csv', index_col='ID', dtype={'initiated':str})
users = pd.read_csv('C:\\SHB\\Kindertelefoon\\users_list.csv', index_col='nick_name', dtype={'code':str})

# topics = topics.drop(columns='Unnamed: 0')
# topics.to_csv('C:\\SHB\\Kindertelefoon\\20210530_topic_list.csv')

# exit()

labels = {
    "Topic" : "n_topics",
    "Topics" : "n_topics",
    "Reacties" : "n_reactions",
    "Beantwoord" : "n_bestanswers",
    "Lid sinds"	: "registered",
    "Geslacht" : "sex",
    "Geboortejaar" : "birth_year",
    "Interesses" : "interests"
}

try:
    graph = igraph.load('C:\\SHB\\\Kindertelefoon\\De_Kindertelefoon_users.graphml')
except FileNotFoundError:
    graph = igraph.Graph().as_directed()

def get_vertex_by_name(graph,name):
    try:
        return graph.vs.find(name)
    except ValueError:
        return graph.add_vertex(name)

def extract_text_from_xpath_in_profile(driver,key):
    elem = driver.find_element(By.XPATH, '//table[@class="bigtxt"]//tr[./td/span[text()="' + key + ':"]]/td[2]')
    return elem.text

def get_user_pseudo_code(nick, author_id, users, driver, link, graph):
    try:
        author_code = users.loc[nick,'code']    
        node = graph.vs.find(author_code)
    except KeyError:
        user_data = {"n_initiations":0, 'n_sex_comments':0}
        author_code = str(len(users))
        if nick != 'Anonymous':
            if link == None:
                user_data["id"] = '#anon_' + nick
            else:
                user_data["id"] = author_id
                url_author = link
                html = requests.get(url_author).text
                soup = BeautifulSoup(html, 'html.parser')
                stats = soup.select_one('div[class="box__content"] div[class*="group box"]')
                for span in stats.find_all('span',recursive=False):
                    stat = span.text.strip().split('\n')
                    try:
                        user_data[labels[stat[0]]] = int(stat[1])
                    except KeyError:
                        logger.warning('No label found for %s', stat[0])
                    except IndexError:
                        logger.exception(e)
                user_data['n_followers'] = int(stats.select_one('span[class="qa-user-followers"]').text)
                user_data['n_following'] = int(stats.select_one('span[class="qa-user-following"]').text)
                personal_data = soup.select('div[class*="box box__pad box--profile-fields"] div[class*="table table"] div[class="table__row"]')
                for row in personal_data:
                    divs = row.select('div')
                    label = divs[0].text.strip().replace('\n','')
                    val = divs[1].text.strip().replace('\n','')
                    try:
                        if labels[label] == 'registered':
                            val = parse(val).strftime('%Y-%m-%d')
                        user_data[labels[label]] = val
                    except KeyError as e:
                        logger.warning('%s not collected from the user %s', e.args[0], author_id)
        users.loc[nick] = user_data
        users.loc[nick,'code'] = author_code
        user_data['id'] = author_code
        node = graph.add_vertex(name=author_code,**user_data)
    return author_code, node

def get_comment_info(comment):
    comment_id = comment.attrs['id']
    user = comment.select_one('div[class*="post__user__meta"]').select_one('li')
    nick = user.text.strip().replace('\n','')
    user_link = user.select_one('a')
    if user_link!=None:
        link = 'https://forum.kindertelefoon.nl' + user_link.attrs['href']
        author_id = link.split('/')[-1]
    else:
        link = author_id = None
    return comment_id, nick, author_id, link

def extract_comment(soup,url,row, topic_index):
    i = 1
    if soup.select_one('h1[class="qa-page-title"]') == None or soup.select_one('h1[class="qa-page-title"]').text != 'Pagina niet gevonden':
        i = i + 1
    else:
        return None
    if not pd.isna(row['CommentID']):
        comment = soup.find(id=row['CommentID'])
        if comment != None:
            return comment
    else:
        #return soup.select('div#comments div[class*="post box__pad qa-topic-post-box post"]')[topic_index % 8]
        for c in soup.select('div#comments div[class*="post box__pad qa-topic-post-box post"]'):
            c_content = c.select_one('div[class*="post__content"]')
            if c_content.text.strip().replace(' ','').replace('\r','').replace('\n','').replace('\xa0', '') == str(row['Content']).strip().replace(' ','').replace('\r','').replace('\n','').replace('\xa0', ''):
                return c
    try:
        return soup.select('div#comments div[class*="post box__pad qa-topic-post-box post"]')[(topic_index) % 25]
    except IndexError as e:
        logger.error(e)
        return None
    
            
def set_initial_comment(comment_index,comment,topic_id):
    comment_id, nick, author_id, link = get_comment_info(comment)
    author_code, start = get_user_pseudo_code(nick, author_id, users, driver, link, graph)
    comments.loc[comment_index,'Author_code'] = topics.loc[topic_id,'initiated'] = str(int(author_code))
    users.loc[nick, 'n_initiations'] = users.loc[nick]['n_initiations'] + 1
    start['n_initiations'] = users.loc[nick, 'n_initiations']
    return comment_id, start

def detect_initial_comment(soup,row_comment,topic_id,url):
    post = soup.select_one('div[class="box qa-topic-first-post"]')
    comment = post.select_one('div[class*="post box__pad"]')
    answer = comment.find('div[class="answer-field qa-answer-field"]')
    if answer != None:
        answer.decompose()
    comment_text = comment.select_one('div[class*="post__content"]')
    if comment['id'] == row_comment['CommentID']:
        set_initial_comment(row_comment.name,comment,topic_id)
        logger.info('Comment ID ' + str(row_comment.name) + ' in the topic ' + str(topic_id) + ' is matched by comment ID')
    elif row_comment['Content'].strip().replace(' ','').replace('\r','').replace('\n','').replace('\xa0', '') == comment_text.text.strip().replace(' ','').replace('\r','').replace('\n','').replace('\xa0', ''):
        comments.loc[row_comment.name,'CommentID'], _ = set_initial_comment(row_comment.name,comment,topic_id)
        logger.info('Comment ID ' + str(row_comment.name) + ' in the topic ' + str(topic_id) + ' is matched by comment text')
    else:
        logger.warning('Comment ID ' + str(row_comment.name) + ' in the topic ' + str(topic_id) + ' is not matched with the content! (Link: ' + url + ')')

def scrape_quotes():
    for topic_id, row_topic in topics.iterrows():
        if row_topic['is_processed'] == True:
            logger.info('Topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ') has already been processed')
            continue
        logger.info('Processing topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ')')
        url = url_page = row_topic['URL']
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        if soup.select_one('h1[class="qa-page-title"]') != None and soup.select_one('h1[class="qa-page-title"]').text in ['Pagina niet gevonden', 'Er is iets fout gegaan']:
            topics.loc[topic_id,'is_processed'] = True
            continue
        is_error = None
        topic_index = 0
        page = 1
        if is_error != None:
            logger.error('Error occured when processing topic ' + str(topic_id) + '. Link: ' + url)
            continue
        # elif topic_id not in comments('TopicID'):
        #     logger.info('No comments found for the topic ' + str(topic_id))
        #     continue
        else:
            for comment_index, row_comment in comments[comments['TopicID'] == topic_id].iterrows():
                if not pd.isna(row_comment['Author_code']):
#                    logger.info('Comment ' + str(comment_index) + ' (' + str(comments.index.get_loc((topic_id,comment_index)) + 1) + ' out of ' + str(len(comments)) + ') has already been processed')
                    logger.info('Comment ' + str(comment_index) + ' (' + str(comment_index + 1) + ' out of ' + str(len(comments)) + ') has already been processed')
                    if row_comment['FirstPost'] == False:
                        topic_index = topic_index + 1
                    continue
                #logger.info('Processing comment ' + str(comment_index) + ' (' + str(comments.index.get_loc((topic_id,comment_index)) + 1) + ' out of ' + str(len(comments)) + ')')
                logger.info('Processing comment ' + str(comment_index) + ' (' + str(comment_index + 1) + ' out of ' + str(len(comments)) + ')')
                if row_comment['FirstPost'] == True:
                    detect_initial_comment(soup,row_comment,topic_id,url)
                else:
                    if topic_index / page > 24:
                        page = page + 1
                        url_page = url + '/index' + str(page) +'.html'
                        soup = BeautifulSoup(requests.get(url_page).text, 'html.parser')
                        logger.info('New page: ' + url_page)
                    comment = extract_comment(soup,url_page,row_comment,topic_index)
                    if comment == None:
                        logger.error('No content matched for the comment "%s"', row_comment['Content'])
                        continue
                    comments.loc[comment_index,'CommentID'], nick, author_id, link = get_comment_info(comment)
                    author_code, start = get_user_pseudo_code(nick, author_id, users, driver, link, graph)
                    quotes = comment.find_all('content-quote')
                    quoted_users = []
                    for quote in quotes:
                        quoted_nick = quote.attrs['data-username']
                        quoted_user, finish = get_user_pseudo_code(quoted_nick, None, users, driver, None, graph)
                        if quoted_user not in quoted_users:
                            graph.add_edge(start,finish)
                            quoted_users.append(quoted_user)
                    comments.loc[comment_index,'Author_code'] = author_code
                    topic_index = topic_index + 1
                users.loc[nick,'n_sex_comments'] = start['n_sex_comments'] = users.loc[nick,'n_sex_comments'] + 1
        topics.loc[topic_id,'is_processed'] = True


def scrape_first_posts():
    for topic_id, row_topic in topics.loc[pd.isna(topics['initiated'])].iterrows():
        logger.info('Processing topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ')')
        url = row_topic['URL']
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        if soup.select_one('h1[class="qa-page-title"]') != None and soup.select_one('h1[class="qa-page-title"]').text in ['Pagina niet gevonden', 'Er is iets fout gegaan']:
            topics.loc[topic_id,'is_processed'] = True
            logger.info('Topic %s is not found', str(topic_id))
            continue 
        detect_initial_comment(soup,comments.loc[(comments['TopicID'] == topic_id) & (comments['FirstPost'])].iloc[0],topic_id,url)

def comments_per_user():
    for nick_name, row_user in users.iterrows():
        users.loc[nick_name,'n_sex_comments'] = graph.vs.find(row_user['code'])['n_sex_comments'] = len(comments[comments['Author_code'] == row_user['code']])
        logger.info('%s comments count processed',nick_name)

try:
    comments_per_user()

except Exception as e:
    logger.exception(e)
finally:
    logger.info('Saving file\nSaving topics progress\n')
    topics.to_csv('C:\\SHB\\Kindertelefoon\\20210530_topic_list.csv')
    logger.info('Topics progress saved\nSaving comments with authors\n')
    comments.to_csv('C:\\SHB\\Kindertelefoon\\20210530_comment_list.csv')
    clean_comments = pd.read_csv('C:\\SHB\\Kindertelefoon\\20210530_comment_list_clean.csv', index_col='Index', dtype={'TopicID':'Int32', 'Author_code':str})
    clean_comments['CommentID'] = comments['CommentID']
    clean_comments.to_csv('C:\\SHB\\Kindertelefoon\\20210530_comment_list_clean.csv')
    logger.info('Saving comments with authors complete\nSaving graph\n')
    graph.save('C:\\SHB\\Kindertelefoon\\De_Kindertelefoon_users.graphml')
    logger.info('Saving graph complete\nSaving users list')
    users.to_csv('C:\\SHB\\Kindertelefoon\\users_list.csv')
    logger.info('Saving users list complete\n')
