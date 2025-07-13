#!/usr/bin/env python3
import os
import argparse
import yaml
from pypdf import PdfReader
import weaviate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm


def load_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        exit(1)


def get_weaviate_client():
    """Initializes and returns a Weaviate client."""
    try:
        client = weaviate.connect_to_local()
        print("Successfully connected to Weaviate.")
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        exit(1)


def load_pdf_documents(directory_path):
    """Loads PDF documents from a directory."""
    documents = []
    print(f"Loading PDF documents from '{directory_path}'...")
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            filepath = os.path.join(directory_path, filename)
            try:
                reader = PdfReader(filepath)
                document_text = ""
                for page in reader.pages:
                    document_text += page.extract_text() + "\n"
                documents.append({"content": document_text, "source": filename})
            except Exception as e:
                print(f"Error reading '{filepath}': {e}")
    print(f"Loaded {len(documents)} PDF documents.")
    return documents


def chunk_documents(documents):
    """Splits documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    chunked_documents = []
    for doc in documents:
        chunks = text_splitter.split_text(doc["content"])
        for i, chunk in enumerate(chunks):
            chunked_documents.append({"content": chunk, "source": f"{doc['source']}_chunk_{i+1}"})
    print(f"Split documents into {len(chunked_documents)} chunks.")
    return chunked_documents


def ingest_documents(client, documents, class_name):
    """Ingests documents into Weaviate."""
    with client.batch as batch:
        for doc in tqdm(documents, desc="Ingesting documents"):
            properties = {
                "content": doc["content"],
                "source": doc.get("source", "unknown"),
            }
            batch.add_data_object(properties, class_name)
    print("Data ingestion complete.")


def ensure_weaviate_schema(client, class_name, vectorizer, model):
    """Ensures the Weaviate schema is created."""
    class_obj = {
        "class": class_name,
        "vectorizer": vectorizer,
        "moduleConfig": {
            vectorizer: {
                "model": model,
            }
        },
    }
    if not client.schema.exists(class_name):
        client.schema.create_class(class_obj)
        print(f"'{class_name}' class created.")


def main():
    """Main function to run the RAG pipeline."""
    config = load_config()
    weaviate_config = config["weaviate"]
    data_config = config["data"]
    query_config = config["query"]

    parser = argparse.ArgumentParser(description="RAG pipeline with Weaviate.")
    parser.add_argument(
        "query", type=str, nargs="?", default=query_config["default_query"], help="The query to search for."
    )
    args = parser.parse_args()

    client = get_weaviate_client()

    ensure_weaviate_schema(
        client, weaviate_config["class_name"], weaviate_config["vectorizer"], weaviate_config["model"]
    )

    pdf_documents = load_pdf_documents(data_config["directory"])
    chunked_documents = chunk_documents(pdf_documents)
    ingest_documents(client, chunked_documents, weaviate_config["class_name"])

    # Perform a similarity search
    query = args.query
    result = (
        client.query.get(weaviate_config["class_name"], ["content"])
        .with_near_text({"concepts": [query]})
        .with_limit(2)
        .do()
    )

    # Print the results
    print("\nQuery: ", query)
    print("Results: ", result)


if __name__ == "__main__":
    main()
