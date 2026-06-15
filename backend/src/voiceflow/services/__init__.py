"""Service layer package.

`RecordingService` is re-exported lazily (PEP 562): `recording.service` imports
`services.dictionary`, so eagerly importing `RecordingService` here would create
an import-time circular dependency. Deferring it until first access breaks the
cycle while keeping `from voiceflow.services import RecordingService` working.
"""

__all__ = ["RecordingService"]


def __getattr__(name: str):
    if name == "RecordingService":
        from ..recording import RecordingService

        return RecordingService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
