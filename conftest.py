import sys
from pathlib import Path

# The repo root contains a legacy taparash/ directory and a root __init__.py,
# both with broken absolute imports.  When pytest adds the repo root to
# sys.path those files shadow the real installed package (taparash_pkg/).
# Remove every entry that resolves to the repo root so the editable-install
# finder (pip install -e .) serves 'taparash' from taparash_pkg/ instead.
_repo_root = str(Path(__file__).parent.resolve())
sys.path = [p for p in sys.path if str(Path(p).resolve()) != _repo_root]
