import uvicorn
from fastapi import FastAPI
from starlette.responses import RedirectResponse

from src.routes.allowances import router as allowances_router

app = FastAPI(title="Allowances Parser Service", swagger_ui_parameters={"operationsSorter": "method"})
app.include_router(router=allowances_router)


@app.api_route("/health", methods=["GET", "HEAD"])
async def healthcheck() -> dict[str, str]:
    """
    Health endpoint for monitoring integrations.

    :return: health status payload
    """

    return {"status": "ok"}

@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    """
    Redirect user to docs

    :return: RedirectResponse to /docs
    """
    return RedirectResponse("/docs")

if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)
