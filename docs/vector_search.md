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
3. **Vectorization** – by default a deterministic **hash backend**
   (`EMBEDDING_BACKEND=hash`) generates normalized vectors fully offline, so
   local/CI runs never try to download a Hugging Face model. To use a real E5
   model, set `EMBEDDING_BACKEND=hf` and point `EMBEDDING_LOCAL_MODEL` to a
   mounted path (or rely on a pre-populated Hugging Face cache). The builder
   still follows the `query:`/`passage:` convention. Dimension mismatches are
   detected up front to avoid silent pgvector errors. 【F:src/services/vectorizer.py†L16-L120】【F:src/services/vectorizer.py†L122-L214】
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
- **Offline first:** `EMBEDDING_BACKEND=hash` (default) requires no network and
  produces deterministic vectors for development/CI.
- **Hugging Face model:** set `EMBEDDING_BACKEND=hf` plus:
  - `EMBEDDING_MODEL` (defaults to `intfloat/multilingual-e5-small`, 384 dims),
  - `EMBEDDING_LOCAL_MODEL` pointing to a mounted directory with model files,
    or pre-fill the HF cache inside the image.
  - `EMBEDDING_OFFLINE=true` keeps loading strictly local; set to `false` only
    if downloads are allowed.
- Set `EMBEDDING_DIM` to the model’s embedding size (for example, `384` for the
  default, or `1024` for `intfloat/multilingual-e5-large-instruct`). On mismatch
  the vectorizer will fail fast with guidance to update the pgvector column.

## Operational tips
- The E5 family requires `query:`/`passage:` prefixes even for non-English text;
  the builders handle this automatically so callers should only supply raw
  questionnaire strings or allowance fields.
- Use `EMBEDDING_BACKEND=hash` for guaranteed offline startup; switch to
  `hf` only when a local model directory is mounted. The loader will refuse to
  download models if `EMBEDDING_OFFLINE=true`. 【F:src/services/vectorizer.py†L90-L119】【F:src/services/vectorizer.py†L173-L214】
- Ensure PostgreSQL has the `vector` extension installed (migration
  `2025-03-07_0002_add_pgvector_embeddings.py`).
