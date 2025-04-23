import numpy as np
import pandas as pd
from pathlib import Path
import torch


import spacy, gensim

# # Sklearn
# from sklearn.decomposition import LatentDirichletAllocation
# from sklearn.feature_extraction.text import CountVectorizer
# from sklearn.model_selection import GridSearchCV
# from pprint import pprint

# # Plotting tools
# import pyLDAvis
# import pyLDAvis.sklearn
# import matplotlib.pyplot as plt
# #%matplotlib inline

import spacy.lang.nl.stop_words as sw_nl
import spacy.lang.en.stop_words as sw_en
stop_words = sw_nl.STOP_WORDS
stop_words = stop_words.union(sw_en.STOP_WORDS)
stop_words.update(['jij', 'jullie', 'wel', 'echt', 'alleen', 'jouw', 'af', 'the', 'to', 'on', 'and', 'it', 'you'])
stop_words = stop_words - {'andere','zelf'}


# #nltk.download('stopwords')
# dutch_stop_words = stopwords.words('dutch')
# dutch_stop_words.extend(stopwords.words('english'))
# dutch_stop_words.extend(['jij', 'jullie', 'wel', 'echt', 'alleen', 'jouw', 'af',\
#                         'the', 'to', 'on', 'and', 'it', 'you'])
# dutch_stop_words.remove('andere')
# dutch_stop_words.remove('zelf')

nlp = spacy.load("nl_core_news_sm")

working_dir = Path('C:\\SHB\\')

topics_rng = [2,3,4,5,6,7,8,9,10,12,15]
platforms = ['FOK!','Kindertelefoon']
types = ['interaction_engagers','discussion_initiators','betweenness','closeness']

def get_high_centrality(graph,working_dir,platform,centrality_method):
    vals = []
    if centrality_method == 'betweenness':
        avg = np.mean(graph.betweenness())
        sd = np.std(graph.betweenness())
    if centrality_method == 'closeness':
        closeness = [c for c in graph.closeness() if not pd.isna(c)]
        avg = np.mean(closeness)
        sd = np.std(closeness)
    try:
        res = pd.read_csv(working_dir.joinpath(platform + '_' + centrality_method +'_key_users.csv'), index_col='id')
        if res.empty:
            create_new = True
        else:
            create_new = False
    except FileNotFoundError:
        create_new = True
    if create_new:
        res = set()
        for v in graph.vs:
            print('Processing vertex ',v.index)
            val = v.betweenness() if centrality_method == 'betweenness' else v.closeness() if centrality_method == 'closeness' and not pd.isna(v.closeness()) else 0
            vals.append(val)
            if val > avg + sd:
                res.add(v)
    else:
        res = set(res.apply(lambda x: graph.vs.find(x.name),axis=1))
    return avg,sd,res,vals,create_new


def get_users_with_high_attribute_value(graph,attribute):
    val_vector = [v.attributes()[attribute] for v in graph.vs if v.attributes()[attribute] != 0]
    avg_vector = np.mean(val_vector)
    sd_vector = np.std(val_vector)
    return avg_vector, sd_vector, [v for v in graph.vs if v.attributes()[attribute] > avg_vector + sd_vector]

def key_actors_to_df(vector,platform,type,f):
    data = []
    path = Path('C:\\SHB\\',platform,platform + '_' + type +'_key_users.csv')
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print('No file with dataset found! Generating new dataset!')
        for v in vector:
            print('Processing vertex ',v.index)
            attrs = v.attributes()
            if f != None:
                attrs[type] = f(v)
            data.append(attrs)
        df = pd.DataFrame(data).set_index('id')
        df.to_csv(path)
    return df

def read_users(platform,type):
    return pd.read_csv(working_dir.joinpath(platform).joinpath(platform + '_' + type +'_key_users.csv'))

def read_comments(platform):
    return pd.read_csv(working_dir.joinpath(platform).joinpath(platform +'_comment_list.csv'))


