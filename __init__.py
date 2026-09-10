"""
Compatibility shim loaded when the repo root is imported as the 'taparash'
package.  This happens because the repository is named 'taparash' and Python
treats it as a package when any ancestor directory is in sys.path.

The real source is in taparash_pkg/.  This shim loads that directory
transparently so that 'import taparash' and 'from taparash import X'
always resolve correctly regardless of which __init__.py Python finds first.
"""
import sys
import importlib.util
from pathlib import Path

_repo_root = Path(__file__).parent
_pkg_dir = str(_repo_root / "taparash_pkg")
_pkg_init = str(_repo_root / "taparash_pkg" / "__init__.py")

spec = importlib.util.spec_from_file_location(
    "taparash",
    _pkg_init,
    submodule_search_locations=[_pkg_dir],
)

if spec and spec.loader:
    _module = importlib.util.module_from_spec(spec)
    _module.__path__ = [_pkg_dir]   # lets 'from taparash.core import' find taparash_pkg/core/
    _module.__package__ = "taparash"
    sys.modules["taparash"] = _module
    spec.loader.exec_module(_module)
