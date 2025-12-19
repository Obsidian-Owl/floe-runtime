"""Custom exceptions for floe-polaris.

This module defines the exception hierarchy:
- FloeStorageError (base)
- CatalogConnectionError
- CatalogAuthenticationError
- NamespaceExistsError
- NamespaceNotFoundError
- NamespaceNotEmptyError
- TableNotFoundError
"""

from __future__ import annotations


class FloeStorageError(Exception):
    """Base exception for all floe storage operations.

    This is the root exception class for both floe-polaris and floe-iceberg
    packages. All storage-related exceptions inherit from this class.

    Attributes:
        message: Human-readable error description.
        details: Optional additional context about the error.

    Example:
        >>> try:
        ...     catalog.load_table("nonexistent.table")
        ... except FloeStorageError as e:
        ...     print(f"Storage error: {e}")
    """

    def __init__(self, message: str, *, details: dict[str, str] | None = None) -> None:
        """Initialize FloeStorageError.

        Args:
            message: Human-readable error description.
            details: Optional additional context about the error.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation with details if present."""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class CatalogConnectionError(FloeStorageError):
    """Failed to connect to the Polaris catalog.

    Raised when:
    - Network connectivity issues prevent reaching the catalog
    - The catalog endpoint is unreachable or times out
    - SSL/TLS handshake fails

    Example:
        >>> try:
        ...     catalog = create_catalog(config)
        ... except CatalogConnectionError as e:
        ...     print(f"Cannot connect: {e}")
    """

    def __init__(
        self,
        message: str = "Failed to connect to catalog",
        *,
        uri: str | None = None,
        cause: str | None = None,
    ) -> None:
        """Initialize CatalogConnectionError.

        Args:
            message: Human-readable error description.
            uri: The catalog URI that was unreachable.
            cause: The underlying cause of the connection failure.
        """
        details: dict[str, str] = {}
        if uri:
            details["uri"] = uri
        if cause:
            details["cause"] = cause
        super().__init__(message, details=details)
        self.uri = uri
        self.cause = cause


class CatalogAuthenticationError(FloeStorageError):
    """Authentication to the Polaris catalog failed.

    Raised when:
    - OAuth2 client credentials are invalid
    - Token has expired and refresh fails
    - Insufficient permissions for the requested operation

    Security:
        This exception intentionally does NOT expose sensitive details like
        client_id or scope in error messages to prevent information leakage.
        These details are logged internally but not included in the exception.

    Example:
        >>> try:
        ...     catalog = create_catalog(invalid_config)
        ... except CatalogAuthenticationError as e:
        ...     print(f"Auth failed: {e}")
    """

    def __init__(
        self,
        message: str = "Authentication failed",
    ) -> None:
        """Initialize CatalogAuthenticationError.

        Args:
            message: Human-readable error description.

        Note:
            For security reasons, client_id and scope are not included in
            the exception to prevent sensitive information leakage.
        """
        # Security: Do not include client_id or scope in details
        super().__init__(message, details={})


class NamespaceExistsError(FloeStorageError):
    """Namespace already exists in the catalog.

    Raised when attempting to create a namespace that already exists
    (when not using the idempotent create_namespace_if_not_exists method).

    Example:
        >>> try:
        ...     catalog.create_namespace("bronze")  # Already exists
        ... except NamespaceExistsError as e:
        ...     print(f"Namespace exists: {e.namespace}")
    """

    def __init__(
        self,
        namespace: str,
        message: str | None = None,
    ) -> None:
        """Initialize NamespaceExistsError.

        Args:
            namespace: The namespace that already exists.
            message: Optional custom error message.
        """
        msg = message or f"Namespace already exists: {namespace}"
        super().__init__(msg, details={"namespace": namespace})
        self.namespace = namespace


class NamespaceNotFoundError(FloeStorageError):
    """Namespace not found in the catalog.

    Raised when attempting to access a namespace that does not exist.

    Example:
        >>> try:
        ...     catalog.load_namespace("nonexistent")
        ... except NamespaceNotFoundError as e:
        ...     print(f"Namespace not found: {e.namespace}")
    """

    def __init__(
        self,
        namespace: str,
        message: str | None = None,
    ) -> None:
        """Initialize NamespaceNotFoundError.

        Args:
            namespace: The namespace that was not found.
            message: Optional custom error message.
        """
        msg = message or f"Namespace not found: {namespace}"
        super().__init__(msg, details={"namespace": namespace})
        self.namespace = namespace


class NamespaceNotEmptyError(FloeStorageError):
    """Cannot drop a namespace that contains tables.

    Raised when attempting to drop a namespace that still has tables.
    Tables must be dropped first before the namespace can be removed.

    Example:
        >>> try:
        ...     catalog.drop_namespace("bronze")  # Has tables
        ... except NamespaceNotEmptyError as e:
        ...     print(f"Namespace has tables: {e.namespace}")
    """

    def __init__(
        self,
        namespace: str,
        message: str | None = None,
    ) -> None:
        """Initialize NamespaceNotEmptyError.

        Args:
            namespace: The namespace that is not empty.
            message: Optional custom error message.
        """
        msg = message or f"Namespace is not empty: {namespace}"
        super().__init__(msg, details={"namespace": namespace})
        self.namespace = namespace


class TableNotFoundError(FloeStorageError):
    """Table not found in the catalog.

    Raised when attempting to access a table that does not exist.

    Example:
        >>> try:
        ...     catalog.load_table("bronze.nonexistent")
        ... except TableNotFoundError as e:
        ...     print(f"Table not found: {e.table}")
    """

    def __init__(
        self,
        table: str,
        message: str | None = None,
    ) -> None:
        """Initialize TableNotFoundError.

        Args:
            table: The table identifier that was not found.
            message: Optional custom error message.
        """
        msg = message or f"Table not found: {table}"
        super().__init__(msg, details={"table": table})
        self.table = table
