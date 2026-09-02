"""Mikrofon giriş cihazı seçimi.

Regresyon: /api/devices cihazları listeliyordu ama hiçbir yerden seçilemiyordu —
AudioCapture her zaman sistem varsayılanını kullanıyordu. Varsayılan susturulmuş
bir Bluetooth kulaklık olduğunda (Jabra Evolve2) dikte sessizce boş dönüyordu.
"""

from unittest.mock import MagicMock, patch

import pytest

from voiceflow.audio.capture import AudioCapture, AudioConfig

FAKE_DEVICES = [
    {"name": "Jabra Evolve2 55", "max_input_channels": 1, "default_samplerate": 16000.0},
    {"name": "MacBook Pro Speakers", "max_input_channels": 0, "default_samplerate": 48000.0},
    {"name": "Jabra Evolve2 55", "max_input_channels": 1, "default_samplerate": 16000.0},
    {"name": "MacBook Pro Microphone", "max_input_channels": 1, "default_samplerate": 48000.0},
]


@pytest.fixture
def capture():
    with patch("voiceflow.audio.capture.sd") as sd:
        sd.query_devices.side_effect = lambda i=None: (
            FAKE_DEVICES if i is None else FAKE_DEVICES[i]
        )
        sd.default.device = [0, 1]
        cap = AudioCapture()
        cap._sd = sd  # testin erişebilmesi için
        yield cap


class TestResolveDevice:
    def test_exact_name_wins(self, capture):
        assert capture.resolve_device("MacBook Pro Microphone") == 3

    def test_first_match_when_name_is_duplicated(self, capture):
        # Aynı cihaz birden fazla index'te görünebiliyor (Jabra 0 ve 2)
        assert capture.resolve_device("Jabra Evolve2 55") == 0

    def test_partial_match_is_accepted(self, capture):
        assert capture.resolve_device("macbook pro mic") == 3

    def test_output_only_devices_are_never_matched(self, capture):
        # "MacBook Pro Speakers" giriş değil — eşleşmemeli
        assert capture.resolve_device("MacBook Pro Speakers") is None

    def test_unknown_name_falls_back_to_system_default(self, capture):
        assert capture.resolve_device("Bilinmeyen Kulaklık") is None

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_means_system_default(self, capture, value):
        assert capture.resolve_device(value) is None


class TestSetDevice:
    def test_set_device_updates_config(self, capture):
        capture.set_device(3)
        assert capture.config.device == 3

    def test_set_same_device_is_a_noop(self, capture):
        capture.set_device(3)
        capture.force_reset = MagicMock()
        capture.set_device(3)
        capture.force_reset.assert_not_called()

    def test_changing_device_while_recording_resets_stream(self, capture):
        from voiceflow.audio.capture import RecordingState

        capture._state = RecordingState.RECORDING
        capture.set_device(3)
        # force_reset çağrıldıysa state IDLE'a döner ve stream kapanır
        assert capture._state == RecordingState.IDLE
        assert capture.config.device == 3

    def test_none_returns_to_system_default(self, capture):
        capture.set_device(3)
        capture.set_device(None)
        assert capture.config.device is None


class TestDeviceListing:
    def test_only_input_devices_are_listed(self, capture):
        names = [d["name"] for d in capture.get_devices()]
        assert "MacBook Pro Speakers" not in names
        assert len(names) == 3

    def test_default_and_selected_flags(self, capture):
        capture.set_device(3)
        devices = {d["id"]: d for d in capture.get_devices()}
        assert devices[0]["is_default"] is True
        assert devices[3]["is_default"] is False
        assert devices[3]["is_selected"] is True
        assert devices[0]["is_selected"] is False


class TestStreamUsesSelectedDevice:
    def test_start_passes_device_to_input_stream(self, capture):
        capture.set_device(3)
        capture.start()
        kwargs = capture._sd.InputStream.call_args.kwargs
        assert kwargs["device"] == 3

    def test_start_passes_none_for_system_default(self, capture):
        capture.start()
        assert capture._sd.InputStream.call_args.kwargs["device"] is None


class TestServicePassthrough:
    def test_set_input_device_resolves_name(self):
        from voiceflow.recording.service import RecordingService

        transcriber = MagicMock()
        transcriber.config = MagicMock()
        svc = RecordingService(transcriber=transcriber, corrector=MagicMock())
        svc._audio = MagicMock()
        svc._audio.resolve_device.return_value = 3
        svc._audio.current_device_name.return_value = "MacBook Pro Microphone (#3)"

        name = svc.set_input_device("MacBook Pro Microphone")

        svc._audio.resolve_device.assert_called_once_with("MacBook Pro Microphone")
        svc._audio.set_device.assert_called_once_with(3)
        assert name == "MacBook Pro Microphone (#3)"
