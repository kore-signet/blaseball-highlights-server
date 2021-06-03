from db import *
from quart import Quart, request
import os

app = Quart(__name__)
db = HighlightDB(app, os.environ["DATABASE_URL"])

@app.route("/submit", methods=["POST"])
async def submit():
    data = await request.get_json()
    r = await db.create_story(
        data["story"], data["events"], user=data.get("user", None)
    )
    return r, r["status"]


@app.route("/story", methods=["GET"])
async def get():
    id = request.args.get("id", None)
    if not id:
        return {"status": 400, "reason": "missing story id"}, 400

    r = await db.get_story(id)
    return r, r["status"]


if __name__ == "__main__":
    app.run(debug=True)
