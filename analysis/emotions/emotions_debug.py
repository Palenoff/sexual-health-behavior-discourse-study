import pandas as pd
from nltk.stem.snowball import SnowballStemmer
import nltk
nltk.download('punkt')
from nltk import word_tokenize
from pathlib import Path

class EmotionRecognizer:
    def __init__(self):
        path = Path('dutch_lexicon.txt')
        self.emolex_words = pd.read_csv(path,
                                #names=["word", "emotion", "association"],
                                sep=r'\t', engine='python')

        self.emotions = self.emolex_words.columns.drop(['word','english_word'])

        self.stemmer = SnowballStemmer("dutch")


    def extract_emotion(self,text):

        '''
        Takes text and adds if to a dictionary with 10 Keys  for each of the 10 emotions in the NRC Emotion Lexicon,
        each dictionay contains the value of the text in that emotions divided to the text word count
        INPUT: string
        OUTPUT: dictionary with the text and the value of 10 emotions


        '''

        # response = requests.get('https://raw.github.com/dinbav/LeXmo/master/NRC-Emotion-Lexicon-Wordlevel-v0.92.txt')
        # nrc = StringIO(response.text)



        LeXmo_dict = {'text': text, 'anger': [], 'anticipation': [], 'disgust': [], 'fear': [], 'joy': [], 'negative': [],
                    'positive': [], 'sadness': [], 'surprise': [], 'trust': []}

        
        document = word_tokenize(text)

        word_count = len(document)
        rows_list = []
        for word in document:
            word = self.stemmer.stem(word.lower())

            emo_score = (self.emolex_words[self.emolex_words.word == word])
            emo_score_avg = emo_score.mean()
            rows_list.append(emo_score_avg)

        df = pd.concat(rows_list)
        df.reset_index(drop=True)

        for emotion in list(self.emotions):
            LeXmo_dict[emotion] = df[emotion].sum() / word_count

        return LeXmo_dict
        

er = EmotionRecognizer()
er.extract_emotion('Vreselijk mooi')