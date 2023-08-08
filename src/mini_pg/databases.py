from contextlib import contextmanager

import psycopg2
import psycopg2.errors
from psycopg2 import sql


@contextmanager
def get_cursor(db_url: str):
    with psycopg2.connect(dsn=db_url) as conn:
        # This vexes me. autocommit != "auto commit transactions at close". Instead, it
        # means "every statement has an immediate effect", a.k.a.
        conn.set_session(autocommit=True)
        with conn.cursor() as cur:
            yield cur


def make_user(cur, username: str, password: str) -> None:
    try:
        cur.execute(
            sql.SQL("CREATE USER {} WITH PASSWORD {};").format(
                sql.Identifier(username), sql.Literal(password)
            )
        )
    except psycopg2.errors.DuplicateObject:
        pass


def make_db(cur, name: str, owner: str) -> None:
    try:
        cur.execute(
            sql.SQL("CREATE DATABASE {} WITH OWNER {};").format(
                sql.Identifier(name), sql.Identifier(owner)
            )
        )
    except psycopg2.errors.DuplicateDatabase:
        pass


def drop_user(cur, username: str) -> None:
    cur.execute(sql.SQL("DROP USER IF EXISTS {}").format(sql.Identifier(username)))


def drop_db(cur, name: str) -> None:
    cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))
