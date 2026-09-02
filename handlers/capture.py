"""Mock capture command handler."""

from flask import current_app


def handle_capture(message: str) -> None:
    """Handle a capture request; camera control will be added later."""
    current_app.logger.info("Capture command received")
