"""Migration-graph sanity checks (DB-free).

Guards the class of bug where a second Alembic head (or a broken chain) silently
makes `alembic upgrade head` ambiguous or a no-op on deploy.
"""

from __future__ import annotations

import os

from alembic.config import Config
from alembic.script import ScriptDirectory

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _script_directory() -> ScriptDirectory:
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(_BACKEND, "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_single_migration_head():
    """Exactly one head — otherwise `upgrade head` is ambiguous."""
    assert len(_script_directory().get_heads()) == 1


def test_migration_chain_is_linear_and_includes_new_revisions():
    script = _script_directory()
    revisions = list(script.walk_revisions())  # head -> base; raises if multiple heads

    # Every revision links to at most one parent (a linear chain).
    for rev in revisions:
        assert rev.down_revision is None or isinstance(rev.down_revision, str)

    ids = {rev.revision for rev in revisions}
    assert "004_waitlist" in ids
    assert "005_fix_enum_lengths" in ids

    # The base is reachable (exactly one revision with no parent).
    roots = [r for r in revisions if r.down_revision is None]
    assert len(roots) == 1
