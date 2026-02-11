"""
Transcript Summarizer using Claude
Generates concise, human-readable summaries of phone call transcripts
"""

import os
from typing import Optional
import anthropic


class TranscriptSummarizer:
    """Summarizes phone call transcripts using Claude"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def summarize(self, transcript: str, retailer_name: str, watch_name: str = "Tudor Ranger 36mm with beige dial") -> str:
        """
        Summarize a phone call transcript into 1-3 sentences.

        Args:
            transcript: The full call transcript
            retailer_name: Name of the retailer called
            watch_name: Name of the watch being inquired about

        Returns:
            A concise 1-3 sentence summary
        """
        if not transcript or not transcript.strip():
            return "No transcript available."

        prompt = f"""Summarize this phone call transcript in 1-3 sentences. The caller was asking {retailer_name} about the availability of a {watch_name}.

Focus on:
- Whether the watch is in stock or not
- Any waitlist, special order, or callback options mentioned
- Any other relevant details (e.g., if they reached an automated system, if the store was busy, etc.)

Keep the summary concise and factual. Write from a third-person perspective (e.g., "The store confirmed..." not "I confirmed...").

Transcript:
{transcript}

Summary:"""

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            summary = message.content[0].text.strip()
            return summary

        except Exception as e:
            print(f"Error summarizing transcript: {e}")
            return f"Call completed but summary generation failed."


# Convenience function
def summarize_transcript(transcript: str, retailer_name: str, watch_name: str = None) -> str:
    """Quick function to summarize a transcript"""
    try:
        # Debug: check if env var is set
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        print(f"  ANTHROPIC_API_KEY present: {bool(api_key)}")
        if api_key:
            print(f"  Key starts with: {api_key[:10]}...")

        summarizer = TranscriptSummarizer()
        # Use provided watch_name or default
        if watch_name:
            return summarizer.summarize(transcript, retailer_name, watch_name)
        return summarizer.summarize(transcript, retailer_name)
    except ValueError as e:
        # No API key configured
        print(f"  ValueError: {e}")
        return "Summary not available (API key not configured)."
    except Exception as e:
        print(f"  Exception: {e}")
        return f"Summary generation failed: {str(e)}"


if __name__ == "__main__":
    # Test with a sample transcript
    test_transcript = """
    assistant: Hi, I'm calling to check if you have a specific Tudor watch in stock.
    user: Thank you for calling Watches of Switzerland. How can I help you?
    assistant: Hello? I'm looking for the Tudor Ranger thirty six millimeter with a beige dial, reference M seven nine nine three zero dash zero zero zero seven. Do you have that in stock?
    user: Let me check for you... Unfortunately we don't have that specific model in stock right now. We do have a waitlist if you'd like to be added.
    assistant: Yes, I'd be interested in the waitlist. How does that work?
    user: Just come into the store with your ID and we can add you to our client book. We'll call you when one comes in.
    assistant: Great, thank you for the information. Have a nice day.
    user: You too, goodbye.
    """

    print("Testing transcript summarizer...")
    summary = summarize_transcript(test_transcript, "Watches of Switzerland")
    print(f"Summary: {summary}")
