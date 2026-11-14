import array
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import wave


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Capture integration tests need FFmpeg and ffprobe")
class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.script = Path(__file__).resolve().parents[1] / "scripts" / "capture.sh"

    def record(self, requested, available=1):
        fixture = self.directory / "input.wav"
        with wave.open(str(fixture), "wb") as audio:
            audio.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            samples = array.array("h", [int(6000 * math.sin(2 * math.pi * 220 * i / 44100))
                                         for i in range(int(available * 44100))
                                         for _ in range(2)])
            audio.writeframes(samples.tobytes())
        env = dict(os.environ, RADIO_STREAM_URL=str(fixture))
        return subprocess.run(["sh", str(self.script), str(requested)],
                              cwd=self.directory, env=env, capture_output=True,
                              text=True, timeout=15)

    def test_complete_recording_is_analyzed(self):
        result = self.record(1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.directory / "artifacts" / "broadcast.wav").is_file())
        self.assertTrue((self.directory / "artifacts" / "analysis.log").is_file())
        self.assertIn("Recording:", result.stdout)
        with wave.open(str(self.directory / "artifacts" / "broadcast.wav")) as audio:
            self.assertEqual(audio.getnframes() / audio.getframerate(), 1)

    def test_fractional_duration_is_supported(self):
        result = self.record(.5)
        self.assertEqual(result.returncode, 0, result.stderr)
        with wave.open(str(self.directory / "artifacts" / "broadcast.wav")) as audio:
            self.assertEqual(audio.getnframes() / audio.getframerate(), .5)

    def test_early_end_is_not_reported_as_a_complete_capture(self):
        result = self.record(2, available=.25)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Capture incomplete", result.stderr)
        self.assertNotIn("Recording:", result.stdout)
        self.assertFalse((self.directory / "artifacts" / "analysis.log").exists())

    def test_failed_capture_does_not_leave_previous_analysis(self):
        output = self.directory / "artifacts"
        output.mkdir()
        (output / "analysis.log").write_text("previous successful run")
        result = self.record(2, available=.25)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((output / "analysis.log").exists())

    def test_invalid_duration_is_rejected_before_recording(self):
        for value in ["0", "-1", "not-a-duration"]:
            with self.subTest(value=value):
                result = self.record(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("positive number of seconds", result.stderr)
                self.assertFalse((self.directory / "artifacts" / "broadcast.wav").exists())
