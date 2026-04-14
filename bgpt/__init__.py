"""
Bgpt - Advanced AI Shell Command Assistant

A next-generation command-line AI assistant that transforms natural language
into powerful shell commands with enterprise-grade safety features.
"""

__version__ = "1.0.0"
__author__ = "Bgpt Development Team"
__email__ = "hello@bgpt.dev"

__all__ = ["Bgpt", "__version__", "__author__", "__email__"]


def __getattr__(name: str):
	"""Lazy attribute access to avoid importing CLI modules on package import."""
	if name == "Bgpt":
		from .main import Bgpt

		return Bgpt
	raise AttributeError(f"module 'bgpt' has no attribute {name!r}")
