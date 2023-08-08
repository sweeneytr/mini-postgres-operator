from logging import Logger
from typing import Any
import base64
import kopf
import psycopg2
import psycopg2.errors
from kubernetes import client, config
from psycopg2 import sql
from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings
import copy

class Secret(BaseModel):
    secretName: str
    key: str


class Spec(BaseModel):
    name: str
    username: str
    password: Secret
    connectionUrl: Secret | None = None
    host: str | None = None
    port: str | None = None


class Config(BaseSettings):
    db_url: PostgresDsn


def template(name: str, key: str, value: str) -> dict:
    return {"apiVersion": "v1", "kind": "Secret", "type": "Opaque", "metadata": {"name": name}, "data": {key: value}}

@kopf.on.startup()
async def startup_fn(logger: Logger, **kwargs) -> None:
    cfg = Config()
    logger.info(f"Config validated")

@kopf.on.create("databases")
def create_fn(spec: Any, namespace: str, logger: Logger, **kwargs) -> None:
    cfg = Config()
    config.load_kube_config()

    db = Spec.model_validate(spec)

    v1 = client.CoreV1Api()
    secret = v1.read_namespaced_secret(db.password.secretName, namespace)
    password = base64.b64decode(secret.data.get(db.password.key)).decode()

    conn = psycopg2.connect(dsn=str(cfg.db_url))
    conn.set_session(autocommit=True)
    with conn.cursor() as cur:
        try:
            cur.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD {};").format(sql.Identifier(db.username), sql.Literal(password))
            )
        except psycopg2.errors.DuplicateObject:
            pass
        try:
            cur.execute(
                sql.SQL("CREATE DATABASE {} WITH OWNER {};").format(sql.Identifier(db.name), sql.Identifier(db.username))
            )
        except psycopg2.errors.DuplicateDatabase:
            pass

    connection_url = base64.b64encode('foo'.encode()).decode()

    data = template(
        name=db.connectionUrl.secretName,
        key=db.connectionUrl.key,
        value=connection_url,
    )

    kopf.adopt(data)
    v1.create_namespaced_secret(namespace, data)
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

    conn = psycopg2.connect(dsn=str(cfg.db_url))
    conn.set_session(autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db.name))
        )
        cur.execute(
            sql.SQL("DROP USER IF EXISTS {}").format(sql.Identifier(db.username))
        )
    logger.info(f"Database {db.name} was deleted")
