# RAG Knowledge Base Structure

This directory contains all documents and indexes used by the Retrieval-Augmented Generation (RAG) system in the Marketplace Seller Intelligence Copilot.

The structure is designed to mirror real-world ingestion pipelines used at large-scale marketplaces (Amazon, Flipkart, Myntra, Meesho), where documents evolve and must be versioned, cleaned, and re-indexed over time.

```
data/rag/
├── raw_docs/
├── md/
└── index/
```

---

## 1. `raw_docs/` – Raw Marketplace Documents (Optional in This Version)

This folder is reserved for original, unprocessed files such as:

- PDFs from Amazon Seller University  
- Flipkart Seller Handbook pages  
- Myntra/FK/Meesho policy HTML dumps  
- Large policy booklets (100–400 pages)  
- Archived versions of guidelines  

These files are **not used directly** by the retrieval system.

They are kept for:
- auditability  
- reproducibility  
- re-indexing when policies change  
- future automation (web scraping, PDF extraction, etc.)  

*In the current version of the project, we manually curated markdown policies, so this folder may be empty — but it stays to support future ingestion.*

---

## 2. `md/` – Clean, Structured Markdown Corpus (Source of Truth)

This folder contains **normalized, chunk-friendly markdown files** for all marketplace policies:

```
md/amazon/policies/.md
md/flipkart/policies/.md
md/meesho/policies/.md
md/myntra/policies/.md
```

These are the **actual documents** used by RAG.

They have been cleaned, structured, and standardized so the system can:
- chunk them effectively  
- embed them consistently  
- retrieve relevant rules reliably  

This ensures correctness for:
- listing optimization  
- SEO rewriting  
- compliance checking  
- weekly action plans  

---

## 3. `index/` – Vector Store (Generated Automatically)

This folder stores the **FAISS/Chroma vector index** generated from the markdown files.

It may contain:
- `.faiss` files  
- `.npy` embedding arrays  
- `chroma.sqlite3`  
- metadata JSON mapping chunks to docs  

This directory is populated by running:

```
backend/app/rag/index_builder.py
```