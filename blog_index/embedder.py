import httpx
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHUNK_SIZE = 500  # words
CHUNK_OVERLAP = 50  # words


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + chunk_size]))
        i += chunk_size - overlap
    return chunks


class Embedder:
    def __init__(self, api_key: str, ssl_ca_bundle: str | None = None) -> None:
        http_client = httpx.Client(verify=ssl_ca_bundle) if ssl_ca_bundle else None
        self._client = OpenAI(api_key=api_key, http_client=http_client)

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding

    def embed_post(self, post: dict) -> list[tuple[int, str, list[float]]]:
        """Return list of (chunk_index, content, vector) for a post."""
        chunks = chunk_text(post["body"])
        return [(i, chunk, self.embed(chunk)) for i, chunk in enumerate(chunks)]
