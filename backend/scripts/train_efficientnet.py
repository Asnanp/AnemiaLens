from __future__ import annotations

import json
import math
import random
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from app.config import (
    BACKEND_ROOT,
    DEFAULT_EFFICIENTNET_MODEL_PATH,
    DEFAULT_EFFICIENTNET_REPORT_PATH,
    DEFAULT_TRAINING_REPORT_PATH,
)
from app.ml.archive_model import ANEMIA_HB_THRESHOLD, _first_path, _load_image_with_fallback, _parse_float, _parse_workbook
from app.ml.efficientnet_model import (
    EFFICIENTNET_VERSION,
    build_efficientnet_model,
    build_train_transform,
    build_val_transform,
)
from app.services.conjunctiva_roi import ConjunctivaRoiExtractor


DATA_ROOT = BACKEND_ROOT / "data"
ARCHIVE_ROOT = BACKEND_ROOT.parent / "archive" / "dataset anemia"
SEED = 42
BATCH_SIZE = 16
EPOCHS = 60
PATIENCE = 15
MAX_GRAD_NORM = 1.0
WARMUP_EPOCHS = 5
LABEL_SMOOTHING = 0.05
MIXUP_ALPHA = 0.3
# Hb spread loss: penalizes predictions that cluster near the mean
HB_SPREAD_WEIGHT = 0.15


@dataclass(frozen=True)
class ImageRecord:
    subject_id: str
    label: int
    hb: float
    image_path: Path
    source: str


class ConjunctivaDataset(Dataset):
    def __init__(self, records: list[ImageRecord], transform: object) -> None:
        self.records = records
        self.transform = transform
        self.roi_extractor = ConjunctivaRoiExtractor()

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        record = self.records[index]
        image, label, hb = self._prepare_item(record)
        tensor = self.transform(image)
        return tensor, torch.tensor([label], dtype=torch.float32), torch.tensor([hb], dtype=torch.float32)

    def _prepare_item(self, record: ImageRecord) -> tuple[Image.Image, float, float]:
        image = _load_image_with_fallback(record.image_path)
        if record.source == "roi_original":
            image = self.roi_extractor.extract(image).image
        return image.convert("RGB"), float(record.label), float(record.hb)


class FocalLoss(nn.Module):
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0, pos_weight: torch.Tensor | None = None) -> None:
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight, reduction="none")

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce_loss = self.bce(inputs, targets)
        probabilities = torch.sigmoid(inputs)
        p_t = probabilities * targets + (1 - probabilities) * (1 - targets)
        loss = bce_loss * ((1 - p_t) ** self.gamma)
        if self.alpha >= 0:
            alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
            loss = alpha_t * loss
        return loss.mean()


