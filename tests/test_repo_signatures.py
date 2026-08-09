"""Structural enforcement of the isolation rule: every repository method takes user_id.

The single exemption is UserRepository, whose email-lookup and profile-list methods are
inherently pre-identity (they exist to establish who the user is). Everything else must
take `user_id` as its first parameter.
"""
from __future__ import annotations

import inspect

import app.repositories.audit
import app.repositories.ledger
import app.repositories.users

EXEMPT_CLASSES = {"UserRepository"}
MODULES = [app.repositories.ledger, app.repositories.audit, app.repositories.users]


def _repository_classes():
    for module in MODULES:
        for name, cls in vars(module).items():
            if inspect.isclass(cls) and name.endswith("Repository") \
                    and cls.__module__ == module.__name__:
                yield name, cls


def test_every_repository_method_is_user_scoped():
    checked = 0
    for cls_name, cls in _repository_classes():
        if cls_name in EXEMPT_CLASSES:
            continue
        for meth_name, meth in inspect.getmembers(cls, inspect.isfunction):
            if meth_name.startswith("_"):
                continue
            params = list(inspect.signature(meth).parameters)
            assert params[:2] == ["self", "user_id"], (
                f"{cls_name}.{meth_name} must take user_id as its first parameter; "
                f"got {params}"
            )
            checked += 1
    assert checked >= 10, "signature audit found suspiciously few repository methods"
