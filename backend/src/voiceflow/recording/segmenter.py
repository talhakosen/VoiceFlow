"""recording/segmenter.py — shared MLX executor + audio constants.

All MLX work (Whisper + LLM) must run on this single worker: Metal GPU is not
thread-safe.
"""

from concurrent.futures import ThreadPoolExecutor

# Single-thread executor for MLX operations (Metal GPU is not thread-safe)
_mlx_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")

_SAMPLE_RATE = 16000
