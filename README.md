# 🧠 Online Sexual Health Conversations: A Comparative Analysis of Moderated and Non-Moderated Platforms

This repository contains the code, data structure, and documentation for the internship project conducted by **Kirill Palenov** at the **Amsterdam School of Communication Research (UvA)**, as part of the **VU Amsterdam MSc in Social Sciences for a Digital Society**. The project explores the behavioral patterns and content quality of user-generated discussions on **online sexual health platforms**, with a focus on the effect of **moderation**.

---

## 📘 Project Overview

This study investigates how **key users** engage in sexual health discussions on two Dutch-language platforms:

- **De Kindertelefoon** (moderated helpline forum for adolescents)
- **FOK! Forum** (non-moderated general discussion forum)

The research aims to describe user behaviors and the content they produce using a **multi-method analytical pipeline**, including:
- **Social Network Analysis (SNA)**
- **Topic Modeling (LDA)**
- **Sentiment & Emotion Analysis**
- **Toxicity Detection**

---

## 🔍 Research Questions

**Main RQ**:  
_What are the discourses of online sexual health discussions in terms of user activity and content shared on moderated vs. non-moderated platforms?_

---

## 🧰 Methods & Tools

### 💬 Data
- Two datasets per platform: threads & comments (2014–2021)
- Collected using Python's **BeautifulSoup** and **Selenium**
- Over 200,000 comments analyzed
- Data available upon request

### 🔗 Network Analysis
- Conducted with `igraph` in Python
- Metrics: in-degree, out-degree, betweenness, closeness centralities
- Identification of four key user groups: **Initiators**, **Repliers**, **Mediators**, **Independents**

### 🧠 NLP Tasks
- **Topic modeling**: `sklearn` LDA with custom preprocessing
- **Sentiment**: `Pattern.nl`, `TextBlob-nl`, dictionary-based analysis
- **Emotion detection**: `NRC Word-Emotion Lexicon` via `LeXmo`
- **Toxicity**: Dutch BERT-based models from HuggingFace (`IMSyPP`, `ml6team`)

---

## 📊 Key Findings

- Moderated platform (De Kindertelefoon) had more topic-specific, neutral, and civil discourse.
- Non-moderated platform (FOK!) had higher topic diversity and emotional expression but also higher toxicity.
- Key users often shaped discourse similarly to general users, but with slightly more neutral tone and higher influence within the network.

---

## 📁 Repository Structure

```
├── data/
│   └── available under request
├── analysis/
│   └── key users (network analysis)
│   └── descriptive statitics
│   └── emotion analysis
│   └── topic modeling
│      └── LDA models
│   └── sentiment analysis
│   └── toxicity analysis
├── scraping/
│   └── FOK!
│   └── De Kindertelefoon
├── visualization/
├── README.md
└── report/
    └── UAaCoOSHC Internship report_Palenov_2022.pdf
```

---

## 📢 Contact

For questions or collaborations, please contact:  
**Kirill Palenov**  
📧 kirill.i.palenov[at]gmail.com  
🔗 [LinkedIn Profile](https://linkedin.com/in/kirill-palenov)
