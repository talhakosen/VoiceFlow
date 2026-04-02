"""
HuggingFace PEFT LoRA adapter → MLX adapter formatına dönüştür

Kullanım:
  python convert_adapter.py

Giriş:  scripts/training/adapters_runpod/  (unsloth/HF PEFT format)
Çıkış:  scripts/training/adapters_mlx/     (mlx_lm format)
"""

import json
import numpy as np
from pathlib import Path
from safetensors import safe_open
from safetensors.numpy import save_file

HF_PATH  = Path("scripts/training/adapters_runpod")
MLX_PATH = Path("scripts/training/adapters_mlx")

# Qwen2.5-7B = 28 layer
NUM_LAYERS = 28
LORA_RANK  = 8
LORA_ALPHA = 16.0
SCALE      = LORA_ALPHA / LORA_RANK  # 2.0

TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

def convert():
    MLX_PATH.mkdir(parents=True, exist_ok=True)

    # 1. Adapter ağırlıklarını dönüştür
    mlx_weights = {}
    hf_path = HF_PATH / "adapter_model.safetensors"

    with safe_open(str(hf_path), framework="numpy") as f:
        keys = list(f.keys())
        print(f"HF adapter: {len(keys)} key")

        for hf_key in keys:
            tensor = f.get_tensor(hf_key)

            # base_model.model.model.layers.N.X.lora_A.weight → model.layers.N.X.lora_a
            mlx_key = hf_key
            mlx_key = mlx_key.replace("base_model.model.", "")  # → model.layers...

            if ".lora_A.weight" in mlx_key:
                mlx_key = mlx_key.replace(".lora_A.weight", ".lora_a")
                # HF: [r, in_features] → MLX: [in_features, r]
                tensor = tensor.T
            elif ".lora_B.weight" in mlx_key:
                mlx_key = mlx_key.replace(".lora_B.weight", ".lora_b")
                # HF: [out_features, r] → MLX: [r, out_features]
                tensor = tensor.T
            else:
                print(f"  Skipping unknown key: {hf_key}")
                continue

            mlx_weights[mlx_key] = tensor.astype(np.float16)

    print(f"MLX adapter: {len(mlx_weights)} key")

    # Birkaç örnek göster
    for k, v in list(mlx_weights.items())[:3]:
        print(f"  {k}: {v.shape}")

    save_file(mlx_weights, str(MLX_PATH / "adapters.safetensors"))
    print(f"Saved: {MLX_PATH / 'adapters.safetensors'}")

    # 2. MLX adapter_config.json oluştur
    mlx_config = {
        "fine_tune_type": "lora",
        "num_layers": NUM_LAYERS,
        "lora_parameters": {
            "rank": LORA_RANK,
            "alpha": LORA_ALPHA,
            "scale": SCALE,
            "dropout": 0.0,
            "keys": TARGET_MODULES,
        },
    }

    with open(MLX_PATH / "adapter_config.json", "w") as f:
        json.dump(mlx_config, f, indent=2)
    print(f"Saved: {MLX_PATH / 'adapter_config.json'}")
    print("\nDone! .env'de LLM_ADAPTER_PATH=scripts/training/adapters_mlx olarak güncelle.")

if __name__ == "__main__":
    convert()
