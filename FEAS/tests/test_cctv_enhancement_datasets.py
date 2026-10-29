"""
Unit Tests for CCTV Enhancement Datasets, Metrics, and Models:
1. LOL-v2 Paired Frame Dataset
2. SDSD Multi-Frame Dynamic Video Dataset with Temporal Consistency
3. REDS Super-Resolution Experiment & Forensic Integrity Warning
4. CCTVEnhanceNet & CCTVTemporalVideoEnhanceNet Forward Passes
"""

from pathlib import Path
import cv2
import numpy as np
import pytest
import torch

from src.cctv.dataset_loaders import (
    LOLv2Dataset,
    SDSDVideoDataset,
    REDSSuperResDataset,
    calculate_psnr,
    calculate_ssim,
    calculate_temporal_flicker,
)
from src.models.cctv_enhancement_model import (
    CCTVEnhanceNet,
    CCTVTemporalVideoEnhanceNet,
    CCTVRealBasicVSRExperiment,
    get_cctv_enhancer,
)
from src.cctv.enhancement import enhance_frame, enhance_video_frames, EnhancementMode


def test_metrics_psnr_and_ssim():
    img1 = np.full((128, 128, 3), 120, dtype=np.uint8)
    img2 = np.full((128, 128, 3), 120, dtype=np.uint8)

    # Identical images
    psnr_identical = calculate_psnr(img1, img2)
    ssim_identical = calculate_ssim(img1, img2)
    assert psnr_identical >= 99.0
    assert abs(ssim_identical - 1.0) < 1e-3

    # Degraded image
    img_dark = np.full((128, 128, 3), 40, dtype=np.uint8)
    psnr_diff = calculate_psnr(img1, img_dark)
    ssim_diff = calculate_ssim(img1, img_dark)
    assert 0.0 < psnr_diff < psnr_identical
    assert ssim_diff < 1.0


def test_temporal_flicker_metric():
    # Stable sequence
    stable_seq = [np.full((64, 64, 3), 100, dtype=np.uint8) for _ in range(5)]
    flicker_stable = calculate_temporal_flicker(stable_seq)
    assert flicker_stable == 0.0

    # Flickering sequence
    flicker_seq = [np.full((64, 64, 3), 100 + (30 if i % 2 == 0 else -30), dtype=np.uint8) for i in range(5)]
    flicker_score = calculate_temporal_flicker(flicker_seq)
    assert flicker_score > 0.0


def test_lol_v2_dataset_loader(tmp_path):
    dataset = LOLv2Dataset(root_dir=tmp_path, split="Train", patch_size=64, samples_per_epoch=4)
    assert len(dataset) == 4

    low_tensor, norm_tensor = dataset[0]
    assert isinstance(low_tensor, torch.Tensor)
    assert isinstance(norm_tensor, torch.Tensor)
    assert low_tensor.shape == (3, 64, 64)
    assert norm_tensor.shape == (3, 64, 64)
    assert 0.0 <= low_tensor.max().item() <= 1.0
    assert 0.0 <= norm_tensor.max().item() <= 1.0


def test_sdsd_video_dataset_loader(tmp_path):
    dataset = SDSDVideoDataset(root_dir=tmp_path, window_size=3, patch_size=64, samples_per_epoch=4)
    assert len(dataset) == 4

    low_window, tgt_t, tgt_prev = dataset[0]
    # 3-frame concatenated window: 3 frames * 3 channels = 9 channels
    assert low_window.shape == (9, 64, 64)
    assert tgt_t.shape == (3, 64, 64)
    assert tgt_prev.shape == (3, 64, 64)


def test_reds_sr_dataset_and_forensic_disclaimer(tmp_path):
    dataset = REDSSuperResDataset(root_dir=tmp_path, scale=4, patch_size_hr=64, samples_per_epoch=4)
    assert len(dataset) == 4
    assert "NOT be introduced as authenticated evidence" in dataset.FORENSIC_DISCLAIMER

    lr_t, hr_t = dataset[0]
    assert lr_t.shape == (3, 16, 16)
    assert hr_t.shape == (3, 64, 64)


