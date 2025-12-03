import uvicorn
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse

from src.routes.allowances import router as allowances_router
from src.routes.embeddings import router as embeddings_router
from src.core.migrations import run_migrations

app = FastAPI(title="Allowances Parser Service", swagger_ui_parameters={"operationsSorter": "method"})
app.include_router(router=allowances_router)
app.include_router(router=embeddings_router)


@app.get("/health", operation_id="healthcheck")
async def healthcheck() -> dict[str, str]:
    """
    Health endpoint for monitoring integrations.

    :return: health status payload
    """

    return {"status": "ok"}


@app.head("/health", include_in_schema=False)
async def healthcheck_head() -> dict[str, str]:
    """
    Lightweight health probe response for HEAD requests.

    :return: health status payload
    """

    return {"status": "ok"}

@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    """
    Redirect user to docs.

    :return: redirect response to documentation
    """
    return RedirectResponse("/docs")

if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)
