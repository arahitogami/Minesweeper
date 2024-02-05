import uuid

from httpx import AsyncClient, Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils import MinesErrorText as Met


class TestNewGame:

    async def test_new_standard_game(self, ac: AsyncClient):
        width = 10
        height = 10
        mines_count = 10
        response: Response = await ac.post(
            "/api/new",
            json={
                "width": width,
                "height": height,
                "mines_count": mines_count
            }
        )
        assert response.status_code == 200
        assert all(
            key in [
                "game_id", "width", "height",
                "mines_count", "completed", "field"
            ] for
            key in response.json()
        )

    async def test_new_no_standard_game(self, ac: AsyncClient):
        response_1: Response = await ac.post(
            "/api/new",
            json={
                "width": 2,
                "height": 30,
                "mines_count": 1
            }
        )
        assert response_1.status_code == 200, "w=2, h=30, m_c=1"

        response_2: Response = await ac.post(
            "/api/new",
            json={
                "width": 30,
                "height": 2,
                "mines_count": 59
            }
        )
        assert response_2.status_code == 200, "w=30, h=2, m_c=59"
        field = response_2.json()['field']
        assert len(field) == 30
        for y in field:
            assert len(y) == 2

    async def test_new_bad_params_game(self, ac: AsyncClient):
        # Проверка на недопустимую ширину и высоту
        for i in [1, 31, 0, -5]:
            response_1: Response = await ac.post(
                "/api/new",
                json={
                    "width": i,
                    "height": 10,
                    "mines_count": 10
                }
            )
            assert response_1.status_code == 400, f"w={i}, h=30, m_c=10"
            assert response_1.json()['error'] == Met.error_width

            response_2: Response = await ac.post(
                "/api/new",
                json={
                    "width": 10,
                    "height": i,
                    "mines_count": 10
                }
            )
            assert response_2.status_code == 400, f"w=10, h={i}, m_c=10"
            assert response_2.json()['error'] == Met.error_height

        # Проверка на плохое количество мин
        for w, h, m_c in ((2, 2, 4), (30, 30, 900), (10, 10, -5)):
            response_3: Response = await ac.post(
                "/api/new",
                json={
                    "width": w,
                    "height": h,
                    "mines_count": m_c
                }
            )
            assert response_3.status_code == 400, f"w={w}, h={h}, m_c={m_c}"
            assert response_3.json()['error'] == Met.error_mines_count.format(
                cells=w*h
            )

        # Передача не верных типов данных
        for w, h, m_c in (('rr', 10, 10), (10, 'rr', 10), (10, 10, 'rr')):
            response_4: Response = await ac.post(
                "/api/new",
                json={
                    "width": w,
                    "height": h,
                    "mines_count": m_c
                }
            )
            assert response_4.status_code == 422, f"w={w}, h={h}, m_c={m_c}"


class TestTurnGame:

    @staticmethod
    async def new_game(ac: AsyncClient, w, h, m_c):
        response: Response = await ac.post(
            "/api/new",
            json={
                "width": w,
                "height": h,
                "mines_count": m_c
            }
        )
        return response.json()

    async def test_first_open_cell(self, ac: AsyncClient):
        game = await self.new_game(ac, 10, 10, 10)
        response: Response = await ac.post(
            "/api/turn",
            json={
                "game_id": game['game_id'],
                "row": 0,
                "col": 0
            }
        )
        assert response.status_code == 200
        assert all(
            key in [
                "game_id", "width", "height",
                "mines_count", "completed", "field"
            ] for
            key in response.json()
        )
        assert game['field'] != response.json()['field']
        assert response.json()['field'][0][0] != ' '

    async def test_win_game(self, ac: AsyncClient):
        game = await self.new_game(ac, 10, 10, 99)
        response: Response = await ac.post(
            "/api/turn",
            json={
                "game_id": game['game_id'],
                "row": 0,
                "col": 0
            }
        )
        assert response.status_code == 200
        assert response.json()['completed']
        field = [
            ['3']+['M' for _ in range(9)],
        ] + [['M' for _ in range(10)] for _ in range(9)]
        assert response.json()['field'] == field

    async def test_lose_game(self, ac: AsyncClient, db: AsyncIOMotorDatabase):
        game = await self.new_game(ac, 30, 30, 40)
        row, col = 0, 0
        await ac.post(
            "/api/turn",
            json={
                "game_id": game['game_id'],
                "row": row,
                "col": col
            }
        )

        # Находим ячейку с миной
        game_in_db = await db.mongodb["games"].find_one(
            {'game_id': game['game_id']},
        )
        for nx, x in enumerate(game_in_db['data_field']):
            if row or col:
                break
            for ny, y in enumerate(x):
                if y == ' ':
                    row, col = nx, ny
                    break

        response_2: Response = await ac.post(
            "/api/turn",
            json={
                "game_id": game['game_id'],
                "row": row,
                "col": col
            }
        )
        assert response_2.status_code == 200
        assert response_2.json()['completed']
        field = [
            [col if col != ' ' else 'X' for col in row]
            for row in game_in_db['data_field']
        ]
        assert response_2.json()['field'] == field

    async def test_bad_params_turn(self, ac: AsyncClient):
        w, h, m_c = 10, 10, 98
        game = await self.new_game(ac, w, h, m_c)

        # Не верный формат game_id
        response_1: Response = await ac.post(
            "/api/turn",
            json={
                "game_id": game['game_id'] + '2',
                "row": 0,
                "col": 0
            }
        )
        assert response_1.status_code == 400
        assert response_1.json()['error'] == Met.error_form_game_id

        # Не верный формат game_id
        new_uuid = uuid.uuid4()
        response_1_1: Response = await ac.post(
            "/api/turn",
            json={
                "game_id": str(new_uuid),
                "row": 0,
                "col": 0
            }
        )
        assert response_1_1.status_code == 400
        assert response_1_1.json()['error'] == Met.error_game_id.format(
            game_id=str(new_uuid)
        )

        # Неверная ячейка
        for i in [-1, 10]:
            response_2: Response = await ac.post(
                "/api/turn",
                json={
                    "game_id": game['game_id'],
                    "row": i,
                    "col": 0
                }
            )
            assert response_2.status_code == 400, f"r={i}, c=0"
            assert response_2.json()['error'] == Met.error_row.format(w=w)

            response_3: Response = await ac.post(
                "/api/turn",
                json={
                    "game_id": game['game_id'],
                    "row": 0,
                    "col": i
                }
            )
            assert response_3.status_code == 400, f"r=0, c={i}"
            assert response_3.json()['error'] == Met.error_col.format(h=h)

        # Открытая ячейка
        response_4: Response | None = None
        for i in range(2):
            response_4: Response = await ac.post(
                "/api/turn",
                json={
                    "game_id": game['game_id'],
                    "row": 0,
                    "col": 0
                }
            )
        assert response_4.status_code == 400
        assert response_4.json()['error'] == Met.error_open_cell

        # Игра завершена
        response_5: Response | None = None
        for i in range(2):
            response_5: Response = await ac.post(
                "/api/turn",
                json={
                    "game_id": game['game_id'],
                    "row": 1,
                    "col": 1
                }
            )
        assert response_5.status_code == 400
        assert response_5.json()['error'] == Met.error_completed
