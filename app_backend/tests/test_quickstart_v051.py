import sys

import quickstart


def test_quickstart_accepts_missing_stack_name(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["quickstart.py"])

    args = quickstart.parse_args()

    assert args.stack_name is None
    assert args.action == "up"


def test_quickstart_accepts_explicit_stack_name(monkeypatch) -> None:
    monkeypatch.setattr(
        sys, "argv", ["quickstart.py", "demo-stack", "--action", "destroy"]
    )

    args = quickstart.parse_args()

    assert args.stack_name == "demo-stack"
    assert args.action == "destroy"
