# VoiceFlow — RunPod Configs

Pod oluşturmak ve setup yapmak için tek yer.

## Kullanım

```bash
cd runpod/

# Pod oluştur
python create_pod.py issai    # ISSAI Whisper training (H100)
python create_pod.py qwen     # Qwen LoRA training (RTX 4090)
python create_pod.py ollama   # Ollama inference (RTX 4090)

# Çalışan pod'ları listele
python create_pod.py --list
```

## Workflow: ISSAI Training

```bash
# 1. Pod oluştur
python create_pod.py issai

# 2. Script + setup yükle (pod IP ve PORT RunPod UI'dan)
scp -P <PORT> ../ml/whisper/whisper_issai_finetune.py root@<IP>:/workspace/
scp -P <PORT> setup/issai.sh root@<IP>:/workspace/

# 3. SSH + kurulum + training başlat
ssh -p <PORT> root@<IP>
export HF_TOKEN=hf_xxx
bash /workspace/issai.sh

# 4. Log takip
tail -f /workspace/training.log

# 5. Bittikten sonra model indir
scp -rP <PORT> root@<IP>:/workspace/voiceflow-whisper-tr ../ml/whisper/
```

## Workflow: Qwen Training

```bash
# 1. Pod oluştur
python create_pod.py qwen

# 2. Dataset + script yükle
scp -P <PORT> ../ml/qwen/datasets/train.jsonl root@<IP>:/workspace/
scp -P <PORT> ../ml/qwen/datasets/valid.jsonl root@<IP>:/workspace/
scp -P <PORT> ../ml/qwen/scripts/train_runpod.py root@<IP>:/workspace/
scp -P <PORT> setup/qwen.sh root@<IP>:/workspace/

# 3. SSH + çalıştır
ssh -p <PORT> root@<IP>
bash /workspace/qwen.sh

# 4. Adapter indir + dönüştür
scp -rP <PORT> root@<IP>:/workspace/adapters ../ml/qwen/adapters_runpod
cd ../ml/qwen/scripts && python convert_adapter.py
```

## Workflow: Ollama Inference

```bash
# 1. Pod oluştur
python create_pod.py ollama

# 2. SSH + setup
scp -P <PORT> setup/ollama.sh root@<IP>:/workspace/
ssh -p <PORT> root@<IP> 'bash /workspace/ollama.sh'

# 3. .env güncelle
# RUNPOD_OLLAMA_URL=https://<POD_ID>-11434.proxy.runpod.net
```

## Pod Configs

| Config | GPU | Disk | Volume | Süre |
|---|---|---|---|---|
| `issai_h100.json` | H100 80GB | 150GB | 20GB | ~4-5 saat |
| `qwen_4090.json` | RTX 4090 | 120GB | 20GB | ~7 saat |
| `ollama_inference.json` | RTX 4090 | 30GB | — | stateless |

## Notlar

- SECURE cloud zorunlu — COMMUNITY'de Docker Hub/HF download timeout riski
- Pod **silinse de** volume (20GB, /workspace) korunur
- SSH public key: `~/.ssh/id_ed25519.pub` içeriği → `SSH_PUBLIC_KEY` env var
- `HF_TOKEN` olmadan HF download çok yavaş (rate limit)
