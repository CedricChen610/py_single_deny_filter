"""Public API for py_single_deny_filter.

Exports :class:`SingleDenyFilter`, a :class:`logging.Filter` that drops log
records whose logger name contains a single configured substring.
"""

from .core import SingleDenyFilter

__all__ = ["SingleDenyFilter"]
