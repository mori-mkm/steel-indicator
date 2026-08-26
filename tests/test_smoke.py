"""Smoke test: confirm indices_setoriais imports cleanly under pytest."""


def test_import_indices_setoriais():
    import indices_setoriais  # noqa: F401


def test_import_reporting_report_builder():
    import reporting.report_builder  # noqa: F401
