import datetime
import random
from logging import Logger
from typing import Any

import kopf
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


@kopf.on.create("databases")
async def create_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    db = Spec.model_validate(spec)
    password = (await secrets.read_secret(db.password.secretName, namespace))[
        db.password.key
    ]

    async with databases.get_cursor(str(cfg.db_url)) as cur:
        await databases.make_user(cur, db.username, password)
        await databases.make_db(cur, db.name, db.username)

    await secrets.make_secret(
        db.connectionUrl.secretName, namespace, {db.connectionUrl.key: "foo"}
    )
    logger.info(f"Database {db.name} was created")


@kopf.on.update("databases")
async def update_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    db = Spec.model_validate(spec)
    logger.info(f"Database {db.name} was updated")


@kopf.on.delete("databases")
async def delete_fn(spec: Any, logger: Logger, **kwargs) -> None:
    # Don't worry about deleting secrets, the above `kopf.adopt` takes care of setting
    # up a cascade
    db = Spec.model_validate(spec)
    async with databases.get_cursor(str(cfg.db_url)) as cur:
        await databases.drop_db(cur, db.name)
        await databases.drop_user(cur, db.username)
    logger.info(f"Database {db.name} was deleted")
