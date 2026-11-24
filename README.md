# py_single_deny_filter

A `logging.Filter` that drops log records whose logger name contains one
configured substring.

```python
import logging

from py_single_deny_filter import SingleDenyFilter

handler = logging.StreamHandler()
handler.addFilter(SingleDenyFilter("urllib3"))

logging.basicConfig(handlers=[handler], level=logging.DEBUG)
logging.getLogger("myapp").info("kept")
logging.getLogger("urllib3.connectionpool").info("dropped")
```

## Why this exists

Third-party libraries often log through a shared root logger, so muting one
noisy library normally means raising the level for the whole application or
reaching for `logging.disable`, which is process-wide. This filter is attached
to a single handler instead. One handler can stay quiet about a known-noisy
namespace while a second handler still captures the full stream for
diagnostics.

The trade-off is that the filter holds exactly one substring. Supporting a
list of patterns would mean deciding on ordering, precedence, and whether an
allow pattern can override a deny pattern, and none of those decisions have an
obvious right answer. One substring keeps the predicate small enough to leave
attached to every record without thinking about it. If you need more, add a
second filter to the same handler; filters compose with `and`.

## The awkward edge

The filter matches `record.name` with a plain case-sensitive `in` check. That
means a filter for `"urllib3"` also denies `"myapp.urllib3_shim"`, and it does
not deny `"Urllib3"`. Both behaviours are deliberate: logger names are
case-sensitive identifiers, and a substring match is what the name promises.
If you need a prefix match, use `logging.Filter("urllib3")` directly.

An empty substring is allowed and denies every record. That is a supported way
to mute a handler completely, not an oversight.

## API

The package exports one name:

- `SingleDenyFilter(denied_substring: str)` — a subclass of `logging.Filter`.
  Its `filter(record)` method returns `False` when `denied_substring` appears
  in `record.name`, and `True` otherwise. A non-`str` argument raises
  `TypeError` at construction.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

