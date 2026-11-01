"""Topic modelling for the phage funding grants (LDA), as in Mbogning Fonkou & Kong (2024).

Pipeline:
  text = Title translated + Abstract translated + Keywords
  -> lowercase, remove stopwords (WordCloud list + NLTK stopwords in all languages + 'amp')
  -> drop exact duplicate texts
  -> spaCy en_core_web_md lemmas of nouns, adjectives and verbs
  -> term counts (tokens > 2 characters, min_df=50, max_df=0.75)
  -> sklearn LDA, online learning, learning_offset=50, random_state=111

Fix compared with the 2024 notebook: coherence was computed with vocab = vectorizer.vocabulary_.keys(),
whose order does not match the columns of lda.components_. Here the vocabulary comes from
get_feature_names_out(), so the top words given to the coherence measure are the right ones.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TEXT_COLS = ("Title translated", "Abstract translated", "Keywords")


def stopword_set() -> set[str]:
    from nltk.corpus import stopwords
    from wordcloud import STOPWORDS
    sw = set(STOPWORDS)
    for lang in stopwords.fileids():
        sw.update(stopwords.words(lang))
    sw.add("amp")
    return sw


def build_corpus(df: pd.DataFrame, sw: set[str]):
    """Return unique cleaned texts, the Grant IDs that kept each text, and a map for duplicates."""
    # a missing field becomes the token "nan"; it is kept, as part of the model specification
    raw = pd.Series([" ".join(str(v) for v in row) for row in df[list(TEXT_COLS)].itertuples(index=False)], index=df.index)
    cleaned = raw.apply(lambda t: " ".join(w for w in t.lower().split() if w not in sw))
    keep, first_id, dup_of = [], {}, {}
    for gid, text in zip(df["Grant ID"], cleaned):
        if not text:
            continue
        if text in first_id:
            dup_of[gid] = first_id[text]
        else:
            first_id[text] = gid
            keep.append((gid, text))
    ids = [g for g, _ in keep]
    texts = [t for _, t in keep]
    return ids, texts, dup_of


def lemmatize(texts, model="en_core_web_md", pos=("NOUN", "ADJ", "VERB")):
    import spacy
    nlp = spacy.load(model)
    return [" ".join(t.lemma_ for t in doc if t.pos_ in pos) for doc in nlp.pipe(texts, batch_size=64)]


def tokenize(text: str):
    import nltk
    return [w for w in nltk.word_tokenize(text) if len(w) > 2]


def vectorize(lemmas, sw, min_df=50, max_df=0.75):
    from sklearn.feature_extraction.text import CountVectorizer
    vec = CountVectorizer(tokenizer=tokenize, stop_words=list(sw), min_df=min_df, max_df=max_df,
                          token_pattern=None)
    return vec, vec.fit_transform(lemmas)


def fit_lda(X, k, seed=111):
    from sklearn.decomposition import LatentDirichletAllocation
    return LatentDirichletAllocation(n_components=k, learning_method="online", learning_offset=50,
                                     random_state=seed).fit(X)


def coherence_cv(lda, vec, lemmas, top_n=30) -> float:
    from gensim.corpora import Dictionary
    from gensim.models.coherencemodel import CoherenceModel
    terms = vec.get_feature_names_out()
    vocab = set(terms)
    toks = [[w for w in tokenize(s) if w in vocab] for s in lemmas]
    tops = [[terms[i] for i in comp.argsort()[::-1][:top_n]] for comp in lda.components_]
    return CoherenceModel(topics=tops, texts=toks, dictionary=Dictionary(toks), coherence="c_v").get_coherence()


def seed_agreement(X, k, seeds=(1, 2, 3, 4, 5), base_seed=111) -> pd.DataFrame:
    """Share of grants given the same topic as the base run, after best relabelling."""
    from scipy.optimize import linear_sum_assignment
    base = fit_lda(X, k, base_seed).transform(X).argmax(1)
    rows = []
    for s in seeds:
        other = fit_lda(X, k, s).transform(X).argmax(1)
        ct = pd.crosstab(base, other).reindex(index=range(k), columns=range(k), fill_value=0).values
        r, c = linear_sum_assignment(-ct)
        rows.append({"k": k, "seed": s, "agreement_pct": round(ct[r, c].sum() / ct.sum() * 100, 1)})
    return pd.DataFrame(rows)


def top_words(lda, vec, n=50) -> pd.DataFrame:
    terms = vec.get_feature_names_out()
    return pd.DataFrame({f"topic_{k}": [terms[i] for i in comp.argsort()[::-1][:n]]
                         for k, comp in enumerate(lda.components_)})
