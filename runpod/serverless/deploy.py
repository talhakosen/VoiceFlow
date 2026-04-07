#!/usr/bin/env python3
"""Deploy VoiceFlow serverless endpoint to RunPod.

Usage:
  python deploy.py build    # Build & push Docker image
  python deploy.py create   # Create serverless endpoint
  python deploy.py test     # Test with sample audio
  python deploy.py status   # Check endpoint status
Prerequisites:
  pip install runpod
  export RUNPOD_API_TOKEN=rpa_xxx
  docker login  (for pushing image)
"""

import base64
import json
import os
import subprocess
import sys
import time

DOCKER_IMAGE = "tkosen/voiceflow-serverless:latest"
ENDPOINT_NAME = "voiceflow-inference"


def build():
    """Build and push Docker image."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Building Docker image: {DOCKER_IMAGE}")
    subprocess.run(
        ["docker", "build", "--platform", "linux/amd64", "-t", DOCKER_IMAGE, "."],
        cwd=script_dir,
        check=True,
    )

    print(f"Pushing to Docker Hub: {DOCKER_IMAGE}")
    subprocess.run(["docker", "push", DOCKER_IMAGE], check=True)
    print("Done!")


def create():
    """Create RunPod serverless endpoint."""
    import runpod

    runpod.api_key = os.environ["RUNPOD_API_TOKEN"]

    print(f"Creating serverless endpoint: {ENDPOINT_NAME}")
    print(f"  Image: {DOCKER_IMAGE}")
    print(f"  GPU: NVIDIA RTX 4090 (24GB)")

    endpoint = runpod.create_endpoint(
        name=ENDPOINT_NAME,
        template_id=None,
        docker_image=DOCKER_IMAGE,
        gpu_ids="NVIDIA GeForce RTX 4090",
        workers_min=0,
        workers_max=1,
        idle_timeout=5,         # Scale to 0 after 5s idle
        flash_boot=True,
        volume_in_gb=0,
        container_disk_in_gb=50,  # faster-whisper ~3GB + Ollama ~5GB + CUDA + system
        env={
            "OLLAMA_MODEL": "qwen2.5:7b",
            "WHISPER_MODEL": "Systran/faster-whisper-large-v3",
        },
    )

    endpoint_id = endpoint.get("id", str(endpoint))
    print(f"\nEndpoint created: {endpoint_id}")
    print(f"\nAdd to .env:")
    print(f"  RUNPOD_ENDPOINT_ID={endpoint_id}")
    print(f"\nAdd to config.yaml:")
    print(f"  whisper:")
    print(f"    backend: runpod")
    return endpoint_id


def test():
    """Test endpoint with a sample WAV file."""
    import runpod

    runpod.api_key = os.environ["RUNPOD_API_TOKEN"]
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")

    if not endpoint_id:
        print("RUNPOD_ENDPOINT_ID not set. Run 'deploy.py create' first.")
        sys.exit(1)

    # Generate a short silence WAV for testing
    import struct
    import wave
    import io

    buf = io.BytesIO()
    sr = 16000
    duration = 2  # seconds
    samples = [0] * (sr * duration)
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

    audio_b64 = base64.b64encode(buf.getvalue()).decode()

    print(f"Testing endpoint {endpoint_id}...")
    print(f"  Audio: {duration}s silence (test)")

    endpoint = runpod.Endpoint(endpoint_id)

    t_start = time.time()
    run = endpoint.run_sync({
        "audio_base64": audio_b64,
        "mode": "general",
        "correction_enabled": True,
    }, timeout=120)

    elapsed = time.time() - t_start
    print(f"\nResponse ({elapsed:.1f}s):")
    print(json.dumps(run, indent=2, ensure_ascii=False))


def status():
    """Check endpoint status."""
    import runpod

    runpod.api_key = os.environ["RUNPOD_API_TOKEN"]
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID")

    if not endpoint_id:
        # List all endpoints
        endpoints = runpod.get_endpoints()
        if not endpoints:
            print("No endpoints found.")
            return
        for ep in endpoints:
            print(f"  {ep.get('id', '?')}  {ep.get('name', '?')}  workers: {ep.get('workersMin', '?')}-{ep.get('workersMax', '?')}")
        return

    endpoint = runpod.Endpoint(endpoint_id)
    health = endpoint.health()
    print(f"Endpoint {endpoint_id}:")
    print(json.dumps(health, indent=2))


def main():
    cmds = {"build": build, "create": create, "test": test, "status": status}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        print(f"Commands: {', '.join(cmds.keys())}")
        return
    cmds[sys.argv[1]]()


if __name__ == "__main__":
    main()
