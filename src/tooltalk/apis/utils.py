import re
from functools import lru_cache
from typing import List

import numpy as np
from sent2vec.vectorizer import Vectorizer


def verify_phone_format(phone_number: str) -> bool:
    match = re.match(r"^\d{3}-\d{3}-\d{4}$", phone_number)
    return match is not None


def verify_email_format(email: str) -> bool:
    match = re.match(r"^[\w\-\d\.]+@[\w\-\d\.]+$", email)
    return match is not None


# lru cache should help when running a bunch of comparisons against the same sentence
class _TextVectorizer:
    """
    Mocks sent2vec vectorizer API into a function.
    """
    def __init__(self):
        self.vectorizer = Vectorizer()

    @lru_cache()
    def __call__(self, text: str) -> np.ndarray:
        self.vectorizer.run([text])
        return_vec = self.vectorizer.vectors[0]
        self.vectorizer.vectors = list()  # don't care, please clear
        return return_vec


# TODO this is a hacky way to do this, but it works for now
_vectorize_text: callable = None


def semantic_str_compare(prediction_text: str, ground_truth_text: str) -> bool:
    """
    Compares two strings semantically.
    """
    global _vectorize_text
    if _vectorize_text is None:
        # initialize vectorizer only when needed
        _vectorize_text = _TextVectorizer()

    prediction_vec = _vectorize_text(prediction_text)
    ground_truth_vec = _vectorize_text(ground_truth_text)
    cosine_similarity = np.dot(prediction_vec, ground_truth_vec) / (np.linalg.norm(prediction_vec) * np.linalg.norm(ground_truth_vec))
    return cosine_similarity
