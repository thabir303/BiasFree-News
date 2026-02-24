#!/usr/bin/env bash
# Render build script — installs CPU-only PyTorch + downloads embedding model
set -o errexit

echo "=== Installing dependencies ==="
pip install --upgrade pip

# Install CPU-only PyTorch first (saves ~1.5 GB vs full CUDA build)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining requirements
pip install -r requirements.txt

# Pre-download the sentence-transformers model so first request isn't slow
echo "=== Pre-downloading embedding model ==="
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('Model downloaded successfully')"

echo "=== Build complete ==="
