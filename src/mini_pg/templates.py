def secret(name: str, data: dict) -> dict:
    return {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {"name": name},
        "data": data,
    }
