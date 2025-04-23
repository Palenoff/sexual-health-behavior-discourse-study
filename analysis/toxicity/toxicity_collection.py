import analysis_toolbox as at
platforms = ['FOK!','Kindertelefoon']
types = ['discussion_initiators','interaction_engagers','betweenness','closeness']
for platform in platforms:
    for type in types:
        print(platform,'\n',type)
        at.get_toxicity(platform,type)