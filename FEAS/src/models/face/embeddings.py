"""
Forensic Evidence Analysis System (FEAS) - FaceNet 512-d Suspect Embeddings
Extracts normalized 512-dimensional facial representations and computes gallery cosine distances.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

try:
    from facenet_pytorch import InceptionResnetV1
    FACENET_AVAILABLE = True
except ImportError:
    FACENET_AVAILABLE = False

from src.config import DEVICE, EMBEDDING_DIM, SEED
from src.db.audit import get_suspect_profiles_sync


class FaceNetExtractor:
    """InceptionResnetV1 (FaceNet) 512-d feature extractor with gallery matching."""

    def __init__(self):
        self.device = DEVICE
        self.dim = EMBEDDING_DIM
        
        if FACENET_AVAILABLE:
            try:
                self.model = InceptionResnetV1(pretrained="vggface2", classify=False).to(self.device).eval()
            except Exception:
                self.model = InceptionResnetV1(pretrained=None, classify=False).to(self.device).eval()
        else:
            # Deterministic fallback backbone for 512-d embedding
            from torchvision.models import resnet18
            net = resnet18(weights=None)
            net.fc = nn.Linear(net.fc.in_features, self.dim)
            self.model = net.to(self.device).eval()

        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

    @torch.no_grad()
    def extract_embedding(self, face_input: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """
        Extract normalized 512-dimensional facial embedding vector.
        """
        if isinstance(face_input, (str, Path)):
            img = Image.open(str(face_input)).convert("RGB")
        elif isinstance(face_input, np.ndarray):
            rgb = cv2.cvtColor(face_input, cv2.COLOR_BGR2RGB) if len(face_input.shape) == 3 else face_input
            img = Image.fromarray(rgb)
        elif isinstance(face_input, Image.Image):
            img = face_input.convert("RGB")
        else:
            raise TypeError(f"Unsupported face image type: {type(face_input)}")

        tensor = self.transform(img).unsqueeze(0).to(self.device)
        emb_tensor = self.model(tensor)
        
        # L2 normalization
        norm_emb = torch.nn.functional.normalize(emb_tensor, p=2, dim=1)
        emb_np = norm_emb.squeeze(0).cpu().numpy().astype(np.float32)
        return emb_np

    def match_against_gallery(
        self,
        query_embedding: np.ndarray,
        gallery: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Compute cosine similarity and distance against suspect gallery.
        Returns top matches sorted by similarity descending.
        """
        suspects = gallery if gallery is not None else get_suspect_profiles_sync()
        if not suspects:
            return []

        results = []
        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        for s in suspects:
            s_emb = np.array(s["embedding"], dtype=np.float32)
            s_norm = s_emb / (np.linalg.norm(s_emb) + 1e-8)
            
            # Cosine similarity
            cosine_sim = float(np.dot(q_norm, s_norm))
            # Bound between -1.0 and 1.0, map to normalized score
            similarity = float(np.clip((cosine_sim + 1.0) / 2.0, 0.0, 1.0))
            distance = float(round(1.0 - similarity, 4))
            
            results.append({
                "suspect_id": s.get("suspect_id", "UNKNOWN"),
                "name": s.get("name", "Unknown Suspect"),
                "similarity": round(similarity, 4),
                "distance": distance,
                "notes": s.get("notes", ""),
                "image_path": s.get("image_path", "")
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]


# Global singleton
_facenet_extractor = None


def get_facenet_extractor() -> FaceNetExtractor:
    global _facenet_extractor
    if _facenet_extractor is None:
        _facenet_extractor = FaceNetExtractor()
    return _facenet_extractor
