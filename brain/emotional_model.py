# backend/brain/emotional_model.py
from datetime import datetime

class EmotionalModel:
    def __init__(self):
        # 0.0 to 1.0 scale
        self.mood_score = 0.5 
        self.energy_level = 0.5
        self.last_update = datetime.now()

    def update(self, user_input: str, context: dict) -> str:
        """
        Analyzes input and context to drift the AI's internal state.
        Returns a string description of the current emotion.
        """
        # 1. Detect Sentiment (Simplified Keyword Drift)
        text = user_input.lower()
        positive_words = ['thanks', 'great', 'awesome', 'good', 'love', 'help']
        negative_words = ['bad', 'wrong', 'error', 'stop', 'hate', 'slow']
        
        drift = 0.0
        if any(word in text for word in positive_words):
            drift += 0.1
        if any(word in text for word in negative_words):
            drift -= 0.15

        # 2. Apply Drift with Momentum
        self.mood_score = max(0.0, min(1.0, self.mood_score * 0.9 + (0.5 + drift) * 0.1))
        
        # 3. Time-of-day Energy Logic
        hour = datetime.now().hour
        if 6 <= hour <= 10:
            self.energy_level = 0.8  # Morning boost
        elif hour >= 22:
            self.energy_level = 0.3  # Late night low energy
        else:
            self.energy_level = 0.6

        return self.get_state()

    def get_state(self) -> str:
        """Translates scores into a descriptive tone for the Reasoner."""
        if self.mood_score > 0.75:
            return "enthusiastic and helpful"
        if self.mood_score < 0.3:
            return "empathetic and apologetic"
        
        if self.energy_level > 0.7:
            return "high-energy and efficient"
        if self.energy_level < 0.4:
            return "calm and concise"
            
        return "warm and professional"
