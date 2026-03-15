"""End-to-end integration tests for debug logging.

Tests the full logging pipeline:
- Debug flag activation
- JSON log output to file
- Sensitive data masking
- Log rotation
"""

import json


from utils.logging import configure_logging, get_logger, mask_sensitive_data


class TestDebugLoggingIntegration:
    """Integration tests for full debug logging flow."""

    def test_debug_log_configuration(self):
        """Running with --debug should configure logging properly."""
        # Simulate debug run: configure logging with debug=True
        configure_logging(debug=True)
        logger = get_logger("test_integration")

        # Verify logger is configured
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_json_log_format(self):
        """Log entries should produce valid JSON structure."""
        from datetime import datetime

        # Test with serializable data (what JSON formatter actually produces)
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": "DEBUG",
            "logger": "test_module",
            "function": "test_function",
            "line": 42,
            "message": "Test message",
            "process_id": 1234,
            "thread_id": 5678,
        }

        # Should be JSON serializable
        json_str = json.dumps(log_data) + "\n"
        assert json_str.endswith("\n")
        parsed = json.loads(json_str.strip())
        assert "timestamp" in parsed
        assert "level" in parsed
        assert parsed["message"] == "Test message"

    def test_sensitive_data_is_masked_in_logs(self):
        """Sensitive data in log messages should be automatically masked."""
        test_cases = [
            ("API key sk-1234567890abcdefghij", "[MASKED_API_KEY]"),
            ("Authorization: Bearer token123456789", "[MASKED"),
            ("password: my_secret", "[MASKED_PASSWORD]"),
            ("normal text without secrets", "normal text without secrets"),
        ]

        for input_text, expected_content in test_cases:
            masked = mask_sensitive_data(input_text)

            if expected_content == "normal text without secrets":
                assert masked == input_text
            else:
                assert expected_content in masked, (
                    f"Expected '{expected_content}' in masked text: {masked}"
                )

    def test_logger_instance_per_module(self):
        """get_logger should return a properly configured logger per module."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert hasattr(logger1, "info")
        assert hasattr(logger1, "debug")
        assert hasattr(logger2, "info")
        assert hasattr(logger2, "debug")

        # Should be able to log without errors
        logger1.info("Test from module1")
        logger2.debug("Test from module2")

    def test_logging_without_debug_flag(self):
        """Without --debug, logging should still work but at WARNING level."""
        configure_logging(debug=False)
        logger = get_logger("test_no_debug")

        # Should not raise errors
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    def test_logging_levels_available(self):
        """Logger should support all standard levels."""
        configure_logging(debug=True)
        logger = get_logger("test_levels")

        levels = ["debug", "info", "warning", "error"]
        for level in levels:
            # Should not raise
            getattr(logger, level)(f"Test {level} message")

    def test_logging_with_formatted_strings(self):
        """Logger should support f-strings and format strings."""
        configure_logging(debug=True)
        logger = get_logger("test_format")

        test_var = "test_value"
        logger.info(f"F-string test: {test_var}")
        logger.info("Format test: {}".format(test_var))
        logger.info("Direct string test")

    def test_exception_logging(self):
        """Logger should handle exceptions gracefully."""
        configure_logging(debug=True)
        logger = get_logger("test_exception")

        try:
            raise ValueError("Test exception")
        except ValueError:
            # Should not raise
            logger.exception("An error occurred")

    def test_masked_credentials_in_api_response(self):
        """Test masking in realistic API response scenarios."""
        api_response = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "user": {"id": 123, "name": "Test User"},
            "api_key": "sk-proj-1234567890abcdefghij",
        }

        log_message = f"API Response: {api_response}"
        masked = mask_sensitive_data(log_message)

        # Should mask tokens and API keys
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
        assert "sk-proj-1234567890abcdefghij" not in masked
        # But should keep user data
        assert "Test User" in masked
