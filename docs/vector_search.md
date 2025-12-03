# Vector search in the allowances parser

The service already ships with an end-to-end semantic search pipeline that
turns questionnaire text into embeddings and matches it against stored
allowances.

## Data flow
1. **User input** – `/allowances/vector-search` accepts `InputFormDTO` with the
   concatenated answers (for example, `"25 лет, сын участника военных действий, медицинский работник, житель Дальнего Востока, есть ипотека"`).
2. **Query normalization** – `QueryEmbeddingBuilder` prefixes the text with
   `query:` and collapses whitespace so the embedding model receives a clean
   string. 【F:src/services/embedding_builder.py†L36-L46】
3. **Vectorization** – `E5Vectorizer` loads the Hugging Face model
   (configurable via `EMBEDDING_MODEL`) and produces a normalized embedding.
   Dimension mismatches are now detected up front to avoid silent pgvector
   errors. 【F:src/services/vectorizer.py†L34-L189】【F:src/services/vectorizer.py†L243-L322】
4. **Storage & indexing** – every `Allowance` is rendered into a single passage
   (`name`, `level`, `legal_basis`, `eligibility`, `validity`) and indexed in
   the `allowance_embeddings` table. 【F:src/services/embedding_builder.py†L14-L33】【F:src/services/allowance_embedding_service.py†L18-L55】
5. **Similarity search** – the `pgvector` `cosine_distance` function orders
   allowances by proximity to the query vector, returning the top results (limit
   configurable with `VECTOR_SEARCH_LIMIT`). 【F:src/repositories/allowance_embedding_repository.py†L35-L71】

## API surface
- `POST /allowances/vector-search` – run semantic search over allowances using
  questionnaire text. 【F:src/routes/allowances.py†L38-L78】
- `POST /embeddings/input` – return the raw embedding for a questionnaire
  payload (useful for debugging). 【F:src/routes/embeddings.py†L13-L33】
- `POST /embeddings/allowances` – (re)build embeddings for specific allowance
  IDs. 【F:src/routes/embeddings.py†L35-L52】
- `POST /embeddings/allowances/missing` – index any allowances that do not yet
  have vectors. 【F:src/routes/embeddings.py†L54-L63】

## Choosing a model
- Default model is set via `EMBEDDING_MODEL` (defaults to
  `intfloat/multilingual-e5-base`). Set `EMBEDDING_DIM` to the model’s embedding
  size (for example, `1024` for `intfloat/multilingual-e5-large-instruct`).
- If the configured dimension does not match the loaded model, startup now fails
  early with a clear message so you can update the `allowance_embeddings`
  column/migration before serving traffic. 【F:src/services/vectorizer.py†L296-L322】

## Operational tips
- Ensure PostgreSQL has the `vector` extension installed (migration
  `2025-03-07_0002_add_pgvector_embeddings.py`).
- Keep `HF_TOKEN` configured if you switch to gated/private models.
- The vectorizer performs network, disk-space, and cache preflight checks to
  avoid long hangs during model download. 【F:src/services/vectorizer.py†L68-L229】
