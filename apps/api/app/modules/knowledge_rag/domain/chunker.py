import hashlib
from typing import Any, Dict, List


class RecursiveCharacterChunker:
    """
    Deterministic Recursive Character Text Chunker.
    Preserves structural sentence & paragraph boundaries with metadata provenance tracking.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        raw_text = (text or "").strip()
        if not raw_text:
            return []

        chunks_text = self._split_text(raw_text, self.separators)
        
        results = []
        for idx, chunk_str in enumerate(chunks_text):
            cleaned = chunk_str.strip()
            if not cleaned:
                continue

            # Estimate token count (~1.3 tokens per whitespace word)
            word_count = len(cleaned.split())
            estimated_tokens = max(1, int(word_count * 1.3))

            content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

            results.append({
                "chunk_index": idx,
                "content": cleaned,
                "token_count": estimated_tokens,
                "content_hash": content_hash
            })

        return results

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks = []
        
        separator = separators[-1]
        new_separators = []
        for i, s in enumerate(separators):
            if s == "":
                separator = s
                break
            if s in text:
                separator = s
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits = []
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_splits = self._split_text(s, new_separators)
                    good_splits.extend(other_splits)
                else:
                    good_splits.append(s)

        # Merge splits with overlap
        current_chunk = []
        current_len = 0

        for split in good_splits:
            split_len = len(split)
            if current_len + split_len > self.chunk_size and current_chunk:
                joined = separator.join(current_chunk)
                final_chunks.append(joined)

                # Maintain overlap
                while current_len > self.chunk_overlap and current_chunk:
                    popped = current_chunk.pop(0)
                    current_len -= (len(popped) + len(separator))

            current_chunk.append(split)
            current_len += split_len + len(separator)

        if current_chunk:
            final_chunks.append(separator.join(current_chunk))

        return [c.strip() for c in final_chunks if c.strip()]
