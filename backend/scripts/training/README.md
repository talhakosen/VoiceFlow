# VoiceFlow Fine-Tuning Pipeline

Fine-tune Qwen2.5-7B on Turkish ASR correction pairs using MLX LoRA.

## 1. Generate Training Data

```bash
cd backend/scripts

# Step 1 — Synthetic corruptions (3K pairs, ~5s)
python data_gen/corruption_pipeline.py \
    --generate-synthetic \
    --output data_gen/corruption_pairs.jsonl \
    --target 3000

# Step 2 — Claude API pairs (1K pairs, ~$10)
ANTHROPIC_API_KEY=sk-... python data_gen/claude_generator.py \
    --output data_gen/claude_pairs.jsonl \
    --target 1000

# Step 3 — Real Whisper errors via macOS TTS (500 pairs, ~30 min)
python data_gen/whisper_loop.py \
    --output data_gen/whisper_pairs.jsonl \
    --target 500

# Step 4 — Merge & split
python training/prepare_dataset.py \
    --sources data_gen/corruption_pairs.jsonl \
               data_gen/claude_pairs.jsonl \
               data_gen/whisper_pairs.jsonl \
    --output-dir training/
```

## 2. Run MLX LoRA Fine-Tuning

```bash
mlx_lm.lora \
    --model mlx-community/Qwen2.5-7B-Instruct-4bit \
    --data training/ \
    --train \
    --batch-size 4 \
    --num-layers 8 \
    --iters 1000 \
    --learning-rate 1e-5 \
    --lora-rank 8 \
    --adapter-path training/adapters \
    --val-batches 25 \
    --steps-per-report 10 \
    --steps-per-eval 100 \
    --save-every 200
```

Expected: ~20 min on M2 Pro, ~12 min on M3 Max.

## 3. Evaluate

```bash
# Run inference on test set first (produces predictions.jsonl)
mlx_lm.generate \
    --model mlx-community/Qwen2.5-7B-Instruct-4bit \
    --adapter-path training/adapters \
    --prompt "$(cat training/test.jsonl | head -1 | python3 -c 'import sys,json; print(json.loads(sys.stdin.read())["prompt"])')"

# Or evaluate with combined file (input/output/prediction)
python training/evaluate.py \
    --combined training/eval_results.jsonl \
    --output training/report.json
```

## 4. Activate Adapter in VoiceFlow

In `.env` or `voiceflow.sh`:

```bash
LLM_ADAPTER_PATH=/path/to/backend/scripts/training/adapters
```

In `RecordingService` / `LLMCorrector` config:

```python
config = CorrectorConfig(
    adapter_path="/path/to/training/adapters",
    enabled=True,
)
```

When `adapter_path` is set, `LLMCorrector` uses a shorter system prompt
(adapter already encodes correction behaviour) — ~2x faster inference.

## 5. Fuse + Export (Production)

```bash
# Fuse adapter into model weights (MLX)
mlx_lm.fuse \
    --model mlx-community/Qwen2.5-7B-Instruct-4bit \
    --adapter-path training/adapters \
    --save-path training/fused_model

# Export to GGUF for Ollama (server/NVIDIA)
mlx_lm.convert \
    --hf-path training/fused_model \
    --mlx-path training/fused_model_gguf \
    --quantize \
    --q-bits 4
```

## Dependencies

```
mlx-lm>=0.21.0   # already in pyproject.toml
jiwer            # evaluation WER
anthropic        # claude_generator.py
soundfile        # whisper_loop.py WAV handling
```

Install extras:
```bash
pip install jiwer anthropic soundfile
```