def get_comments(platform,type=None):
    df_comments = read_comments(platform)
    df_comments['Content'] = df_comments['Content'].map(lambda x: pd.NA if str(x).strip() == '' else x)
    df_not_na_comments = df_comments[df_comments['Content'].notna()]
    if type != None:
        users_df = read_users(platform,type)
        return df_not_na_comments[df_not_na_comments['Author_code'].isin(users_df['id'])],df_comments
    else:
        return df_not_na_comments,df_comments

def clean_comments(comments):

    comments = comments.copy()
    # Remove gewijzigd messages
    comments['Content'] = comments['Content'].map(lambda x: pd.NA if str(x).strip() == '' else x)
    comments = comments.Content[comments.Content.notnull()]
    comments = comments.str.replace(r'\[.*?gewijzigd.*?\]', '', regex=True)

    # Remove improperly quoted content
    comments = comments[~comments.str.contains(r'\[quote\]') | comments.str.contains('quote: Op')]

    # Remove empty comments



    comments = comments.astype(str)
    return comments

def get_toxicity_of_the_comment(comment,tokenizer,toxicity_model):
        inputs = tokenizer(comment,padding=True, truncation=True,max_length=512, add_special_tokens = True,return_tensors="pt")
        with torch.no_grad():
            logits = toxicity_model(**inputs).logits
        predicted_class_id = logits.argmax().item()
        return toxicity_model.config.id2label[predicted_class_id]


def get_toxicity(platform,type):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained("IMSyPP/hate_speech_nl")
    toxicity_model = AutoModelForSequenceClassification.from_pretrained("IMSyPP/hate_speech_nl")
    df_selected_comments, df_comments = get_comments(platform,type)
    i = 1
    for index,comment in df_selected_comments[df_selected_comments[pd.isna(df_comments['Toxicity'])]].iterrows():
        print('Processing comment',i,'out of',len(df_selected_comments))
        try:
            toxicity = get_toxicity_of_the_comment(comment.Content,tokenizer,toxicity_model)
            df_comments.loc[index,'Toxicity'] = toxicity
            i = i + 1
        except Exception as ex:
            print(ex)
    df_comments.to_csv(working_dir.joinpath(platform).joinpath(platform +'_comment_list.csv'))



