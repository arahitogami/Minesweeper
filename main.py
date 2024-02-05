from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.router import router_minesweeper
from app.utils import MinesWeeperHTTPException


app = FastAPI()


@app.exception_handler(MinesWeeperHTTPException)
async def http_exception_handler(
        request: Request, exc: MinesWeeperHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

# Для тестирования из браузера на другом сервере, разрешим любые запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],
)

app.include_router(router_minesweeper)
