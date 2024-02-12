import random
import uuid
from typing import List

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, model_validator, Field
from pymongo import ReturnDocument

from app.database import get_db
from app.utils import MinesWeeperHTTPException, MinesErrorText as Met

# По умолчанию максимальные поля 30х30, но можно увеличить их размер
MAX_WIDTH = 30
MAX_HEIGHT = 30


class NewGameParams(BaseModel):
    width: int
    height: int
    mines_count: int


class TurnParams(BaseModel):
    game_id:  str
    row: int
    col: int

    @model_validator(mode="after")
    def check_formate_game_id(self) -> 'TurnParams':
        try:
            uuid.UUID(self.game_id, version=4)
        except ValueError as exc:
            raise MinesWeeperHTTPException(
                error=Met.error_form_game_id
            ) from exc
        return self


class GameService(BaseModel):
    game_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False

    width: int
    height: int
    mines_count: int
    count_open_cells: int = 0

    field: List[List[str]] | None = None
    data_field: List[List[str]] | None = None

    @model_validator(mode="after")
    def __check_width_height_mines(self) -> 'GameService':
        if not 1 < self.width < (MAX_WIDTH+1):
            raise MinesWeeperHTTPException(
                error=Met.error_width
            )
        if not 1 < self.height < (MAX_HEIGHT+1):
            raise MinesWeeperHTTPException(
                error=Met.error_height
            )
        if (((m_c := self.width*self.height)-1) < self.mines_count or
                self.mines_count < 1):
            raise MinesWeeperHTTPException(
                error=Met.error_mines_count.format(cells=m_c)
            )

        return self

    @model_validator(mode="after")
    def __check_field(self) -> 'GameService':
        """
        Создаем поле для игрока с закрытыми ячейками, если поле не передано.
        :return:
        """
        if self.field is None:
            self.field = [
                [' ' for _ in range(self.height)] for _ in range(self.width)
            ]

        return self

    async def create_new_game(self):
        db = await get_db()
        result = await db.mongodb["games"].insert_one(
            self.model_dump()
        )
        if not result:
            raise MinesWeeperHTTPException(error="Игра не создана")
        return self

    def _create_data_field(self, first_x: int, first_y: int):
        """
        Создаем поле data_field заполненное минами и не ставим мину на первую
        ячейку, которую выбрал игрок.
        :param first_x: Координаты первой открываемой ячейки по оси x
        :param first_y: Координаты первой открываемой ячейки по оси y
        :return:
        """

        self.data_field = [
            ['0' for _ in range(self.height)] for _ in range(self.width)
        ]
        free_cells = [
            (x, y) for y in range(self.height) for x in range(self.width)
            if (x, y) != (first_x, first_y)
        ]

        # Ставим мины в случайном порядке
        for i in range(self.mines_count):
            x, y = free_cells.pop(random.randint(0, len(free_cells) - 1))
            self.data_field[x][y] = ' '

        # Ставим цифры о минах
        for y in range(self.height):
            for x in range(self.width):
                if self.data_field[x][y] == ' ':
                    continue
                counter = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if (0 <= nx < self.width) and (0 <= ny < self.height) and \
                                self.data_field[nx][ny] == ' ':
                            counter += 1
                self.data_field[x][y] = str(counter)

    def __open_cells(self, x, y):
        cells_to_check = {(x, y)}

        while cells_to_check:
            x, y = cells_to_check.pop()
            # Проверка, что ячейка находится внутри поля и еще не была открыта
            if (
                    self.width <= x or x < 0 or
                    self.height <= y or y < 0 or
                    self.field[x][y] != ' '
            ):
                continue

            # Открываем ячейку
            self.field[x][y] = str(self.data_field[x][y])
            self.count_open_cells += 1

            # Если ячейка равна 0, откроем все соседние ячейки
            if self.data_field[x][y] == '0':
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        cells_to_check.add((x + dx, y + dy))

    async def user_opens_cells(self, row: int, col: int) -> 'GameService':
        self.checking_coordinates(row, col)

        # Создать поле при первом открытии ячейки
        first_open = False
        if self.data_field is None:
            first_open = True
            self._create_data_field(row, col)

        # Нажал на мину
        if self.data_field[row][col] == ' ':
            self.field = [
                [col if col != ' ' else 'X' for col in row]
                for row in self.data_field
            ]
            self.completed = True
            await self.__save_turn(db=await get_db(), first_open=first_open)
            return self

        # Открываем ячейку
        self.__open_cells(row, col)

        # Все ячейки открыты, победа
        if self.count_open_cells == self.height*self.width-self.mines_count:
            self.field = [
                [col if col != ' ' else 'M' for col in row]
                for row in self.data_field
            ]
            self.completed = True

        await self.__save_turn(db=await get_db(), first_open=first_open)

        return self

    def checking_coordinates(self, row: int, col: int):
        if self.width <= row or row < 0:
            raise MinesWeeperHTTPException(
                error=Met.error_row.format(w=self.width)
            )
        if self.height <= col or col < 0:
            raise MinesWeeperHTTPException(
                error=Met.error_col.format(h=self.height)
            )
        if self.field[row][col] != ' ':
            raise MinesWeeperHTTPException(
                error=Met.error_open_cell
            )

    async def __save_turn(self, db: AsyncIOMotorDatabase, first_open=False):
        if not self.game_id:
            return

        # Если игра завершилась, то чистим поля в бд
        if self.completed:
            await db.mongodb["games"].find_one_and_replace(
                {'game_id': self.game_id},
                {'game_id': self.game_id,
                 'completed': self.completed},
            )
            return

        new_values = {
            'field': self.field,
            'completed': self.completed,
            'count_open_cells': self.count_open_cells,
        }
        # Записываем игровое поле с минами на первый ход
        if first_open:
            new_values.update(data_field=self.data_field)

        await db.mongodb["games"].find_one_and_update(
            {'game_id': self.game_id},
            {'$set': new_values},
            return_document=ReturnDocument.AFTER
        )

    @staticmethod
    async def game_from_db(
            game_id: str, db: AsyncIOMotorDatabase
    ) -> 'GameService':
        game_data = await db.mongodb["games"].find_one({'game_id': game_id})
        if not game_data:
            raise MinesWeeperHTTPException(
                error=Met.error_game_id.format(game_id=game_id)
            )
        if game_data.get('completed'):
            raise MinesWeeperHTTPException(error=Met.error_completed)
        return GameService(**game_data)
