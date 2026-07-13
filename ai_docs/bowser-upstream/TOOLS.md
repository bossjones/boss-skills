# Claude Code Tools (with --chrome)

## File Operations

```ts
// Read a file from the local filesystem
function Read(
  file_path: string,    // Absolute path to the file to read
  offset?: number,      // Line number to start reading from
  limit?: number,       // Number of lines to read
  pages?: string,       // Page range for PDF files (e.g., "1-5")
): string;

// Perform exact string replacements in files
function Edit(
  file_path: string,    // Absolute path to the file to modify
  old_string: string,   // The text to replace
  new_string: string,   // The text to replace it with
  replace_all?: boolean, // Replace all occurrences (default false)
): void;

// Write/overwrite a file on the local filesystem
function Write(
  file_path: string,    // Absolute path to the file to write
  content: string,      // The content to write to the file
): void;

// Replace contents of a Jupyter notebook cell
function NotebookEdit(
  notebook_path: string,   // Absolute path to the .ipynb file
  new_source: string,      // The new source for the cell
  cell_id?: string,        // ID of the cell to edit
  cell_type?: string,      // "code" or "markdown"
  edit_mode?: string,      // "replace", "insert", or "delete"
): void;
```

## Search & Discovery

```ts
// Fast file pattern matching using glob patterns
function Glob(
  pattern: string,  // Glob pattern to match (e.g., "**/*.ts")
  path?: string,    // Directory to search in (default: cwd)
): string[];

// Search file contents using ripgrep regex
function Grep(
  pattern: string,          // Regex pattern to search for
  path?: string,            // File or directory to search in
  glob?: string,            // Glob pattern to filter files (e.g., "*.js")
  type?: string,            // File type filter (e.g., "js", "py")
  output_mode?: string,     // "content", "files_with_matches", or "count"
  context?: number,         // Lines of context before and after each match
  multiline?: boolean,      // Enable multiline matching
  head_limit?: number,      // Limit output to first N entries
  offset?: number,          // Skip first N entries
  "-i"?: boolean,           // Case insensitive search
  "-n"?: boolean,           // Show line numbers (default true)
  "-A"?: number,            // Lines to show after each match
  "-B"?: number,            // Lines to show before each match
  "-C"?: number,            // Alias for context
): string;
```

## Shell Execution

```ts
// Execute a bash command with optional timeout
function Bash(
  command: string,             // The command to execute
  description?: string,        // Clear description of what this command does
  timeout?: number,            // Optional timeout in milliseconds (max 600000)
  run_in_background?: boolean, // Run command in the background
): string;
```

## Web

```ts
// Search the web and return results with links
function WebSearch(
  query: string,                // The search query
  allowed_domains?: string[],   // Only include results from these domains
  blocked_domains?: string[],   // Exclude results from these domains
): string;

// Fetch and process content from a URL
function WebFetch(
  url: string,     // The URL to fetch content from
  prompt: string,  // What information to extract from the page
): string;
```

## Agents & Tasks

```ts
// Launch a specialized subagent for complex tasks
function Task(
  prompt: string,              // The task for the agent to perform
  description: string,         // Short 3-5 word summary
  subagent_type: string,       // Agent type (e.g., "Explore", "Plan", "Bash", "general-purpose")
  name?: string,               // Name for the spawned agent
  model?: string,              // Model override ("sonnet", "opus", "haiku")
  mode?: string,               // Permission mode (e.g., "plan", "bypassPermissions")
  resume?: string,             // Agent ID to resume from
  run_in_background?: boolean, // Run agent in background
  team_name?: string,          // Team name for spawning
  max_turns?: number,          // Max agentic turns before stopping
): string;

// Retrieve output from a running or completed background task
function TaskOutput(
  task_id: string,     // The task ID to get output from
  block?: boolean,     // Whether to wait for completion (default true)
  timeout?: number,    // Max wait time in ms (default 30000)
): string;

// Stop a running background task
function TaskStop(
  task_id?: string,    // The ID of the background task to stop
  shell_id?: string,   // Deprecated: use task_id instead
): void;

// Create a task in the task list
function TaskCreate(
  subject: string,        // Brief task title
  description: string,    // Detailed description of what needs to be done
  activeForm?: string,    // Present continuous form for spinner (e.g., "Running tests")
  metadata?: object,      // Arbitrary metadata to attach
): void;

// Retrieve a task by ID
function TaskGet(
  taskId: string,   // The ID of the task to retrieve
): Task;

// Update a task's status, details, or dependencies
function TaskUpdate(
  taskId: string,            // The ID of the task to update
  status?: string,           // "pending", "in_progress", "completed", or "deleted"
  subject?: string,          // New subject for the task
  description?: string,      // New description
  activeForm?: string,       // Present continuous form for spinner
  owner?: string,            // New owner agent name
  metadata?: object,         // Metadata keys to merge
  addBlocks?: string[],      // Task IDs this task blocks
  addBlockedBy?: string[],   // Task IDs that block this task
): void;

// List all tasks in the task list
function TaskList(): Task[];
```

## Teams & Messaging

```ts
// Create a new team for multi-agent coordination
function TeamCreate(
  team_name: string,      // Name for the new team
  description?: string,   // Team description/purpose
  agent_type?: string,    // Type/role of the team lead
): void;

// Remove team and task directories
function TeamDelete(): void;

// Send messages to agent teammates
function SendMessage(
  type: string,            // "message", "broadcast", "shutdown_request", "shutdown_response", "plan_approval_response"
  recipient?: string,      // Agent name of the recipient
  content?: string,        // Message text or feedback
  summary?: string,        // 5-10 word preview summary
  request_id?: string,     // Request ID for responses
  approve?: boolean,       // Whether to approve a request
): void;
```

