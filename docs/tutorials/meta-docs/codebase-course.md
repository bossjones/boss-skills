# Build an offline codebase course

Use `codebase-course` to teach a repository workflow with a browser-based lesson and a practice
question. The course is generated for the repository you choose; the plugin does not include a
prebuilt course.

## 1. Pick a scope and destination

From a repository with `meta-docs` installed, name the source area, audience, and a new output
directory:

```text
/meta-docs:codebase-course Teach a new contributor how scripts/symlink_plugins.py plans changes.
Create an offline course in ./learning/symlinks.
```

In Codex, ask to use `codebase-course` by name. Choose a different source path if your repository
does not contain that script. The skill asks before replacing an existing destination.

## 2. Review the result

Open the generated `index.html` in a browser. Follow the lesson links and answer the exercise.
Check the source paths and line ranges against the inspected revision. The course should work
without network access and provide an answer when JavaScript is disabled.

The final response identifies the course path and any unverified behavior or checks that could not
be run. Review the generated content before sharing it: source excerpts may contain information
that should stay within the repository.
