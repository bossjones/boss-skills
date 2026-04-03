### Tools with Claude Code

| Name  | Purpose   |
|---|---|
| Agent  | Launch a subagent to handle a task  |
| Bash  | Run a shell command  |
| Edit  | edit a file  |
| Glob  | find files based on pattern  |
| Grep  | search contents of a file  |
| LS  |  list files and directories |
| MultiEdit  | make several edits at the same time  |
| NotebookEdit  | write to a cell in a jupyter notebook  |
| NotebookRead  | read a cell  |
| Read  | read a file  |
| TodoRead  | read one of the created to-dos  |
| TodoWrite  | update the list of todos  |
| WebFetch  | fetch from aurl  |
| WebSearch  | search the web  |
| Write  | write to a file  |

### Claude thinking modes

Allows claude to reason about more challenging problems

Think
Think more
Think a lot
Think longer
Ultrathink


### Controlling Context

| Command | Description |
|---|---|
| **Escape** | • Interrupt Claude, allowing you to redirect or correct it.<br>• Also useful to fix issues with # memories. |
| **Double-tap Escape** | • Rewind the conversation to an earlier point in time.<br>• Allows you to maintain valuable context. |
| **/compact** | • Summarize the conversation and continue.<br>• Helps Claude stay focused but remember what it has learned in the current session. |
| **/clear** | • Dumps current conversation history.<br>• Useful when switching between different tasks. |


### A Note on Hooks

There are more hooks beyond the PreToolUse and PostToolUse hooks discussed in this course. There are also:

`Notification` - Runs when Claude Code sends a notification, which occurs when Claude needs permission to use a tool, or after Claude Code has been idle for 60 seconds
`Stop` - Runs when Claude Code has finished responding
`SubagentStop` - Runs when a subagent (these are displayed as a "Task" in the UI) has finished
`PreCompact` - Runs before a compact operation occurs, either manual or automatic
`UserPromptSubmit` - Runs when the user submits a prompt, before Claude processes it
`SessionStart` - Runs when starting or resuming a session
`SessionEnd` - Runs when a session ends

Here's the confusing part:

The stdin input to your commands will change based upon the type of hook being executed (`PreToolUse`, `PostToolUse`, `Notification`, etc)
The `tool_input` contained in that will differ based upon the tool that was called (in the case of `PreToolUse` and `PostToolUse` hooks)
For example, here's a sample of some stdin input to a hook, where the hook is a PostToolUse that was watching for uses of the TodoWrite tool. For reference, that is the tool that Claude uses to keep track of to-do items.

```json
{
  "session_id": "9ecf22fa-edf8-4332-ae85-b6d5456eda64",
  "transcript_path": "<path_to_transcript>",
  "hook_event_name": "PostToolUse",
  "tool_name": "TodoWrite",
  "tool_input": {
    "todos": [{ "content": "write a readme", "status": "pending", "priority": "medium", "id": "1" }]
  },
  "tool_response": {
    "oldTodos": [],
    "newTodos": [{ "content": "write a readme", "status": "pending", "priority": "medium", "id": "1" }]
  }
}
```

And for comparison, here's an example of the input to a Stop hook:

```json
{
  "session_id": "af9f50b6-f042-4773-b3e2-c3a4814765ce",
  "transcript_path": "<path_to_transcript>",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

As you can see, the stdin input to your command will differ significantly based upon the hook (PreToolUse, PostToolUse, Stop, etc) and the matcher used (in the case of PreToolUse and PostToolUse). This can make writing hooks challenging - you might not know the exact structure of the input to your command!

To handle this challenge, try making a helper hook like this:

```json
"PostToolUse": [ // Or "PreToolUse" or "Stop", etc
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "jq . > post-log.json"
      }
    ]
  },
]
```

Notice the provided command. It will write the input to this hook to the post-log.json file, which allows you to inspect exactly what would have been fed into your command! This makes it a lot easier for you to understand what data your command should inspect.


### Built-in Subagents

Claude Code ships with several built-in subagents you can use right away:

General purpose subagent -- for multi-step tasks that require both exploration and action
Explore -- for fast searching and navigation of codebases
Plan -- used during plan mode for research and analysis of your codebase before presenting a plan

### Subagent tips

```yaml
# Example: .claude/agents/your-agent-name.md
---
name: code-quality-reviewer
description: Use this agent when you need to review recently written or modified code for quality, security, and best practice compliance.
tools: Bash, Glob, Grep, Read, WebFetch, WebSearch
model: sonnet
color: purple
---

