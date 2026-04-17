"""Transportes de comunicación con Odoo."""

from __future__ import annotations

import xmlrpc.client
from abc import ABC, abstractmethod
from typing import Any

import requests


class OdooTransport(ABC):
    """Interfaz base para comunicación con Odoo."""

    @abstractmethod
    def authenticate(self) -> int:
        """Autentica y retorna el uid."""

    @property
    @abstractmethod
    def uid(self) -> int:
        """Uid autenticado."""

    @abstractmethod
    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta método sobre un modelo de Odoo."""


class XmlRpcTransport(OdooTransport):
    """Transporte XML-RPC para Odoo 14-18 y compatibilidad legacy."""

    def __init__(self, url: str, db: str, user: str, password: str) -> None:
        self.url = url
        self.db = db
        self.user = user
        self.password = password
        self._uid: int | None = None
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    @property
    def uid(self) -> int:
        """Retorna uid autenticado en XML-RPC."""
        if self._uid is None:
            self.authenticate()
        if self._uid is None:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        return self._uid

    def authenticate(self) -> int:
        """Autentica en XML-RPC."""
        uid = self.common.authenticate(self.db, self.user, self.password, {})
        if not uid:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        self._uid = int(uid)
        return self._uid

    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta un método XML-RPC."""
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs or {})


class JsonRpcTransport(OdooTransport):
    """Transporte JSON-RPC /json/2 para Odoo 19+."""

    def __init__(self, url: str, db: str, user: str, password: str = "", api_key: str = "") -> None:
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.api_key = api_key
        self._uid: int | None = None
        self._request_id = 0

    @property
    def uid(self) -> int:
        """Retorna uid autenticado en JSON-RPC."""
        if self._uid is None:
            self.authenticate()
        if self._uid is None:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        return self._uid

    def _call(self, endpoint: str, method: str, params: dict[str, Any]) -> Any:
        """Realiza una llamada JSON-RPC y retorna result."""
        self._request_id += 1
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        try:
            response = requests.post(
                f"{self.url}{endpoint}",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as exc:
            raise ConnectionError(f"Error de comunicación con Odoo JSON-RPC: {exc}") from exc
        except ValueError as exc:
            raise ConnectionError("Respuesta inválida de Odoo JSON-RPC") from exc

        if "error" in result:
            raise ConnectionError(f"Odoo JSON-RPC Error: {result['error']}")
        return result.get("result")

    def authenticate(self) -> int:
        """Autentica en JSON-RPC."""
        password = self.password or self.api_key
        if not password:
            raise ConnectionError("Se requiere ODOO_PASSWORD u ODOO_API_KEY para JSON-RPC")
        result = self._call(
            "/json/2/common",
            "authenticate",
            {"db": self.db, "login": self.user, "password": password},
        )
        if not result:
            raise ConnectionError("No fue posible autenticarse en Odoo")
        self._uid = int(result)
        return self._uid

    def execute_kw(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta un método sobre /json/2/object."""
        password = self.password or self.api_key
        if not password:
            raise ConnectionError("Se requiere ODOO_PASSWORD u ODOO_API_KEY para JSON-RPC")
        return self._call(
            "/json/2/object",
            "execute_kw",
            {
                "db": self.db,
                "uid": self.uid,
                "password": password,
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
            },
        )


def create_transport(
    url: str,
    db: str,
    user: str,
    password: str,
    api_key: str = "",
    protocol: str = "auto",
) -> OdooTransport:
    """Crea un transporte según configuración."""
    normalized_protocol = (protocol or "auto").lower()
    if normalized_protocol == "xmlrpc":
        return XmlRpcTransport(url=url, db=db, user=user, password=password)
    if normalized_protocol == "jsonrpc":
        return JsonRpcTransport(url=url, db=db, user=user, password=password, api_key=api_key)
    if normalized_protocol == "auto":
        if api_key:
            return JsonRpcTransport(url=url, db=db, user=user, password=password, api_key=api_key)
        return XmlRpcTransport(url=url, db=db, user=user, password=password)
    raise ValueError("ODOO_PROTOCOL debe ser auto, xmlrpc o jsonrpc")

