# RunPod Ollama Deployment

## Kaynak Dokümanlar
- https://docs.runpod.io/tutorials/pods/run-ollama
- https://docs.runpod.io/serverless/quickstart
- https://medium.com/@pooya.haratian/running-ollama-with-runpod-serverless-and-langchain-6657763f400d

---

## Yaklaşım 1: Pod (Basit, Pahalı)

Sürekli çalışır, saatlik ücret öder. Test için uygun.

### Pod Oluşturma
- Image: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`
- HTTP Port: `11434`
- Env var: `OLLAMA_HOST=0.0.0.0`
- Cloud: SECURE (COMMUNITY'de Docker Hub timeout riski var)

### Kurulum (Pod terminali)
```bash
apt update && apt install -y lshw zstd
(curl -fsSL https://ollama.com/install.sh | sh && ollama serve > ollama.log 2>&1) &
ollama run qwen2.5:7b
```

### Test
```bash
curl https://<POD_ID>-11434.proxy.runpod.net/api/tags
```

---

## Yaklaşım 2: Serverless (Önerilen, Ucuz)

İstek gelince açılır, bitmince kapanır. Active workers = 0 → sıfır maliyet beklemede.

### Dosya Yapısı
```
runpod-ollama/
├── Dockerfile
├── start.sh
├── handler.py
└── test_input.json
```

### Dockerfile
```dockerfile
FROM ollama/ollama:latest

RUN apt-get update && apt-get install -y python3.11 python3-pip
RUN pip install runpod

COPY start.sh /start.sh
COPY handler.py /handler.py
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
CMD ["qwen2.5:7b"]
```

### start.sh
```bash
#!/bin/bash
ollama serve &

# Ollama hazır olana kadar bekle
until ollama list 2>/dev/null; do sleep 1; done

# Modeli çek
ollama pull $1

# RunPod handler'ı başlat
python3 /handler.py
```

### handler.py
```python
import runpod
import httpx

def handler(job):
    input = job["input"]
    method = input.get("method", "generate")
    payload = input.get("input", {})
    payload["stream"] = False  # Serverless'ta streaming yok

    response = httpx.post(f"http://localhost:11434/api/{method}", json=payload)
    return response.json()

runpod.serverless.start({"handler": handler})
```

### test_input.json
```json
{
  "input": {
    "method": "generate",
    "input": {
      "model": "qwen2.5:7b",
      "prompt": "Merhaba, nasılsın?"
    }
  }
}
```

### Deploy
```bash
docker build --platform linux/amd64 -t <USERNAME>/voiceflow-ollama:latest .
docker push <USERNAME>/voiceflow-ollama:latest
```

RunPod Console → Serverless → New Endpoint:
- Image: `<USERNAME>/voiceflow-ollama:latest`
- Container disk: 10 GB
- Docker CMD: `qwen2.5:7b`
- Active workers: `0`

---

## Kritik Notlar

- **COMMUNITY cloud**: Docker Hub'a erişim timeout riski var → SECURE kullan
- **Streaming**: Serverless modda desteklenmez, `"stream": false` zorunlu
- **Model boyutu**: qwen2.5:7b ~4.5 GB → container disk en az 10 GB olmalı
- **Cold start**: İlk istek model download + load süresi kadar bekler
- **OLLAMA_HOST=0.0.0.0**: Pod oluşturulurken env var olarak set edilmeli, sonradan eklemek yetmez
