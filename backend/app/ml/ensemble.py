from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

from app.ml.features import COLOR_FEATURES, FULL_FEATURES, TEXTURE_FEATURES, vectorize_features


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def pstdev(values: list[float]) -> float:
    if not values:
        return 0.0
    center = mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


@dataclass
class StandardScaler:
    means: list[float]
    stds: list[float]

    @classmethod
    def fit(cls, rows: list[list[float]]) -> "StandardScaler":
        columns = list(zip(*rows))
        means = [sum(column) / len(column) for column in columns]
        stds = []
        for column, column_mean in zip(columns, means):
            variance = sum((value - column_mean) ** 2 for value in column) / len(column)
            stds.append(math.sqrt(variance) or 1.0)
        return cls(means=means, stds=stds)

    def transform_row(self, row: list[float]) -> list[float]:
        return [(value - mean_value) / std for value, mean_value, std in zip(row, self.means, self.stds)]

    def to_dict(self) -> dict[str, list[float]]:
        return {"means": self.means, "stds": self.stds}


@dataclass
class LogisticModel:
    weights: list[float]
    bias: float

    @classmethod
    def fit(
        cls,
        rows: list[list[float]],
        labels: list[int],
        learning_rate: float = 0.08,
        epochs: int = 700,
        l2: float = 0.001,
    ) -> "LogisticModel":
        weights = [0.0 for _ in rows[0]]
        bias = 0.0
        positives = sum(labels)
        negatives = len(labels) - positives
        pos_weight = len(labels) / max(positives * 2, 1)
        neg_weight = len(labels) / max(negatives * 2, 1)

        for _ in range(epochs):
            gradient = [0.0 for _ in weights]
            bias_gradient = 0.0

            for row, label in zip(rows, labels):
                probability = sigmoid(dot(weights, row) + bias)
                weight = pos_weight if label == 1 else neg_weight
                error = (probability - label) * weight

                for index, value in enumerate(row):
                    gradient[index] += error * value
                bias_gradient += error

            sample_count = len(rows)
            for index in range(len(weights)):
                weights[index] -= learning_rate * (
                    (gradient[index] / sample_count) + (l2 * weights[index])
                )
            bias -= learning_rate * (bias_gradient / sample_count)

        return cls(weights=weights, bias=bias)

    def predict_proba(self, row: list[float]) -> float:
        return sigmoid(dot(self.weights, row) + self.bias)

    def to_dict(self) -> dict[str, object]:
        return {"weights": self.weights, "bias": self.bias}


@dataclass
class LinearModel:
    weights: list[float]
    bias: float

    @classmethod
    def fit(
        cls,
        rows: list[list[float]],
        targets: list[float],
        learning_rate: float = 0.03,
        epochs: int = 1000,
        l2: float = 0.001,
    ) -> "LinearModel":
        weights = [0.0 for _ in rows[0]]
        bias = 0.0

        for _ in range(epochs):
            gradient = [0.0 for _ in weights]
            bias_gradient = 0.0

            for row, target in zip(rows, targets):
                prediction = dot(weights, row) + bias
                error = prediction - target
                for index, value in enumerate(row):
                    gradient[index] += error * value
                bias_gradient += error

            sample_count = len(rows)
            for index in range(len(weights)):
                weights[index] -= learning_rate * (
                    (gradient[index] / sample_count) + (l2 * weights[index])
                )
            bias -= learning_rate * (bias_gradient / sample_count)

        return cls(weights=weights, bias=bias)

    def predict(self, row: list[float]) -> float:
        return dot(self.weights, row) + self.bias

    def to_dict(self) -> dict[str, object]:
        return {"weights": self.weights, "bias": self.bias}


