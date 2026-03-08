from sentence_transformers import SentenceTransformer
import numpy as np

class SemanticMemory:

    _model = None   # Shared across all instances

    def __init__(self):
        self.vectors = []
        self.texts = []

    def _get_model(self):
        """
        Load model ONLY when first needed
        """
        if SemanticMemory._model is None:
            print("Loading SentenceTransformer model...")
            SemanticMemory._model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                cache_folder="./backend/secrets/models"
            )

        return SemanticMemory._model

    def store(self, text: str):
        model = self._get_model()
        vec = model.encode(text)

        self.vectors.append(vec)
        self.texts.append(text)

    def search(self, query: str):

        if not self.vectors:
            return None

        model = self._get_model()
        query_vec = model.encode(query)

        sims = [
            np.dot(query_vec, v) /
            (np.linalg.norm(query_vec) * np.linalg.norm(v))
            for v in self.vectors
        ]

        return self.texts[int(np.argmax(sims))]