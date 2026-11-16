---
name: design-docs-organizer
description: Phase 8 of a backend design. Moves the design files into phase folders (git mv when versioned, plain move otherwise), fixes links, writes README.md as an index with a reading order, and proves no content was lost. Touches only the design output folder.
model: haiku
allowed-tools: Read Glob Grep Edit Bash(python3 *organize.py*) Bash(python *organize.py*)
---

# design-docs-organizer

Model: haiku. A script does the moves, the link rewriting and the checks. The model only writes one-line summaries.

Source: adapted from living-docs-governance (ECC, MIT): one index file that maps every document, plus a reading order, with no orphan files.

Inputs: `<out>` and the profile's `version_control`. The script is `${CLAUDE_SKILL_DIR}/scripts/organize.py`. If that variable is not expanded, find the script with Glob `**/design-docs-organizer/scripts/organize.py`. Run it with `python3 -I`, or with `python -I` if `python3` isn't on PATH:

```
python3 -I <organize.py> plan   <out>                   # show the moves first
python3 -I <organize.py> apply  <out> --vcs <git|none>  # git mv for tracked files; plain move otherwise
python3 -I <organize.py> readme <out>                   # README.md index + reading order with placeholders
python3 -I <organize.py> check  <out>                   # must print OK
```

Layout after `apply`: `project-profile.md`, `00-state.md` and `README.md` stay at the root. The other folders are `brief/`, `strategic/`, `tactical/`, `data/` (03 and 04), `diagrams/`, `api/` (06 and the contract files) and `review/` (07).

## Steps

1. Run `plan`, then `apply`. Use `--vcs git` only if the profile says git. Files git does not track yet are moved plainly, and the script says so. Never run any other git command.
2. Run `readme`. Then edit `README.md`: replace `<one paragraph ...>` with 3 to 5 sentences (what was designed, the contexts, the review verdict, the number of open questions), and each `<one line>` with what the file gives a reader. Take these from each file's title and Decisions, never invented. Change nothing else.
3. Run `check`. Each failure names a file and a link. Fix only links, by editing the link target. Never change content: the manifest compares content hashes.
4. Do not edit, merge or delete any design content. If two files overlap, report it. Do not fix it.

Reply in at most 300 words: the absolute path of `organize.py`, the number of files moved and how (git mv or plain move), the links rewritten, and the final `check` output.
