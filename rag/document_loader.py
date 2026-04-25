from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
import os

DATA_DIR = Path(__file__).parent.parent / "data"

def load_documents():
    documents = []
    files = ["resume.txt", "projects.md", "skills.md"]
    optional = ["crawled_site.md"]
    for filename in optional:
        fp = DATA_DIR / filename
        if fp.exists():
            files.append(filename)

    for filename in files:
        filepath = DATA_DIR / filename
        loader = TextLoader(str(filepath), encoding="utf-8")
        docs = loader.load()

        # Tag each doc with its source
        for doc in docs:
            doc.metadata["source"] = filename

        documents.extend(docs)
        print(f"✅ Loaded {filename} — {len(docs)} document(s)")

    return documents


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )

    chunks = splitter.split_documents(documents)
    print(f"✅ Created {len(chunks)} chunks from {len(documents)} documents")
    return chunks