"""
Advanced transaction management with retry logic.

This module provides transaction management capabilities including
automatic retry for transient failures and proper error handling.
"""

import functools
import logging
import asyncio
from typing import Callable, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, OperationalError

logger = logging.getLogger(__name__)


class TransactionManager:
    """
    Advanced transaction management with retry logic.

    Provides automatic retry for transient database failures with
    exponential backoff and proper error handling.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 0.1):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retriable_errors = [
            "deadlock",
            "timeout",
            "connection",
            "temporary",
            "lock",
            "server closed",
            "connection lost",
            "network",
        ]

    async def execute_with_retry(
        self, session: AsyncSession, operation: Callable, *args, **kwargs
    ) -> Any:
        """
        Execute operation with automatic retry on transient failures.

        Args:
            session: Database session
            operation: Function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            SQLAlchemyError: If operation fails after all retries
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute the operation
                result = await operation(session, *args, **kwargs)

                # If we get here, operation succeeded
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")

                return result

            except SQLAlchemyError as e:
                last_exception = e

                # Check if this is the last attempt
                if attempt >= self.max_retries:
                    logger.error(
                        f"Operation failed after {self.max_retries + 1} attempts: {e}"
                    )
                    await session.rollback()
                    raise

                # Check if error is retriable
                if not self._is_retriable_error(e):
                    logger.error(f"Non-retriable error on attempt {attempt + 1}: {e}")
                    await session.rollback()
                    raise

                # Log retry attempt
                logger.warning(
                    f"Transaction attempt {attempt + 1} failed, retrying in "
                    f"{self.retry_delay * (2 ** attempt):.2f}s: {e}"
                )

                # Rollback and wait before retry
                await session.rollback()
                await asyncio.sleep(self.retry_delay * (2**attempt))

            except Exception as e:
                # Non-SQLAlchemy errors are not retriable
                logger.error(f"Non-retriable error on attempt {attempt + 1}: {e}")
                await session.rollback()
                raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in retry logic")

    def _is_retriable_error(self, error: SQLAlchemyError) -> bool:
        """
        Check if database error is retriable.

        Args:
            error: SQLAlchemy error to check

        Returns:
            bool: True if error is retriable, False otherwise
        """
        # Check for specific error types that are always retriable
        if isinstance(error, (DisconnectionError, OperationalError)):
            return True

        # Check error message for retriable keywords
        error_msg = str(error).lower()
        return any(keyword in error_msg for keyword in self.retriable_errors)


def transactional(
    max_retries: int = 3,
    retry_on_failure: bool = True,
    isolation_level: Optional[str] = None,
):
    """
    Decorator for transactional operations with automatic retry.

    Args:
        max_retries: Maximum number of retry attempts
        retry_on_failure: Whether to retry on transient failures
        isolation_level: Transaction isolation level

    Returns:
        Decorated function with transaction management
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract session from arguments
            session = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break

            if session is None:
                raise ValueError(
                    f"No AsyncSession found in function arguments for {func.__name__}. "
                    "Make sure the first argument is an AsyncSession instance."
                )

            if retry_on_failure:
                # Use transaction manager with retry logic
                tx_manager = TransactionManager(max_retries=max_retries)
                return await tx_manager.execute_with_retry(
                    session, func, *args, **kwargs
                )
            else:
                # Simple transaction without retry
                try:
                    # Set isolation level if specified
                    if isolation_level:
                        await session.execute(
                            f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                        )

                    result = await func(*args, **kwargs)
                    await session.commit()
                    return result

                except Exception as e:
                    logger.error(f"Transaction failed in {func.__name__}: {e}")
                    await session.rollback()
                    raise

        return wrapper

    return decorator


class TransactionContext:
    """
    Context manager for manual transaction management.

    Provides fine-grained control over transaction lifecycle with
    automatic retry capabilities.
    """

    def __init__(
        self, session: AsyncSession, max_retries: int = 3, retry_on_failure: bool = True
    ):
        self.session = session
        self.max_retries = max_retries
        self.retry_on_failure = retry_on_failure
        self.tx_manager = TransactionManager(max_retries=max_retries)
        self._transaction = None

    async def __aenter__(self):
        """Start transaction context"""
        self._transaction = await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End transaction context with proper cleanup"""
        try:
            if exc_type is None:
                # No exception, commit the transaction
                await self._transaction.commit()
            else:
                # Exception occurred, rollback
                await self._transaction.rollback()

                # If it's a retriable error and retry is enabled, reraise for retry
                if (
                    self.retry_on_failure
                    and isinstance(exc_val, SQLAlchemyError)
                    and self.tx_manager._is_retriable_error(exc_val)
                ):
                    logger.debug(f"Retriable error in transaction context: {exc_val}")

            return False  # Don't suppress exceptions

        except Exception as e:
            logger.error(f"Error in transaction context cleanup: {e}")
            await self._transaction.rollback()
            raise

    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation within this transaction context with retry"""
        return await self.tx_manager.execute_with_retry(
            self.session, operation, *args, **kwargs
        )


# Utility functions for common transaction patterns
async def execute_in_transaction(
    session: AsyncSession, operation: Callable, *args, max_retries: int = 3, **kwargs
) -> Any:
    """
    Execute a function within a transaction with retry logic.

    Args:
        session: Database session
        operation: Function to execute
        *args: Arguments for the operation
        max_retries: Maximum retry attempts
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation
    """
    tx_manager = TransactionManager(max_retries=max_retries)
    return await tx_manager.execute_with_retry(session, operation, *args, **kwargs)


async def bulk_operation_with_retry(
    session: AsyncSession, operations: List[Callable], max_retries: int = 3
) -> List[Any]:
    """
    Execute multiple operations in a single transaction with retry.

    Args:
        session: Database session
        operations: List of functions to execute
        max_retries: Maximum retry attempts

    Returns:
        List of operation results
    """

    async def execute_all(session: AsyncSession) -> List[Any]:
        results = []
        for operation in operations:
            if isinstance(operation, tuple):
                func, args, kwargs = operation[0], operation[1], operation[2]
                result = await func(session, *args, **kwargs)
            else:
                result = await operation(session)
            results.append(result)
        return results

    tx_manager = TransactionManager(max_retries=max_retries)
    return await tx_manager.execute_with_retry(session, execute_all)
