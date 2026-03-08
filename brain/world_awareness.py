class WorldAwareness:

    def score_relevance(self, news_item, user_context):

        score = 0

        if user_context.get("location") in news_item:
            score += 0.4

        if user_context.get("interests"):
            for interest in user_context["interests"]:
                if interest in news_item:
                    score += 0.3

        return min(score, 1.0)
