"""Sphinx configuration for debug-toolbar documentation."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = "Async Debug Toolbar"
copyright = "2024, Jacob Coffee"
author = "Jacob Coffee"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "shibuya"
html_static_path = ["_static"]

html_theme_options = {
    "accent_color": "violet",
    "github_url": "https://github.com/JacobCoffee/async-python-debug-toolbar",
    "nav_links": [
        {"title": "Litestar", "url": "https://litestar.dev"},
        {"title": "PyPI", "url": "https://pypi.org/project/debug-toolbar"},
    ],
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "litestar": ("https://docs.litestar.dev/latest/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

autosummary_generate = True
autosummary_imported_members = False

suppress_warnings = [
    "myst.xref_missing",
    "ref.duplicate_object",
]

nitpicky = False
napoleon_google_docstring = True
napoleon_numpy_docstring = False

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
