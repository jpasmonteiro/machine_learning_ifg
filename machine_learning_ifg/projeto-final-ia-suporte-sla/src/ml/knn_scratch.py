"""
K-Nearest Neighbors (KNN) implementado "na mao", so com NumPy.

KNN nao "treina": guarda os exemplos e, para prever, calcula a distancia
euclidiana ate todos os pontos de treino, pega os k vizinhos mais proximos e
faz a votacao (probabilidade da classe 1 = fracao de vizinhos da classe 1).
Interface igual a' do scikit-learn (fit/predict/predict_proba).
"""
import numpy as np


class KNNScratch:
    def __init__(self, k=15):
        self.k = k
        self.X = None
        self.y = None

    def fit(self, X, y):
        self.X = np.asarray(X, dtype=float)
        self.y = np.asarray(y, dtype=int)
        return self

    def _distances(self, A):
        a2 = (A ** 2).sum(axis=1)[:, None]
        b2 = (self.X ** 2).sum(axis=1)[None, :]
        d2 = a2 + b2 - 2.0 * (A @ self.X.T)
        return np.sqrt(np.maximum(d2, 0.0))

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        idx = np.argsort(self._distances(X), axis=1)[:, :self.k]
        p1 = self.y[idx].mean(axis=1)
        return np.column_stack([1.0 - p1, p1])

    def predict(self, X, threshold=0.5):
        return (self.predict_proba(X)[:, 1] >= threshold).astype(int)
