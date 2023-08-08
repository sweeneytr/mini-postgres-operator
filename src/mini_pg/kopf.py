import datetime
import random
from functools import partial
from logging import Logger
from typing import Any

import kopf
import psycopg
from kubernetes_asyncio import config

from . import databases, secrets
from .config import Config
from .crd import Spec

cfg: Config


@kopf.on.startup()
async def startup_fn(logger: Logger, **kwargs) -> None:
    global cfg
    cfg = Config()
    await config.load_kube_config()
    logger.info(f"Config validated & loaded")


@kopf.on.probe(id="now")
async def get_current_timestamp(**kwargs):
    return datetime.datetime.utcnow().isoformat()


@kopf.on.probe(id="random")
async def get_random_value(**kwargs):
    return random.randint(0, 1_000_000)


@kopf.on.create("wavecat.net", "v1", "databases")
async def create_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    db = Spec.model_validate(spec)
    passwordSecret = await secrets.read_secret(db.passwordSecret, namespace)
    password = passwordSecret[db.passwordSecretKey]

    await kopf.execute(fns={"user": partial(handle_create_user, db.username, password)})
    await kopf.execute(
        fns={"db": partial(handle_create_database, db.name, db.username)}
    )

    db_url = cfg.db_url.hosts()[0]
    host, port = db_url["host"], db_url["port"]
    await secrets.write_secret(
        db.credentialsSecret,
        namespace,
        {
            "username": db.username,
            "password": password,
            "database": db.name,
            "host": host,
            "port": port,
            "url": f"postgresql://{db.username}:{password}@{host}:{port}/{db.name}",
        },
    )
    logger.info(f"Database {db.name} was created")


async def handle_create_user(username, password, /, **kwargs) -> None:
    async with databases.get_cursor(str(cfg.db_url)) as cur:
        try:
            await databases.make_user(cur, username, password)
        except psycopg.errors.DuplicateObject as e:
            raise kopf.TemporaryError("The username is in conflict.", delay=60) from e


async def handle_create_database(name, owner, /, **kwargs) -> None:
    async with databases.get_cursor(str(cfg.db_url)) as cur:
        try:
            await databases.make_db(cur, name, owner)
        except psycopg.errors.DuplicateDatabase as e:
            raise kopf.TemporaryError(
                "The database name is in conflict.", delay=60
            ) from e


@kopf.on.update("wavecat.net", "v1", "databases")
async def update_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    db = Spec.model_validate(spec)
    logger.info(f"Database {db.name} was updated")


@kopf.on.delete("wavecat.net", "v1", "databases")
async def delete_fn(spec: Any, logger: Logger, **kwargs) -> None:
    # Don't worry about deleting secrets, the above `kopf.adopt` takes care of setting
    # up a cascade
    db = Spec.model_validate(spec)
    async with databases.get_cursor(str(cfg.db_url)) as cur:
        await databases.drop_db(cur, db.name)
        await databases.drop_user(cur, db.username)
    logger.info(f"Database {db.name} was deleted")
