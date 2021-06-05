import asyncpg
import uuid, secrets, json
from quart import Quart


class HighlightDB:
    def __init__(self, app: Quart, uri: str) -> None:
        self.init_app(app)
        self._pool = None
        self.uri = uri

    def init_app(self, app: Quart) -> None:
        app.before_serving(self._before_serving)
        app.after_serving(self._after_serving)

    async def _before_serving(self) -> None:
        self._pool = await asyncpg.create_pool(self.uri)

    async def _after_serving(self) -> None:
        await self._pool.close()

    async def create_story(self, story, events, user=None):
        user_existed = user != None

        if "story_id" in story:
            return await self.edit_story(story, events, user=user)

        async with self._pool.acquire() as conn:
            while True:
                story_id = secrets.token_urlsafe(12)
                row = await conn.fetchrow(
                    "SELECT * FROM stories WHERE story_id = $1", story_id
                )
                if not row:
                    story["story_id"] = story_id
                    break

            if user:
                if not (await self.check_user_token(user, conn)):
                    return {"status": 403, "reason": "invalid user token/id"}
            else:
                user = await self.create_user(conn)

            await conn.execute(
                """
                INSERT INTO stories (story_id, game_id, user_id, title)
                VALUES ($1,$2,$3,$4)
            """,
                story["story_id"],
                uuid.UUID(story["game_id"]),
                user["user_id"],
                story["title"],
            )

            processed_events = []
            for event in events:
                processed_events.append(
                    [
                        story["story_id"],
                        uuid.UUID(event["blaseball_event_id"]),
                        event["description"],
                        json.dumps(event["visual"]),
                    ]
                )

            await conn.executemany(
                """
                INSERT INTO events (story_id, blaseball_event_id, description, visual)
                VALUES ($1,$2,$3,$4)
            """,
                processed_events,
            )

        if not user_existed:
            return {
                "status": 200,
                "user_token": user["user_token"],
                "user_id": user["user_id"],
                "story_id": story["story_id"],
            }
        else:
            return {"status": 200, "story_id": story["story_id"]}

    async def edit_story(self, story, events, user=None):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM stories WHERE story_id = $1", story["story_id"]
            )
            if not row:
                return {"status": 404, "reason": "story id not found"}

            if row["user_id"] != user["user_id"] or not (
                await self.check_user_token(user, conn)
            ):
                return {"status": 401, "reason": "invalid user token/id"}

            processed_events = []
            for event in events:
                processed_events.append(
                    [
                        story["story_id"],
                        uuid.UUID(event["blaseball_event_id"]),
                        event["description"],
                        json.dumps(event["visual"]),
                    ]
                )

            await conn.executemany(
                """
                INSERT INTO events (story_id, blaseball_event_id, description, visual)
                VALUES ($1,$2,$3,$4)
                ON CONFLICT (story_id,blaseball_event_id) DO UPDATE
                SET description = $3,
                    visual = $4
            """,
                processed_events,
            )

            return {"status": 200}

    async def get_story(self, id):
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM stories WHERE story_id = $1", id)
            if not row:
                return {"status": 404, "reason": "story id not found"}

            res = {
                "story": {
                    "story_id": row["story_id"],
                    "game_id": row["game_id"],
                    "user_id": row["user_id"],
                    "title": row["title"],
                },
                "events": [],
            }

            for event in await conn.fetch(
                "SELECT * FROM events WHERE story_id = $1", id
            ):
                res["events"].append(
                    {
                        "blaseball_event_id": event["blaseball_event_id"],
                        "description": event["description"],
                        "visual": json.loads(event["visual"]),
                    }
                )

            res["status"] = 200
            return res

    async def create_user(self, conn):
        user_token = secrets.token_urlsafe(64)
        user_id = ""
        while True:
            user_id = secrets.token_urlsafe(12)
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            if not row:
                break

        await conn.execute(
            """
            INSERT INTO users (username, user_id, user_token)
            VALUES ($1, $2, $3)
        """,
            "",
            user_id,
            user_token,
        )

        return {"user_id": user_id, "user_token": user_token}

    async def check_user_token(self, user, conn):
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1 AND user_token = $2",
            user["user_id"],
            user["user_token"],
        )
        return row != None
