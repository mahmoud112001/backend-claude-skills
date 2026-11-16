"""Unit tests for design-docs-organizer/scripts/organize.py (stdlib unittest; needs git on PATH).

Run: python3 -I tests/test_organize.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "design-docs-organizer" / "scripts" / "organize.py"
FILES = {
    "project-profile.md": "# Profile\nsee [brief](00-project-brief.md)\n",
    "00-state.md": "# State\n[strategic](01-strategic.md) [api](06-api.md#operations)\n",
    "00-project-brief.md": "# 00 Brief\nREQ-1\n",
    "01-strategic.md": "# 01 Strategic\nback to [brief](00-project-brief.md)\n",
    "02-tactical-alpha.md": "# 02 Alpha\nsee [db](03-db-design.md) and [x](https://example.invalid/a.md)\n",
    "03-db-design.md": "# 03 DB\n[erd](04-erd.md)\n",
    "04-erd.md": "# 04 ERD\n",
    "06-api.md": "# 06 API\ncontract: [proto](06-api.proto)\n",
    "06-api.proto": "syntax = \"proto3\";\n",
}


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


def make(root: Path) -> Path:
    out = root / "docs" / "design"
    out.mkdir(parents=True)
    for name, text in FILES.items():
        (out / name).write_text(text, encoding="utf-8")
    return out


class OrganizeTest(unittest.TestCase):
    def check_layout(self, out: Path):
        self.assertTrue((out / "strategic" / "01-strategic.md").is_file())
        self.assertTrue((out / "data" / "04-erd.md").is_file())
        self.assertTrue((out / "api" / "06-api.proto").is_file())
        self.assertTrue((out / "00-state.md").is_file(), "state stays at the root")
        state = (out / "00-state.md").read_text(encoding="utf-8")
        self.assertIn("](strategic/01-strategic.md)", state)
        self.assertIn("](api/06-api.md#operations)", state, "anchors survive")
        tac = (out / "tactical" / "02-tactical-alpha.md").read_text(encoding="utf-8")
        self.assertIn("](../data/03-db-design.md)", tac)
        self.assertIn("https://example.invalid/a.md", tac, "external links untouched")

    def finish(self, out: Path):
        self.assertEqual(run("readme", str(out)).returncode, 0)
        r = run("check", str(out))
        self.assertEqual(r.returncode, 1, "placeholders must fail the check")
        readme = out / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("<one line>", "summary")
                          .replace("<one paragraph: what was designed, for whom, status>", "Done."), encoding="utf-8")
        r = run("check", str(out))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_plain_move_without_vcs(self):
        with tempfile.TemporaryDirectory() as d:
            out = make(Path(d))
            r = run("apply", str(out), "--vcs", "none")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("plain move", r.stdout)
            self.assertNotIn("git mv", r.stdout)
            self.check_layout(out)
            self.finish(out)

    def test_git_mv_for_tracked_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = make(root)
            g = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(g + ["commit", "-qm", "x"], cwd=root, check=True)
            (out / "07-review.md").write_text("# 07 Review\n", encoding="utf-8")  # untracked
            r = run("apply", str(out), "--vcs", "git")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("git mv: 01-strategic.md -> strategic/01-strategic.md", r.stdout)
            self.assertIn("plain move (untracked): 07-review.md -> review/07-review.md", r.stdout)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout
            # "R" = staged rename (git mv); a second column "M" = links rewritten after the move
            self.assertRegex(status, r"(?m)^R[ M] docs/design/01-strategic.md -> docs/design/strategic/01-strategic.md$")
            self.check_layout(out)
            self.finish(out)

    def test_check_detects_lost_and_changed_content(self):
        with tempfile.TemporaryDirectory() as d:
            out = make(Path(d))
            run("apply", str(out), "--vcs", "none")
            (out / "data" / "04-erd.md").unlink()
            p = out / "strategic" / "01-strategic.md"
            p.write_text(p.read_text(encoding="utf-8") + "extra line\n", encoding="utf-8")
            r = run("check", str(out))
            self.assertEqual(r.returncode, 1)
            self.assertIn("lost: 04-erd.md", r.stdout)
            self.assertIn("content changed beyond links: strategic/01-strategic.md", r.stdout)
            self.assertIn("broken link data/03-db-design.md -> 04-erd.md", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
