#!/usr/bin/env python3
"""
RunPod pod oluşturucu — config dosyasından pod yarat.

Kullanım:
  python create_pod.py issai        # issai_h100.json
  python create_pod.py qwen         # qwen_4090.json
  python create_pod.py ollama       # ollama_inference.json
  python create_pod.py --list       # mevcut pod'ları listele

Gereklilik:
  pip install runpod
  export RUNPOD_API_TOKEN=rpa_xxx
  export HF_TOKEN=hf_xxx           (ISSAI için)
  export SSH_PUBLIC_KEY="ssh-ed25519 AAAA..."
"""

import json
import os
import sys
from pathlib import Path

try:
    import runpod
except ImportError:
    print("Eksik: pip install runpod")
    sys.exit(1)

PODS_DIR   = Path(__file__).parent / "pods"
SETUP_DIR  = Path(__file__).parent / "setup"

SHORTNAME_MAP = {
    "issai":  "issai_h100.json",
    "qwen":   "qwen_4090.json",
    "ollama": "ollama_inference.json",
}


def list_pods():
    runpod.api_key = os.environ["RUNPOD_API_TOKEN"]
    pods = runpod.get_pods()
    if not pods:
        print("Çalışan pod yok.")
        return
    for p in pods:
        print(f"  {p['id']}  {p['desiredStatus']:8}  {p['name']}")
        print(f"     IP:{p.get('publicIp','?')}  SSH port:{p.get('portMappings',{}).get('22','?')}")


def create_pod(config_name: str):
    # Config yükle
    cfg_path = PODS_DIR / config_name
    if not cfg_path.exists():
        short = config_name.removesuffix(".json")
        mapped = SHORTNAME_MAP.get(short)
        if not mapped:
            print(f"Config bulunamadı: {cfg_path}")
            print(f"Mevcut: {[f.name for f in PODS_DIR.glob('*.json')]}")
            sys.exit(1)
        cfg_path = PODS_DIR / mapped

    with open(cfg_path) as f:
        cfg = json.load(f)

    # API key
    api_token = os.environ.get("RUNPOD_API_TOKEN")
    if not api_token:
        print("RUNPOD_API_TOKEN env var gerekli.")
        sys.exit(1)
    runpod.api_key = api_token

    # Env vars hazırla
    env = dict(cfg.get("env", {}))
    ssh_pub = os.environ.get("SSH_PUBLIC_KEY")
    if ssh_pub:
        env["PUBLIC_KEY"] = ssh_pub
    if "__FROM_ENV__" in env.get("HF_TOKEN", ""):
        env["HF_TOKEN"] = os.environ.get("HF_TOKEN", "")
    if "__YOUR_SSH_PUBLIC_KEY__" in env.get("PUBLIC_KEY", ""):
        env.pop("PUBLIC_KEY", None)
        if ssh_pub:
            env["PUBLIC_KEY"] = ssh_pub

    # Pod parametreleri
    params = {
        "name":               cfg["name"],
        "image_name":         cfg["imageName"],
        "gpu_type_id":        cfg["gpuTypeId"],
        "gpu_count":          cfg.get("gpuCount", 1),
        "cloud_type":         cfg.get("cloudType", "SECURE"),
        "container_disk_in_gb": cfg.get("containerDiskInGb", 50),
        "volume_in_gb":       cfg.get("volumeInGb", 0),
        "volume_mount_path":  cfg.get("volumeMountPath", "/workspace"),
        "ports":              cfg.get("ports", "22/tcp"),
        "env":                env,
    }

    print(f"Pod oluşturuluyor: {params['name']}")
    print(f"  GPU    : {params['gpu_type_id']}")
    print(f"  Image  : {params['image_name']}")
    print(f"  Cloud  : {params['cloud_type']}")
    print(f"  Disk   : container={params['container_disk_in_gb']}GB, volume={params['volume_in_gb']}GB")

    # Notlar
    notes = cfg.get("_notes", [])
    if notes:
        print("\nNotlar:")
        for note in notes:
            print(f"  • {note}")

    confirm = input("\nOluşturulsun mu? [y/N] ").strip().lower()
    if confirm != "y":
        print("İptal.")
        return

    pod = runpod.create_pod(**params)
    pod_id = pod.get("id") or pod.get("podId") or str(pod)
    print(f"\n✓ Pod oluşturuldu: {pod_id}")
    print(f"  SSH hazır olunca (1-2 dakika):")
    print(f"  ssh -p <PORT> root@<IP>")
    print(f"\nSonraki adım:")
    setup_script = cfg.get("_setup")
    if setup_script:
        print(f"  # Script'i yükle + çalıştır:")
        print(f"  scp -P <PORT> {setup_script} root@<IP>:/workspace/setup.sh")
        print(f"  ssh -p <PORT> root@<IP> 'export HF_TOKEN={os.environ.get('HF_TOKEN','hf_xxx')} && bash /workspace/setup.sh'")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--list":
        list_pods()
        return
    create_pod(args[0])


if __name__ == "__main__":
    main()
