# Attribution

This skill is **vendored** (copied and locally modified) from an upstream open-source project.

## Upstream source

- **Repository:** <https://github.com/aidankinzett/claude-git-pr-skill>
- **Skill path:** `github-pr-review/skills/github-pr-review/SKILL.md`
- **Pinned tag:** `v1.1.1`
- **Pinned commit:** `3660dca92424b91f1eb716b5815b476c3913450e`
- **Author:** Aidan Kinzett (<https://github.com/aidankinzett>)
- **License:** MIT (declared in the upstream README; upstream ships no `LICENSE` file)

## Local modifications

This vendored copy differs from upstream as follows:

- Expanded `allowed-tools` frontmatter to declare the `gh` commands the skill actually runs
  (`gh --version`, `gh auth status`, `gh pr view`, `gh api`) in addition to `AskUserQuestion`.
- Added the **"Passing long or multi-line review bodies safely"** section, plus matching entries in
  the *Common Mistakes* and *Red Flags* lists, to prevent the literal-`@file` bug where a drafted
  body file path is posted verbatim instead of its contents.
- Added this attribution file and a provenance note at the top of `SKILL.md`.

## MIT License

```text
MIT License

Copyright (c) Aidan Kinzett

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
