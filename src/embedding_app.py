from fastapi import FastAPI

from src.core.dependencies.vector_search import get_vectorizer
from src.utils.logger import logger

app = FastAPI(title="Embedding Loader", docs_url=None, redoc_url=None)


@app.on_event("startup")
async def warm_embedding_model() -> None:
    """
    Warm up the embedding model in a dedicated container.

    The handler loads the configured vectorizer so that the Hugging Face cache
    is populated before the application container starts, reducing cold starts
    and keeping model dependencies isolated.

    :return: None.
    """

    vectorizer = get_vectorizer()
    logger.info(f"Starting embedding preload for '{vectorizer.model_name}'")
    await vectorizer.warm_up()
    logger.info(f"Embedding preload for '{vectorizer.model_name}' completed")


@app.get("/health", operation_id="embedding_health")
async def healthcheck() -> dict[str, str]:
    """
    Report readiness of the embedding loader container.

    :return: Health payload.
    """

    return {"status": "ready"}
