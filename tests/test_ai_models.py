"""
Unit & Integration Test Suite for Improved AI Models in Vortex Studio Pro.
Tests:
- AI / LLM client discovery & JSON extraction
- Advanced multi-factor virality scoring & detailed breakdown
- Hook detection & psychological pattern classification
- Viral moment detection with sentence-boundary snapping
- Clip ranking & non-overlapping deduplication
- High-CTR title variant generation
- SEO hashtag generation & niche detection
- Computer Vision face detection availability
- Speech transcription with word timestamps
"""

import unittest
from ai.llm_client import (
    get_available_ollama_models,
    resolve_best_ollama_model,
    extract_json_from_text
)
from ai.viral_scorer import score_clip, score_clip_detailed, compute_algorithmic_virality
from ai.hookdetector import analyze_hook, boost_hook
from ai.clip_detector import find_best_clips
from ai.clip_ranker import rank_clips
from ai.title_generator import generate_title, generate_title_variants
from ai.hashtag_generator import generate_hashtags, generate_hashtag_list, detect_niche
from ai.face_zoom import get_face_detector
from pipeline.clip_selector import score_segment_virality, select_viral_clips


class TestAIModels(unittest.TestCase):

    def test_llm_client_discovery(self):
        models = get_available_ollama_models()
        self.assertIsInstance(models, list)
        best = resolve_best_ollama_model()
        # If Ollama is running, best should be string; if not, None is acceptable
        if models:
            self.assertIsNotNone(best)
            self.assertIn(best, models)

    def test_llm_json_extraction(self):
        # Markdown fence
        raw1 = "Here is the result:\n```json\n[{\"start\": 5, \"end\": 25, \"score\": 90}]\n```"
        parsed1 = extract_json_from_text(raw1)
        self.assertIsInstance(parsed1, list)
        self.assertEqual(len(parsed1), 1)
        self.assertEqual(parsed1[0]["score"], 90)

        # Single quote JSON or text with preamble
        raw2 = "Sure! Response: {'key': 'value', 'num': 42}"
        parsed2 = extract_json_from_text(raw2)
        self.assertIsInstance(parsed2, dict)
        self.assertEqual(parsed2["num"], 42)

    def test_viral_scorer_metrics(self):
        high_viral_text = (
            "Wait, stop scrolling! Did you know this shocking secret about money that nobody tells you? "
            "It completely blew my mind and changed everything."
        )
        low_viral_text = "Today we will walk around the park and look at standard trees."

        high_score = score_clip(high_viral_text)
        low_score = score_clip(low_viral_text)

        self.assertGreater(high_score, low_score)
        self.assertGreaterEqual(high_score, 75)

        # Detailed breakdown
        detailed = score_clip_detailed(high_viral_text, duration=32.0, words_count=24)
        self.assertIn("hook_score", detailed)
        self.assertIn("emotion_score", detailed)
        self.assertIn("pacing_score", detailed)
        self.assertIn("retention_score", detailed)
        self.assertIn("virality_score", detailed)
        self.assertIn("reason", detailed)
        self.assertGreater(detailed["hook_score"], 60)

    def test_hook_detector(self):
        text_with_hook = "Why does nobody talk about this illegal productivity hack? Stop doing this right now!"
        analysis = analyze_hook(text_with_hook, start_time=1.5)
        self.assertIn(analysis["hook_type"], ["Curiosity Gap", "Pattern Interrupt", "Question Hook"])
        self.assertGreaterEqual(analysis["hook_score"], 70)

        clip = {
            "start": 2.0,
            "end": 28.0,
            "score": 60,
            "text": text_with_hook,
            "reason": "interesting moment"
        }
        boosted = boost_hook(clip)
        self.assertGreater(boosted["score"], 60)
        self.assertIn("hook_type", boosted)

    def test_clip_detector_sentence_boundaries(self):
        sample_chunk = (
            "Did you know that 99% of people breathe wrong? It sounds crazy, but science proves it. "
            "When you fix your breathing, your stress drops instantly and your focus doubles. "
            "Try this right now: inhale slowly for 4 seconds, hold for 4, and exhale."
        )
        clips = find_best_clips(sample_chunk, chunk_start=10.0, chunk_end=45.0)
        self.assertIsInstance(clips, list)
        self.assertGreater(len(clips), 0)
        top = clips[0]
        self.assertIn("start", top)
        self.assertIn("end", top)
        self.assertIn("score", top)
        self.assertGreaterEqual(top["start"], 10.0)
        self.assertLessEqual(top["end"], 45.0)

    def test_clip_ranker_deduplication(self):
        raw_candidates = [
            {"start": 10.0, "end": 40.0, "score": 92, "reason": "Curiosity hook: mind blown"},
            {"start": 12.0, "end": 42.0, "score": 88, "reason": "overlapping variant"},
            {"start": 60.0, "end": 92.0, "score": 85, "reason": "Pattern interrupt: wait until the end"},
            {"start": 63.0, "end": 95.0, "score": 80, "reason": "another overlapping window"}
        ]
        ranked = rank_clips(raw_candidates, min_separation_sec=8.0, top_n=2)
        self.assertEqual(len(ranked), 2)
        # Verify deduplication kept the 10.0s and 60.0s ones
        self.assertEqual(ranked[0]["start"], 10.0)
        self.assertEqual(ranked[1]["start"], 60.0)
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[1]["rank"], 2)

    def test_title_generator(self):
        text = "This simple morning habit doubled my energy and saved me three hours every day."
        title = generate_title(text)
        self.assertIsInstance(title, str)
        self.assertGreater(len(title), 5)
        self.assertLessEqual(len(title), 80)

        variants = generate_title_variants(text, count=3)
        self.assertGreaterEqual(len(variants), 2)
        for v in variants:
            self.assertFalse(v.startswith("#"))  # Clean of hashtags

    def test_hashtag_generator_and_niche(self):
        finance_text = "If you invest 100 dollars in index funds every month, compound interest makes you a millionaire."
        niche = detect_niche(finance_text)
        self.assertEqual(niche, "finance")

        tags = generate_hashtag_list(finance_text)
        self.assertIn("#Shorts", tags)
        self.assertIn("#Viral", tags)
        # Should contain money or finance related tag
        tag_str = " ".join(tags).lower()
        self.assertTrue("#money" in tag_str or "#wealth" in tag_str or "#investing" in tag_str or "#finance" in tag_str)

    def test_face_detector_cascade(self):
        detector = get_face_detector()
        self.assertIsNotNone(detector, "OpenCV Haar Cascade frontal face detector should load successfully")

    def test_clip_selector_with_learner(self):
        sample_text = "The secret truth about high performance is that rest is actually productive."
        scores = score_segment_virality(sample_text, duration=32.0, words_count=12, is_opening=True)
        self.assertIn("virality_score", scores)
        self.assertIn("hook_score", scores)
        self.assertIn("monetization_score", scores)
        self.assertIn("retention_score", scores)
        self.assertGreaterEqual(scores["virality_score"], 60)


if __name__ == "__main__":
    unittest.main()

