from pydantic import BaseModel, Field
from typing import Annotated, Any
import json


def immutable(name: str) -> dict[str, Any]:
    return {
        "x-kubernetes-validations": [
            {"rule": "self == oldSelf", "message": f"Cannot change {name}"}
        ]
    }


class Spec(BaseModel):
    name: Annotated[str, Field(json_schema_extra=immutable("name"))]
    """The name for the database."""
    username: Annotated[str, Field(json_schema_extra=immutable("username"))]
    """The name for the database's admin user."""
    passwordSecret: Annotated[
        str, Field(json_schema_extra=immutable("passwordSecret"))
    ]
    """The secret to load the database password from."""
    passwordSecretKey: Annotated[
        str, Field(json_schema_extra=immutable("passwordSecretKey"))
    ] = "password"
    """The secret key to load the database password from."""
    credentialsSecret: Annotated[
        str, Field(json_schema_extra=immutable("credentialsSecret"))
    ]
    """The secret to store the database connection details to."""


CRD = {
    "apiVersion": "apiextensions.k8s.io/v1",
    "kind": "CustomResourceDefinition",
    "metadata": {"name": "databases.wavecat.net"},
    "spec": {
        "group": "wavecat.net",
        "scope": "Namespaced",
        "names": {
            "plural": "databases",
            "singular": "database",
            "kind": "Database",
            "shortNames": ["db"],
        },
        "versions": [
            {
                "name": "v1",
                "served": True,
                "storage": True,
                "schema": {
                    "openAPIV3Schema": {
                        "type": "object",
                        "required": ["spec"],
                        "properties": {"spec": Spec.model_json_schema()},
                    },
                },
            }
        ],
    },
}

if __name__ == "__main__":
    print(json.dumps(CRD))
