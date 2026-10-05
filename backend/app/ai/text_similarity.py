"""TF-IDF + cosine similarity between short texts.

Why TF-IDF: it is a classic, easy-to-explain way to measure how much two texts talk
about the same things. Words that appear in every job ("team", "work") count little;
words that are rare across jobs ("kubernetes", "analytics") count a lot.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def tfidf_similarities(queries: list[str], documents: list[str]) -> list[list[float]]:
    """Cosine similarity (0..1) of every query against every document.

    The vocabulary and word weights (idf) are learned from the documents plus the
    queries together. Blank texts, or texts with no usable words, score 0.
    """
    zeros = [[0.0] * len(documents) for _ in queries]
    if not queries or not documents:
        return zeros
    corpus = [*documents, *queries]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True, lowercase=True)
        matrix = vectorizer.fit_transform(corpus)  # rows are L2-normalised
    except ValueError:  # empty vocabulary: nothing but stop words / blanks
        return zeros
    docs, qrys = matrix[: len(documents)], matrix[len(documents):]
    sims = (qrys @ docs.T).toarray()
    return np.clip(sims, 0.0, 1.0).tolist()
