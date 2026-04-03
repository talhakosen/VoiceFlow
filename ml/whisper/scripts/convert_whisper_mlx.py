"""
Convert HuggingFace fine-tuned Whisper model → MLX format.

Usage:
    python convert_whisper_mlx.py \
        --input  ml/whisper/models/voiceflow-whisper-tr \
        --output ml/whisper/models/voiceflow-whisper-tr-mlx \
        --dtype  float16

Output dir contains weights.safetensors + config.json compatible with mlx_whisper.load_model().
Original model is NOT modified.
"""

import argparse
import json
from pathlib import Path

import mlx.core as mx
import numpy as np


# ── HuggingFace → MLX key mapping ────────────────────────────────────────────

def remap_keys(hf_weights: dict, n_encoder_layers: int, n_decoder_layers: int) -> dict:
    mlx = {}

    def add(mlx_key, tensor):
        mlx[mlx_key] = tensor

    for k, v in hf_weights.items():
        # Strip leading "model." prefix
        k = k.removeprefix("model.")

        # ── Encoder ────────────────────────────────────────────────────────
        if k == "encoder.embed_positions.weight":
            # HF shape: (1500, d) — already positional embedding, not used directly
            # MLX AudioEncoder uses a computed sinusoid, not a learned embedding
            # Skip (mlx_whisper recomputes it via sinusoids())
            continue

        elif k == "encoder.conv1.weight":
            # PyTorch Conv1d: (out, in, kernel) → MLX Conv1d: (out, kernel, in)
            add("encoder.conv1.weight", v.transpose(0, 2, 1))
        elif k == "encoder.conv1.bias":
            add("encoder.conv1.bias", v)

        elif k == "encoder.conv2.weight":
            add("encoder.conv2.weight", v.transpose(0, 2, 1))
        elif k == "encoder.conv2.bias":
            add("encoder.conv2.bias", v)

        elif k == "encoder.layer_norm.weight":
            add("encoder.ln_post.weight", v)
        elif k == "encoder.layer_norm.bias":
            add("encoder.ln_post.bias", v)

        elif k.startswith("encoder.layers."):
            rest = k[len("encoder.layers."):]
            idx, rest = rest.split(".", 1)
            base = f"encoder.blocks.{idx}"

            rest = (rest
                .replace("self_attn.q_proj",          "attn.query")
                .replace("self_attn.k_proj",           "attn.key")
                .replace("self_attn.v_proj",           "attn.value")
                .replace("self_attn.out_proj",         "attn.out")
                .replace("self_attn_layer_norm",       "attn_ln")
                .replace("fc1",                        "mlp1")
                .replace("fc2",                        "mlp2")
                .replace("final_layer_norm",           "mlp_ln"))
            add(f"{base}.{rest}", v)

        # ── Decoder ────────────────────────────────────────────────────────
        elif k == "decoder.embed_tokens.weight":
            add("decoder.token_embedding.weight", v)

        elif k == "decoder.embed_positions.weight":
            # shape: (n_text_ctx, d_model) — learned positional embedding
            add("decoder.positional_embedding", v)

        elif k == "decoder.layer_norm.weight":
            add("decoder.ln.weight", v)
        elif k == "decoder.layer_norm.bias":
            add("decoder.ln.bias", v)

        elif k.startswith("decoder.layers."):
            rest = k[len("decoder.layers."):]
            idx, rest = rest.split(".", 1)
            base = f"decoder.blocks.{idx}"

            rest = (rest
                .replace("self_attn.q_proj",           "attn.query")
                .replace("self_attn.k_proj",            "attn.key")
                .replace("self_attn.v_proj",            "attn.value")
                .replace("self_attn.out_proj",          "attn.out")
                .replace("self_attn_layer_norm",        "attn_ln")
                .replace("encoder_attn.q_proj",         "cross_attn.query")
                .replace("encoder_attn.k_proj",         "cross_attn.key")
                .replace("encoder_attn.v_proj",         "cross_attn.value")
                .replace("encoder_attn.out_proj",       "cross_attn.out")
                .replace("encoder_attn_layer_norm",     "cross_attn_ln")
                .replace("fc1",                         "mlp1")
                .replace("fc2",                         "mlp2")
                .replace("final_layer_norm",            "mlp_ln"))
            add(f"{base}.{rest}", v)

        elif k == "proj_out.weight":
            # Tied to token_embedding — skip (mlx_whisper uses as_linear on embedding)
            continue

        else:
            print(f"  [SKIP] {k}")

    return mlx


# ── Config conversion ─────────────────────────────────────────────────────────

def make_mlx_config(hf_config: dict) -> dict:
    return {
        "n_mels":       hf_config["num_mel_bins"],
        "n_audio_ctx":  hf_config["max_source_positions"],
        "n_audio_state": hf_config["d_model"],
        "n_audio_head": hf_config["encoder_attention_heads"],
        "n_audio_layer": hf_config["encoder_layers"],
        "n_vocab":      hf_config["vocab_size"],
        "n_text_ctx":   hf_config["max_target_positions"],
        "n_text_state": hf_config["d_model"],
        "n_text_head":  hf_config["decoder_attention_heads"],
        "n_text_layer": hf_config["decoder_layers"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  required=True, help="Path to HF model dir")
    parser.add_argument("--output", required=True, help="Output MLX model dir")
    parser.add_argument("--dtype",  default="float16", choices=["float16", "float32"])
    args = parser.parse_args()

    src = Path(args.input)
    dst = Path(args.output)
    dst.mkdir(parents=True, exist_ok=True)

    dtype = mx.float16 if args.dtype == "float16" else mx.float32
    np_dtype = np.float16 if args.dtype == "float16" else np.float32

    # Load HF config
    print(f"Loading config from {src}/config.json ...")
    with open(src / "config.json") as f:
        hf_config = json.load(f)

    mlx_config = make_mlx_config(hf_config)
    print(f"MLX config: {mlx_config}")

    # Save MLX config
    with open(dst / "config.json", "w") as f:
        json.dump(mlx_config, f, indent=2)
    print(f"Saved {dst}/config.json")

    # Load HF weights
    print(f"Loading weights from {src}/model.safetensors ...")
    hf_weights_mx = mx.load(str(src / "model.safetensors"))
    # Convert to numpy for remapping
    hf_weights = {k: np.array(v) for k, v in hf_weights_mx.items()}
    print(f"  {len(hf_weights)} tensors loaded")

    # Remap keys
    print("Remapping keys HF → MLX ...")
    mlx_weights = remap_keys(
        hf_weights,
        n_encoder_layers=mlx_config["n_audio_layer"],
        n_decoder_layers=mlx_config["n_text_layer"],
    )
    print(f"  {len(mlx_weights)} tensors after remap")

    # Convert dtype + wrap as mx arrays
    print(f"Converting to {args.dtype} ...")
    mlx_weights_final = {
        k: mx.array(v.astype(np_dtype)) for k, v in mlx_weights.items()
    }

    # Save
    out_path = dst / "weights.safetensors"
    print(f"Saving {out_path} ...")
    mx.save_safetensors(str(out_path), mlx_weights_final)

    size_mb = out_path.stat().st_size / 1e6
    print(f"\nDone! {out_path} ({size_mb:.0f} MB)")
    print(f"Load with: mlx_whisper.load_model('{dst}')")

    # Quick sanity check: load the converted model
    print("\nSanity check — loading converted model ...")
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parents[3] / "backend" / "src"))
        from mlx_whisper import load_models
        model = load_models.load_model(str(dst), dtype=dtype)
        print(f"  Model loaded OK: {type(model)}")
    except Exception as e:
        print(f"  Load check failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
