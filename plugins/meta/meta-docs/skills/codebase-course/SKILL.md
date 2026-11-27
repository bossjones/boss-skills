---
name: codebase-course
description: >-
  Use when asked to teach how a repository or selected code works through an
  interactive HTML course, guided code walkthrough, or learning exercise.
  Builds a local course grounded in inspected source rather than inventing behavior.
---

# Codebase Course

Create a small, source-grounded learning experience that runs in a browser without a server or
network connection. Tailor the depth to the learner and the requested part of the repository.

## 1. Set the boundary

Use the repository or paths named by the user; otherwise use the current repository. Determine the
audience and destination from the request. If unspecified, teach a newcomer the main workflow and
write to `codebase-course/index.html` under the current directory. If the destination already
exists, ask before replacing anything; offer an unused sibling directory instead.

Read only the code needed for the chosen scope. Do not inspect credentials, environment files,
private keys, or unrelated personal data. Include source excerpts only when the user has authority
to use them, and keep the output local unless sharing is authorized. Do not clone a remote repository,
install dependencies, execute project code, or publish the result without the user's approval.
Explain any missing access or evidence instead of guessing.

## 2. Build an evidence map

Find the entry point, follow the relevant calls or data transformations, and inspect tests or
configuration when they clarify behavior. Record the repository-relative file and line range for
each substantive claim. Check quoted code against the source exactly and include only excerpts
necessary to teach the requested concept. Note when the source cannot establish runtime behavior.

Choose a few coherent lessons rather than attempting to document every file. For a small or
incomplete repository, use the evidence available and state the coverage limit. Keep a note of the
repository revision when available so learners can recognize stale citations.

## 3. Produce the course

Write a self-contained `index.html` in the agreed destination. Include:

1. A title, intended audience, learning goals, and an outline linking to each lesson.
2. Lessons that explain the chosen workflow in plain language, with short, relevant source
   references and examples. Distinguish observed facts from inferences or unverified behavior.
3. At least one application exercise with a way to check an answer and a useful explanation for
   both correct and incorrect choices. Keep an accessible answer available when JavaScript is off.
4. A source list with paths, line ranges, and the inspected revision if known, plus a short section
   identifying what was not investigated.

Use semantic headings, a labelled navigation region, keyboard-operable controls, visible focus,
and readable text that adapts to narrow screens. Include CSS and any JavaScript in the HTML; do not
load fonts, scripts, images, analytics, or other resources from the network. A course should remain
readable without JavaScript. Escape source text and paths before inserting them into HTML or
JavaScript; never execute code copied from the repository.

## 4. Check the result

Open the generated file in a browser when available. Follow every outline link, use the controls
with a keyboard, and exercise the correct, incorrect, and unanswered states. Check the narrow-screen
layout and confirm that cited paths, line ranges, and excerpts match the inspected revision. Use
local checks for broken fragments and unintended external resources.

If browser or accessibility testing is unavailable, state exactly which checks were not performed;
do not claim a visual or screen-reader pass from static inspection alone. Report the output path,
covered scope, and any source or validation gaps.

## Example

```text
/meta-docs:codebase-course Teach a new contributor how scripts/symlink_plugins.py plans
changes. Create an offline course in ./learning/symlinks and include a practice question.
```

In Codex, request the `codebase-course` skill by name in the prompt.