@dataclass
class KnnModel:
    rows: list[list[float]]
    labels: list[int]
    neighbors: int = 17

    def predict_proba(self, row: list[float], exclude_index: int | None = None) -> float:
        scored = []
        for index, candidate in enumerate(self.rows):
            if exclude_index is not None and index == exclude_index:
                continue
            distance = math.sqrt(sum((left - right) ** 2 for left, right in zip(candidate, row)))
            scored.append((distance, self.labels[index]))

        scored.sort(key=lambda item: item[0])
        nearest = scored[: self.neighbors]
        numerator = 0.0
        denominator = 0.0
        for distance, label in nearest:
            weight = 1.0 / max(distance, 1e-6)
            numerator += weight * label
            denominator += weight
        return numerator / max(denominator, 1e-6)

    def to_dict(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "labels": self.labels,
            "neighbors": self.neighbors,
        }


def split_records(records: list[dict[str, object]], validation_ratio: float = 0.2) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rng = random.Random(42)
    positive = [record for record in records if record["label"] == 1]
    negative = [record for record in records if record["label"] == 0]
    rng.shuffle(positive)
    rng.shuffle(negative)

    positive_cut = max(1, int(len(positive) * validation_ratio))
    negative_cut = max(1, int(len(negative) * validation_ratio))

    validation = positive[:positive_cut] + negative[:negative_cut]
    train = positive[positive_cut:] + negative[negative_cut:]
    rng.shuffle(train)
    rng.shuffle(validation)
    return train, validation


def train_ensemble(records: list[dict[str, object]]) -> dict[str, object]:
    train_records, validation_records = split_records(records)

    color_train = _rows(train_records, COLOR_FEATURES)
    texture_train = _rows(train_records, TEXTURE_FEATURES)
    full_train = _rows(train_records, FULL_FEATURES)
    train_labels = [int(record["label"]) for record in train_records]
    train_hb = [float(record["hb"]) for record in train_records]

    color_scaler = StandardScaler.fit(color_train)
    texture_scaler = StandardScaler.fit(texture_train)
    full_scaler = StandardScaler.fit(full_train)

    color_scaled_train = [color_scaler.transform_row(row) for row in color_train]
    texture_scaled_train = [texture_scaler.transform_row(row) for row in texture_train]
    full_scaled_train = [full_scaler.transform_row(row) for row in full_train]

    color_model = LogisticModel.fit(color_scaled_train, train_labels)
    texture_model = LogisticModel.fit(texture_scaled_train, train_labels)
    hb_model = LinearModel.fit(full_scaled_train, train_hb)
    knn_model = KnnModel(rows=full_scaled_train, labels=train_labels)

    hb_threshold = _best_hb_threshold(train_hb, train_labels)
    hb_scale = max(0.35, pstdev(train_hb))

    fusion_rows = []
    for index, record in enumerate(train_records):
        feature_map = record["features"]
        color_probability = color_model.predict_proba(color_scaled_train[index])
        texture_probability = texture_model.predict_proba(texture_scaled_train[index])
        predicted_hb = hb_model.predict(full_scaled_train[index])
        hb_probability = sigmoid((hb_threshold - predicted_hb) / hb_scale)
        knn_probability = knn_model.predict_proba(full_scaled_train[index], exclude_index=index)
        fusion_rows.append(
            [
                color_probability,
                texture_probability,
                hb_probability,
                knn_probability,
                float(feature_map["blur_score"]) / 2000.0,
                float(feature_map["brightness"]),
                float(feature_map["center_red_green_gap"]),
            ]
        )

    fusion_scaler = StandardScaler.fit(fusion_rows)
    fusion_model = LogisticModel.fit(
        [fusion_scaler.transform_row(row) for row in fusion_rows],
        train_labels,
        learning_rate=0.05,
        epochs=600,
    )

    metrics = evaluate_ensemble(
        validation_records,
        {
            "color_model": color_model,
            "color_scaler": color_scaler,
            "texture_model": texture_model,
            "texture_scaler": texture_scaler,
            "hb_model": hb_model,
            "full_scaler": full_scaler,
            "knn_model": knn_model,
            "fusion_model": fusion_model,
            "fusion_scaler": fusion_scaler,
            "hb_threshold": hb_threshold,
            "hb_scale": hb_scale,
        },
    )

    return {
        "feature_names": FULL_FEATURES,
        "subsets": {
            "color": COLOR_FEATURES,
            "texture": TEXTURE_FEATURES,
            "full": FULL_FEATURES,
        },
        "models": {
            "color": {
                "scaler": color_scaler.to_dict(),
                "model": color_model.to_dict(),
            },
            "texture": {
                "scaler": texture_scaler.to_dict(),
                "model": texture_model.to_dict(),
            },
            "hb_regressor": {
                "scaler": full_scaler.to_dict(),
                "model": hb_model.to_dict(),
            },
            "knn": {
                "model": knn_model.to_dict(),
            },
            "fusion": {
                "scaler": fusion_scaler.to_dict(),
                "model": fusion_model.to_dict(),
            },
        },
        "calibration": {
            "hb_threshold": hb_threshold,
            "hb_scale": hb_scale,
        },
        "training": metrics | {
            "train_size": len(train_records),
            "validation_size": len(validation_records),
        },
    }


