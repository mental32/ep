# see: http://www.sphinx-doc.org/en/master/config
# -- Path setup --------------------------------------------------------------

import os
import sys
import datetime

sys.path.insert(0, os.path.abspath("../.."))  # sphinx.ext.autodoc

# -- Project information -----------------------------------------------------

project = "ep"
author = "mental"
year = datetime.datetime.today().year
copyright = "%s, %s" % (year, author)
release = "1.0.0"
master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
exclude_patterns = []

todo_include_todos = True

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

napoleon_numpy_docstring = True
napoleon_google_docstring = False

raw_extension_names = [
    "napoleon",
    "autodoc",
    # "doctest",
    "extlinks",
    # "githubpages",
    "intersphinx",
    # "linkcode",
    "todo",
    "viewcode",
]

def _format_ext(name: str) -> str:
    return f"sphinx.ext.{name}"

extensions = list(map(_format_ext, raw_extension_names))

# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_static_path = ["_static"]

html_theme_options = {
    "logo": "/images/logo.png",
    "logo_name": True,
    "logo_text_align": "center",
    "description": "A different kind of discord bot framework",
    "github_user": "mental32",
    "github_repo": "ep",
    "travis_button": True,
    "codecov_button": True,
    "link": "#3782BE",
    "link_hover": "#3782BE",
    # Wide enough that 80-col code snippets aren't truncated on default font
    # settings (at least for bitprophet's Chrome-on-OSX-Yosemite setup)
    "page_width": "1024px",
}
