# Sample test data

This is a small Markdown document used by end-to-end tests to populate the vector database.

It serves as lightweight content so retrieval returns at least one chunk, allowing the CLI
to generate a non-empty answer during containerized E2E runs. In local workflows, the
project also includes `example_data/test.pdf`; this Markdown file mirrors the intent of
that example and avoids adding a binary PDF to the repository for tests.

The content here is intentionally brief but sufficient for retrieval:

- Topic: Example project overview
- Summary: Demonstrates ingestion → indexing → retrieval → answer

