import uvicorn
from fastapi import FastAPI

from src.routes.allowances import router as allowances_router

app = FastAPI(title="Allowances Parser Service", swagger_ui_parameters={"operationsSorter": "method"})
app.include_router(router=allowances_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    """
    Health endpoint for monitoring integrations.

    :return: health status payload
    """

    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000)
