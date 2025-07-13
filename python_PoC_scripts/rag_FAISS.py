#!/usr/bin/env python3
import os
from langchain_nomic import NomicEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter

# Define the path for your persistent FAISS index
FAISS_INDEX_PATH = "faiss_index"

# Define the path to your data
# For this example, create a file named 'data.txt' in the 'phase2/data' directory
# with the content you want to index.
DATA_PATH = "./data/data.txt"

# 1. Create embeddings
# This needs to be available both for creating and loading the index
embeddings = NomicEmbeddings(model="nomic-embed-text-v1.5")

if os.path.exists(FAISS_INDEX_PATH):
    # If an index already exists, load it
    print("Loading existing FAISS index...")
    db = FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True,  # This is required for loading local FAISS indexes
    )
    print("Index loaded.")
else:
    # If no index exists, create one
    print("No FAISS index found. Creating a new one...")

    # Create a dummy data file if it doesn't exist
    if not os.path.exists(DATA_PATH):
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w") as f:
            f.write("The quick brown fox jumps over the lazy dog.\n")
            f.write("The five boxing wizards jump quickly.\n")
            f.write("How vexingly quick daft zebras jump!\n")
            f.write("Sphinx of black quartz, judge my vow.\n")

    # Load your documents from the data directory
    loader = TextLoader(DATA_PATH)
    documents = loader.load()

    # Split the documents into chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    # Create the FAISS vector store from the documents
    db = FAISS.from_documents(texts, embeddings)

    # Save the FAISS index to disk
    db.save_local(FAISS_INDEX_PATH)
    print(f"New index created and saved to {FAISS_INDEX_PATH}")

# Now you can connect and query the database
print("\nPerforming a similarity search...")
query = "What did the fox jump over?"
docs = db.similarity_search(query)

# Print the results
print("Query: ", query)
print("Results: ", docs)
