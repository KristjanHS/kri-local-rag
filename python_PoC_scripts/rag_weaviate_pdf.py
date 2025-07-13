#!/usr/bin/env python3
import weaviate
import argparse
import glob
import os
from typing import List
from weaviate.util import generate_uuid5  # deterministic UUIDs for upsert

# No explicit authentication needed for default local instance of Weaviate

"""
# Example usage:
# Use example string list (existing behaviour)
python rag_weaviate_pdf.py
# Ingest all PDFs from ./data/
python rag_weaviate_pdf.py --source pdf
# Ingest PDFs from a custom directory
python rag_weaviate_pdf.py --source pdf --data-dir /path/to/pdfs
"""

# Optional dependencies for PDF parsing
try:
    # Preferred: use Unstructured for higher-quality PDF parsing if available
    # basic PDF support: pip install "unstructured[pdf]"
    # or everything the project can parse: pip install "unstructured[all-docs]"
    from unstructured.partition.pdf import partition_pdf  # type: ignore
except ImportError:
    partition_pdf = None

# PDF text extraction backend: try pypdf first (modern), then PyPDF2 as legacy.
try:
    from pypdf import PdfReader  # type: ignore
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
        import warnings

        # Silence the global deprecation warning by issuing it once here.
        warnings.warn(
            "PyPDF2 is deprecated. Please install 'pypdf' instead (pip install pypdf)",
            DeprecationWarning,
            stacklevel=2,
        )
    except ImportError:
        PdfReader = None

from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


# -----------------------------------------------------------------------------
# Helper utilities
# -----------------------------------------------------------------------------


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Return the plain-text content of a single PDF file.

    Preferring the 'unstructured' library if installed, otherwise falls back
    to PyPDF2. A clear error is raised when neither backend is available.
    """
    if partition_pdf is not None:
        # Unstructured returns a list of elements with optional .text attribute
        elements = partition_pdf(filename=pdf_path)
        return "\n".join([e.text for e in elements if hasattr(e, "text") and e.text])

    if PdfReader is not None:
        reader = PdfReader(pdf_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])

    raise ImportError("Neither 'unstructured' nor 'PyPDF2' is installed to parse PDFs.")


def load_documents(source: str = "string", data_dir: str = "data/") -> List[str]:
    """Load documents from either the hard-coded examples or PDF files."""
    if source == "pdf":
        pdf_paths = glob.glob(os.path.join(data_dir, "*.pdf"))
        if not pdf_paths:
            print(f"No PDF files found in '{data_dir}'. Falling back to string list.")
            source = "string"
        else:
            # Just return the file paths; actual parsing happens later during ingestion
            return pdf_paths

    # Default: return sample strings
    return [
        "The quick brown fox jumps over the lazy dog.",
        "The five boxing wizards jump quickly.",
        "How vexingly quick daft zebras jump!",
        "Sphinx of black quartz, judge my vow.",
    ]


# --- Main execution ---
# Accept parsed CLI args so we can choose the document source.
def main(args):
    client = None  # Initialize client to None
    try:
        # Connect to your Weaviate instance
        client = weaviate.connect_to_local()
        print("Successfully connected to Weaviate.")

        # Define the collection name
        collection_name = "Document"

        # Create the collection if it doesn't exist
        if not client.collections.exists(collection_name):
            client.collections.create(name=collection_name)
            # The collection will automatically use the default vectorizer
            # (text2vec-transformers) backed by the local GPU inference service.
            print(f"Collection '{collection_name}' created.")

        # Get the collection
        docs = client.collections.get(collection_name)

        # ------------------------------------------------------------------
        # Load documents according to the chosen source
        # ------------------------------------------------------------------
        documents = load_documents(source=args.source, data_dir=args.data_dir)
        print(f"Loaded {len(documents)} document(s) from '{args.source}'.")

        # ------------------------------------------------------------------
        # Upsert each chunk with a deterministic UUID (avoids duplicates)
        # ------------------------------------------------------------------
        for item in documents:
            # When --source=pdf we receive a file path, otherwise we receive raw text
            if args.source == "pdf":
                raw_text = _extract_text_from_pdf(item)
                source_file = os.path.basename(item)
            else:
                raw_text = item
                source_file = "string_input"

            chunks = splitter.split_text(raw_text)

            for i, chunk in enumerate(chunks):
                # Build a stable identifier: file (or "string_input"), page number, and chunk hash
                obj_uuid = generate_uuid5(f"{source_file}:{i}:{chunk}")

                props = {
                    "content": chunk,
                    "page": i,
                    "source_file": source_file,
                }

                # Try to replace (update) first; if the object doesn't exist, insert it.
                try:
                    docs.data.replace(uuid=obj_uuid, properties=props)
                except Exception:
                    docs.data.insert(uuid=obj_uuid, properties=props)

        print("Data ingested.")

        # Perform a similarity search
        # query = "What did the fox jump over?"
        query = "How many boxing wizards jump quickly?"
        response = docs.query.near_text(query=query, limit=2)

        # Print the results
        print("\nQuery: ", query)
        for o in response.objects:
            print("Results: ", o.properties)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the client connection is closed
        if client:
            client.close()
            print("Client connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example Weaviate ingestion script with optional PDF loading.")
    parser.add_argument(
        "--source",
        choices=["string", "pdf"],
        default="pdf",
        help="Choose 'string' for built-in examples or 'pdf' to load all PDFs from --data-dir.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing PDF files when --source=pdf.",
    )

    cli_args = parser.parse_args()
    main(cli_args)
