class ShopkeeperError(Exception):
    """Base exception for the project."""

class DataLoadError(ShopkeeperError):
    """Raised when JSON / data files cannot be loaded."""
