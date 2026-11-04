"""Implementation of the single deny substring log filter."""

import logging


class SingleDenyFilter(logging.Filter):
    """A logging filter that rejects records from noisy logger name substrings.

    The filter is intentionally narrow: it holds exactly one substring and
    rejects any record whose ``record.name`` contains that substring. This is
    the common case when a third-party library emits a flood of messages from
    one namespace (for example ``"urllib3.connectionpool"``) and the
    application wants everything else to keep flowing.

    A filter is a better fit than ``logging.disable`` because it can be
    attached to a single handler. That lets one handler stay quiet about a
    noisy library while a second handler still captures the full stream for
    diagnostics.

    The comparison is a plain case-sensitive substring check against
    ``record.name``. It does not inspect the message, the level, or the
    logger's effective level. Keeping the predicate this small makes the
    filter cheap enough to leave attached to every record on a hot path.

    Parameters
    ----------
    denied_substring:
        The substring to look for in ``record.name``. An empty string is
        allowed and matches every record, which is a deliberate way to mute a
        handler entirely. A non-string value raises :class:`TypeError` so a
        typo such as ``SingleDenyFilter(None)`` fails at construction instead
        of silently filtering nothing.

    Raises
    ------
    TypeError
        If ``denied_substring`` is not a ``str``.

    Examples
    --------
    >>> import logging
    >>> handler = logging.StreamHandler()
    >>> handler.addFilter(SingleDenyFilter("urllib3"))
    >>> logging.getLogger("urllib3.connectionpool").warning("hidden")
    >>> logging.getLogger("myapp").warning("shown")
    """

    __slots__ = ("denied_substring",)

    def __init__(self, denied_substring: str) -> None:
        # logging.Filter.__init__ accepts a name argument that performs a
        # prefix match on the logger name. We deliberately do not use it: a
        # prefix match on "urllib3" would also match "urllib3x", and the
        # brief calls for a substring match. Calling super() with no argument
        # leaves Filter.name empty and keeps its behaviour out of the way.
        super().__init__()
        if not isinstance(denied_substring, str):
            raise TypeError(
                "denied_substring must be a str, got "
                f"{type(denied_substring).__name__}"
            )
        self.denied_substring = denied_substring

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``False`` when ``record.name`` contains the deny substring.

        A return value of ``False`` tells the logging machinery to drop the
        record for whichever handler this filter is attached to. A ``True``
        return lets the record through.

        The check is case-sensitive because logger names are case-sensitive
        identifiers in the logging hierarchy; folding case here would make the
        filter surprise people who deliberately distinguish ``Foo`` and
        ``foo``.
        """
        return self.denied_substring not in record.name

    def __repr__(self) -> str:
        # A useful repr matters when filters are printed while debugging a
        # logging configuration; the default object repr hides the one piece
        # of state that explains the filter's behaviour.
        return f"{type(self).__name__}({self.denied_substring!r})"