def lemmatization(texts, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV']):
    """https://spacy.io/api/annotation"""
    texts_out = []
    for sent in texts:
        doc = nlp(" ".join(sent)) 
        texts_out.append(" ".join([token.lemma_ if token.lemma_ not in ['-PRON-'] else '' for token in doc if token.pos_ in allowed_postags]))
    return texts_out

# def topic_modeling(comments):
#     # user_ids = [v.attributes()['id'] for v in user_nodes]
#     # df_comments = pd.read_csv(working_dir.joinpath(platform +'_comment_list.csv'))
#     # comments = df_comments[df_comments['Author_code'] in user_ids]
#     cleaned_comments = comments.map(lambda x: gensim.utils.simple_preprocess(str(x), deacc=True))

#     # Do lemmatization keeping only Noun, Adj, Verb, Adverb
#     lemmatized_comments = lemmatization(cleaned_comments, allowed_postags=['NOUN', 'ADJ', 'VERB', 'ADV'])

#     vectorizer = CountVectorizer(analyzer='word',       
#                              min_df=10,                        # minimum reqd occurences of a word 
#                              stop_words=stop_words,             # remove stop words
#                              lowercase=True,                   # convert all words to lowercase
#                              token_pattern='[a-zA-Z0-9]{3,}',  # num chars > 3
#                              # max_features=50000,             # max number of uniq words
#                             )

#     vectorized_comments = vectorizer.fit_transform(lemmatized_comments)
#     # Materialize the sparse data
#     data_dense = vectorized_comments.todense()

#     # Compute Sparsicity = Percentage of Non-Zero cells
#     print("Sparsicity: ", ((data_dense > 0).sum()/data_dense.size)*100, "%")

#     lda_model = LatentDirichletAllocation(n_components=20,               # Number of topics
#                                       max_iter=10,               # Max learning iterations
#                                       learning_method='online',   
#                                       random_state=100,          # Random state
#                                       batch_size=128,            # n docs in each learning iter
#                                       evaluate_every = -1,       # compute perplexity every n iters, default: Don't
#                                       n_jobs = -1,               # Use all available CPUs
#                                      )
#     lda_output = lda_model.fit_transform(vectorized_comments)

#     print(lda_model)  # Model attributes
#     print(lda_output)
#     return lda_model,vectorized_comments,vectorizer

# def select_lda_model(vectorized_comments):
#     # Define Search Param
#     search_params = {'n_components': topics_rng, 'learning_decay': [.5, .7, .9]}

#     # Init the Model
#     lda = LatentDirichletAllocation()

#     # Init Grid Search Class
#     model = GridSearchCV(lda, param_grid=search_params,verbose=4)

#     # Do the Grid Search
#     model.fit(vectorized_comments)

#     # Best Model
#     best_lda_model = model.best_estimator_

#     # Model Parameters
#     print("Best Model's Params: ", model.best_params_)

#     # Log Likelihood Score
#     print("Best Log Likelihood Score: ", model.best_score_)

#     # Perplexity
#     print("Model Perplexity: ", best_lda_model.perplexity(vectorized_comments))

#     return best_lda_model,model

# def get_dominant_topics_ny_docs(best_lda_model,data_vectorized,data):
#         # Create Document - Topic Matrix
#     lda_output = best_lda_model.transform(data_vectorized)

#     # column names
#     topicnames = ["Topic" + str(i) for i in range(best_lda_model.n_topics)]

#     # index names
#     docnames = ["Doc" + str(i) for i in range(len(data))]

#     # Make the pandas dataframe
#     df_document_topic = pd.DataFrame(np.round(lda_output, 2), columns=topicnames, index=docnames)

#     # Get dominant topic for each document
#     dominant_topic = np.argmax(df_document_topic.values, axis=1)
#     df_document_topic['dominant_topic'] = dominant_topic

#     # Styling
#     def color_green(val):
#         color = 'green' if val > .1 else 'black'
#         return 'color: {col}'.format(col=color)

#     def make_bold(val):
#         weight = 700 if val > .1 else 400
#         return 'font-weight: {weight}'.format(weight=weight)

#     # Apply Style
#     #df_document_topics = df_document_topic.head(15).style.applymap(color_green).applymap(make_bold)
#     df_topic_distribution = df_document_topic['dominant_topic'].value_counts().reset_index(name="Num Documents")
#     df_topic_distribution.columns = ['Topic Num', 'Num Documents']
#     return df_topic_distribution

# def plot_best_lda(model):
    # Get Log Likelyhoods from Grid Search Output
    n_topics = topics_rng
    log_likelyhoods_5 = [round(model.cv_results_['mean_test_score'][index]) for index, gscore in enumerate(model.cv_results_['params']) if gscore['learning_decay']==0.5]
    log_likelyhoods_7 = [round(model.cv_results_['mean_test_score'][index]) for index, gscore in enumerate(model.cv_results_['params']) if gscore['learning_decay']==0.7]
    log_likelyhoods_9 = [round(model.cv_results_['mean_test_score'][index]) for index, gscore in enumerate(model.cv_results_['params']) if gscore['learning_decay']==0.9]

    # Show graph
    plt.figure(figsize=(12, 8))
    plt.plot(n_topics, log_likelyhoods_5, label='0.5')
    plt.plot(n_topics, log_likelyhoods_7, label='0.7')
    plt.plot(n_topics, log_likelyhoods_9, label='0.9')
    plt.title("Choosing Optimal LDA Model")
    plt.xlabel("Num Topics")
    plt.ylabel("Log Likelyhood Scores")
    plt.legend(title='Learning decay', loc='best')
    plt.show()

def show_topics(vectorizer, lda_model, n_words=20):
    keywords = np.array(vectorizer.get_feature_names())
    topic_keywords = []
    for topic_weights in lda_model.components_:
        top_keyword_locs = (-topic_weights).argsort()[:n_words]
        topic_keywords.append(keywords.take(top_keyword_locs))
    return topic_keywords

