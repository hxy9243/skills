from __future__ import annotations

from collections.abc import Sequence
from tempfile import TemporaryDirectory
import sys
from types import ModuleType
from uuid import uuid4

from pydantic import BaseModel

try:
    import langchain  # noqa: F401
    from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
except ModuleNotFoundError:
    class BaseDocumentCompressor(BaseModel):
        """Compatibility shim for ragatouille on modern langchain."""

        model_config = {"arbitrary_types_allowed": True}

    retrievers_module = ModuleType("langchain.retrievers")
    compressors_module = ModuleType("langchain.retrievers.document_compressors")
    base_module = ModuleType("langchain.retrievers.document_compressors.base")
    base_module.BaseDocumentCompressor = BaseDocumentCompressor
    sys.modules.setdefault("langchain.retrievers", retrievers_module)
    sys.modules.setdefault("langchain.retrievers.document_compressors", compressors_module)
    sys.modules["langchain.retrievers.document_compressors.base"] = base_module

from ragatouille import RAGPretrainedModel


class ColBERTRetriever:
    """Real ColBERT retriever backed by ragatouille."""

    def __init__(self, notes: dict[str, str]) -> None:
        self._notes = notes
        self._ids = list(notes.keys())
        self._temp_dir = TemporaryDirectory(prefix="zettel-colbert-")
        self._index_name = f"zettel-eval-{uuid4().hex}"
        self._model = RAGPretrainedModel.from_pretrained(
            "colbert-ir/colbertv2.0",
            index_root=self._temp_dir.name,
        )
        self._model.index(
            collection=[notes[note_id] for note_id in self._ids],
            document_ids=self._ids,
            index_name=self._index_name,
            split_documents=False,
        )

    def __del__(self) -> None:
        temp_dir = getattr(self, "_temp_dir", None)
        if temp_dir is not None:
            temp_dir.cleanup()

    def search(
        self,
        query: str,
        exclude_ids: set[str] | None = None,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        exclude_ids = exclude_ids or set()
        requested = min(len(self._ids), max(limit + len(exclude_ids), limit))
        if requested <= 0:
            return []

        results = self._model.search(query=query, k=requested)
        return self._filter_results(results, exclude_ids=exclude_ids, limit=limit)

    def _filter_results(
        self,
        results: Sequence[dict],
        exclude_ids: set[str],
        limit: int,
    ) -> list[tuple[str, float]]:
        filtered: list[tuple[str, float]] = []
        for result in results:
            note_id = str(result["document_id"])
            if note_id in exclude_ids:
                continue
            filtered.append((note_id, float(result["score"])))
            if len(filtered) >= limit:
                break
        return filtered
