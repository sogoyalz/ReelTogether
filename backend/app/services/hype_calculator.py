import math
from datetime import datetime


class HypeCalculator:
    @staticmethod
    def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value))

    @staticmethod
    def calculate_buzz_score(analytics_data: dict) -> float:
        youtube_buzz = math.log1p(
            analytics_data.get("youtube_views", 0)
            + analytics_data.get("youtube_comments", 0) * 15
        ) / 18
        search_buzz = analytics_data.get("google_trends_score", 0) / 100
        social_buzz = math.log1p(
            analytics_data.get("twitter_mentions", 0)
            + analytics_data.get("reddit_mentions", 0)
        ) / 14
        momentum = analytics_data.get("momentum_score", 0)

        weighted = (
            HypeCalculator._clamp(youtube_buzz) * 0.35
            + HypeCalculator._clamp(search_buzz) * 0.25
            + HypeCalculator._clamp(social_buzz) * 0.3
            + HypeCalculator._clamp(momentum) * 0.1
        )
        return round(weighted * 100, 2)

    @staticmethod
    def calculate_hype_score(analytics_data: dict, release_date: datetime) -> float:
        youtube_interest = math.log1p(
            analytics_data.get("youtube_views", 0)
            + analytics_data.get("youtube_likes", 0) * 8
            + analytics_data.get("youtube_comments", 0) * 12
        ) / 18
        search_interest = analytics_data.get("google_trends_score", 0) / 100
        social_buzz = math.log1p(
            analytics_data.get("twitter_mentions", 0)
            + analytics_data.get("reddit_mentions", 0)
        ) / 14

        raw_sentiment = analytics_data.get("sentiment_score", 0)
        sentiment = (raw_sentiment + 1) / 2

        momentum = analytics_data.get("momentum_score", 0.5)
        days_until_release = (release_date - datetime.now()).days
        release_proximity = max(0, 1 - abs(days_until_release) / 365)

        weighted = (
            HypeCalculator._clamp(youtube_interest) * 0.25
            + HypeCalculator._clamp(search_interest) * 0.2
            + HypeCalculator._clamp(social_buzz) * 0.2
            + HypeCalculator._clamp(sentiment) * 0.15
            + HypeCalculator._clamp(momentum) * 0.1
            + HypeCalculator._clamp(release_proximity) * 0.1
        )
        return round(weighted * 100, 2)
