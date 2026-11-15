"""Detect the stack, the dead-code / duplicate tools the repo ALREADY has, and the
build and test commands. Never installs anything.

Usage: python -I detect_stack.py ROOT
A tool counts as present if the repo declares or configures it, or it is on PATH or
in node_modules/.bin. Standard library only. No network.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

# tool -> (stack, files whose text mentions it, command to run it)
TOOLS = {
    "knip": ("js", ["package.json", "knip.json", "knip.jsonc", ".knip.json"], "npx knip --reporter compact"),
    "ts-prune": ("js", ["package.json"], "npx ts-prune"),
    "depcheck": ("js", ["package.json", ".depcheckrc"], "npx depcheck"),
    "jscpd": ("any", ["package.json", ".jscpd.json"], "npx jscpd --reporters console ."),
    "eslint": ("js", ["package.json", "eslint.config.js", "eslint.config.mjs", ".eslintrc.json", ".eslintrc.js"],
               "npx eslint . --rule 'no-unused-vars: error'"),
    "vulture": ("py", ["pyproject.toml", "requirements-dev.txt", "requirements.txt", "setup.cfg",
                       ".pre-commit-config.yaml"], "vulture . --min-confidence 80"),
    "ruff": ("py", ["pyproject.toml", "ruff.toml", ".ruff.toml", "requirements-dev.txt", ".pre-commit-config.yaml"],
             "ruff check --select F401,F811,F841 ."),
    "pylint": ("py", ["pyproject.toml", ".pylintrc", "requirements-dev.txt"], "pylint --disable=all --enable=W0611,W0612 ."),
    "staticcheck": ("go", [".golangci.yml", ".golangci.yaml", "go.mod"], "staticcheck -checks U1000 ./..."),
    "golangci-lint": ("go", [".golangci.yml", ".golangci.yaml"], "golangci-lint run --enable unused"),
    "dotnet": ("dotnet", [], "dotnet build -warnaserror:IDE0051,IDE0052,CS0168,CS0219"),
    "cargo": ("rust", [], "cargo check 2>&1 | grep dead_code"),
}
MANIFESTS = {"package.json": "js", "pyproject.toml": "py", "requirements.txt": "py", "setup.py": "py",
             "go.mod": "go", "Cargo.toml": "rust", "pom.xml": "java", "build.gradle": "java",
             "build.gradle.kts": "kotlin"}


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def stacks(root: Path) -> set[str]:
    found = {s for m, s in MANIFESTS.items() if (root / m).is_file()}
    if any(root.glob("*.sln")) or any(root.glob("**/*.csproj")):
        found.add("dotnet")
    return found


def tool_present(root: Path, tool: str, files: list[str]) -> str:
    for f in files:
        if re.search(rf"(?<![\w-]){re.escape(tool)}(?![\w-])", read(root / f)):
            return f"declared in {f}"
    if (root / "node_modules" / ".bin" / tool).exists():
        return "node_modules/.bin"
    if shutil.which(tool):
        return "on PATH"
    return ""


def build_test(root: Path, found: set[str]) -> list[str]:
    cmds = []
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            scripts = json.loads(read(pkg)).get("scripts", {})
        except ValueError:
            scripts = {}
        cmds += [f"npm run {s}" for s in ("build", "typecheck", "lint", "test") if s in scripts]
    if "py" in found:
        py = read(root / "pyproject.toml")
        try:
            pytest_cfg = "pytest" in tomllib.loads(py).get("tool", {}) if py else False
        except ValueError:
            pytest_cfg = False
        if pytest_cfg or (root / "pytest.ini").is_file() or "pytest" in read(root / "requirements-dev.txt"):
            cmds.append("python -m pytest -q")
        elif (root / "tests").is_dir():
            cmds.append("python -m unittest discover -s tests -t .")
    if "dotnet" in found:
        cmds += ["dotnet build", "dotnet test"]
    if "go" in found:
        cmds += ["go build ./...", "go test ./..."]
    if "rust" in found:
        cmds += ["cargo build", "cargo test"]
    mk = read(root / "Makefile")
    cmds += [f"make {t}" for t in ("build", "test") if re.search(rf"^{t}:", mk, re.M)]
    for line in read(root / "README.md").splitlines():
        m = re.search(r"(?i)(run )?tests?:?\s*`([^`]+)`", line)
        if m:
            cmds.append(f"{m.group(2)}   (from README.md)")
    return cmds


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:] or ["."])[0]).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    found = stacks(root)
    print("stacks:", ", ".join(sorted(found)) or "unknown")
    print("\ntools already available (use these):")
    missing = []
    for tool, (stack, files, cmd) in TOOLS.items():
        if stack not in found and stack != "any":
            continue
        where = tool_present(root, tool, files)
        if where:
            print(f"  {tool:14} {where:28} run: {cmd}")
        else:
            missing.append(tool)
    print("\nnot available (do NOT install; ask the user first):", ", ".join(missing) or "none")
    print("fallback scripts: find_unused.py, find_dupes.py")
    print("\nbuild/test commands:")
    print("\n".join(f"  {c}" for c in dict.fromkeys(build_test(root, found))) or "  none found: ask the user")
    return 0


if __name__ == "__main__":
    sys.exit(main())
