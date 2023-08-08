from contextlib import asynccontextmanager

import psycopg
from psycopg import sql


@asynccontextmanager
async def get_cursor(db_url: str) -> psycopg.AsyncCursor:
    # This vexes me. autocommit != "auto commit transactions at close". Instead, it
    # means "every statement has an immediate effect", a.k.a.
    async with await psycopg.AsyncConnection.connect(db_url, autocommit=True) as conn:
        async with conn.cursor() as cur:
            yield cur


async def make_user(cur: psycopg.AsyncCursor, username: str, password: str) -> None:
    try:
        await cur.execute(
            sql.SQL("CREATE USER {} WITH PASSWORD {};").format(
                sql.Identifier(username), sql.Literal(password)
            )
        )
    except psycopg.errors.DuplicateObject:
        pass


async def make_db(cur: psycopg.AsyncCursor, name: str, owner: str) -> None:
    try:
        await cur.execute(
            sql.SQL("CREATE DATABASE {} WITH OWNER {};").format(
                sql.Identifier(name), sql.Identifier(owner)
            )
        )
    except psycopg.errors.DuplicateDatabase:
        pass


async def drop_user(cur: psycopg.AsyncCursor, username: str) -> None:
    await cur.execute(
        sql.SQL("DROP USER IF EXISTS {}").format(sql.Identifier(username))
    )


async def drop_db(cur: psycopg.AsyncCursor, name: str) -> None:
    await cur.execute(
        sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name))
    )
