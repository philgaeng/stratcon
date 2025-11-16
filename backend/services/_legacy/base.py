#!/usr/bin/env python3
"""Shared service context utilities."""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Sequence, Union

from .utils import ReportLogger
from .db_manager import DbQueries


class ServiceContext:
    """Provides shared context (logger, DB access, client/tenant scope) for services."""

    def __init__(
        self,
        *,
        user_id: Optional[int] = None,
        epc_id: Optional[int] = None,
        client_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        logger: Optional[ReportLogger] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        self.logger = logger or ReportLogger()
        self.conn = conn
        self.user_id = user_id
        self.epc_id = epc_id
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.user_epc_ids: List[int] = []
        self.user_client_ids: List[int] = []
        self.user_tenant_ids: List[int] = []

        if self.user_id is not None:
            info = DbQueries.get_info_for_user(self.user_id, conn=self.conn)
            self.user_epc_ids = self._normalize_id_list(info.get("epc_id"))
            self.user_client_ids = self._normalize_id_list(info.get("client_id"))
            self.user_tenant_ids = self._normalize_id_list(info.get("tenant_id"))
            self.epc_id = self.epc_id or self._first_or_none(self.user_epc_ids)
            self.client_id = self.client_id or self._first_or_none(self.user_client_ids)
            self.tenant_id = self.tenant_id or self._first_or_none(self.user_tenant_ids)

        if self.tenant_id is not None and self.client_id is None:
            try:
                self.client_id = DbQueries.get_client_id_for_tenant(
                    self.tenant_id, conn=self.conn
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.debug(
                    "Failed to resolve client_id for tenant %s: %s", self.tenant_id, exc
                )

        if self.client_id is not None and self.epc_id is None:
            try:
                self.epc_id = DbQueries.get_epc_id_for_client(
                    self.client_id, conn=self.conn
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.debug(
                    "Failed to resolve epc_id for client %s: %s", self.client_id, exc
                )


    @property
    def db(self) -> DbQueries:
        """Convenience accessor for DbQueries."""
        return DbQueries


    @staticmethod
    def _normalize_id_list(value: Optional[Union[int, Sequence[int]]]) -> List[int]:
        """Return a sanitized list of integer identifiers."""
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            result: List[int] = []
            for item in value:
                if item is None:
                    continue
                try:
                    result.append(int(item))
                except (TypeError, ValueError):
                    continue
            return result
        try:
            return [int(value)]
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _first_or_none(values: Sequence[int]) -> Optional[int]:
        """Return first element of sequence or None."""
        return values[0] if values else None


__all__ = ["ServiceContext"]
