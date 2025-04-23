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

driver = webdriver.Chrome()

quote_pattern = re.compile("^Op\s(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s\d{1,2}\s(januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\s\d{4}\s\d{2}\:\d{2}\sschreef\s(?P<nick>\S+)\shet\svolgende:$")
comments = pd.read_csv('C:\\SHB\\FOK!\\20210520_comment_list.csv', index_col=['TopicID','CommentID'],dtype={'TopicID':'Int32', 'Author_code':str})
topics = pd.read_csv('C:\\SHB\\FOK!\\20210520_topic_list.csv', index_col='ID', dtype={'initiated':str})
users = pd.read_csv('C:\\SHB\\FOK!\\users_list.csv', index_col='nick_name')

try:
    graph = igraph.load('C:\\SHB\\FOK!\\FOK!_users.graphml')
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
    author_code = None
    node = None
    try:
        author_code = users.loc[nick,'code']    
        node = graph.vs.find(str(author_code))
    except KeyError:
        author_code = str(len(users))
        user_data = {"id" : author_id, "n_initiations":0, "code" : author_code, "n_sex_comments" : 0}
        if link != None:
            url_author = link
        else:
            url_author = 'https://forum.fok.nl/user/profile/' + author_id
        driver.get(url_author)
        WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, 'pageWrapper'))
                )
        if 'error #2' in driver.find_element(By.XPATH,'//div[@id="pageWrapper"]/div[@class="fieldholder breadcrumb"]/h1').text:
            try:
                cookies_window = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//iframe[@src="https://webads.mgr.consensu.org/consentUi/"]'))
                )
                driver.switch_to.frame(cookies_window)
                driver.find_element(By.XPATH,'//div[@id="buttons"]/div[2]').click()
                return get_user_pseudo_code(nick, author_id, users, driver, link, graph)
            except TimeoutException as e:
                logger.warn('error #2 : user:' + author_id + ' TIMEOUT EXCEPTION')
        elif 'error' in driver.find_element(By.XPATH,'//div[@id="pageWrapper"]/div[@class="fieldholder breadcrumb"]/h1').text:
            logger.error(driver.find_element(By.XPATH,'//div[@id="pageWrapper"]/div[@class="fieldholder breadcrumb"]/h1').text + ' user:' + author_id)
        else:
            user_data['sex'] = extract_text_from_xpath_in_profile(driver, 'geslacht')
            birth_date = extract_text_from_xpath_in_profile(driver, 'geboortedatum')
            if birth_date != '' and birth_date != '00-00-0000':
                try:
                    user_data['birth_date'] = datetime.strptime(birth_date, "%Y-%m-%d")
                except ValueError:
                    user_data['birth_date_dt'] = pd.NA
            user_data['place'] = extract_text_from_xpath_in_profile(driver, 'woonplaats')
            user_data['education'] = extract_text_from_xpath_in_profile(driver, 'opleiding')
            user_data['profession'] = extract_text_from_xpath_in_profile(driver, 'beroep')
            user_data['hobbies'] = extract_text_from_xpath_in_profile(driver, 'hobby\'s/interesses')
            registered = extract_text_from_xpath_in_profile(driver, 'geregistreerd op')
            if registered != '':
                try:
                    user_data['registered'] = parse(registered).strftime('%d.%m.%Y %H:%M')
                except ValueError:
                    user_data['registered'] = ''
            user_data['last_visit'] = extract_text_from_xpath_in_profile(driver, 'laatste bezoek')
            n_posts = extract_text_from_xpath_in_profile(driver, 'aantal posts')
            n_posts_str = n_posts.split(' ')
            user_data['n_posts'] = int(n_posts_str[0].replace('.',''))
            user_data['n_posts_per_day'] = int(n_posts_str[2].replace('.',''))
        users.loc[nick] = user_data
        users.loc[nick,'code'] = author_code
        user_data['id'] = author_code
        node = graph.add_vertex(name=author_code,**user_data)
    return author_code, node

