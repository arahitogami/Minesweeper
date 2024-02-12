from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.schemas import NewGameParams, GameService, TurnParams


router_minesweeper = APIRouter(
    prefix="/api",
    tags=["Minesweeper"],
)


@router_minesweeper.post(
    "/new",
    response_model=GameService,
    response_model_exclude={'data_field', 'count_open_cells'}
)
async def new_game(
        params: NewGameParams,
):

    return await GameService(**params.model_dump()).create_new_game()


@router_minesweeper.post(
    "/turn",
    response_model=GameService,
    response_model_exclude={'data_field', 'count_open_cells'}
)
async def make_move(
        params: TurnParams,
        db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]
):
    game: GameService = await GameService.game_from_db(params.game_id, db)

    return await game.user_opens_cells(params.row, params.col)
