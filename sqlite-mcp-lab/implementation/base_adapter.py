from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    @abstractmethod
    def connect(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_tables(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: dict[str, Any] | None = None,
        group_by: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError