"""
Forensic Evidence Analysis System (FEAS) - Audio & Voice Forensics Engine
Extracts audio tracks from video/audio evidence and performs pitch tracking, spectral flux, and synthetic voice clone detection.
"""

import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from scipy import signal
from scipy.io import wavfile

from src.config import TEMP_DIR
from src.models.audio.spectrogram import render_audio_spectrogram, render_waveform_plot


class AudioForensicAnalyzer:
    """Forensic Voice & Audio Integrity Examiner."""

    def extract_audio_from_file(self, file_path: Union[str, Path], temp_wav_path: Path) -> Tuple[bool, Optional[np.ndarray], int]:
        """
        Extract audio stream to 16kHz Mono PCM float32 array.
        Uses scipy.io.wavfile directly for WAV or ffmpeg for container files (.mp4, .mkv, .avi, .mp3).
        """
        path = Path(file_path)
        if not path.exists():
            return False, None, 0

        # Direct WAV read
        if path.suffix.lower() == ".wav":
            try:
                sr, data = wavfile.read(str(path))
                if data.ndim > 1:
                    data = np.mean(data, axis=1) # Downmix to mono
                # Convert to float32 in [-1.0, 1.0]
                if data.dtype == np.int16:
                    samples = (data / 32768.0).astype(np.float32)
                elif data.dtype == np.int32:
                    samples = (data / 2147483648.0).astype(np.float32)
                elif data.dtype == np.uint8:
                    samples = ((data - 128) / 128.0).astype(np.float32)
                else:
                    samples = data.astype(np.float32)
                return True, samples, sr
            except Exception:
                pass

        # Use ffmpeg subprocess if available
        try:
            cmd = [
                "ffmpeg", "-y", "-i", str(path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                str(temp_wav_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
            if res.returncode == 0 and temp_wav_path.exists() and temp_wav_path.stat().st_size > 100:
                sr, data = wavfile.read(str(temp_wav_path))
                samples = (data / 32768.0).astype(np.float32)
                return True, samples, sr
        except Exception:
            pass

        return False, None, 0

    def analyze_voice_signals(self, samples: np.ndarray, sr: int) -> Dict[str, Any]:
        """
        Extract forensic pitch, spectral, and synthetic vocal tract anomalies.
        """
        duration = len(samples) / float(sr)
        if duration < 0.1:
            return {
                "synthetic_voice_score": 0.0,
                "is_synthetic_voice": False,
                "snr_db": 0.0,
                "pitch_mean_hz": 0.0,
                "pitch_jitter": 0.0,
                "clipping_ratio": 0.0,
                "anomalies": ["Audio track too short for forensic evaluation"]
            }

        anomalies: List[str] = []
        synthetic_points = 0.0

        # 1. Measure Waveform Clipping & Dynamic Compression
        clipping_threshold = 0.99
        clipped_samples = np.sum(np.abs(samples) >= clipping_threshold)
        clipping_ratio = float(clipped_samples / len(samples))
        if clipping_ratio > 0.02:
            anomalies.append(f"Excessive digital clipping detected ({clipping_ratio*100:.1f}% samples)")

        # 2. Estimate Signal-to-Noise Ratio (SNR) in dB
        # Estimate noise floor from 10th percentile of local RMS energy
        frame_len = int(sr * 0.03) # 30ms
        hop_len = int(sr * 0.015)  # 15ms
        rms_frames = []
        for i in range(0, len(samples) - frame_len, hop_len):
            chunk = samples[i:i + frame_len]
            rms = np.sqrt(np.mean(chunk ** 2) + 1e-12)
            rms_frames.append(rms)

        rms_arr = np.array(rms_frames)
        if len(rms_arr) > 0:
            signal_power = np.mean(rms_arr ** 2) + 1e-12
            noise_power = np.percentile(rms_arr ** 2, 10) + 1e-12
            snr_db = float(10 * np.log10(signal_power / noise_power))
        else:
            snr_db = 20.0

        # Unnaturally high SNR (> 55dB) without ambient acoustic floor indicates direct synthetic vocoder render
        if snr_db > 50.0:
            synthetic_points += 0.35
            anomalies.append(f"Sterile acoustic floor (SNR: {snr_db:.1f} dB) — indicates direct synthetic TTS rendering")

        # 3. Fundamental Frequency (F0) / Pitch Tracking via Autocorrelation
        pitches = []
        for i in range(0, len(samples) - frame_len, hop_len):
            chunk = samples[i:i + frame_len]
            if np.sqrt(np.mean(chunk ** 2)) < 0.01:
                continue # Skip silence
            
            # Autocorrelation
            corr = signal.correlate(chunk, chunk, mode="full")
            corr = corr[len(corr) // 2:]
            
            # Look for pitch peak between 70 Hz and 400 Hz
            min_lag = int(sr / 400)
            max_lag = int(sr / 70)
            if max_lag < len(corr):
                peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
                f0 = sr / peak_lag
                pitches.append(f0)

        if len(pitches) >= 5:
            pitch_mean = float(np.mean(pitches))
            pitch_std = float(np.std(pitches))
            # Jitter: relative standard deviation of pitch
            pitch_jitter = float(pitch_std / (pitch_mean + 1e-6))

            # Synthetic voice clones often have either unnaturally low pitch jitter (<0.02, robotic monotone)
            # or erratic discontinuous jumps (>0.45)
            if pitch_jitter < 0.025:
                synthetic_points += 0.40
                anomalies.append("Unnatural pitch micro-jitter suppression (<2.5% variance) — Robotic TTS pattern")
            elif pitch_jitter > 0.50:
                synthetic_points += 0.30
                anomalies.append("Discontinuous pitch phase jumps across phoneme boundaries")
        else:
            pitch_mean = 0.0
            pitch_jitter = 0.0

        # 4. Spectral High-Frequency Rolloff Discontinuity
        # Synthetic vocoders (e.g. 16kHz/22kHz models) abruptly truncate above 7.5 kHz
        freqs, psd = signal.welch(samples, fs=sr, nperseg=min(512, len(samples)))
        high_band_mask = freqs >= (sr * 0.45) # near Nyquist
        low_band_mask = (freqs >= 300) & (freqs < 3000)
        
        if np.any(high_band_mask) and np.any(low_band_mask):
            high_energy = np.mean(psd[high_band_mask]) + 1e-12
            speech_energy = np.mean(psd[low_band_mask]) + 1e-12
            rolloff_ratio = float(high_energy / speech_energy)
            if rolloff_ratio < 1e-5:
                synthetic_points += 0.25
                anomalies.append("Abrupt spectral cutoff at upper Nyquist boundary (vocoder band-limiting)")

        synth_score = round(float(np.clip(synthetic_points, 0.01, 0.99)), 4)
        is_synthetic = bool(synth_score >= 0.50)

        return {
            "synthetic_voice_score": synth_score,
            "is_synthetic_voice": is_synthetic,
            "snr_db": round(snr_db, 2),
            "pitch_mean_hz": round(pitch_mean, 1),
            "pitch_jitter": round(pitch_jitter, 4),
            "clipping_ratio": round(clipping_ratio, 5),
            "anomalies": anomalies
        }


_audio_analyzer_instance: Optional[AudioForensicAnalyzer] = None


def get_audio_analyzer() -> AudioForensicAnalyzer:
    global _audio_analyzer_instance
    if _audio_analyzer_instance is None:
        _audio_analyzer_instance = AudioForensicAnalyzer()
    return _audio_analyzer_instance


def analyze_audio_forensics(
    file_input: Union[str, Path],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute comprehensive audio forensics on video or audio evidence.
    """
    out_dir = output_dir or (TEMP_DIR / "audio_results")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    path = Path(file_input)
    base_name = path.stem

    analyzer = get_audio_analyzer()
    temp_wav = out_dir / f"{base_name}_temp_stream.wav"

    has_audio, samples, sr = analyzer.extract_audio_from_file(path, temp_wav)

    if not has_audio or samples is None or len(samples) == 0:
        return {
            "has_audio": False,
            "duration_seconds": 0.0,
            "sample_rate_hz": 0,
            "synthetic_voice_score": 0.0,
            "is_synthetic_voice": False,
            "snr_db": 0.0,
            "pitch_mean_hz": 0.0,
            "pitch_jitter": 0.0,
            "voice_anomalies": [],
            "spectrogram_image_path": None,
            "waveform_image_path": None,
            "message": "No playable acoustic audio stream present in evidence file."
        }

    duration = round(float(len(samples) / sr), 3)

    # Render Spectrogram & Waveform
    spec_path = out_dir / f"{base_name}_spectrogram.jpg"
    wave_path = out_dir / f"{base_name}_waveform.jpg"
    
    render_audio_spectrogram(samples, sr, spec_path)
    render_waveform_plot(samples, sr, wave_path)

    # Forensic Analysis
    voice_metrics = analyzer.analyze_voice_signals(samples, sr)

    return {
        "has_audio": True,
        "duration_seconds": duration,
        "sample_rate_hz": sr,
        "synthetic_voice_score": voice_metrics["synthetic_voice_score"],
        "is_synthetic_voice": voice_metrics["is_synthetic_voice"],
        "snr_db": voice_metrics["snr_db"],
        "pitch_mean_hz": voice_metrics["pitch_mean_hz"],
        "pitch_jitter": voice_metrics["pitch_jitter"],
        "clipping_ratio": voice_metrics["clipping_ratio"],
        "voice_anomalies": voice_metrics["anomalies"],
        "spectrogram_image_path": str(spec_path),
        "waveform_image_path": str(wave_path)
    }
