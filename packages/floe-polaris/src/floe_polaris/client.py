"""Polaris catalog client wrapper.

This module provides PolarisCatalog, a wrapper around PyIceberg's RestCatalog
with added observability, retry policies, and connection management.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, cast

from pyiceberg.catalog import Catalog
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.exceptions import (
    NamespaceAlreadyExistsError as PyIcebergNamespaceExistsError,
)
from pyiceberg.exceptions import (
    NamespaceNotEmptyError as PyIcebergNamespaceNotEmptyError,
)
from pyiceberg.exceptions import (
    NoSuchNamespaceError as PyIcebergNamespaceNotFoundError,
)
from pyiceberg.exceptions import (
    NoSuchTableError as PyIcebergTableNotFoundError,
)

from floe_polaris.config import NamespaceInfo, PolarisCatalogConfig
from floe_polaris.errors import (
    CatalogAuthenticationError,
    CatalogConnectionError,
    NamespaceExistsError,
    NamespaceNotEmptyError,
    NamespaceNotFoundError,
    TableNotFoundError,
)
from floe_polaris.observability import catalog_operation, get_logger, get_tracer
from floe_polaris.retry import CircuitBreaker, create_retry_decorator

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer
    from pyiceberg.table import Table
    from structlog.stdlib import BoundLogger


class PolarisCatalog:
    """Polaris catalog client with observability and retry support.

    This class wraps PyIceberg's RestCatalog and adds:
    - Configurable retry policies with exponential backoff
    - Structured logging via structlog
    - OpenTelemetry span tracing
    - Automatic token refresh
    - Circuit breaker for cascading failure prevention

    Attributes:
        config: Catalog configuration.

    Note:
        Use create_catalog() factory function instead of direct instantiation.

    Example:
        >>> from floe_polaris import create_catalog, PolarisCatalogConfig
        >>> config = PolarisCatalogConfig(
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     client_id="my_client",
        ...     client_secret="my_secret",
        ... )
        >>> catalog = create_catalog(config)
        >>> namespaces = catalog.list_namespaces()
    """

    def __init__(
        self,
        config: PolarisCatalogConfig,
        *,
        tracer: Tracer | None = None,
        logger: BoundLogger | None = None,
    ) -> None:
        """Initialize PolarisCatalog.

        Args:
            config: Catalog configuration with connection and retry settings.
            tracer: Optional OpenTelemetry tracer. Uses default if not provided.
            logger: Optional structlog logger. Uses default if not provided.
        """
        self.config = config
        self._tracer = tracer or get_tracer()
        self._logger = logger or get_logger()
        self._catalog: RestCatalog | None = None
        self._lock = threading.Lock()
        self._token_expiry: float | None = None
        self._circuit_breaker = CircuitBreaker(config.retry.circuit_breaker_threshold)

        # Create retry decorator from config
        self._retry = create_retry_decorator(
            config.retry,
            operation_name="catalog_operation",
            circuit_breaker=self._circuit_breaker,
        )

        # Initialize connection
        self._connect()

    def _connect(self) -> None:
        """Establish connection to the Polaris catalog.

        Raises:
            CatalogConnectionError: If connection fails.
            CatalogAuthenticationError: If authentication fails.
        """
        with catalog_operation(
            "connect",
            uri=self.config.uri,
            warehouse=self.config.warehouse,
        ):
            try:
                catalog_properties = self._build_catalog_properties()
                self._catalog = RestCatalog(
                    name="polaris",
                    **catalog_properties,
                )
                self._logger.info(
                    "catalog_connected",
                    uri=self.config.uri,
                    warehouse=self.config.warehouse,
                )
            except Exception as exc:
                self._handle_connection_error(exc)

    def _build_catalog_properties(self) -> dict[str, Any]:
        """Build PyIceberg catalog properties from config.

        Returns:
            Dictionary of catalog properties for RestCatalog.
        """
        properties: dict[str, Any] = {
            "uri": self.config.uri,
            "warehouse": self.config.warehouse,
        }

        # OAuth2 client credentials flow
        if self.config.client_id and self.config.client_secret:
            properties["credential"] = (
                f"{self.config.client_id}:{self.config.client_secret.get_secret_value()}"
            )
            properties["scope"] = self.config.scope

        # Bearer token authentication
        elif self.config.token:
            properties["token"] = self.config.token.get_secret_value()

        # Access delegation mode
        properties["header.X-Iceberg-Access-Delegation"] = self.config.access_delegation

        # S3 FileIO properties (for S3-compatible storage like LocalStack/MinIO)
        # These override any server-side configuration from the REST catalog
        if self.config.s3_endpoint:
            # Force PyArrow FileIO to use our client-side S3 configuration
            # This is critical for local testing where the catalog server uses
            # Docker-internal hostnames (e.g., localstack:4566) but the client
            # needs localhost:4566
            properties["py-io-impl"] = "pyiceberg.io.pyarrow.PyArrowFileIO"
            properties["s3.endpoint"] = self.config.s3_endpoint
            properties["s3.path-style-access"] = str(self.config.s3_path_style_access).lower()
            properties["s3.region"] = self.config.s3_region

            # Static S3 credentials (if not using vended credentials)
            if self.config.s3_access_key_id:
                properties["s3.access-key-id"] = self.config.s3_access_key_id
            if self.config.s3_secret_access_key:
                properties["s3.secret-access-key"] = (
                    self.config.s3_secret_access_key.get_secret_value()
                )

        return properties

    def _handle_connection_error(self, exc: Exception) -> None:
        """Convert PyIceberg exceptions to floe-polaris exceptions.

        Args:
            exc: The original exception.

        Raises:
            CatalogAuthenticationError: If authentication failed.
            CatalogConnectionError: For other connection failures.
        """
        error_msg = str(exc).lower()

        if "401" in error_msg or "unauthorized" in error_msg or "authentication" in error_msg:
            self._logger.error(
                "catalog_authentication_failed",
                uri=self.config.uri,
                error=str(exc),
            )
            raise CatalogAuthenticationError(
                f"Authentication failed: {exc}",
                client_id=self.config.client_id,
                scope=self.config.scope,
            ) from exc

        self._logger.error(
            "catalog_connection_failed",
            uri=self.config.uri,
            error=str(exc),
        )
        raise CatalogConnectionError(
            "Failed to connect to catalog",
            uri=self.config.uri,
            cause=str(exc),
        ) from exc

    def _ensure_connected(self) -> RestCatalog:
        """Ensure catalog is connected and return the inner catalog.

        Returns:
            The underlying RestCatalog.

        Raises:
            CatalogConnectionError: If not connected and reconnection fails.
        """
        with self._lock:
            if self._catalog is None:
                self._connect()

            # Check token refresh
            if self.config.token_refresh_enabled and self._should_refresh_token():
                self._refresh_token()

            if self._catalog is None:
                raise CatalogConnectionError(
                    "Catalog connection not established",
                    uri=self.config.uri,
                )
            return self._catalog

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed.

        Returns:
            True if token should be refreshed (within 5 minutes of expiry).
        """
        if self._token_expiry is None:
            return False
        # Refresh if within 5 minutes of expiry
        return time.time() > (self._token_expiry - 300)

    def _refresh_token(self) -> None:
        """Refresh the authentication token.

        This reconnects to the catalog to obtain a fresh token.
        """
        self._logger.debug("token_refresh_started")
        self._catalog = None
        self._connect()
        self._logger.info("token_refreshed")

    @property
    def inner_catalog(self) -> Catalog:
        """Access the underlying PyIceberg Catalog object.

        Returns:
            The wrapped PyIceberg Catalog.
        """
        return self._ensure_connected()

    def is_connected(self) -> bool:
        """Check if catalog connection is active.

        Returns:
            True if connected to catalog.
        """
        return self._catalog is not None

    def reconnect(self) -> None:
        """Force reconnection to catalog (refreshes token).

        Raises:
            CatalogConnectionError: If reconnection fails.
        """
        with self._lock:
            self._catalog = None
            self._circuit_breaker.reset()
            self._connect()

    # ==================== Namespace Operations ====================

    def create_namespace(
        self,
        namespace: str | tuple[str, ...],
        properties: dict[str, str] | None = None,
        *,
        create_parents: bool = True,
    ) -> NamespaceInfo:
        """Create a namespace in the catalog.

        Args:
            namespace: Namespace name (string or tuple for nested).
            properties: Optional namespace properties.
            create_parents: If True, create parent namespaces if they don't exist.

        Returns:
            NamespaceInfo: Created namespace information.

        Raises:
            NamespaceExistsError: If namespace already exists.
            CatalogConnectionError: If catalog is unreachable.

        Example:
            >>> catalog.create_namespace("bronze.raw", {"owner": "data_team"})
            NamespaceInfo(name='bronze.raw', properties={'owner': 'data_team'})
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)
        props = properties or {}

        with catalog_operation("create_namespace", namespace=ns_str):
            catalog = self._ensure_connected()

            # Create parent namespaces if requested
            if create_parents and len(ns_tuple) > 1:
                for i in range(1, len(ns_tuple)):
                    parent = ns_tuple[:i]
                    try:
                        catalog.create_namespace(parent)
                        self._logger.debug("parent_namespace_created", namespace=".".join(parent))
                    except PyIcebergNamespaceExistsError:
                        pass  # Parent already exists

            try:
                catalog.create_namespace(ns_tuple, props)
                self._logger.info("namespace_created", namespace=ns_str, properties=props)
                return NamespaceInfo(name=ns_str, properties=props)
            except PyIcebergNamespaceExistsError as exc:
                raise NamespaceExistsError(ns_str) from exc

    def create_namespace_if_not_exists(
        self,
        namespace: str | tuple[str, ...],
        properties: dict[str, str] | None = None,
    ) -> NamespaceInfo:
        """Create namespace if it doesn't exist (idempotent).

        Args:
            namespace: Namespace name.
            properties: Optional namespace properties.

        Returns:
            NamespaceInfo: Namespace information (created or existing).
        """
        try:
            return self.create_namespace(namespace, properties)
        except NamespaceExistsError:
            return self.load_namespace(namespace)

    def list_namespaces(
        self,
        parent: str | tuple[str, ...] | None = None,
    ) -> list[NamespaceInfo]:
        """List namespaces in the catalog.

        Args:
            parent: Optional parent namespace to list children of.
                If None, lists top-level namespaces.

        Returns:
            List of NamespaceInfo objects.

        Example:
            >>> catalog.list_namespaces()
            [NamespaceInfo(name='bronze'), NamespaceInfo(name='silver')]
        """
        parent_tuple = self._normalize_namespace(parent) if parent else ()
        parent_str = ".".join(parent_tuple) if parent_tuple else None

        with catalog_operation("list_namespaces", namespace=parent_str):
            catalog = self._ensure_connected()
            # PyIceberg expects empty tuple for top-level, not None
            namespaces = catalog.list_namespaces(parent_tuple)

            result = []
            for ns in namespaces:
                ns_name = ".".join(ns) if isinstance(ns, tuple) else ns
                result.append(NamespaceInfo(name=ns_name))

            self._logger.debug("namespaces_listed", parent=parent_str, count=len(result))
            return result

    def load_namespace(
        self,
        namespace: str | tuple[str, ...],
    ) -> NamespaceInfo:
        """Load namespace information.

        Args:
            namespace: Namespace name.

        Returns:
            NamespaceInfo: Namespace information with properties.

        Raises:
            NamespaceNotFoundError: If namespace doesn't exist.
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)

        with catalog_operation("load_namespace", namespace=ns_str):
            catalog = self._ensure_connected()
            try:
                props = catalog.load_namespace_properties(ns_tuple)
                return NamespaceInfo(name=ns_str, properties=dict(props))
            except PyIcebergNamespaceNotFoundError as exc:
                raise NamespaceNotFoundError(ns_str) from exc

    def drop_namespace(
        self,
        namespace: str | tuple[str, ...],
    ) -> None:
        """Drop an empty namespace.

        Args:
            namespace: Namespace name to drop.

        Raises:
            NamespaceNotEmptyError: If namespace contains tables.
            NamespaceNotFoundError: If namespace doesn't exist.
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)

        with catalog_operation("drop_namespace", namespace=ns_str):
            catalog = self._ensure_connected()
            try:
                catalog.drop_namespace(ns_tuple)
                self._logger.info("namespace_dropped", namespace=ns_str)
            except PyIcebergNamespaceNotEmptyError as exc:
                raise NamespaceNotEmptyError(ns_str) from exc
            except PyIcebergNamespaceNotFoundError as exc:
                raise NamespaceNotFoundError(ns_str) from exc

    def update_namespace_properties(
        self,
        namespace: str | tuple[str, ...],
        updates: dict[str, str] | None = None,
        removals: set[str] | None = None,
    ) -> NamespaceInfo:
        """Update namespace properties.

        Args:
            namespace: Namespace name.
            updates: Properties to add or update.
            removals: Property keys to remove.

        Returns:
            Updated NamespaceInfo.

        Raises:
            NamespaceNotFoundError: If namespace doesn't exist.
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)

        with catalog_operation("update_namespace_properties", namespace=ns_str):
            catalog = self._ensure_connected()
            try:
                catalog.update_namespace_properties(
                    ns_tuple,
                    updates=updates or {},
                    removals=removals or set(),
                )
                self._logger.info(
                    "namespace_properties_updated",
                    namespace=ns_str,
                    updates=updates,
                    removals=list(removals) if removals else None,
                )
                return self.load_namespace(namespace)
            except PyIcebergNamespaceNotFoundError as exc:
                raise NamespaceNotFoundError(ns_str) from exc

    # ==================== Table Operations ====================

    def load_table(
        self,
        identifier: str,
    ) -> Table:
        """Load an Iceberg table.

        Args:
            identifier: Table identifier (namespace.table).

        Returns:
            PyIceberg Table object.

        Raises:
            TableNotFoundError: If table doesn't exist.
        """
        with catalog_operation("load_table", table=identifier):
            catalog = self._ensure_connected()
            try:
                table = catalog.load_table(identifier)
                self._logger.debug("table_loaded", table=identifier)
                return cast("Table", table)
            except PyIcebergTableNotFoundError as exc:
                raise TableNotFoundError(identifier) from exc

    def table_exists(
        self,
        identifier: str,
    ) -> bool:
        """Check if a table exists.

        Args:
            identifier: Table identifier.

        Returns:
            True if table exists.
        """
        with catalog_operation("table_exists", table=identifier):
            catalog = self._ensure_connected()
            try:
                catalog.load_table(identifier)
                return True
            except PyIcebergTableNotFoundError:
                return False

    def list_tables(
        self,
        namespace: str | tuple[str, ...],
    ) -> list[str]:
        """List tables in a namespace.

        Args:
            namespace: Namespace name.

        Returns:
            List of fully qualified table names.
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)

        with catalog_operation("list_tables", namespace=ns_str):
            catalog = self._ensure_connected()
            tables = catalog.list_tables(ns_tuple)
            # Convert identifiers to strings
            result = [".".join(t) if isinstance(t, tuple) else str(t) for t in tables]
            self._logger.debug("tables_listed", namespace=ns_str, count=len(result))
            return result

    # ==================== Helper Methods ====================

    @staticmethod
    def _normalize_namespace(namespace: str | tuple[str, ...] | None) -> tuple[str, ...]:
        """Normalize namespace to tuple format.

        Args:
            namespace: Namespace as string or tuple.

        Returns:
            Namespace as tuple of strings.
        """
        if namespace is None:
            return ()
        if isinstance(namespace, str):
            return tuple(namespace.split("."))
        return namespace
