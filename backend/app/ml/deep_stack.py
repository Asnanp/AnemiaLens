from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import torch
from PIL import Image
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from torchvision import models, transforms
from torchvision.models import EfficientNet_B0_Weights
from xgboost import XGBClassifier


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def std(values: list[float]) -> float:
    if not values:
        return 0.0
    center = sum(values) / len(values)
    variance = sum((value - center) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


@dataclass
class DeepEmbeddingExtractor:
    image_size: tuple[int, int] = (224, 224)

    def __post_init__(self) -> None:
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1
        self._preprocess = transforms.Compose(
            [
                transforms.Resize(self.image_size),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=weights.transforms().mean,
                    std=weights.transforms().std,
                ),
            ]
        )
        model = models.efficientnet_b0(weights=weights)
        self._backbone = torch.nn.Sequential(model.features, model.avgpool, torch.nn.Flatten())
        self._backbone.eval()
        self.embedding_dim = 1280

    def embed_image(self, image: Image.Image) -> np.ndarray:
        tensor = self._preprocess(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            return self._backbone(tensor).squeeze(0).numpy().astype(np.float32)

    def embed_paths(self, image_paths: list[Path]) -> np.ndarray:
        rows = []
        for image_path in image_paths:
            with Image.open(image_path) as image:
                rows.append(self.embed_image(image))
        return np.stack(rows)


def train_deep_stack(
    image_paths: list[Path],
    labels: list[int],
    groups: list[str] | None = None,
    random_state: int = 42,
) -> dict[str, object]:
    extractor = DeepEmbeddingExtractor()
    features = extractor.embed_paths(image_paths)
    targets = np.array(labels, dtype=np.int32)
    group_labels = np.array(groups if groups is not None else [f"sample_{i}" for i in range(len(labels))])

    train_indices, validation_indices = _stratified_group_holdout(
        targets=targets,
        groups=group_labels,
        n_splits=5,
        random_state=random_state,
    )

    train_group_labels = group_labels[train_indices]
    train_targets = targets[train_indices]
    base_indices_rel, meta_indices_rel = _stratified_group_holdout(
        targets=train_targets,
        groups=train_group_labels,
        n_splits=4,
        random_state=random_state,
    )
    base_indices = train_indices[base_indices_rel]
    meta_indices = train_indices[meta_indices_rel]

    base_features = features[base_indices]
    base_labels = targets[base_indices]
    meta_features = features[meta_indices]
    meta_labels = targets[meta_indices]
    validation_features = features[validation_indices]
    validation_labels = targets[validation_indices]

    base_models: dict[str, object] = {
        "rf": RandomForestClassifier(
            n_estimators=700,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=random_state,
            n_jobs=-1,
        ),
        "extra": ExtraTreesClassifier(
            n_estimators=900,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        ),
        "knn": KNeighborsClassifier(
            n_neighbors=7,
            weights="distance",
            metric="cosine",
            n_jobs=-1,
        ),
        "xgb": XGBClassifier(
            n_estimators=600,
            max_depth=5,
            learning_rate=0.03,
            subsample=0.9,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=-1,
        ),
    }

    hard_mining_summary: dict[str, object] = {}
    meta_train_columns = []
    validation_columns = []
    trained_models: dict[str, object] = {}
    for model_name, model in base_models.items():
        trained_model, mining_stats = _fit_with_hard_mining(
            model_name=model_name,
            base_model=model,
            features=base_features,
            labels=base_labels,
            hard_multiplier=3.0,
        )
        trained_models[model_name] = trained_model
        hard_mining_summary[model_name] = mining_stats
        meta_train_columns.append(trained_model.predict_proba(meta_features)[:, 1])
        validation_columns.append(trained_model.predict_proba(validation_features)[:, 1])

    meta_train_matrix = np.stack(meta_train_columns, axis=1)
    validation_matrix = np.stack(validation_columns, axis=1)

    meta_model = LogisticRegression(max_iter=1200, class_weight="balanced")
    meta_model.fit(meta_train_matrix, meta_labels)
    validation_probabilities = meta_model.predict_proba(validation_matrix)[:, 1]

    threshold, metrics = _best_threshold_metrics(validation_labels, validation_probabilities)

    artifact = {
        "version": "deep-stack-v1",
        "threshold": threshold,
        "models": trained_models,
        "meta_model": meta_model,
        "metrics": metrics
        | {
            "train_size": int(len(train_indices)),
            "validation_size": int(len(validation_indices)),
            "split_strategy": "stratified-group-holdout",
            "hard_mining": hard_mining_summary,
        },
    }
    return artifact


def predict_with_deep_stack(
    artifact: dict[str, object],
    embedding: np.ndarray,
) -> dict[str, float]:
    base_models: dict[str, object] = artifact["models"]
    meta_model: LogisticRegression = artifact["meta_model"]
    threshold = float(artifact["threshold"])

    base_probabilities = []
    for model in base_models.values():
        probability = float(model.predict_proba(embedding.reshape(1, -1))[0, 1])
        base_probabilities.append(probability)

    stacked_probability = float(
        meta_model.predict_proba(np.array(base_probabilities, dtype=np.float32).reshape(1, -1))[0, 1]
    )
    disagreement = std(base_probabilities)
    margin = abs(stacked_probability - threshold)
    uncertainty = clamp((disagreement * 1.3) + (0.42 - margin), 0.05, 0.92)

    return {
        "anemia_risk": stacked_probability,
        "uncertainty": uncertainty,
        "base_min": min(base_probabilities),
        "base_max": max(base_probabilities),
    }


def save_deep_stack_artifact(artifact: dict[str, object], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path)


def load_deep_stack_artifact(path: str | Path) -> dict[str, object]:
    return joblib.load(path)


def _best_threshold_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> tuple[float, dict[str, float]]:
    best_threshold = 0.5
    best_metrics: dict[str, float] | None = None

    for threshold in np.linspace(0.3, 0.7, 81):
        y_pred = (y_prob >= threshold).astype(np.int32)
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }
        if best_metrics is None or metrics["f1"] > best_metrics["f1"]:
            best_metrics = metrics
            best_threshold = float(threshold)

    assert best_metrics is not None
    return best_threshold, {
        key: round(value, 4) for key, value in best_metrics.items()
    }


