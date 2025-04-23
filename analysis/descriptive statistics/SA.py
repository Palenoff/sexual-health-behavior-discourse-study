from pathlib import Path
import pandas as pd
import analysis_toolbox as at
from pattern.nl import sentiment
import numpy as np

for platform in at.platforms:
    working_dir = Path('C:\\SHB\\',platform)
    for type in at.types:
        try:
            # users_df = pd.read_csv(working_dir.joinpath(platform + '_' + type +'_key_users.csv'))
            # df_comments = pd.read_csv(working_dir.joinpath(platform +'_comment_list.csv'))
            # comments = df_comments[df_comments['Author_code'].isin(users_df['id'])]
            # cleaned_comments = at.clean_comments(comments)
            cleaned_comments,df_comments = at.get_comments(platform,type)
            polarity=[]
            subjectivity = []
            for c in cleaned_comments.Content:
                polarity.append(sentiment(c)[0])
                subjectivity.append(sentiment(c)[1])
            print('\n\n'+platform + '\n')
            print(type + '\n')
            print('N comments: ' + str(len(cleaned_comments)) + ' (' + str(len(cleaned_comments)/len(df_comments)*100) + '%)')
            print('Mean polarity: '+str(np.mean(polarity)))
            print('SD polarity: '+str(np.std(polarity)))
            print('Mean positive polarity: '+str(np.mean([s for s in polarity if s > 0])))
            print('SD positive polarity: '+str(np.std([s for s in polarity if s > 0])))
            print('Mean negative polarity: '+str(np.mean([s for s in polarity if s < 0])))
            print('SD negative polarity: '+str(np.std([s for s in polarity if s < 0])))
            print('Percentage of neutral: ' + str((len([s  for s in polarity if s == 0])/len(polarity))*100))
            print('Mean subjectivity: '+str(np.mean(subjectivity)))
            print('SD subjectivity: '+str(np.std(subjectivity)))
        except FileNotFoundError:
            continue