## Planning & Interaction

```ts
// Transition into plan mode for implementation planning
function EnterPlanMode(): void;

// Signal plan is complete and ready for user approval
function ExitPlanMode(
  allowedPrompts?: AllowedPrompt[],  // Prompt-based permissions needed
): void;

// Ask the user a question with selectable options
function AskUserQuestion(
  questions: Question[],   // Array of 1-4 questions to ask the user
): Record<string, string>;

// Execute a skill/slash command within the conversation
function Skill(
  skill: string,   // The skill name (e.g., "commit", "review-pr")
  args?: string,   // Optional arguments for the skill
): void;
```

## Browser Automation

### Page Interaction

```ts
// Execute JavaScript in the context of a browser page
function mcp__claude_in_chrome__javascript_tool(
  action: string,    // Must be "javascript_exec"
  text: string,      // JavaScript code to evaluate in page context
  tabId: number,     // Tab ID to execute in
): string;

// Mouse, keyboard, and screenshot interactions
function mcp__claude_in_chrome__computer(
  action: string,              // "left_click", "type", "screenshot", "scroll", "key", etc.
  tabId: number,               // Tab ID to act on
  coordinate?: [number, number], // [x, y] pixel coordinates
  text?: string,               // Text to type or key to press
  scroll_direction?: string,   // "up", "down", "left", "right"
  scroll_amount?: number,      // Number of scroll ticks (1-10)
  duration?: number,           // Seconds to wait (for "wait" action)
  region?: [number, number, number, number], // [x0,y0,x1,y1] for "zoom"
  ref?: string,                // Element ref for "scroll_to"
  modifiers?: string,          // Modifier keys (e.g., "ctrl+shift")
  start_coordinate?: [number, number], // Start position for drag
  repeat?: number,             // Times to repeat key (1-100)
): string;

// Set values in form elements
function mcp__claude_in_chrome__form_input(
  ref: string,                       // Element reference ID (e.g., "ref_1")
  value: string | boolean | number,  // Value to set
  tabId: number,                     // Tab ID
): void;

// Upload a screenshot or image to a file input or drag target
function mcp__claude_in_chrome__upload_image(
  imageId: string,           // ID of a previously captured screenshot
  tabId: number,             // Tab ID where the target is
  ref?: string,              // Element ref for file inputs
  coordinate?: [number, number], // [x, y] for drag & drop targets
  filename?: string,         // Optional filename (default "image.png")
): void;
```

### Page Reading

```ts
// Get accessibility tree representation of page elements
function mcp__claude_in_chrome__read_page(
  tabId: number,         // Tab ID to read from
  depth?: number,        // Max tree depth (default 15)
  filter?: string,       // "interactive" or "all"
  max_chars?: number,    // Max output characters (default 50000)
  ref_id?: string,       // Focus on a specific element by ref ID
): string;

// Find elements on page using natural language
function mcp__claude_in_chrome__find(
  query: string,   // Natural language description (e.g., "search bar")
  tabId: number,   // Tab ID to search in
): Element[];

// Extract raw text content from a page
function mcp__claude_in_chrome__get_page_text(
  tabId: number,   // Tab ID to extract text from
): string;
```

### Navigation & Tabs

```ts
// Navigate to a URL or go forward/back
function mcp__claude_in_chrome__navigate(
  url: string,     // URL to navigate to, or "forward"/"back"
  tabId: number,   // Tab ID to navigate
): void;

// Resize browser window
function mcp__claude_in_chrome__resize_window(
  width: number,    // Target width in pixels
  height: number,   // Target height in pixels
  tabId: number,    // Tab ID to get window for
): void;

// Get context info about the current MCP tab group
function mcp__claude_in_chrome__tabs_context_mcp(
  createIfEmpty?: boolean,   // Create a new tab group if none exists
): TabContext;

// Create a new empty tab in the MCP tab group
function mcp__claude_in_chrome__tabs_create_mcp(): Tab;

// Present a plan to the user for domain approval
function mcp__claude_in_chrome__update_plan(
  domains: string[],      // Domains you will visit
  approach: string[],     // High-level steps you will take
): void;
```

### Debugging

```ts
// Read browser console messages
function mcp__claude_in_chrome__read_console_messages(
  tabId: number,         // Tab ID to read from
  pattern?: string,      // Regex pattern to filter messages
  limit?: number,        // Max messages to return (default 100)
  onlyErrors?: boolean,  // Only return errors/exceptions
  clear?: boolean,       // Clear messages after reading
): ConsoleMessage[];

// Read HTTP network requests from a tab
function mcp__claude_in_chrome__read_network_requests(
  tabId: number,          // Tab ID to read from
  urlPattern?: string,    // URL substring to filter requests
  limit?: number,         // Max requests to return (default 100)
  clear?: boolean,        // Clear requests after reading
): NetworkRequest[];
```

### Recording & Shortcuts

```ts
// Record and export browser actions as animated GIF
function mcp__claude_in_chrome__gif_creator(
  action: string,     // "start_recording", "stop_recording", "export", "clear"
  tabId: number,      // Tab ID for the recording
  download?: boolean, // Set true for export to download the GIF
  filename?: string,  // Optional filename for exported GIF
  options?: object,   // GIF enhancement options (click indicators, labels, etc.)
): void;

// List available shortcuts and workflows
function mcp__claude_in_chrome__shortcuts_list(
  tabId: number,   // Tab ID to list shortcuts from
): Shortcut[];

// Execute a shortcut or workflow
function mcp__claude_in_chrome__shortcuts_execute(
  tabId: number,          // Tab ID to execute on
  command?: string,       // Command name (e.g., "debug")
  shortcutId?: string,    // ID of the shortcut to execute
): void;
```
