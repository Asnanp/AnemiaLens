"""
Stacked ensemble wrapper classes for AnemiaLens v4 model.
Must live in a stable importable module (not __main__) for joblib pickling.
"""
from __future__ import annotations
import numpy as np


class StackedRegressor:
    """ET + XGB base learners + Ridge meta-learner. Exposes .predict()."""
    def __init__(self, et_r, xgb_r, et_c, xgb_c, meta):
        self.et_r = et_r
        self.xgb_r = xgb_r
        self.et_c = et_c
        self.xgb_c = xgb_c
        self.meta = meta

    def predict(self, X: np.ndarray) -> np.ndarray:
        cols = [
            self.et_r.predict(X),
            self.xgb_r.predict(X) if self.xgb_r is not None else np.zeros(len(X)),
            self.et_c.predict_proba(X)[:, 1],
            self.xgb_c.predict_proba(X)[:, 1] if self.xgb_c is not None else np.zeros(len(X)),
        ]
        return self.meta.predict(np.column_stack(cols))


class StackedClassifier:
    """ET + XGB base learners + LogReg meta-learner. Exposes .predict_proba()."""
    def __init__(self, et_c, xgb_c, et_r, xgb_r, meta):
        self.et_c = et_c
        self.xgb_c = xgb_c
        self.et_r = et_r
        self.xgb_r = xgb_r
        self.meta = meta

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        cols = [
            self.et_r.predict(X),
            self.xgb_r.predict(X) if self.xgb_r is not None else np.zeros(len(X)),
            self.et_c.predict_proba(X)[:, 1],
            self.xgb_c.predict_proba(X)[:, 1] if self.xgb_c is not None else np.zeros(len(X)),
        ]
        return self.meta.predict_proba(np.column_stack(cols))
