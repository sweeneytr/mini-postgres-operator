import base64
from typing import Any

import kopf
from kubernetes_asyncio import client

from . import templates
import jsonpatch

async def read_secret(name: str, namespace: str) -> dict[str, str]:
    v1 = client.CoreV1Api()
    secret = await v1.read_namespaced_secret(name, namespace)
    return {k: base64.b64decode(v).decode() for k, v in secret.data.items()}


async def write_secret(name: str, namespace: str, data: dict[str, Any]) -> None:
    v1 = client.CoreV1Api()
    encoded = {k: base64.b64encode(str(v).encode()).decode() for k, v in data.items()}

    data = templates.secret(name=name, data=encoded)

    kopf.adopt(data)
    await v1.create_namespaced_secret(namespace, data)


async def patch_secret(name: str, namespace: str, data: dict[str, Any]) -> None:
    v1 = client.CoreV1Api()
    old_data = read_secret(name, namespace)
    encoded = {k: base64.b64encode(str(v).encode()).decode() for k, v in data.items()}
    patch = jsonpatch.make_patch(old_data, encoded).patch

    await v1.patch_namespaced_secret(name, namespace, patch)
