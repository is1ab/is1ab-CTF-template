"""Inline YAML fixture strings for setup_helpers / cleanup tests.

We embed these as Python strings (rather than as on-disk private.yml files) so
that the repo's pre-commit hook — which blocks any path containing
``private.yml`` from being committed — does not refuse our test fixtures.
The hook's purpose is to prevent real challenge flags leaking; test fixtures
that intentionally contain placeholder flags need a separate channel.
"""

LEGACY_PRIVATE_YML = """title: Legacy Web
author: alice
reviewer: bob
validation_status: pending
internal_validation_notes: |
  [2026-04-01] bob: pending — 尚未驗題
difficulty: easy
category: web
points: 100
flag: is1abCTF{legacy_test_flag}
hints:
  - level: 1
    cost: 0
    content: hint
"""

LEGACY_PUBLIC_YML = """title: Legacy Web
author: alice
reviewer: bob
validation_status: pending
difficulty: easy
category: web
points: 100
hints:
  - level: 1
    cost: 0
    content: hint
"""

CLEAN_PRIVATE_YML = """title: Clean Web
author: alice
difficulty: easy
category: web
points: 100
flag: is1abCTF{clean_test_flag}
hints:
  - level: 1
    cost: 0
    content: hint
"""

CLEAN_PUBLIC_YML = """title: Clean Web
author: alice
difficulty: easy
category: web
points: 100
hints:
  - level: 1
    cost: 0
    content: hint
"""
