#!/usr/bin/env python3
"""
FEAS Enterprise CCTV - Model Export & ONNX INT8/FP16 Quantization Pipeline.
==========================================================================
Exports PyTorch YOLO surveillance models to high-throughput ONNX Runtime engines
and performs dynamic INT8 quantization for optimal CPU/GPU edge performance.

Usage:
  python export_cctv_onnx.py --model-weights yolov8n.pt --imgsz 640 --quantize-int8
"""

from __future__ import annotations
import argparse
from pathlib import Path
import time
import numpy as np
from ultralytics import YOLO


def export_and_quantize(
    weights_path: str = "yolov8n.pt",
    imgsz: int = 640,
    half_precision: bool = False,
    quantize_int8: bool = True
) -> Path:
    """Export model to ONNX and optionally apply INT8 dynamic quantization."""
    print(f"\n=======================================================")
    print(f"  FEAS Enterprise CCTV - ONNX Export & Optimization   ")
    print(f"=======================================================")
    print(f"  Input PyTorch Weights : {weights_path}")
    print(f"  Export Resolution     : {imgsz}x{imgsz}")
    print(f"  Half Precision (FP16) : {half_precision}")
    print(f"  INT8 Quantization     : {quantize_int8}")
    print(f"=======================================================\n")

    model = YOLO(weights_path)

    # 1. Export to ONNX via Ultralytics exporter
    print(f"[*] Step 1: Exporting PyTorch model to ONNX format...")
    exported_onnx_path = model.export(
        format="onnx",
        imgsz=imgsz,
        dynamic=True,
        simplify=True,
        half=half_precision
    )
    onnx_path = Path(exported_onnx_path)
    print(f"✓ Base ONNX model exported: {onnx_path} ({onnx_path.stat().st_size / (1024*1024):.2f} MB)")

    # 2. INT8 Dynamic Quantization
    final_model_path = onnx_path
    if quantize_int8:
        print(f"\n[*] Step 2: Applying ONNX INT8 Dynamic Quantization...")
        try:
            from onnxruntime.quantization import quantize_dynamic, QuantType

            int8_path = onnx_path.with_name(onnx_path.stem + "_int8.onnx")
            quantize_dynamic(
                model_input=str(onnx_path),
                model_output=str(int8_path),
                weight_type=QuantType.QUInt8
            )
            print(f"✓ INT8 Quantized model created: {int8_path} ({int8_path.stat().st_size / (1024*1024):.2f} MB)")
            final_model_path = int8_path
        except Exception as e:
            print(f"⚠️ INT8 quantization failed: {e}. Falling back to standard ONNX model.")

    # 3. Benchmark Inference Latency
    print(f"\n[*] Step 3: Benchmarking ONNX Runtime Inference Latency...")
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(final_model_path), providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        dummy_input = np.random.randn(1, 3, imgsz, imgsz).astype(np.float32)

        # Warmup
        for _ in range(5):
            _ = session.run(None, {input_name: dummy_input})

        # Measure 20 runs
        t0 = time.perf_counter()
        runs = 20
        for _ in range(runs):
            _ = session.run(None, {input_name: dummy_input})
        avg_ms = ((time.perf_counter() - t0) / runs) * 1000.0

        fps = 1000.0 / avg_ms
        print(f"✓ Inference Benchmark Result: {avg_ms:.2f} ms / frame (~{fps:.1f} FPS on CPU)")
    except Exception as e:
        print(f"⚠️ Benchmark failed: {e}")

    print(f"\n[OK] Enterprise CCTV ONNX Engine is ready for production deployment: {final_model_path}\n")
    return final_model_path


def main():
    parser = argparse.ArgumentParser(description="Export YOLO to ONNX with INT8 dynamic quantization")
    parser.add_argument("--model-weights", type=str, default="yolov8n.pt", help="Path to .pt weights file")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution")
    parser.add_argument("--fp16", action="store_true", help="Export with half precision (FP16)")
    parser.add_argument("--quantize-int8", action="store_true", default=True, help="Apply INT8 dynamic quantization")
    args = parser.parse_args()

    export_and_quantize(
        weights_path=args.model_weights,
        imgsz=args.imgsz,
        half_precision=args.fp16,
        quantize_int8=args.quantize_int8
    )


if __name__ == "__main__":
    main()

