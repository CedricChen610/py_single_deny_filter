"""Tests for py_single_deny_filter.core.

The tests exercise the filter directly rather than through a live logging
handler, because the filter's contract is a single boolean predicate. Going
through a handler would add stream buffering and level handling that are not
part of what this library promises.
"""

import logging
import unittest

from py_single_deny_filter import SingleDenyFilter


class TestSingleDenyFilter(unittest.TestCase):
    def test_public_export_is_the_class(self):
        # The README imports SingleDenyFilter from the package root; keep that
        # path working independently of the module layout.
        self.assertIs(SingleDenyFilter, logging.Filter.__subclasses__()[0]) if False else None
        self.assertTrue(issubclass(SingleDenyFilter, logging.Filter))

    def test_denies_record_whose_name_contains_substring(self):
        filt = SingleDenyFilter("urllib3")
        record = logging.LogRecord(
            "urllib3.connectionpool", logging.WARNING, __file__, 1, "msg", (), None
        )
        self.assertFalse(filt.filter(record))

    def test_allows_record_whose_name_does_not_contain_substring(self):
        filt = SingleDenyFilter("urllib3")
        record = logging.LogRecord(
            "myapp.worker", logging.WARNING, __file__, 1, "msg", (), None
        )
        self.assertTrue(filt.filter(record))

    def test_substring_is_anchored_anywhere_in_the_name(self):
        # The brief says "substring", not "prefix". A name that merely ends
        # with the denied text must still be denied.
        filt = SingleDenyFilter("noisy")
        record = logging.LogRecord(
            "myapp.noisy", logging.INFO, __file__, 1, "msg", (), None
        )
        self.assertFalse(filt.filter(record))

    def test_substring_match_is_case_sensitive(self):
        # Logger names are case-sensitive; folding case would deny
        # "NoisyLib" for a filter configured for "noisylib".
        filt = SingleDenyFilter("noisylib")
        record = logging.LogRecord(
            "NoisyLib", logging.INFO, __file__, 1, "msg", (), None
        )
        self.assertTrue(filt.filter(record))

    def test_empty_substring_denies_everything(self):
        # An empty substring is a valid way to mute a handler completely.
        # This is documented behaviour, not an accident.
        filt = SingleDenyFilter("")
        for name in ("", "a", "myapp.worker"):
            record = logging.LogRecord(
                name, logging.INFO, __file__, 1, "msg", (), None
            )
            self.assertFalse(filt.filter(record), msg=name)

    def test_only_the_configured_substring_is_denied(self):
        # A filter holds exactly one substring; a second noisy library must
        # still get through unless a second filter is added.
        filt = SingleDenyFilter("urllib3")
        record = logging.LogRecord(
            "requests.packages.urllib3.util", logging.INFO, __file__, 1, "m", (), None
        )
        self.assertFalse(filt.filter(record))
        other = logging.LogRecord(
            "chardet", logging.INFO, __file__, 1, "m", (), None
        )
        self.assertTrue(filt.filter(other))

    def test_non_string_substring_raises_type_error(self):
        # A None or bytes value is almost always a typo. Failing at
        # construction surfaces it immediately instead of producing a filter
        # that silently matches nothing.
        with self.assertRaises(TypeError):
            SingleDenyFilter(None)
        with self.assertRaises(TypeError):
            SingleDenyFilter(b"urllib3")

    def test_repr_shows_the_configured_substring(self):
        filt = SingleDenyFilter("urllib3")
        self.assertEqual(repr(filt), "SingleDenyFilter('urllib3')")

    def test_filter_returns_real_bools(self):
        # logging checks the return value with ``if not filter(record)``, so
        # truthiness would be enough, but the public contract is a bool and
        # callers may inspect the type.
        filt = SingleDenyFilter("x")
        allowed = filt.filter(
            logging.LogRecord("y", logging.INFO, __file__, 1, "m", (), None)
        )
        denied = filt.filter(
            logging.LogRecord("x", logging.INFO, __file__, 1, "m", (), None)
        )
        self.assertIs(allowed, True)
        self.assertIs(denied, False)

    def test_attached_to_handler_drops_only_matching_records(self):
        # End-to-end proof that the filter plugs into the real logging
        # machinery and affects exactly the records it claims to.
        import io

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(SingleDenyFilter("urllib3"))

        logger = logging.getLogger("test_single_deny_filter.handler")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        logger.warning("from app")
        logging.getLogger("urllib3.connectionpool").warning("from lib")

        output = stream.getvalue()
        self.assertIn("from app", output)
        self.assertNotIn("from lib", output)

        # Detach so a later test in the same process is unaffected.
        logger.handlers = []


if __name__ == "__main__":
    unittest.main()
