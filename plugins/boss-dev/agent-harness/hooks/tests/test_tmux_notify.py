"""Tests for the tmux-aware desktop notification hook (``tmux_notify.py``).

The hook is stdlib-only and must always exit 0. These tests exercise its
pieces in isolation with mocks so they run on any OS with no ``tmux`` /
``terminal-notifier`` / ``notify-send`` present (the Linux CI case):

- ``_flag`` / ``enabled`` — env-var truthiness and the master toggle gate
- ``read_event`` — stdin JSON parsing (incl. malformed / empty)
- ``build_text`` — per-event title/subtitle/message (the v0.10.0 logic)
- ``tmux_context`` — ``$TMUX`` parsing + ``tmux display-message`` argv (mocked)
- ``notify_macos`` / ``notify_linux`` — notifier argv construction (mocked)
- ``main`` — the macOS → Linux → bell fallback chain

One real-server integration test at the bottom uses the libtmux pytest plugin
and is skipped unless a real ``tmux`` binary is available.
"""

from __future__ import annotations

import io
import shutil
from types import SimpleNamespace

import pytest
from hook_loader import load_hook

tmux_notify = load_hook("tmux_notify.py")

TOGGLE = "CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS"
SOUND = "CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_SOUND"
BUNDLE = "CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_ACTIVATE_BUNDLE_ID"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scrub every env var the hook reads so the real shell can't leak in."""
    for var in (TOGGLE, SOUND, BUNDLE, "TMUX", "TMUX_PANE"):
        monkeypatch.delenv(var, raising=False)


