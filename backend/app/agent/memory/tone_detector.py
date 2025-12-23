"""
Tone detection utilities for automatic user preference detection.

Analyzes user message patterns to infer preferred communication tone
and suggest tone settings for the agent.
"""
import re
from typing import Dict, List


class ToneDetector:
    """
    Detects user communication tone from message patterns.

    This helps auto-configure agent responses to match the user's
    preferred communication style without explicit configuration.
    """

    # Patterns indicating concise/brief preference
    CONCISE_INDICATORS = [
        r"^(yes|no|ok|done|thanks|ty|thx|k|np)$",  # Very short responses
        r"^.{1,15}$",  # Messages under 15 chars
        r"(just|quick|brief|short)",  # Explicit brevity requests
    ]

    # Patterns indicating casual tone
    CASUAL_INDICATORS = [
        r"(lol|haha|omg|btw|idk|tbh|ngl)",  # Internet slang
        r"[:;]-?[)D(P]",  # Emoticons
        r"(gonna|wanna|gotta|kinda)",  # Informal contractions
        r"(yeah|yep|nah|nope)",  # Casual affirmatives/negatives
    ]

    # Patterns indicating professional/formal tone
    PROFESSIONAL_INDICATORS = [
        r"(please|kindly|could you|would you|thank you)",
        r"(sir|madam|mr\.|ms\.|dr\.)",
        r"(regarding|concerning|per|pursuant to)",
    ]

    # Patterns indicating direct/to-the-point preference
    DIRECT_INDICATORS = [
        r"(just tell me|get to the point|bottom line)",
        r"^(what|when|where|why|how)\s",  # Direct questions
        r"(summarize|tldr|in short)",
    ]

    @classmethod
    def analyze_message(cls, message: str) -> Dict[str, float]:
        """
        Analyze a single message for tone indicators.

        Args:
            message: User message text

        Returns:
            Dictionary with tone scores (0.0-1.0):
            - concise: Preference for brief responses
            - casual: Informal communication style
            - professional: Formal communication style
            - direct: To-the-point preference
        """
        message_lower = message.lower()
        scores = {
            "concise": 0.0,
            "casual": 0.0,
            "professional": 0.0,
            "direct": 0.0,
        }

        # Check concise indicators
        for pattern in cls.CONCISE_INDICATORS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["concise"] += 0.3

        # Check casual indicators
        for pattern in cls.CASUAL_INDICATORS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["casual"] += 0.3

        # Check professional indicators
        for pattern in cls.PROFESSIONAL_INDICATORS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["professional"] += 0.3

        # Check direct indicators
        for pattern in cls.DIRECT_INDICATORS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                scores["direct"] += 0.3

        # Normalize scores to 0-1 range
        for key in scores:
            scores[key] = min(scores[key], 1.0)

        return scores

    @classmethod
    def analyze_conversation(cls, messages: List[str]) -> Dict[str, float]:
        """
        Analyze multiple messages to detect overall tone preference.

        Args:
            messages: List of user message texts

        Returns:
            Aggregated tone scores (0.0-1.0) averaged across messages
        """
        if not messages:
            return {
                "concise": 0.0,
                "casual": 0.0,
                "professional": 0.0,
                "direct": 0.0,
            }

        # Analyze each message
        all_scores = [cls.analyze_message(msg) for msg in messages]

        # Average scores across messages
        avg_scores = {
            "concise": sum(s["concise"] for s in all_scores) / len(all_scores),
            "casual": sum(s["casual"] for s in all_scores) / len(all_scores),
            "professional": sum(s["professional"] for s in all_scores) / len(all_scores),
            "direct": sum(s["direct"] for s in all_scores) / len(all_scores),
        }

        return avg_scores

    @classmethod
    def suggest_tone(cls, scores: Dict[str, float], threshold: float = 0.4) -> str:
        """
        Suggest preferred tone based on analysis scores.

        Args:
            scores: Tone scores from analyze_message or analyze_conversation
            threshold: Minimum score to trigger suggestion (0.0-1.0)

        Returns:
            Suggested tone: "casual", "professional", "direct", "concise", or "friendly" (default)
        """
        # Sort by score descending
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Get highest scoring tone
        top_tone, top_score = sorted_scores[0]

        if top_score >= threshold:
            # Map internal tone names to user-facing preferences
            tone_mapping = {
                "casual": "casual",
                "professional": "professional",
                "direct": "direct",
                "concise": "direct",  # Concise maps to direct tone
            }
            return tone_mapping.get(top_tone, "friendly")

        # Default to friendly if no strong preference detected
        return "friendly"
