# Test Project

Defines a project-prefixed custom agent for a declared custom pipeline. This is
allowed by Check 2 because the agent does not reuse a canonical role name and the
project's pipeline declaration (`.claude/pipelines.json`) selects a pipeline that
invokes it.
