import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.database import get_db
from app.schemas import NewGameParams, GameService, TurnParams
from app.utils import MinesWeeperHTTPException, MinesErrorText as Met


router_minesweeper = APIRouter(
    prefix="/api",
    tags=["Minesweeper"],
)


@router_minesweeper.post(
    "/new",
    response_model=GameService,
    response_model_exclude={'data_field'}
)
async def new_game(
        params: NewGameParams,
):

    return await GameService(**params.model_dump()).create_new_game()


@router_minesweeper.post(
    "/turn",
    response_model=GameService,
    response_model_exclude={'data_field'}
)
async def make_move(
        params: TurnParams,
        db: Annotated[AsyncIOMotorDatabase, Depends(get_db)]
):
    game = await db.mongodb["games"].find_one(
        {'game_id': params.game_id},
    )

    if not game:
        raise MinesWeeperHTTPException(
            error=Met.error_game_id.format(game_id=params.game_id)
        )

    if game.get('completed'):
        raise MinesWeeperHTTPException(error=Met.error_completed)

    game_turn = GameService(**game).user_opens_cells(params.row, params.col)

    # Если игра завершилась, то стираем данные о полях из базы
    if game_turn.completed:
        await db.mongodb["games"].find_one_and_replace(
            {'game_id': game_turn.game_id},
            {'game_id': game_turn.game_id, 'completed': game_turn.completed},
        )
        return game_turn

    new_values = {
            'field': game_turn.field,
            'completed': game_turn.completed,
        }
    # Записываем игровое поле на первый ход
    if 'data_field' not in game:
        new_values.update(data_field=game_turn.data_field)

    result = await db.mongodb["games"].find_one_and_update(
        {'game_id': game_turn.game_id},
        {'$set': new_values},
        return_document=ReturnDocument.AFTER
    )
    return result