You are an expert code reviewer specializing in quality assurance, security best practices, and
adherence to project standards. Your role is to thoroughly examine recently written or modified code
and identify issues that could impact reliability, security, maintainability, or performance.
```

Making Claude Use Your Subagent Automatically
If you want Claude to delegate tasks to the subagent without you explicitly asking, include the word "proactively" in the description field. For example:

description: Proactively suggest running this agent after major code changes.

You can also add example conversations to the description to help Claude understand specific scenarios where the subagent should be used. The more concrete your examples, the better Claude gets at knowing when to delegate.

### Subagents output format to control run time

Defining an Output Format
The single most important improvement you can make to a subagent is defining an output format in its system prompt. This does two things:

It creates natural stopping points -- the subagent knows it's done when it has filled in each section of the format.
It prevents the subagent from running too long. Without a defined output, subagents struggle to decide when enough research has been done and tend to run much longer than necessary.
Here's an example of a structured output format for a code review subagent:

Provide your review in a structured format:

1. Summary: Brief overview of what you reviewed and overall assessment
2. Critical Issues: Any security vulnerabilities, data integrity risks,
   or logic errors that must be fixed immediately
3. Major Issues: Quality problems, architecture misalignment, or
   significant performance concerns
4. Minor Issues: Style inconsistencies, documentation gaps, or
   minor optimizations
5. Recommendations: Suggestions for improvement, refactoring
   opportunities, or best practices to apply
6. Approval Status: Clear statement of whether the code is ready
   to merge/deploy or requires changes

This format gives the subagent a clear checklist to work through. Once every section is filled in, the subagent knows it can stop.


### Subagents: Reporting Obstacles

When a subagent discovers a workaround during its work -- like solving a dependency issue or finding that a certain command needs particular flags -- those details need to appear in the summary it returns. If they don't, the main thread has to rediscover the same solutions on its own, which wastes time and tokens.

The kinds of things you want surfaced include:

Setup issues or environment quirks
Workarounds discovered during the task
Commands that needed special flags or configuration
Dependencies or imports that caused problems
The way to get this information is to explicitly ask for it in the output format. Adding an "Obstacles Encountered" section to your output template surfaces this information reliably.

7. Obstacles Encountered: Report any obstacles encountered during the
   review process. This can be: setup issues, workarounds discovered or
   environment quirks. Report commands that needed a special flag or
   configuration. Report dependencies or imports that caused problems.

### Subagents: Putting It All Together

Effective subagents share four characteristics:

1. Specific descriptions -- The description controls when the subagent is launched and what instructions it receives. Write it to steer both.
2. Structured output -- Define an output format in the system prompt so the subagent knows when it's done and returns information the main thread can use.
3. Obstacle reporting -- Include a section in the output format for workarounds, quirks, and problems so the main thread doesn't have to rediscover them.
4. Limited tool access -- Only give a subagent the tools it actually needs. Read-only for research, bash for reviewers, edit/write only for agents that should change code.

Each of these patterns is simple on its own, but together they turn a subagent from something that vaguely tries to help into a focused, predictable worker that finishes on time and reports back clearly.

### Subagents: When to use them?

The Decision Rule
When you're deciding whether to use a subagent, ask yourself one question: does the intermediate work matter?

If the answer is no -- you just need the final result -- delegate it to a subagent. If the answer is yes -- you need to see and react to what's happening along the way -- keep it in your main thread.

Use subagents for:

- Research and exploration
- Code reviews
- Tasks that need a custom system prompt

Avoid subagents for:

- "Expert" personas that don't add real capability
- Multi-step pipelines where each step depends on the last
- Running tests where you need full output for debugging