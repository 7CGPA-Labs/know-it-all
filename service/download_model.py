#!/usr/bin/env python3
"""
Model Downloader for Qwen-2.5-0.5B-Instruct ONNX (INT4 / INT8 Quantized)
Downloads INT4 / INT8 quantized ONNX weights and tokenizer configs for ONNX Runtime GenAI.
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path

DEFAULT_REPO = "onnx-community/Qwen2.5-0.5B-Instruct"

def download_model(output_dir: Path, repo_id: str = DEFAULT_REPO, quant: str = "q4"):
    print(f"[*] Target directory: {output_dir}")
    print(f"[*] Repository ID: {repo_id}")
    print(f"[*] Quantization mode: {quant.upper()}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
        model_filename = f"onnx/model_{quant}.onnx"
        print(f"[*] Downloading quantized ONNX model snapshot ({model_filename})...")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            allow_patterns=[
                "*.json", "*.txt", model_filename
            ]
        )
        
        target_quant_file = output_dir / "onnx" / f"model_{quant}.onnx"
        main_model_file = output_dir / "model.onnx"
        
        if target_quant_file.exists() and not main_model_file.exists():
            print(f"[*] Linking {target_quant_file.name} -> model.onnx...")
            shutil.copy2(target_quant_file, main_model_file)
            
        genai_cfg_path = output_dir / "genai_config.json"
        print("[*] Writing genai_config.json for ONNX Runtime GenAI...")
        cfg_data = {
            "model": {
                "bos_token_id": 151643,
                "context_length": 4096,
                "decoder": {
                    "filename": "model.onnx",
                    "head_size": 128,
                    "hidden_size": 896,
                    "num_attention_heads": 14,
                    "num_key_value_heads": 2,
                    "num_hidden_layers": 24
                },
                "eos_token_id": 151645,
                "pad_token_id": 151643,
                "type": "qwen2",
                "vocab_size": 151936
            },
            "search": {
                "do_sample": False,
                "max_length": 4096,
                "min_length": 0,
                "num_beams": 1,
                "top_p": 0.9,
                "temperature": 0.7
            }
        }
        genai_cfg_path.write_text(json.dumps(cfg_data, indent=2))

        print(f"[+] Quantized ONNX Model ({quant.upper()}) and configs downloaded successfully!")
    except Exception as e:
        print(f"[!] Primary download failed: {e}")
        print("[*] Creating fallback model placeholder structure...")
        (output_dir / "genai_config.json").write_text('{"model": {"type": "qwen2"}}')
        (output_dir / "tokenizer.json").write_text('{}')
        print("[+] Placeholder structure created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Qwen 2.5 0.5B Quantized ONNX Model for onnxruntime-genai")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "models", "qwen2.5-0.5b-onnx"),
        help="Target output directory for ONNX model"
    )
    parser.add_argument(
        "--repo", "-r",
        type=str,
        default=DEFAULT_REPO,
        help="HuggingFace repo ID"
    )
    parser.add_argument(
        "--quant", "-q",
        type=str,
        default="q4",
        choices=["q4", "int8", "uint8", "fp16"],
        help="Quantization precision variant (default: q4 INT4)"
    )
    args = parser.parse_args()
    download_model(Path(args.output), args.repo, args.quant)
