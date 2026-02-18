"""Tests for summarizer.py — transcript summarization"""

import pytest
from unittest.mock import patch, MagicMock
from summarizer import TranscriptSummarizer, summarize_transcript


class TestTranscriptSummarizer:
    @patch("summarizer.anthropic.Anthropic")
    def test_summarize_returns_string(self, mock_anthropic_cls):
        """Summarizer should return a string from the Claude response"""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="The store did not have the watch in stock.")]
        mock_client.messages.create.return_value = mock_message

        summarizer = TranscriptSummarizer(api_key="test-key")
        result = summarizer.summarize("Some transcript", "Test Store", "Tudor Ranger 36mm")

        assert result == "The store did not have the watch in stock."
        mock_client.messages.create.assert_called_once()

    @patch("summarizer.anthropic.Anthropic")
    def test_summarize_empty_transcript(self, mock_anthropic_cls):
        summarizer = TranscriptSummarizer(api_key="test-key")
        assert summarizer.summarize("", "Store", "Watch") == "No transcript available."
        assert summarizer.summarize("   ", "Store", "Watch") == "No transcript available."

    @patch("summarizer.anthropic.Anthropic")
    def test_summarize_handles_api_error(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        summarizer = TranscriptSummarizer(api_key="test-key")
        result = summarizer.summarize("Some transcript", "Store")
        assert "failed" in result.lower()


class TestSummarizeTranscriptConvenience:
    @patch("summarizer.os.environ", {"ANTHROPIC_API_KEY": ""})
    def test_no_api_key_returns_fallback(self):
        result = summarize_transcript("transcript", "Store")
        assert "not available" in result.lower() or "failed" in result.lower()
