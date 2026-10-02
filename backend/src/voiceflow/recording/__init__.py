"""voiceflow.recording — Recording pipeline package.

Same-level as correction/, transcription/, audio/.
"""

from .service import RecordingService
from .segmenter import _mlx_executor

__all__ = ["RecordingService", "_mlx_executor"]