def predict_with_artifact(artifact: dict[str, object], feature_map: dict[str, float]) -> dict[str, float]:
    color_model, color_scaler = _deserialize_classifier(artifact, "color")
    texture_model, texture_scaler = _deserialize_classifier(artifact, "texture")
    hb_model, full_scaler = _deserialize_regressor(artifact)
    knn_model = _deserialize_knn(artifact)
    fusion_model, fusion_scaler = _deserialize_classifier(artifact, "fusion")

    color_row = color_scaler.transform_row(vectorize_features(feature_map, artifact["subsets"]["color"]))
    texture_row = texture_scaler.transform_row(vectorize_features(feature_map, artifact["subsets"]["texture"]))
    full_row = full_scaler.transform_row(vectorize_features(feature_map, artifact["subsets"]["full"]))

    color_probability = color_model.predict_proba(color_row)
    texture_probability = texture_model.predict_proba(texture_row)
    predicted_hb = hb_model.predict(full_row)
    knn_probability = knn_model.predict_proba(full_row)

    calibration = artifact["calibration"]
    hb_probability = sigmoid(
        (float(calibration["hb_threshold"]) - predicted_hb) / float(calibration["hb_scale"])
    )

    fusion_input = [
        color_probability,
        texture_probability,
        hb_probability,
        knn_probability,
        float(feature_map["blur_score"]) / 2000.0,
        float(feature_map["brightness"]),
        float(feature_map["center_red_green_gap"]),
    ]
    fusion_probability = fusion_model.predict_proba(
        fusion_scaler.transform_row(fusion_input)
    )

    disagreement = pstdev([color_probability, texture_probability, hb_probability, knn_probability])
    margin_uncertainty = 1.0 - abs(fusion_probability - 0.5) * 2.0
    uncertainty = clamp((disagreement * 0.9) + (margin_uncertainty * 0.28))

    return {
        "anemia_risk": fusion_probability,
        "predicted_hemoglobin": predicted_hb,
        "uncertainty": uncertainty,
        "color_probability": color_probability,
        "texture_probability": texture_probability,
        "hb_probability": hb_probability,
        "knn_probability": knn_probability,
    }


def save_artifact(artifact: dict[str, object], path: str | Path) -> None:
    Path(path).write_text(json.dumps(artifact, indent=2), encoding="utf-8")


