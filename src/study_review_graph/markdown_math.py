"""Small helpers for renderable Markdown math output."""

from __future__ import annotations

import re


def inline_math(expression: str) -> str:
    """Render an expression as inline Markdown math."""

    return f"${expression_to_latex(expression)}$"


def display_math(expression: str) -> str:
    """Render an expression as display Markdown math."""

    return f"$$\n{expression_to_latex(expression)}\n$$"


def symbol_math(symbol: str) -> str:
    """Render a symbol as inline Markdown math."""

    return inline_math(symbol)


def expression_to_latex(expression: str) -> str:
    """Convert a simple formula string into readable LaTeX-like math."""

    latex = expression.strip()
    if not latex:
        return latex

    latex = re.sub(r"([A-Za-z])_([A-Za-z0-9]+)", r"\1_{\2}", latex)
    latex = re.sub(r"(?<!\{)(\b\d+)\s*/\s*(\d+)(?!\})", r"\\frac{\1}{\2}", latex)
    latex = latex.replace("*", r" \cdot ")
    latex = re.sub(r"\s+", " ", latex)
    return latex.strip()
