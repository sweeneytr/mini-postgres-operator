from pydantic import BaseModel


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
