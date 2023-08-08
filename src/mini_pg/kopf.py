from logging import Logger
from typing import Any

import kopf
from kubernetes import config

from . import databases, secrets
from .config import Config
from .crd import Spec


@kopf.on.startup()
async def startup_fn(logger: Logger, **kwargs) -> None:
    cfg = Config()
    config.load_kube_config()
    logger.info(f"Config validated")


@kopf.on.create("databases")
def create_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    cfg = Config()

    db = Spec.model_validate(spec)
    password = secrets.read_secret(db.password.secretName, namespace)[db.password.key]

    with databases.get_cursor(cfg.db_url) as cur:
        databases.make_user(cur, db.username, password)
        databases.make_db(db.name, db.username)

    secrets.make_secret(
        db.connectionUrl.secretName, namespace, {db.connectionUrl.key: "foo"}
    )
    logger.info(f"Database {db.name} was created")


@kopf.on.update("databases")
def update_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    cfg = Config()
    db = Spec.model_validate(spec)
    logger.info(f"Database {db.name} was updated")


@kopf.on.delete("databases")
def delete_fn(spec: Any, logger: Logger, **kwargs) -> None:
    # Don't worry about deleting secrets, the above `kopf.adopt` takes care of setting
    # up a cascade
    cfg = Config()
    db = Spec.model_validate(spec)
    with databases.get_cursor(cfg.db_url) as cur:
        databases.drop_db(cur, db.name)
        databases.drop_user(cur, db.username)
    logger.info(f"Database {db.name} was deleted")