def main() -> None:
    _set_seed(SEED)
    dataset_root = DATA_ROOT if DATA_ROOT.exists() else ARCHIVE_ROOT
    if not dataset_root.exists():
        raise RuntimeError(f"No dataset directory found at {DATA_ROOT} or {ARCHIVE_ROOT}.")

    records = _build_records(dataset_root)
    if not records:
        raise RuntimeError(f"No training records found in {dataset_root}.")

    train_records, val_records = _balanced_group_split(records, test_size=0.2, n_splits=32)
    train_dataset = ConjunctivaDataset(train_records, build_train_transform())
    val_dataset = ConjunctivaDataset(val_records, build_val_transform())
    hb_mean, hb_std = _hb_normalization_stats(train_records)
    train_sampler = _build_weighted_sampler(train_records)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_efficientnet_model(pretrained=True).to(device)
    optimizer = AdamW(
        [
            {"params": list(model.classifier.parameters()), "lr": 1.5e-4}, # Slightly lower for stability
            {"params": [param for param in model.features.parameters() if param.requires_grad], "lr": 5e-6},
        ],
        weight_decay=4e-4, # Higher weight decay for better regularization
    )

    # Warmup then cosine annealing
    def warmup_cosine_lr(epoch: int) -> float:
        if epoch < WARMUP_EPOCHS:
            return float(epoch + 1) / WARMUP_EPOCHS
        progress = (epoch - WARMUP_EPOCHS) / max(EPOCHS - WARMUP_EPOCHS, 1)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=warmup_cosine_lr)

    # Use Focal Loss with positive weights
    pos_weight = torch.tensor([_positive_class_weight(train_records)], device=device)
    cls_loss_fn = FocalLoss(alpha=0.25, gamma=2.0, pos_weight=pos_weight)
    hb_loss_fn = nn.SmoothL1Loss(beta=0.5)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=train_sampler, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    best_state: dict[str, torch.Tensor] | None = None
    best_metrics: dict[str, float] | None = None
    best_threshold = 0.5
    best_score = -1.0
    epochs_without_improvement = 0
    history: list[dict[str, float]] = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss_total = 0.0

        for images, labels, hbs in train_loader:
            images = images.to(device)
            labels = labels.to(device)
            hbs = hbs.to(device)
            normalized_hbs = (hbs - hb_mean) / hb_std

            # MixUp augmentation
            if MIXUP_ALPHA > 0 and np.random.random() < 0.5:
                lam = float(np.random.beta(MIXUP_ALPHA, MIXUP_ALPHA))
                idx = torch.randperm(images.size(0), device=device)
                images = lam * images + (1.0 - lam) * images[idx]
                labels_a, labels_b = labels, labels[idx]
                hbs_a, hbs_b = normalized_hbs, normalized_hbs[idx]

                optimizer.zero_grad(set_to_none=True)
                output = model(images)
                # Label smoothing applied to both MixUp targets
                smooth_a = labels_a * (1.0 - LABEL_SMOOTHING) + 0.5 * LABEL_SMOOTHING
                smooth_b = labels_b * (1.0 - LABEL_SMOOTHING) + 0.5 * LABEL_SMOOTHING
                cls_loss = lam * cls_loss_fn(output[:, 0:1], smooth_a) + (1.0 - lam) * cls_loss_fn(output[:, 0:1], smooth_b)
                hb_loss = lam * hb_loss_fn(output[:, 1:2], hbs_a) + (1.0 - lam) * hb_loss_fn(output[:, 1:2], hbs_b)
            else:
                optimizer.zero_grad(set_to_none=True)
                output = model(images)
                smooth_labels = labels * (1.0 - LABEL_SMOOTHING) + 0.5 * LABEL_SMOOTHING
                cls_loss = cls_loss_fn(output[:, 0:1], smooth_labels)
                hb_loss = hb_loss_fn(output[:, 1:2], normalized_hbs)

            # Hb spread loss: penalize predictions clustering near zero (normalized mean)
            # Encourages the model to predict a wider range of Hb values
            hb_pred_norm = output[:, 1:2]
            spread_loss = torch.clamp(0.5 - hb_pred_norm.std(), min=0.0)

            total_loss = (0.60 * cls_loss) + (0.30 * hb_loss) + (HB_SPREAD_WEIGHT * spread_loss)
            total_loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
            optimizer.step()
            train_loss_total += float(total_loss.item()) * images.size(0)

        scheduler.step()
        val_metrics = _evaluate_model(model, val_loader, device, hb_mean=hb_mean, hb_std=hb_std)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": round(train_loss_total / max(len(train_dataset), 1), 4),
                "val_f1": val_metrics["f1"],
                "val_auc": val_metrics["auc"],
                "val_hb_mae": val_metrics["hb_mae"],
            }
        )
        print(
            f"epoch={epoch:02d} train_loss={history[-1]['train_loss']:.4f} "
            f"val_f1={val_metrics['f1']:.4f} val_auc={val_metrics['auc']:.4f} "
            f"val_hb_mae={val_metrics['hb_mae']:.4f}"
        )

        # Use composite score: AUC weighted more heavily than F1 (more stable early on)
        composite_score = val_metrics["auc"] * 0.55 + val_metrics["f1"] * 0.35 + (1.0 - min(val_metrics["hb_mae"] / 4.0, 1.0)) * 0.10
        if composite_score > best_score:
            best_score = composite_score
            best_state = deepcopy(model.state_dict())
            best_metrics = val_metrics
            best_threshold = val_metrics["decision_threshold"]
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if epochs_without_improvement >= PATIENCE:
            print(f"Early stopping after {epoch} epochs.")
            break

    if best_state is None or best_metrics is None:
        raise RuntimeError("EfficientNet training did not produce a valid checkpoint.")

    checkpoint = {
        "version": EFFICIENTNET_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state_dict": best_state,
        "decision_threshold": best_threshold,
        "hb_mean": hb_mean,
        "hb_std": hb_std,
        "hb_spread_factor": _compute_hb_spread_factor(val_records, hb_mean, hb_std),
        "val_metrics": best_metrics,
    }
    DEFAULT_EFFICIENTNET_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, DEFAULT_EFFICIENTNET_MODEL_PATH)

    report = {
        "dataset_name": str(dataset_root.name),
        "record_count": len(records),
        "subject_count": len({record.subject_id for record in records}),
        "primary_model": EFFICIENTNET_VERSION,
        "selected_mode": "efficientnet_hybrid_dual",
        "source_counts": _source_counts(records),
        "metrics": {
            "accuracy": round(best_metrics["accuracy"], 4),
            "precision": round(best_metrics["precision"], 4),
            "recall": round(best_metrics["recall"], 4),
            "f1": round(best_metrics["f1"], 4),
            "auc": round(best_metrics["auc"], 4),
            "mae_hb": round(best_metrics["hb_mae"], 4),
            "validation_size": len(val_records),
            "split_strategy": "group-shuffle-balance-select",
            "sample_count": len(records),
            "subject_count": len({record.subject_id for record in records}),
            "decision_threshold": round(best_threshold, 4),
        },
        "training": {
            "epochs_requested": EPOCHS,
            "history": history,
            "batch_size": BATCH_SIZE,
            "patience": PATIENCE,
            "device": str(device),
            "hb_target_mean": round(hb_mean, 4),
            "hb_target_std": round(hb_std, 4),
            "class_positive_weight": round(_positive_class_weight(train_records), 4),
            "sampler": "weighted-random-balanced",
        },
    }
    DEFAULT_EFFICIENTNET_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    DEFAULT_TRAINING_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\nBest validation metrics")
    for key in ("accuracy", "precision", "recall", "f1", "auc", "hb_mae", "decision_threshold"):
        print(f"{key}: {best_metrics[key]:.4f}")


