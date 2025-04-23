from LeXmo import LeXmo
er = LeXmo.EmotionRecognizer()
import pandas as pd
from pathlib import Path
working_dir = Path('C:\\SHB\\')
platform = 'Kindertelefoon'
df_comments = pd.read_csv(working_dir.joinpath(platform).joinpath(platform +'_comment_list.csv'))
df_comments['Content'] = df_comments['Content'].map(lambda x: pd.NA if str(x).strip() == '' else x)
df_selected_comments = df_comments[df_comments['Content'].notna()]
l = len(df_selected_comments)
for i, comment in df_selected_comments.iterrows():
    print(i,'of',l)
    emotion = er.extract_emotion(comment['Content'])
    emotion.pop('text')
    print(emotion)
    for key in emotion.keys():
        df_comments.loc[i, key] = emotion[key]

df_comments.to_csv(working_dir.joinpath(platform).joinpath(platform +'_comment_list.csv'))