def _stratified_group_holdout(
    targets: np.ndarray,
    groups: np.ndarray,
    n_splits: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray]:
    if len(np.unique(groups)) < n_splits:
        all_indices = np.arange(len(targets))
        train_indices, validation_indices = train_test_split(
            all_indices,
            test_size=(1.0 / n_splits),
            stratify=targets,
            random_state=random_state,
        )
        return train_indices, validation_indices

    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=random_state,
    )

    label_rate = float(np.mean(targets))
    best_split: tuple[np.ndarray, np.ndarray] | None = None
    best_gap: float | None = None

    for train_indices, validation_indices in splitter.split(
        X=np.zeros(len(targets)),
        y=targets,
        groups=groups,
    ):
        fold_rate = float(np.mean(targets[validation_indices]))
        gap = abs(fold_rate - label_rate)
        if best_gap is None or gap < best_gap:
            best_gap = gap
            best_split = (train_indices, validation_indices)

    assert best_split is not None
    return best_split


def _fit_with_hard_mining(
    model_name: str,
    base_model: object,
    features: np.ndarray,
    labels: np.ndarray,
    hard_multiplier: float,
) -> tuple[object, dict[str, float]]:
    initial_model = clone(base_model)
    initial_model.fit(features, labels)
    initial_probs = initial_model.predict_proba(features)[:, 1]
    initial_preds = (initial_probs >= 0.5).astype(np.int32)
    confidence = np.abs(initial_probs - 0.5)
    confidence_cutoff = float(np.quantile(confidence, 0.25))
    hard_mask = (initial_preds != labels) | (confidence <= confidence_cutoff)
    hard_count = int(np.sum(hard_mask))

    if hard_count == 0:
        return initial_model, {"hard_samples": 0, "hard_ratio": 0.0}

    hard_features = features[hard_mask]
    hard_labels = labels[hard_mask]

    if model_name == "knn":
        repeat_count = max(1, int(hard_multiplier) - 1)
        boosted_features = np.concatenate(
            [features, np.repeat(hard_features, repeat_count, axis=0)],
            axis=0,
        )
        boosted_labels = np.concatenate(
            [labels, np.repeat(hard_labels, repeat_count, axis=0)],
            axis=0,
        )
        trained_model = clone(base_model)
        trained_model.fit(boosted_features, boosted_labels)
    else:
        sample_weight = np.ones(len(labels), dtype=np.float32)
        sample_weight[hard_mask] = hard_multiplier
        trained_model = clone(base_model)
        try:
            trained_model.fit(features, labels, sample_weight=sample_weight)
        except TypeError:
            repeat_count = max(1, int(hard_multiplier) - 1)
            boosted_features = np.concatenate(
                [features, np.repeat(hard_features, repeat_count, axis=0)],
                axis=0,
            )
            boosted_labels = np.concatenate(
                [labels, np.repeat(hard_labels, repeat_count, axis=0)],
                axis=0,
            )
            trained_model.fit(boosted_features, boosted_labels)

    return trained_model, {
        "hard_samples": float(hard_count),
        "hard_ratio": round(hard_count / max(len(labels), 1), 4),
    }