def _build_records(dataset_root: Path) -> list[ImageRecord]:
    records: list[ImageRecord] = []
    for country in ("India", "Italy"):
        workbook_path = dataset_root / country / f"{country}.xlsx"
        if not workbook_path.exists():
            continue
        metadata = _parse_workbook(workbook_path)
        for subject_number, row in metadata.items():
            hb = _parse_float(row.get("Hgb"))
            if hb is None:
                continue

            subject_dir = dataset_root / country / subject_number
            if not subject_dir.exists():
                continue

            subject_id = f"{country}-{subject_number}"
            label = int(hb < ANEMIA_HB_THRESHOLD)
            original_path = _first_path(subject_dir.glob("*.jpg"))
            palpebral_path = _first_path(
                path
                for path in subject_dir.glob("*_palpebral.png")
                if "forniceal_palpebral" not in path.name.lower()
            )

            if original_path is not None:
                records.append(
                    ImageRecord(
                        subject_id=subject_id,
                        label=label,
                        hb=float(hb),
                        image_path=original_path,
                        source="roi_original",
                    )
                )
            if palpebral_path is not None:
                records.append(
                    ImageRecord(
                        subject_id=subject_id,
                        label=label,
                        hb=float(hb),
                        image_path=palpebral_path,
                        source="palpebral",
                    )
                )
    return records


