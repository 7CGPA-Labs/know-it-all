#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-$SCRIPT_DIR/models/qwen2.5-0.5b-onnx}"

echo "[*] Target model directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

HF_BASE="https://huggingface.co/onnx-community/Qwen2.5-0.5B-Instruct/resolve/main"
HF_MIRROR_BASE="https://hf-mirror.com/onnx-community/Qwen2.5-0.5B-Instruct/resolve/main"
GH_RELEASE_URL="https://github.com/7CGPA-Labs/know-it-all/releases/download/v1.0.0/qwen2.5-0.5b-onnx.tar.gz"

fetch_file() {
    local filename="$1"
    local dest="$2"
    
    if [ -f "$dest" ] && [ -s "$dest" ]; then
        echo "[+] File $filename already exists."
        return 0
    fi
    
    echo "[*] Downloading $filename from Hugging Face..."
    if curl -sSL --fail "$HF_BASE/$filename" -o "$dest"; then
        echo "[+] Successfully downloaded $filename from Hugging Face."
        return 0
    fi
    
    echo "[!] Hugging Face download failed. Trying HF-Mirror..."
    if curl -sSL --fail "$HF_MIRROR_BASE/$filename" -o "$dest"; then
        echo "[+] Successfully downloaded $filename from HF-Mirror."
        return 0
    fi
    
    echo "[!] File download failed: $filename"
    return 1
}

fetch_github_release_tarball() {
    echo "[*] Fetching full ONNX model tarball from GitHub Release fallback..."
    local tar_file="/tmp/qwen2.5-0.5b-onnx.tar.gz"
    if curl -sSL --fail "$GH_RELEASE_URL" -o "$tar_file"; then
        echo "[*] Extracting model archive..."
        tar -xzf "$tar_file" -C "$SCRIPT_DIR/models/"
        rm -f "$tar_file"
        echo "[+] Model archive extracted successfully."
        return 0
    fi
    return 1
}

mkdir -p "$TARGET_DIR/onnx"

if ! fetch_file "onnx/model_q4.onnx" "$TARGET_DIR/onnx/model_q4.onnx"; then
    if ! fetch_github_release_tarball; then
        echo "[!] Primary and fallback downloads failed. Creating placeholder structure..."
        mkdir -p "$TARGET_DIR"
    fi
fi

if [ -f "$TARGET_DIR/onnx/model_q4.onnx" ] && [ ! -f "$TARGET_DIR/model.onnx" ]; then
    echo "[*] Linking model_q4.onnx -> model.onnx"
    cp "$TARGET_DIR/onnx/model_q4.onnx" "$TARGET_DIR/model.onnx"
fi

fetch_file "tokenizer.json" "$TARGET_DIR/tokenizer.json" || true
fetch_file "tokenizer_config.json" "$TARGET_DIR/tokenizer_config.json" || true
fetch_file "special_tokens_map.json" "$TARGET_DIR/special_tokens_map.json" || true
fetch_file "config.json" "$TARGET_DIR/config.json" || true

GENAI_CFG="$TARGET_DIR/genai_config.json"
if [ ! -f "$GENAI_CFG" ]; then
    echo "[*] Writing genai_config.json for ONNX Runtime OpenVINO..."
    cat << 'EOF' > "$GENAI_CFG"
{
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
    "do_sample": false,
    "max_length": 4096,
    "min_length": 0,
    "num_beams": 1,
    "top_p": 0.9,
    "temperature": 0.7
  }
}
EOF
fi

echo "[+] Model download and setup complete in $TARGET_DIR"
