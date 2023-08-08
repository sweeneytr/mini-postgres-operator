from pydantic import PostgresDsn
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_url: PostgresDsn
