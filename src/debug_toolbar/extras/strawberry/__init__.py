"""Strawberry GraphQL integration for debug-toolbar.

This module provides GraphQL operation and resolver tracking for
applications using Strawberry GraphQL with the debug toolbar.

Example:
    >>> import strawberry
    >>> from debug_toolbar.extras.strawberry import DebugToolbarExtension, GraphQLPanel
    >>>
    >>> schema = strawberry.Schema(
    ...     query=Query,
    ...     extensions=[DebugToolbarExtension()],
    ... )
    >>>
    >>> # Add GraphQLPanel to toolbar config
    >>> config = DebugToolbarConfig(
    ...     extra_panels=["debug_toolbar.extras.strawberry.GraphQLPanel"],
    ... )
"""

from __future__ import annotations

from debug_toolbar.extras.strawberry.analyzers import DuplicateDetector, N1Analyzer
from debug_toolbar.extras.strawberry.extension import STRAWBERRY_AVAILABLE, DebugToolbarExtension
from debug_toolbar.extras.strawberry.models import TrackedOperation, TrackedResolver
from debug_toolbar.extras.strawberry.panel import GraphQLPanel
from debug_toolbar.extras.strawberry.utils import StackCapture, format_variables, truncate_query

__all__ = [
    "DebugToolbarExtension",
    "DuplicateDetector",
    "GraphQLPanel",
    "N1Analyzer",
    "STRAWBERRY_AVAILABLE",
    "StackCapture",
    "TrackedOperation",
    "TrackedResolver",
    "format_variables",
    "truncate_query",
]
