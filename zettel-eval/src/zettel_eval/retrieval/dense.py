from __future__ import annotations
import os
import json
import hashlib
import urllib.request
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

_CORPUS_CACHE = {}
_QUERY_CACHE = {}

def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))

def _get_cache_dir() -> Path:
    d = Path("/home/kevin/Workspace/skills/zettel-eval/output/.cache")
    d.mkdir(parents=True, exist_ok=True)
    return d

def _get_openai_embeddings(client, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    batch_size = 500
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-3-small"
        )
        embeddings.extend([data.embedding for data in response.data])
    return embeddings

def _get_nomic_embeddings(texts: list[str]) -> list[list[float]]:
    # Use ollama
    if not texts:
        return []
    embeddings = []
    for text in texts:
        req = urllib.request.Request(
            "http://localhost:11434/api/embeddings",
            data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            embeddings.append(res["embedding"])
    return embeddings

class DenseRetriever:
    def __init__(self, notes: dict[str, str], dimensions: int = 1536, model: str = "openai") -> None:
        self.dimensions = dimensions
        self.model = model
        
        if model == "openai":
            if not OpenAI:
                raise RuntimeError("openai package is required. Run 'pip install openai'.")
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
            self.client = OpenAI(api_key=api_key)
        
        corpus_key = hashlib.md5((model + "".join(sorted(notes.keys()))).encode()).hexdigest()
        cache_file = _get_cache_dir() / f"corpus_{corpus_key}.json"
        
        if corpus_key in _CORPUS_CACHE:
            self.note_vectors = _CORPUS_CACHE[corpus_key]
        elif cache_file.exists():
            with cache_file.open("r") as f:
                self.note_vectors = json.load(f)
            _CORPUS_CACHE[corpus_key] = self.note_vectors
        else:
            print(f"Embedding {len(notes)} notes using {model}...")
            note_ids = list(notes.keys())
            texts = [str(notes[nid]).replace("\n", " ")[:8000] for nid in note_ids]
            
            if model == "openai":
                embeddings = _get_openai_embeddings(self.client, texts)
            elif model == "nomic":
                embeddings = _get_nomic_embeddings(texts)
            else:
                raise ValueError(f"Unknown model {model}")
                
            self.note_vectors = {note_ids[i]: embeddings[i] for i in range(len(note_ids))}
            
            with cache_file.open("w") as f:
                json.dump(self.note_vectors, f)
            _CORPUS_CACHE[corpus_key] = self.note_vectors

    def search(self, query: str, exclude_ids: set[str] | None = None, limit: int = 10) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        
        query_text = str(query).replace("\n", " ")[:8000]
        query_hash = hashlib.md5((self.model + query_text).encode()).hexdigest()
        cache_file = _get_cache_dir() / f"query_{query_hash}.json"
        
        if query_hash in _QUERY_CACHE:
            query_vector = _QUERY_CACHE[query_hash]
        elif cache_file.exists():
            with cache_file.open("r") as f:
                query_vector = json.load(f)
            _QUERY_CACHE[query_hash] = query_vector
        else:
            if self.model == "openai":
                query_vector = _get_openai_embeddings(self.client, [query_text])[0]
            elif self.model == "nomic":
                query_vector = _get_nomic_embeddings([query_text])[0]
                
            with cache_file.open("w") as f:
                json.dump(query_vector, f)
            _QUERY_CACHE[query_hash] = query_vector
        
        scores = [
            (note_id, _cosine(query_vector, vector))
            for note_id, vector in self.note_vectors.items()
            if note_id not in exclude_ids
        ]
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:limit]