def scrape_quotes():
    for topic_id, row_topic in topics.iterrows():
        if row_topic['is_processed'] == True:
            logger.info('Topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ') has already been processed')
            continue
        logger.info('Processing topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ')')
        url = 'https://forum.fok.nl/topic/' + str(topic_id) + '/1/999'
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        first_comment = True
        is_error = soup.find('#pageWrapper div[class="fieldholder breadcrumb"] h1') 
        if is_error != None and is_error.text == 'error #52':
            logger.error('Error occured when processing topic ' + str(topic_id) + '. Link: ' + url)
            continue
        elif topic_id not in comments.index.get_level_values('TopicID'):
            logger.info('No comments found for the topic ' + str(topic_id))
            continue
        else:
            for comment_id, row_comment in comments.loc[(topic_id,)].iterrows():
                if not pd.isna(row_comment['Author_code']):
                    logger.info('Comment ' + str(comment_id) + ' (' + str(comments.index.get_loc((topic_id,comment_id)) + 1) + ' out of ' + str(len(comments)) + ') has already been processed')
                    continue
                logger.info('Processing comment ' + str(comment_id) + ' (' + str(comments.index.get_loc((topic_id,comment_id)) + 1) + ' out of ' + str(len(comments)) + ')')
                comment = soup.find(id=comment_id)
                if comment == None:
                    logger.warning('Comment ID ' + str(comment_id) + ' in the topic ' + str(topic_id) + ' is not found! (Link: ' + url + ')')
                else:
                    author_code, start = get_user_pseudo_code(comment.attrs['data-member'], comment.attrs['data-user'], users, driver, None, graph)
                    users.loc[comment.attrs['data-member'],'n_sex_comments'] = start['n_sex_comments'] = users.loc[comment.attrs['data-member'],'n_sex_comments'] + 1
                    quotes = comment.find_all('blockquote')
                    quoted_users = []
                    for quote in quotes:
                        quote_header = quote.find('b')
                        if quote_header != None:
                            quote_pattern_match = quote_pattern.match(quote_header.text)
                            if quote_pattern_match:
                                try:
                                    quoted = quote_header.find_all('a')[1]
                                    quoted_nick = quoted.text
                                    quoted_profile_link = quoted.attrs['href']
                                    quoted_id = quoted_profile_link.split('/')[-1]
                                except IndexError:
                                    original_quoted_comment_link = quote_header.find_all('a')[0].attrs['href']
                                    original_comment_id = original_quoted_comment_link.split('#')[1].replace('p','')
                                    original_comment = soup.find(id=original_comment_id)
                                    if original_comment != None:
                                        quoted_nick = original_comment.attrs['data-member']
                                        quoted_id = original_comment.attrs['data-user']
                                    else:
                                        quoted_nick = quote_pattern_match.group('nick')
                                        quoted_id = pd.to_numeric(users.id).min() - 1
                                        logger.warning('User ' + quoted_nick + ' quoted in comment ID ' + str(comment_id) + ' (original comment ID is ' + str(original_comment_id) + ') in the topic ' + str(topic_id) + ' is not found! (Link to the original comments is: ' + original_quoted_comment_link + ')')
                                    quoted_profile_link = None
                                quoted_user, finish = get_user_pseudo_code(quoted_nick, quoted_id, users, driver, quoted_profile_link, graph)
                                if quoted_user not in quoted_users:
                                    graph.add_edge(start,finish)
                                    quoted_users.append(quoted_user)
                    comments.loc[(topic_id,comment_id),'Author_code'] = author_code
                    if first_comment:
                        topics.loc[topic_id,'initiated'] = users.loc[comment.attrs['data-member']]['code']
                        users.loc[comment.attrs['data-member'], 'n_initiations'] = users.loc[comment.attrs['data-member']]['n_initiations'] + 1
                        start['n_initiations'] = users.loc[comment.attrs['data-member'], 'n_initiations']
                        first_comment = False
        topics.loc[topic_id,'is_processed'] = True
    

def get_starts_by_users(topics, comments, graph):
    for topic_id, row_topic in topics.iterrows():
        logger.info('Processing topic ' + str(topic_id) + ' (' + str(topics.index.get_loc(topic_id) + 1) + ' out of ' + str(len(topics)) + ')')
        url = 'https://forum.fok.nl/topic/' + str(topic_id) + '/1/999'
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        is_error = soup.find('#pageWrapper div[class="fieldholder breadcrumb"] h1') 
        if is_error != None and is_error.text == 'error #52':
            logger.error('Error occured when processing topic ' + str(topic_id) + '. Link: ' + url)
            continue
        elif topic_id not in comments.index.get_level_values('TopicID'):
            logger.info('No comments found for the topic ' + str(topic_id))
            continue
        else:
            first_comment_id = comments.loc[(topic_id,)].iloc[0].name
            user = soup.find(id=first_comment_id).attrs['data-member']
            row_topic['initiated'] = users.loc[user]['code']
            users.loc[user, 'n_initiations'] = users.loc[user]['n_initiations'] + 1
            logger.info('Processed topic % s. Initiator %s is recodred', str(topic_id), user)
    for _, row_user in users.iterrows():
        node = graph.vs.find(int(row_user['code']))
        node['n_initiations'] = int(row_user['n_initiations'])
        logger.info('Initiator %s is recodred in the graph', node['id'])




try:
    scrape_quotes()

except Exception as e:
    logger.exception(e)
finally:
    logger.info('Saving file\nSaving topics progress\n')
    topics.to_csv('C:\\SHB\\FOK!\\20210520_topic_list.csv')
    logger.info('Topics progress saved\nSaving comments with authors\n')
    comments.to_csv('C:\\SHB\\FOK!\\20210520_comment_list.csv')
    logger.info('Saving comments with authors complete\nSaving graph\n')
    graph.save('C:\\SHB\\FOK!\\FOK!_users.graphml')
    logger.info('Saving graph complete\nSaving users list')
    users.to_csv('C:\\SHB\\FOK!\\users_list.csv')
    logger.info('Saving users list complete\n')
    driver.close()
    logger.info('Driver closed!')
