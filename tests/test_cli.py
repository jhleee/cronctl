from __future__ import annotations

import json
from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from cronctl.cli.main import cli

if TYPE_CHECKING:
    from pathlib import Path


def _make_fake_crontab(tmp_path: Path) -> tuple[str, Path]:
    store = tmp_path / "crontab.txt"
    script = tmp_path / "fake-crontab"
    script.write_text(
        """
#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

store = pathlib.Path(r\"\"\"__STORE__\"\"\")
mode = sys.argv[1]
if mode == "-l":
    if store.exists():
        sys.stdout.write(store.read_text(encoding="utf-8"))
        raise SystemExit(0)
    sys.stderr.write("no crontab for test\\n")
    raise SystemExit(1)
if mode == "-":
    store.write_text(sys.stdin.read(), encoding="utf-8")
    raise SystemExit(0)
raise SystemExit(2)
        """.replace("__STORE__", str(store)).strip(),
        encoding="utf-8",
    )
    script.chmod(0o755)
    return str(script), store


def test_cli_job_lifecycle(tmp_path: Path) -> None:
    runner = CliRunner()
    crontab_bin, crontab_store = _make_fake_crontab(tmp_path)
    home = tmp_path / "home"
    env = {"CRONCTL_CRONTAB_BIN": crontab_bin}

    result = runner.invoke(
        cli,
        ["--home", str(home), "--json", "init", "--non-interactive"],
        env=env,
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli,
        [
            "--home",
            str(home),
            "--json",
            "add",
            "--id",
            "hello",
            "--schedule",
            "* * * * *",
            "--command",
            "printf hello",
        ],
        env=env,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["created"] is True

    result = runner.invoke(cli, ["--home", str(home), "--json", "exec", "hello"], env=env)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "success"

    result = runner.invoke(
        cli, ["--home", str(home), "--json", "logs", "hello", "--last", "1"], env=env
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["runs"][0]["stdout"] == "hello"

    result = runner.invoke(cli, ["--home", str(home), "export"], env=env)
    assert result.exit_code == 0, result.output
    exported = yaml.safe_load(result.output)
    assert exported["jobs"][0]["id"] == "hello"

    assert "CRONCTL MANAGED START" in crontab_store.read_text(encoding="utf-8")


def test_init_copies_agentskills_layout(tmp_path: Path) -> None:
    runner = CliRunner()
    crontab_bin, _ = _make_fake_crontab(tmp_path)
    home = tmp_path / "home"
    skills_root = tmp_path / ".claude" / "skills"
    env = {"CRONCTL_CRONTAB_BIN": crontab_bin}

    result = runner.invoke(
        cli,
        [
            "--home",
            str(home),
            "--json",
            "init",
            "--non-interactive",
            "--skill-path",
            str(skills_root),
        ],
        env=env,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    skill_path = skills_root / "cronctl" / "SKILL.md"
    assert payload["skill_path"] == str(skill_path)
    assert skill_path.exists()
    skill_text = skill_path.read_text(encoding="utf-8")
    assert skill_text.startswith("---\nname: cronctl\n")
    assert "description:" in skill_text
    assert "cronctl --json status" in skill_text


def test_cli_import_round_trip(tmp_path: Path) -> None:
    runner = CliRunner()
    crontab_bin, _ = _make_fake_crontab(tmp_path)
    env = {"CRONCTL_CRONTAB_BIN": crontab_bin}
    source = tmp_path / "jobs.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "jobs": [
                    {
                        "id": "sync-s3",
                        "schedule": "*/5 * * * *",
                        "command": "printf sync",
                        "tags": ["sync"],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        ["--home", str(tmp_path / "target-home"), "--json", "import", str(source)],
        env=env,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["imported"] == 1

    result = runner.invoke(
        cli,
        ["--home", str(tmp_path / "target-home"), "--json", "list", "--tag", "sync"],
        env=env,
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["jobs"][0]["id"] == "sync-s3"


def test_doctor_reports_repo_bootstrap_assets_without_side_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    runner = CliRunner()
    crontab_bin, _ = _make_fake_crontab(tmp_path)
    home = tmp_path / "doctor-home"
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("# fake lock\n", encoding="utf-8")
    (tmp_path / "install.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "bootstrap.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("setup:\n\ttrue\n", encoding="utf-8")
    (tmp_path / ".mcp.json.example").write_text("{}", encoding="utf-8")
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.cronctl.json.example").write_text("{}", encoding="utf-8")
    env = {"CRONCTL_CRONTAB_BIN": crontab_bin}

    result = runner.invoke(cli, ["--home", str(home), "--json", "doctor"], env=env)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["home"] == str(home)
    assert payload["repo_bootstrap_ready"] is True
    assert payload["bootstrap_assets"]["uv_lock"] is True
    assert payload["bootstrap_assets"]["install_script"] is True
    assert payload["bootstrap_assets"]["bootstrap_script"] is True
    assert payload["paths"]["home_exists"] is False
    assert not home.exists()
