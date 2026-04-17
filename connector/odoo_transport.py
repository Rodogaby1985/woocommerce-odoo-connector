"""Capa de transporte para comunicación con Odoo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import xmlrpc.client

import requests


class OdooTransport(ABC):
    """Interfaz base para comunicación con Odoo."""

    @abstractmethod
    def authenticate(self) -> int:
        """Autentica y devuelve uid."""

    @abstractmethod
    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta métodos sobre modelos de Odoo."""


class XmlRpcTransport(OdooTransport):
    """Transporte XML-RPC para Odoo 14-18 (y compatibilidad legacy)."""

    def __init__(self, url: str, db: str, user: str, password: str) -> None:
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self._uid: int | None = None
        self.common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def authenticate(self) -> int:
        uid = self.common.authenticate(self.db, self.user, self.password, {})
        if not uid:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        self._uid = int(uid)
        return self._uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            return self.authenticate()
        return self._uid

    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs or {})


class JsonRpcTransport(OdooTransport):
    """Transporte JSON-RPC para Odoo 19+."""

    def __init__(self, url: str, db: str, user: str, password: str | None = None, api_key: str | None = None) -> None:
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self.api_key = api_key
        self._uid: int | None = None
        self._request_id = 0

    def _call(self, service: str, method: str, args: list[Any]) -> Any:
        self._request_id += 1
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "call",
            "params": {"service": service, "method": method, "args": args},
        }
        response = requests.post(f"{self.url}/jsonrpc", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            raise Exception(f"Odoo JSON-RPC Error: {result['error']}")
        return result.get("result")

    def authenticate(self) -> int:
        credential = self.password or self.api_key
        uid = self._call("common", "authenticate", [self.db, self.user, credential, {}])
        if not uid:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        self._uid = int(uid)
        return self._uid

    @property
    def uid(self) -> int:
        if self._uid is None:
            return self.authenticate()
        return self._uid

    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        credential = self.password or self.api_key
        return self._call(
            "object",
            "execute_kw",
            [self.db, self.uid, credential, model, method, args, kwargs or {}],
        )


def create_transport(
    url: str,
    db: str,
    user: str,
    password: str,
    api_key: str | None = None,
    protocol: str = "auto",
) -> OdooTransport:
    """Crea el transporte apropiado según configuración."""
    selected_protocol = (protocol or "auto").lower()
    if selected_protocol == "jsonrpc" or (selected_protocol == "auto" and api_key):
        return JsonRpcTransport(url=url, db=db, user=user, password=password, api_key=api_key)
    return XmlRpcTransport(url=url, db=db, user=user, password=password)