def load_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_ensemble(records: list[dict[str, object]], runtime: dict[str, object]) -> dict[str, float]:
    predictions = []
    labels = []
    hb_errors = []

    for record in records:
        labels.append(int(record["label"]))
        predicted = predict_with_artifact(
            {
                "subsets": {
                    "color": COLOR_FEATURES,
                    "texture": TEXTURE_FEATURES,
                    "full": FULL_FEATURES,
                },
                "models": {
                    "color": {
                        "scaler": runtime["color_scaler"].to_dict(),
                        "model": runtime["color_model"].to_dict(),
                    },
                    "texture": {
                        "scaler": runtime["texture_scaler"].to_dict(),
                        "model": runtime["texture_model"].to_dict(),
                    },
                    "hb_regressor": {
                        "scaler": runtime["full_scaler"].to_dict(),
                        "model": runtime["hb_model"].to_dict(),
                    },
                    "knn": {
                        "model": runtime["knn_model"].to_dict(),
                    },
                    "fusion": {
                        "scaler": runtime["fusion_scaler"].to_dict(),
                        "model": runtime["fusion_model"].to_dict(),
                    },
                },
                "calibration": {
                    "hb_threshold": runtime["hb_threshold"],
                    "hb_scale": runtime["hb_scale"],
                },
            },
            record["features"],
        )
        predictions.append(predicted["anemia_risk"])
        hb_errors.append(abs(predicted["predicted_hemoglobin"] - float(record["hb"])))

    predicted_labels = [1 if prediction >= 0.5 else 0 for prediction in predictions]
    true_positives = sum(
        1 for predicted, label in zip(predicted_labels, labels) if predicted == 1 and label == 1
    )
    true_negatives = sum(
        1 for predicted, label in zip(predicted_labels, labels) if predicted == 0 and label == 0
    )
    false_positives = sum(
        1 for predicted, label in zip(predicted_labels, labels) if predicted == 1 and label == 0
    )
    false_negatives = sum(
        1 for predicted, label in zip(predicted_labels, labels) if predicted == 0 and label == 1
    )

    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)
    accuracy = (true_positives + true_negatives) / max(len(labels), 1)
    f1 = (2 * precision * recall) / max(precision + recall, 1e-6)

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mae_hb": round(mean(hb_errors), 4),
    }


def _deserialize_classifier(artifact: dict[str, object], key: str) -> tuple[LogisticModel, StandardScaler]:
    model_data = artifact["models"][key]["model"]
    scaler_data = artifact["models"][key]["scaler"]
    return (
        LogisticModel(weights=list(model_data["weights"]), bias=float(model_data["bias"])),
        StandardScaler(
            means=[float(value) for value in scaler_data["means"]],
            stds=[float(value) for value in scaler_data["stds"]],
        ),
    )


def _deserialize_regressor(artifact: dict[str, object]) -> tuple[LinearModel, StandardScaler]:
    model_data = artifact["models"]["hb_regressor"]["model"]
    scaler_data = artifact["models"]["hb_regressor"]["scaler"]
    return (
        LinearModel(weights=list(model_data["weights"]), bias=float(model_data["bias"])),
        StandardScaler(
            means=[float(value) for value in scaler_data["means"]],
            stds=[float(value) for value in scaler_data["stds"]],
        ),
    )


def _deserialize_knn(artifact: dict[str, object]) -> KnnModel:
    model_data = artifact["models"]["knn"]["model"]
    return KnnModel(
        rows=[[float(value) for value in row] for row in model_data["rows"]],
        labels=[int(value) for value in model_data["labels"]],
        neighbors=int(model_data["neighbors"]),
    )


def _rows(records: list[dict[str, object]], names: list[str]) -> list[list[float]]:
    return [vectorize_features(record["features"], names) for record in records]


def _best_hb_threshold(hb_values: list[float], labels: list[int]) -> float:
    candidates = sorted(set(hb_values))
    if len(candidates) == 1:
        return candidates[0]

    best_threshold = candidates[0]
    best_score = -1.0
    for left, right in zip(candidates, candidates[1:]):
        threshold = (left + right) / 2.0
        predictions = [1 if value <= threshold else 0 for value in hb_values]
        tp = sum(1 for prediction, label in zip(predictions, labels) if prediction == 1 and label == 1)
        fp = sum(1 for prediction, label in zip(predictions, labels) if prediction == 1 and label == 0)
        fn = sum(1 for prediction, label in zip(predictions, labels) if prediction == 0 and label == 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        score = (2 * precision * recall) / max(precision + recall, 1e-6)
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold
