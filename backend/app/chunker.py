import re
from typing import Any, Dict, List


def chunk_text_page(
    text: str,
    target_size: int = 800,
    overlap: int = 120
) -> List[str]:
    """
    Chunks a single page's text into blocks of ~target_size chars with ~overlap chars overlap.
    Never crosses page boundaries because it strictly operates on a single page's text.
    Breaks gracefully at paragraph or sentence/space boundaries.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    if len(clean_text) <= target_size:
        return [clean_text]

    chunks = []
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = start + target_size
        if end >= text_len:
            chunks.append(clean_text[start:].strip())
            break

        # Look for a natural break point (paragraph break, period + space, or whitespace)
        candidate_window = clean_text[max(start, end - 150): min(text_len, end + 50)]
        
        # Priority 1: Paragraph break "\n\n"
        para_idx = candidate_window.rfind("\n\n")
        if para_idx != -1:
            split_point = max(start, end - 150) + para_idx + 2
        else:
            # Priority 2: Sentence boundary (". ", "? ", "! ")
            sentence_matches = list(re.finditer(r'[.?!]\s+', candidate_window))
            if sentence_matches:
                split_point = max(start, end - 150) + sentence_matches[-1].end()
            else:
                # Priority 3: Space
                space_idx = candidate_window.rfind(" ")
                if space_idx != -1:
                    split_point = max(start, end - 150) + space_idx + 1
                else:
                    split_point = end

        chunk_str = clean_text[start:split_point].strip()
        if chunk_str:
            chunks.append(chunk_str)

        # Step forward with overlap
        start = max(start + 1, split_point - overlap)

    return chunks


def create_chunks_for_document(
    doc_id: str,
    filename: str,
    pages: List[Dict[str, Any]],
    target_size: int = 800,
    overlap: int = 120
) -> List[Dict[str, Any]]:
    """
    Creates chunks for an entire document where every chunk is guaranteed
    to map to exactly one page (never crosses page boundaries).
    """
    all_chunks = []
    global_chunk_idx = 0

    for page in pages:
        page_num = int(page["page_number"])
        text = str(page["text"])
        page_chunks = chunk_text_page(text, target_size=target_size, overlap=overlap)

        for chunk_text in page_chunks:
            chunk_id = f"{doc_id}_p{page_num}_c{global_chunk_idx}"
            all_chunks.append({
                "id": chunk_id,
                "doc_id": doc_id,
                "filename": filename,
                "page_number": page_num,
                "chunk_index": global_chunk_idx,
                "content": chunk_text
            })
            global_chunk_idx += 1

    return all_chunks