def test_cctv_enhancement_models_forward():
    # 1. LOL-v2 single-frame net
    frame_net = CCTVEnhanceNet(num_features=16, num_blocks=2)
    dummy_frame = torch.rand(2, 3, 64, 64)
    out_frame = frame_net(dummy_frame)
    assert out_frame.shape == (2, 3, 64, 64)
    assert 0.0 <= out_frame.min() and out_frame.max() <= 1.0

    # 2. SDSD temporal multi-frame net (3 frames = 9 channels)
    video_net = CCTVTemporalVideoEnhanceNet(window_size=3, num_features=16, num_blocks=2)
    dummy_seq = torch.rand(2, 9, 64, 64)
    out_video = video_net(dummy_seq)
    assert out_video.shape == (2, 3, 64, 64)
    assert 0.0 <= out_video.min() and out_video.max() <= 1.0

    # 3. REDS RealBasicVSR super-res net (2x upscale)
    sr_net = CCTVRealBasicVSRExperiment(scale=2, num_features=16)
    out_sr = sr_net(dummy_frame)
    assert out_sr.shape == (2, 3, 128, 128)


def test_enhancement_modes_inference():
    raw_frame = np.full((120, 160, 3), 40, dtype=np.uint8)

    # LOL-v2 mode
    enh_lol = enhance_frame(raw_frame, mode=EnhancementMode.LOL_V2)
    assert enh_lol.shape == (120, 160, 3)

    # SDSD temporal mode
    enh_sdsd = enhance_frame(raw_frame, mode=EnhancementMode.SDSD_TEMPORAL)
    assert enh_sdsd.shape == (120, 160, 3)

    # REDS super-res mode (with banner)
    enh_sr = enhance_frame(raw_frame, mode=EnhancementMode.REDS_SR)
    assert enh_sr.shape[0] >= 120  # Height increased due to disclaimer banner

    # Multi-frame sequence
    frames = [raw_frame.copy() for _ in range(4)]
    enh_seq = enhance_video_frames(frames, mode="sdsd_temporal")
    assert len(enh_seq) == 4
    for f in enh_seq:
        assert f.shape == (120, 160, 3)


def test_degradation_diagnostics():
    from src.cctv.degradation_diagnostics import diagnose_frame_degradation

    # Dark frame
    dark_frame = np.full((120, 160, 3), 20, dtype=np.uint8)
    report_dark = diagnose_frame_degradation(dark_frame)
    assert report_dark.primary_degradation == "darkness"
    assert report_dark.recommended_strategy == "lol_v2_illumination"

    # Adequate frame
    clean_frame = np.full((480, 640, 3), 140, dtype=np.uint8)
    cv2.putText(clean_frame, "SHARP TEXT FOR CCTV", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    report_clean = diagnose_frame_degradation(clean_frame)
    assert report_clean.primary_degradation in ("none", "motion_blur")


def test_adaptive_enhancer_and_automatic_fallback():
    from src.cctv.adaptive_enhancer import enhance_frame_with_audit_and_fallback

    dark_frame = np.full((100, 100, 3), 25, dtype=np.uint8)

    # Case A: Detector shows enhancement helps
    def mock_detector_gain(img):
        mean_lum = float(np.mean(img))
        if mean_lum > 30:
            return [{"confidence": 0.88, "class_name": "car"}]
        return [{"confidence": 0.35, "class_name": "car"}]

    enh_frame, audit_gain = enhance_frame_with_audit_and_fallback(
        dark_frame, frame_index=1, detector_callable=mock_detector_gain, allow_fallback=True
    )
    assert audit_gain.action_taken == "enhanced_targeted"
    assert audit_gain.benefit_verified is True

    # Case B: Detector shows enhancement hurt confidence -> automated fallback triggered!
    def mock_detector_harm(img):
        mean_lum = float(np.mean(img))
        if mean_lum > 30:
            return [{"confidence": 0.20, "class_name": "car"}]
        return [{"confidence": 0.90, "class_name": "car"}]

    final_frame, audit_fallback = enhance_frame_with_audit_and_fallback(
        dark_frame, frame_index=2, detector_callable=mock_detector_harm, allow_fallback=True
    )
    assert audit_fallback.action_taken == "fallback_to_raw"
    assert audit_fallback.benefit_verified is False
    assert np.array_equal(final_frame, dark_frame)