class TestFlagAndEnabled:
    @pytest.mark.parametrize("value", ["true", "TRUE", " True ", "1", "yes", "on", "ON"])
    def test_truthy_values(self, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(TOGGLE, value)
        assert tmux_notify._flag(TOGGLE) is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "  ", "nope"])
    def test_falsy_values(self, value: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(TOGGLE, value)
        assert tmux_notify._flag(TOGGLE) is False

    def test_unset_defaults_false(self, clean_env: None) -> None:
        assert tmux_notify._flag(TOGGLE) is False

    def test_enabled_reads_toggle(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        assert tmux_notify.enabled() is False
        monkeypatch.setenv(TOGGLE, "true")
        assert tmux_notify.enabled() is True


class TestReadEvent:
    def test_valid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(tmux_notify.sys, "stdin", io.StringIO('{"message":"hi","session_id":"s1"}'))
        assert tmux_notify.read_event() == {"message": "hi", "session_id": "s1"}

    def test_empty_stdin_returns_empty_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(tmux_notify.sys, "stdin", io.StringIO(""))
        assert tmux_notify.read_event() == {}

    def test_malformed_json_returns_empty_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(tmux_notify.sys, "stdin", io.StringIO("{not json"))
        assert tmux_notify.read_event() == {}


class TestBuildText:
    def test_stopfailure_with_type_and_message(self) -> None:
        title, subtitle, message = tmux_notify.build_text(
            "stopfailure", {"error_type": "overloaded", "error_message": "server busy"}
        )
        assert title == "Claude Code"
        assert subtitle == "Turn failed"
        assert "overloaded: server busy" in message

    def test_stopfailure_without_message_shows_only_type(self) -> None:
        _, subtitle, message = tmux_notify.build_text("stopfailure", {"error_type": "rate_limit"})
        assert subtitle == "Turn failed"
        assert "rate_limit" in message
        assert ":" not in message.split("(", 1)[1]  # no "type: message" form

    def test_stopfailure_missing_type_defaults_unknown(self) -> None:
        _, _, message = tmux_notify.build_text("stopfailure", {})
        assert "unknown" in message

    def test_stop_event(self) -> None:
        title, subtitle, message = tmux_notify.build_text("stop", {})
        assert subtitle == "Response finished"
        assert "ready for your next instruction" in message

    def test_notification_with_message(self) -> None:
        _, subtitle, message = tmux_notify.build_text("notification", {"message": "Approve plan?"})
        assert subtitle == "Waiting for you"
        assert message == "Approve plan?"

    def test_notification_empty_falls_back(self) -> None:
        _, _, message = tmux_notify.build_text("notification", {})
        assert message == "Claude needs your input."


class TestTmuxContext:
    def test_no_tmux_env_returns_none(self, clean_env: None) -> None:
        assert tmux_notify.tmux_context() is None

    def test_tmux_binary_missing_returns_none(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TMUX", "/tmp/sock,1,0")
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: None)
        assert tmux_notify.tmux_context() is None

    def test_happy_path_parses_socket_and_includes_pane(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker
    ) -> None:  # noqa: ANN001
        monkeypatch.setenv("TMUX", "/tmp/sock,123,0")
        monkeypatch.setenv("TMUX_PANE", "%4")
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/tmux")
        run = mocker.patch.object(tmux_notify.subprocess, "run", return_value=SimpleNamespace(stdout="mysession:3\n"))

        ctx = tmux_notify.tmux_context()

        assert ctx == ("/tmp/sock", "mysession:3")
        cmd = run.call_args.args[0]
        assert "-S" in cmd and "/tmp/sock" in cmd
        assert "-t" in cmd and "%4" in cmd

    def test_no_pane_omits_target_flag(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv("TMUX", "/tmp/sock,123,0")
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/tmux")
        run = mocker.patch.object(tmux_notify.subprocess, "run", return_value=SimpleNamespace(stdout="s:0\n"))

        ctx = tmux_notify.tmux_context()

        assert ctx == ("/tmp/sock", "s:0")
        assert "-t" not in run.call_args.args[0]

    def test_empty_stdout_returns_none(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv("TMUX", "/tmp/sock,123,0")
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/tmux")
        mocker.patch.object(tmux_notify.subprocess, "run", return_value=SimpleNamespace(stdout="   \n"))
        assert tmux_notify.tmux_context() is None

    def test_subprocess_error_returns_none(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv("TMUX", "/tmp/sock,123,0")
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/tmux")
        mocker.patch.object(tmux_notify.subprocess, "run", side_effect=OSError("boom"))
        assert tmux_notify.tmux_context() is None


class TestNotifyMacos:
    def test_missing_terminal_notifier_returns_false(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker
    ) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: None)
        run = mocker.patch.object(tmux_notify.subprocess, "run")
        assert tmux_notify.notify_macos("t", "s", "m", "grp", None) is False
        run.assert_not_called()

    def test_includes_execute_when_ctx_present(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/terminal-notifier")
        run = mocker.patch.object(tmux_notify.subprocess, "run")

        ok = tmux_notify.notify_macos("t", "s", "m", "grp", ("/tmp/sock", "sess:2"))

        assert ok is True
        argv = run.call_args.args[0]
        assert "-execute" in argv
        execute = argv[argv.index("-execute") + 1]
        assert "switch-client" in execute and "sess:2" in execute and "/tmp/sock" in execute

    def test_activate_bundle_and_sound_from_env(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/terminal-notifier")
        monkeypatch.setenv(BUNDLE, "com.mitchellh.ghostty")
        monkeypatch.setenv(SOUND, "true")
        run = mocker.patch.object(tmux_notify.subprocess, "run")

        tmux_notify.notify_macos("t", "s", "m", "grp", None)

        argv = run.call_args.args[0]
        assert argv[argv.index("-activate") + 1] == "com.mitchellh.ghostty"
        assert argv[argv.index("-sound") + 1] == "default"

    def test_no_sound_or_bundle_by_default(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/terminal-notifier")
        run = mocker.patch.object(tmux_notify.subprocess, "run")

        tmux_notify.notify_macos("t", "s", "m", "grp", None)

        argv = run.call_args.args[0]
        assert "-sound" not in argv
        assert "-activate" not in argv


class TestNotifyLinux:
    def test_missing_notify_send_returns_false(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: None)
        run = mocker.patch.object(tmux_notify.subprocess, "run")
        assert tmux_notify.notify_linux("t", "s", "m", None) is False
        run.assert_not_called()

    def test_body_includes_tmux_target_when_ctx_present(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker
    ) -> None:  # noqa: ANN001
        monkeypatch.setattr(tmux_notify.shutil, "which", lambda _name: "/usr/bin/notify-send")
        run = mocker.patch.object(tmux_notify.subprocess, "run")

        ok = tmux_notify.notify_linux("t", "s", "msg", ("/tmp/sock", "sess:2"))

        assert ok is True
        argv = run.call_args.args[0]
        body = argv[-1]
        assert "msg" in body and "tmux: sess:2" in body


class TestMain:
    def _run_main(self, monkeypatch: pytest.MonkeyPatch, event: str = "notification", stdin: str = "{}") -> None:
        monkeypatch.setattr(tmux_notify.sys, "argv", ["tmux_notify.py", "--event", event])
        monkeypatch.setattr(tmux_notify.sys, "stdin", io.StringIO(stdin))
        monkeypatch.setattr(tmux_notify, "tmux_context", lambda: None)
        tmux_notify.main()

    def test_toggle_off_is_silent_noop(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        macos = mocker.patch.object(tmux_notify, "notify_macos")
        linux = mocker.patch.object(tmux_notify, "notify_linux")
        bell = mocker.patch.object(tmux_notify, "notify_bell")

        self._run_main(monkeypatch)

        macos.assert_not_called()
        linux.assert_not_called()
        bell.assert_not_called()

    def test_macos_success_short_circuits(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv(TOGGLE, "true")
        macos = mocker.patch.object(tmux_notify, "notify_macos", return_value=True)
        linux = mocker.patch.object(tmux_notify, "notify_linux")
        bell = mocker.patch.object(tmux_notify, "notify_bell")

        self._run_main(monkeypatch)

        macos.assert_called_once()
        linux.assert_not_called()
        bell.assert_not_called()

    def test_falls_through_macos_to_linux(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv(TOGGLE, "true")
        mocker.patch.object(tmux_notify, "notify_macos", return_value=False)
        linux = mocker.patch.object(tmux_notify, "notify_linux", return_value=True)
        bell = mocker.patch.object(tmux_notify, "notify_bell")

        self._run_main(monkeypatch)

        linux.assert_called_once()
        bell.assert_not_called()

    def test_falls_through_to_bell(self, clean_env: None, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        monkeypatch.setenv(TOGGLE, "true")
        mocker.patch.object(tmux_notify, "notify_macos", return_value=False)
        mocker.patch.object(tmux_notify, "notify_linux", return_value=False)
        bell = mocker.patch.object(tmux_notify, "notify_bell")

        self._run_main(monkeypatch)

        bell.assert_called_once()


class TestNotifyBell:
    def test_swallows_oserror(self, monkeypatch: pytest.MonkeyPatch, mocker) -> None:  # noqa: ANN001
        # No controlling tty in CI: opening /dev/tty raises; the hook must not propagate it.
        mocker.patch.object(tmux_notify, "open", side_effect=OSError("no tty"), create=True)
        tmux_notify.notify_bell("subtitle", "message")  # must not raise


# --- Integration: real tmux server via the libtmux pytest plugin ---------------
# Skipped unless libtmux is importable AND a real tmux binary is on PATH.

libtmux = pytest.importorskip("libtmux")


def _real_socket_path(server) -> str:  # noqa: ANN001
    """The on-disk socket path of a libtmux server.

    The pytest fixtures address their server by socket *name* (``tmux -L``), so
    ``server.socket_path`` is ``None``; ``tmux_context`` (like a real ``$TMUX``)
    addresses by socket *path* (``tmux -S``). Ask tmux for the real path.
    """
    if server.socket_path:
        return str(server.socket_path)
    return server.cmd("display-message", "-p", "#{socket_path}").stdout[0]


@pytest.mark.skipif(shutil.which("tmux") is None, reason="requires a real tmux binary")
def test_tmux_context_against_real_server(session, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    """``tmux_context`` resolves a real session:window from a live tmux server."""
    server = session.server
    socket_path = _real_socket_path(server)
    pane = session.active_window.active_pane
    # tmux_context only reads the socket (first comma-separated field) + the pane.
    monkeypatch.setenv("TMUX", f"{socket_path},0,{session.session_id}")
    monkeypatch.setenv("TMUX_PANE", pane.pane_id)

    ctx = tmux_notify.tmux_context()

    assert ctx is not None
    socket, target = ctx
    assert socket == socket_path
    assert ":" in target  # real "session:window"
