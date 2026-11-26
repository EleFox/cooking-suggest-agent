import logging

from app.core.logging import get_logger, setup_logging


def test_get_logger_returns_logger_with_name():
    logger = get_logger("app.test.module")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "app.test.module"


def test_get_logger_has_configured_level():
    logger = get_logger("app.test.level")

    assert logger.level == logging.INFO


def test_get_logger_does_not_duplicate_handlers():
    first = get_logger("app.test.unique")
    handler_count = len(first.handlers)

    second = get_logger("app.test.unique")

    assert len(second.handlers) == handler_count


def test_logger_propagate_is_false_to_avoid_duplication():
    logger = get_logger("app.test.propagate")

    assert logger.propagate is False


def test_setup_logging_sets_root_level():
    setup_logging(level=logging.WARNING)

    assert logging.getLogger().level == logging.WARNING


def test_logger_emits_record_with_expected_format(capsys):
    logger = get_logger("app.test.format")
    logger.info("hello world")

    captured = capsys.readouterr().out
    assert "hello world" in captured
    assert "app.test.format" in captured
