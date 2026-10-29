"""
Laboratory Toolmark Reference Image Indexer
Extracts deep visual embeddings using a vision encoder and creates
an L2-normalized reference index with cryptographic hashes.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from src.common.hashing import calculate_sha256
from src.common.utils import get_optimal_device, set_random_seed


class ToolmarkVisionEncoder(nn.Module):
    """Deep feature encoder producing 512-D L2-normalized visual representations."""

    def __init__(self, pretrained: bool = True):
        super().__init__()
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        backbone = models.resnet18(weights=weights)
        # Remove final linear classifier
        self.features = nn.Sequential(*list(backbone.children())[:-1])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.features(x)
        out = torch.flatten(out, 1)
        # L2 normalize
        out = nn.functional.normalize(out, p=2, dim=1)
        return out


from src.common.utils import set_random_seed


class ToolmarkIndexBuilder:
    """Builds and manages an indexed gallery of laboratory reference toolmark images."""

    def __init__(
        self,
        pretrained: bool = True,
        seed: int = 42,
        encoder: Optional[ToolmarkVisionEncoder] = None,
        device: Optional[str] = None,
    ):
        self.device = torch.device(device) if device else get_optimal_device()
        if encoder is not None:
            self.encoder = encoder.to(self.device)
        else:
            set_random_seed(seed)
            self.encoder = ToolmarkVisionEncoder(pretrained=pretrained).to(self.device)
        self.encoder.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def extract_embedding(self, image_path: Path) -> np.ndarray:
        """Extracts 512-D normalized embedding vector from image."""
        with Image.open(image_path) as img:
            rgb = img.convert("RGB")
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)
        with torch.no_grad():
            emb = self.encoder(tensor).squeeze(0).cpu().numpy()
        return emb

    def build_index(
        self,
        reference_records: List[Dict[str, Any]],
        output_index_dir: Path,
    ) -> Dict[str, Any]:
        """
        Builds embedding index from reference lab image records.
        Each record must contain: 'ref_id', 'image_path', and optional 'metadata'.
        """
        out_dir = Path(output_index_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        embeddings_list: List[np.ndarray] = []
        gallery_metadata: List[Dict[str, Any]] = []

        for rec in reference_records:
            p = Path(rec["image_path"])
            if not p.exists():
                continue

            try:
                emb = self.extract_embedding(p)
                sha = calculate_sha256(p)

                embeddings_list.append(emb)
                gallery_metadata.append({
                    "ref_id": rec.get("ref_id", p.stem),
                    "image_path": str(p),
                    "sha256": sha,
                    "metadata": rec.get("metadata", {}),
                    "lab_dataset": rec.get("lab_dataset", "NIST_NBTRD_BENCHMARK"),
                })
            except Exception:
                continue

        if not embeddings_list:
            raise ValueError("No valid reference images could be processed.")

        embeddings_matrix = np.stack(embeddings_list, axis=0).astype(np.float32)

        # Save embeddings matrix and metadata JSON
        matrix_path = out_dir / "toolmark_embeddings.npy"
        meta_path = out_dir / "toolmark_gallery_meta.json"

        np.save(str(matrix_path), embeddings_matrix)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(gallery_metadata, f, indent=2)

        return {
            "total_indexed": len(gallery_metadata),
            "embedding_dimension": int(embeddings_matrix.shape[1]),
            "embeddings_matrix_path": str(matrix_path),
            "gallery_meta_path": str(meta_path),
        }
