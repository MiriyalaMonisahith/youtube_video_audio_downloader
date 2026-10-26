"""
Comprehensive integration test suite for Vortex Studio Pro pipeline.
Tests:
- Hardware encoder detection and optimization
- Transcript caching
- Multi-factor AI clip virality scoring and boundary snapping
- Animated word-by-word ASS subtitle generation
- Copyright and rights guardrails assessment
- Publishing package generation (A/B titles, scheduling)
- Job queue management and SSE event streaming
"""

import os
import unittest
from core.hardware import detect_hardware_encoder, get_optimal_encoder_args
from core.cache import set_cached_transcript, get_cached_transcript
from pipeline.clip_selector import select_viral_clips
from pipeline.ass_styler import generate_animated_ass, STYLES
from pipeline.rights_guard import assess_rights_and_safety
from pipeline.publisher import generate_shorts_metadata, generate_weekly_posting_schedule
from pipeline.job_manager import JobQueueManager


class TestVortexPipeline(unittest.TestCase):

    def test_hardware_detection(self):
        hw = detect_hardware_encoder()
        self.assertIn("encoder", hw)
        self.assertIn("type", hw)
        args = get_optimal_encoder_args()
        self.assertIsInstance(args, list)
        self.assertGreater(len(args), 0)

    def test_transcript_caching(self):
        test_video_id = "test_vid_123"
        mock_data = {
            "text": "This is a viral test hook for shorts.",
            "words": [
                {"word": "This", "start": 0.0, "end": 0.4},
                {"word": "is", "start": 0.4, "end": 0.6},
                {"word": "viral", "start": 0.6, "end": 1.1}
            ]
        }
        set_cached_transcript(test_video_id, mock_data)
        retrieved = get_cached_transcript(test_video_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["text"], mock_data["text"])
        self.assertEqual(len(retrieved["words"]), 3)

    def test_clip_selector_scoring(self):
        mock_segments = [
            {"start": 0.0, "end": 15.0, "text": "Why does nobody talk about this unbelievable secret?"},
            {"start": 15.0, "end": 32.0, "text": "It completely changed how I think about everything in my entire life."},
            {"start": 32.0, "end": 45.0, "text": "And the crazy part is you can do it right now for free."}
        ]
        mock_words = []
        curr_t = 0.0
        for seg in mock_segments:
            for w in seg["text"].split():
                mock_words.append({"word": w, "start": curr_t, "end": curr_t + 0.4})
                curr_t += 0.45

        candidates = select_viral_clips(mock_segments, mock_words, target_duration_range=(20.0, 50.0), top_n=3)
        self.assertIsInstance(candidates, list)
        self.assertGreater(len(candidates), 0)
        top = candidates[0]
        self.assertIn("virality_score", top)
        self.assertGreater(top["virality_score"], 0)
        self.assertIn("scores", top)
        self.assertIn("hook", top)
        self.assertIn("reason", top)

    def test_ass_styler_generation(self):
        mock_words = [
            {"word": "Never", "start": 10.0, "end": 10.4},
            {"word": "give", "start": 10.4, "end": 10.8},
            {"word": "up", "start": 10.8, "end": 11.2},
            {"word": "on", "start": 11.2, "end": 11.5},
            {"word": "your", "start": 11.5, "end": 11.8},
            {"word": "dreams.", "start": 11.8, "end": 12.3}
        ]
        out_ass = "cache/test_subtitles.ass"
        res_path = generate_animated_ass(
            words=mock_words,
            output_path=out_ass,
            clip_start=10.0,
            clip_end=15.0,
            style_name="mrbeast"
        )
        self.assertTrue(os.path.exists(res_path))
        with open(res_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResY: 1920", content)
        self.assertIn(",2,40,40,190,1", content.replace(" ", ""))
        self.assertIn("Dialogue:", content)
        # Clean up
        if os.path.exists(out_ass):
            os.remove(out_ass)

    def test_rights_guard(self):
        meta_cc = {
            "title": "Educational Physics Breakdown",
            "uploader": "ScienceForAll",
            "license": "Creative Commons Attribution",
            "description": "Released under CC-BY license."
        }
        res_cc = assess_rights_and_safety(meta_cc, user_rights_declaration="creative_commons")
        self.assertTrue(res_cc["is_creative_commons"])
        self.assertEqual(res_cc["risk_level"], "LOW")
        self.assertIn("attribution_text", res_cc)

        meta_warn = {
            "title": "Drake - God's Plan (Official Music Video)",
            "uploader": "DrakeVEVO",
            "license": "Standard YouTube License",
            "description": "Music video by Drake performing God's Plan."
        }
        res_warn = assess_rights_and_safety(meta_warn, user_rights_declaration="fair_use")
        self.assertFalse(res_warn["is_creative_commons"])
        self.assertEqual(res_warn["risk_level"], "HIGH")

    def test_publisher_metadata_and_scheduling(self):
        pub = generate_shorts_metadata(
            clip_text="This 1 secret will double your productivity every day.",
            original_title="How to Master Focus and Work Faster",
            attribution_line="Original: https://youtube.com/watch?v=123",
            duration_sec=42.0
        )
        self.assertEqual(len(pub["titles_ab"]), 3)
        self.assertIn("#Shorts", pub["description"])

        mock_clips = [
            {"id": "clip_1", "title": "Secret 1", "virality_score": 95, "hook": "Look closely"},
            {"id": "clip_2", "title": "Secret 2", "virality_score": 91, "hook": "Don't do this"}
        ]
        sched = generate_weekly_posting_schedule(mock_clips)
        self.assertEqual(len(sched), 2)
        self.assertIn("scheduled_datetime", sched[0])

    def test_job_queue_sse(self):
        mgr = JobQueueManager(max_workers=2)
        job = mgr.create_job("job_unit_test")
        job.update("analyzing", 25, "Running analysis...", {"download_ms": 150})
        self.assertEqual(job.status, "analyzing")
        self.assertEqual(job.progress, 25)
        self.assertEqual(job.timings["download_ms"], 150)
        job.complete({"video_url": "/shorts/test.mp4"}, total_ms=500)
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.progress, 100)


if __name__ == "__main__":
    unittest.main()