def _balanced_group_split(
    records: list[ImageRecord],
    *,
    test_size: float,
    n_splits: int,
) -> tuple[list[ImageRecord], list[ImageRecord]]:
    labels = np.asarray([record.label for record in records], dtype=np.int32)
    groups = np.asarray([record.subject_id for record in records], dtype=object)
    target_ratio = float(labels.mean())
    splitter = GroupShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=SEED)

    best: tuple[np.ndarray, np.ndarray] | None = None
    best_score = float("inf")
    for train_index, val_index in splitter.split(np.zeros(len(records)), labels, groups):
        train_labels = labels[train_index]
        val_labels = labels[val_index]
        if len(np.unique(train_labels)) < 2 or len(np.unique(val_labels)) < 2:
            continue
        score = abs(float(train_labels.mean()) - target_ratio) + abs(float(val_labels.mean()) - target_ratio)
        if score < best_score:
            best_score = score
            best = (train_index, val_index)

    if best is None:
        raise RuntimeError("Unable to create a grouped train/validation split.")

    train_index, val_index = best
    return [records[i] for i in train_index], [records[i] for i in val_index]


def _evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    *,
    hb_mean: float,
    hb_std: float,
) -> dict[str, float]:
    model.eval()
    probabilities: list[float] = []
    labels: list[int] = []
    hb_predictions: list[float] = []
    hb_targets: list[float] = []

    with torch.no_grad():
        for images, batch_labels, batch_hbs in loader:
            images = images.to(device)
            output = model(images)
            probabilities.extend(torch.sigmoid(output[:, 0]).cpu().tolist())
            hb_predictions.extend(((output[:, 1].cpu() * hb_std) + hb_mean).tolist())
            labels.extend(batch_labels.squeeze(1).cpu().int().tolist())
            hb_targets.extend(batch_hbs.squeeze(1).cpu().tolist())

    threshold = _best_threshold(np.asarray(labels), np.asarray(probabilities))
    predicted_labels = [1 if probability >= threshold else 0 for probability in probabilities]
    auc = roc_auc_score(labels, probabilities) if len(set(labels)) > 1 else 0.5

    return {
        "accuracy": float(accuracy_score(labels, predicted_labels)),
        "precision": float(precision_score(labels, predicted_labels, zero_division=0)),
        "recall": float(recall_score(labels, predicted_labels, zero_division=0)),
        "f1": float(f1_score(labels, predicted_labels, zero_division=0)),
        "auc": float(auc),
        "hb_mae": float(mean_absolute_error(hb_targets, hb_predictions)),
        "decision_threshold": float(threshold),
    }


def _best_threshold(labels: np.ndarray, probabilities: np.ndarray) -> float:
    best_threshold = 0.5
    best_score = -1.0
    for threshold in np.linspace(0.25, 0.75, 51):
        predictions = (probabilities >= threshold).astype(np.int32)
        score = f1_score(labels, predictions, zero_division=0)
        if score > best_score:
            best_score = float(score)
            best_threshold = float(threshold)
    return best_threshold


def _source_counts(records: list[ImageRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.source] = counts.get(record.source, 0) + 1
    return counts


def _positive_class_weight(records: list[ImageRecord]) -> float:
    counts = Counter(record.label for record in records)
    positive = max(counts.get(1, 0), 1)
    negative = max(counts.get(0, 0), 1)
    return float(negative / positive)


def _build_weighted_sampler(records: list[ImageRecord]) -> WeightedRandomSampler:
    counts = Counter(record.label for record in records)
    total = sum(counts.values())
    weights = [
        float(total / max(counts[record.label], 1))
        for record in records
    ]
    return WeightedRandomSampler(
        torch.as_tensor(weights, dtype=torch.double),
        num_samples=len(weights),
        replacement=True,
    )


def _hb_normalization_stats(records: list[ImageRecord]) -> tuple[float, float]:
    values = np.asarray([record.hb for record in records], dtype=np.float32)
    mean = float(values.mean())
    std = float(values.std())
    return mean, max(std, 1e-3)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _compute_hb_spread_factor(records: list[ImageRecord], hb_mean: float, hb_std: float) -> float:
    """
    Estimate the spread amplification factor needed to correct regression-to-mean.
    Uses the ratio of true Hb std to the expected model output std (hb_std * 0.75 heuristic).
    """
    true_std = float(np.std([r.hb for r in records]))
    # Models typically predict ~75% of true std due to averaging
    predicted_std_estimate = max(hb_std * 0.75, 0.5)
    factor = float(np.clip(true_std / predicted_std_estimate, 1.0, 2.0))
    return round(factor, 3)


if __name__ == "__main__":
    main()
