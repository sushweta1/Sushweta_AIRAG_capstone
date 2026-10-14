"""Build the FastAPI documentation embedding index."""

from pathlib import Path

from src.rag.naive_rag import (
    load_corpus,
    build_index,
    save_index,
)

CORPUS_DIR = Path("data/corpus")
INDEX_PATH = Path("data/embeddings.json")


def main():
    print("Loading FastAPI documentation...")
    chunks = load_corpus(CORPUS_DIR)
    print(f"Loaded {len(chunks)} chunks.")

    print("Generating embeddings...")
    index = build_index(chunks)

    print("Saving index...")
    save_index(index, INDEX_PATH)

    print(f"Index saved to {INDEX_PATH}")
    print(f"Total indexed chunks: {len(index)}")


if __name__ == "__main__":
    main()