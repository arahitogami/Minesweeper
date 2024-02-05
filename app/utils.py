from typing_extensions import Annotated, Doc

from fastapi import HTTPException, status


class MinesWeeperHTTPException(HTTPException):

    def __init__(
        self,
        error: Annotated[
            str,
            Doc(
                """
                error text
                """
            ),
        ],
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
            headers=None
        )


class MinesErrorText:
    error_width = 'Ширина поля должна быть не менее 2 и не более 30'
    error_height = 'Высота поля должна быть не менее 2 и не более 30'
    error_mines_count = ('Количество мин должно быть не менее 1 и '
                         'строго менее количества ячеек {cells}')

    error_row = ('Ряд должен быть неотрицательный '
                 'и менее ширины {w}')
    error_col = 'Колонка должна быть неотрицательной и менее высоты {h}'
    error_completed = 'Игра завершена'
    error_open_cell = 'Уже открытая ячейка'
    error_form_game_id = 'Некорректный формат идентификатора игры'
    error_game_id = 'Нет игры с идентификатором {game_id}'
