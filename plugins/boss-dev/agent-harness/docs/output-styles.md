# Output Styles Reference

Eight output styles under `output-styles/*.md`, auto-discovered on `/plugin install` and selectable
with `/output-style`. An output style changes **how Claude formats its responses** for the rest of
the session — it does not change the plugin's commands or skills.

## Table of Contents

- [How to use](#how-to-use)
- [The styles](#the-styles)
- [Choosing a style](#choosing-a-style)

## How to use

```text
/output-style                  # list available styles and pick one
/output-style table-based      # switch directly to a style
```

Styles persist for the session. Switch back with `/output-style default` (the built-in style).

## The styles

| Style | Best for | Source |
| --- | --- | --- |
| `markdown-focused` | General-purpose rich docs — headers, tables, blockquotes, task lists | [`output-styles/markdown-focused.md`](../output-styles/markdown-focused.md) |
| `bullet-points` | Hierarchical breakdowns, broad → specific | [`output-styles/bullet-points.md`](../output-styles/bullet-points.md) |
| `table-based` | Comparisons, step lists, and structured analysis | [`output-styles/table-based.md`](../output-styles/table-based.md) |
| `ultra-concise` | Minimal words, fragments over sentences, code-first | [`output-styles/ultra-concise.md`](../output-styles/ultra-concise.md) |
| `yaml-structured` | Machine-readable YAML key/value blocks | [`output-styles/yaml-structured.md`](../output-styles/yaml-structured.md) |
| `html-structured` | Semantic HTML5 with data attributes for programmatic parsing | [`output-styles/html-structured.md`](../output-styles/html-structured.md) |
| `genui` | A styled, self-contained HTML page written to `/tmp/` and opened | [`output-styles/genui.md`](../output-styles/genui.md) |
| `tts-summary` | Spoken task-completion summaries (experimental) | [`output-styles/tts-summary.md`](../output-styles/tts-summary.md) |

## Choosing a style

| You want… | Use |
| --- | --- |
| Readable docs and explanations | `markdown-focused` |
| The shortest possible answers | `ultra-concise` |
| Side-by-side comparisons and checklists | `table-based` |
| Output another program will parse | `yaml-structured` or `html-structured` |
| A shareable rendered page | `genui` |
| Audio recap instead of reading | `tts-summary` (pairs with the |

  [`work-completion-summary`](./agents.md#work-completion-summary) agent) |
</content>
