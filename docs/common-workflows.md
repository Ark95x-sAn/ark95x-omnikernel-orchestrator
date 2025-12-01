# Common Workflows with Claude Code

> Learn about common workflows with Claude Code.

Each task in this document includes clear instructions, example commands, and best practices to help you get the most from Claude Code.

## Table of Contents

- [Understand New Codebases](#understand-new-codebases)
- [Fix Bugs Efficiently](#fix-bugs-efficiently)
- [Refactor Code](#refactor-code)
- [Use Specialized Subagents](#use-specialized-subagents)
- [Use Plan Mode for Safe Code Analysis](#use-plan-mode-for-safe-code-analysis)
- [Work with Tests](#work-with-tests)
- [Create Pull Requests](#create-pull-requests)
- [Handle Documentation](#handle-documentation)
- [Work with Images](#work-with-images)
- [Reference Files and Directories](#reference-files-and-directories)
- [Use Extended Thinking](#use-extended-thinking)
- [Resume Previous Conversations](#resume-previous-conversations)
- [Run Parallel Claude Code Sessions with Git Worktrees](#run-parallel-claude-code-sessions-with-git-worktrees)
- [Use Claude as a Unix-style Utility](#use-claude-as-a-unix-style-utility)
- [Create Custom Slash Commands](#create-custom-slash-commands)
- [Ask Claude About Its Capabilities](#ask-claude-about-its-capabilities)

---

## Understand New Codebases

### Get a Quick Codebase Overview

Suppose you've just joined a new project and need to understand its structure quickly.

**Step 1: Navigate to the project root directory**

```bash
cd /path/to/project
```

**Step 2: Start Claude Code**

```bash
claude
```

**Step 3: Ask for a high-level overview**

```
> give me an overview of this codebase
```

**Step 4: Dive deeper into specific components**

```
> explain the main architecture patterns used here
```

```
> what are the key data models?
```

```
> how is authentication handled?
```

**Tips:**
- Start with broad questions, then narrow down to specific areas
- Ask about coding conventions and patterns used in the project
- Request a glossary of project-specific terms

### Find Relevant Code

Suppose you need to locate code related to a specific feature or functionality.

**Step 1: Ask Claude to find relevant files**

```
> find the files that handle user authentication
```

**Step 2: Get context on how components interact**

```
> how do these authentication files work together?
```

**Step 3: Understand the execution flow**

```
> trace the login process from front-end to database
```

**Tips:**
- Be specific about what you're looking for
- Use domain language from the project

---

## Fix Bugs Efficiently

Suppose you've encountered an error message and need to find and fix its source.

**Step 1: Share the error with Claude**

```
> I'm seeing an error when I run npm test
```

**Step 2: Ask for fix recommendations**

```
> suggest a few ways to fix the @ts-ignore in user.ts
```

**Step 3: Apply the fix**

```
> update user.ts to add the null check you suggested
```

**Tips:**
- Tell Claude the command to reproduce the issue and get a stack trace
- Mention any steps to reproduce the error
- Let Claude know if the error is intermittent or consistent

---

## Refactor Code

Suppose you need to update old code to use modern patterns and practices.

**Step 1: Identify legacy code for refactoring**

```
> find deprecated API usage in our codebase
```

**Step 2: Get refactoring recommendations**

```
> suggest how to refactor utils.js to use modern JavaScript features
```

**Step 3: Apply the changes safely**

```
> refactor utils.js to use ES2024 features while maintaining the same behavior
```

**Step 4: Verify the refactoring**

```
> run tests for the refactored code
```

**Tips:**
- Ask Claude to explain the benefits of the modern approach
- Request that changes maintain backward compatibility when needed
- Do refactoring in small, testable increments

---

## Use Specialized Subagents

Suppose you want to use specialized AI subagents to handle specific tasks more effectively.

**Step 1: View available subagents**

```
> /agents
```

This shows all available subagents and lets you create new ones.

**Step 2: Use subagents automatically**

Claude Code will automatically delegate appropriate tasks to specialized subagents:

```
> review my recent code changes for security issues
```

```
> run all tests and fix any failures
```

**Step 3: Explicitly request specific subagents**

```
> use the code-reviewer subagent to check the auth module
```

```
> have the debugger subagent investigate why users can't log in
```

**Step 4: Create custom subagents for your workflow**

```
> /agents
```

Then select "Create New subagent" and follow the prompts to define:
- Subagent type (e.g., `api-designer`, `performance-optimizer`)
- When to use it
- Which tools it can access
- Its specialized system prompt

**Tips:**
- Create project-specific subagents in `.claude/agents/` for team sharing
- Use descriptive `description` fields to enable automatic delegation
- Limit tool access to what each subagent actually needs
- Check the subagents documentation for detailed examples

---

## Use Plan Mode for Safe Code Analysis

Plan Mode instructs Claude to create a plan by analyzing the codebase with read-only operations, perfect for exploring codebases, planning complex changes, or reviewing code safely.

### When to Use Plan Mode

- **Multi-step implementation**: When your feature requires making edits to many files
- **Code exploration**: When you want to research the codebase thoroughly before changing anything
- **Interactive development**: When you want to iterate on the direction with Claude

### How to Use Plan Mode

**Turn on Plan Mode during a session**

You can switch into Plan Mode during a session using **Shift+Tab** to cycle through permission modes.

If you are in Normal Mode, **Shift+Tab** will first switch into Auto-Accept Mode, indicated by `⏵⏵ accept edits on` at the bottom of the terminal. A subsequent **Shift+Tab** will switch into Plan Mode, indicated by `⏸ plan mode on`.

**Start a new session in Plan Mode**

To start a new session in Plan Mode, use the `--permission-mode plan` flag:

```bash
claude --permission-mode plan
```

**Run "headless" queries in Plan Mode**

You can also run a query in Plan Mode directly with `-p` (i.e., in "headless mode"):

```bash
claude --permission-mode plan -p "Analyze the authentication system and suggest improvements"
```

### Example: Planning a Complex Refactor

```bash
claude --permission-mode plan
```

```
> I need to refactor our authentication system to use OAuth2. Create a detailed migration plan.
```

Claude will analyze the current implementation and create a comprehensive plan. Refine with follow-ups:

```
> What about backward compatibility?
> How should we handle database migration?
```

### Configure Plan Mode as Default

```json
// .claude/settings.json
{
  "permissions": {
    "defaultMode": "plan"
  }
}
```

See the settings documentation for more configuration options.

---

## Work with Tests

Suppose you need to add tests for uncovered code.

**Step 1: Identify untested code**

```
> find functions in NotificationsService.swift that are not covered by tests
```

**Step 2: Generate test scaffolding**

```
> add tests for the notification service
```

**Step 3: Add meaningful test cases**

```
> add test cases for edge conditions in the notification service
```

**Step 4: Run and verify tests**

```
> run the new tests and fix any failures
```

**Tips:**
- Ask for tests that cover edge cases and error conditions
- Request both unit and integration tests when appropriate
- Have Claude explain the testing strategy

---

## Create Pull Requests

Suppose you need to create a well-documented pull request for your changes.

**Step 1: Summarize your changes**

```
> summarize the changes I've made to the authentication module
```

**Step 2: Generate a PR with Claude**

```
> create a pr
```

**Step 3: Review and refine**

```
> enhance the PR description with more context about the security improvements
```

**Step 4: Add testing details**

```
> add information about how these changes were tested
```

**Tips:**
- Ask Claude directly to make a PR for you
- Review Claude's generated PR before submitting
- Ask Claude to highlight potential risks or considerations

---

## Handle Documentation

Suppose you need to add or update documentation for your code.

**Step 1: Identify undocumented code**

```
> find functions without proper JSDoc comments in the auth module
```

**Step 2: Generate documentation**

```
> add JSDoc comments to the undocumented functions in auth.js
```

**Step 3: Review and enhance**

```
> improve the generated documentation with more context and examples
```

**Step 4: Verify documentation**

```
> check if the documentation follows our project standards
```

**Tips:**
- Specify the documentation style you want (JSDoc, docstrings, etc.)
- Ask for examples in the documentation
- Request documentation for public APIs, interfaces, and complex logic

---

## Work with Images

Suppose you need to work with images in your codebase, and you want Claude's help analyzing image content.

**Step 1: Add an image to the conversation**

You can use any of these methods:
1. Drag and drop an image into the Claude Code window
2. Copy an image and paste it into the CLI with ctrl+v (Do not use cmd+v)
3. Provide an image path to Claude. E.g., "Analyze this image: /path/to/your/image.png"

**Step 2: Ask Claude to analyze the image**

```
> What does this image show?
```

```
> Describe the UI elements in this screenshot
```

```
> Are there any problematic elements in this diagram?
```

**Step 3: Use images for context**

```
> Here's a screenshot of the error. What's causing it?
```

```
> This is our current database schema. How should we modify it for the new feature?
```

**Step 4: Get code suggestions from visual content**

```
> Generate CSS to match this design mockup
```

```
> What HTML structure would recreate this component?
```

**Tips:**
- Use images when text descriptions would be unclear or cumbersome
- Include screenshots of errors, UI designs, or diagrams for better context
- You can work with multiple images in a conversation
- Image analysis works with diagrams, screenshots, mockups, and more

---

## Reference Files and Directories

Use @ to quickly include files or directories without waiting for Claude to read them.

**Reference a single file**

```
> Explain the logic in @src/utils/auth.js
```

This includes the full content of the file in the conversation.

**Reference a directory**

```
> What's the structure of @src/components?
```

This provides a directory listing with file information.

**Reference MCP resources**

```
> Show me the data from @github:repos/owner/repo/issues
```

This fetches data from connected MCP servers using the format @server:resource. See MCP resources documentation for details.

**Tips:**
- File paths can be relative or absolute
- @ file references add CLAUDE.md in the file's directory and parent directories to context
- Directory references show file listings, not contents
- You can reference multiple files in a single message (e.g., "@file1.js and @file2.js")

---

## Use Extended Thinking

Suppose you're working on complex architectural decisions, challenging bugs, or planning multi-step implementations that require deep reasoning.

> **Note:** Extended thinking is disabled by default in Claude Code. You can enable it on-demand by using `Tab` to toggle Thinking on, or by using prompts like "think" or "think hard". You can also enable it permanently by setting the `MAX_THINKING_TOKENS` environment variable in your settings.

**Step 1: Provide context and ask Claude to think**

```
> I need to implement a new authentication system using OAuth2 for our API. Think deeply about the best approach for implementing this in our codebase.
```

Claude will gather relevant information from your codebase and use extended thinking, which will be visible in the interface.

**Step 2: Refine the thinking with follow-up prompts**

```
> think about potential security vulnerabilities in this approach
```

```
> think hard about edge cases we should handle
```

**Tips to get the most value out of extended thinking:**

Extended thinking is most valuable for complex tasks such as:
- Planning complex architectural changes
- Debugging intricate issues
- Creating implementation plans for new features
- Understanding complex codebases
- Evaluating tradeoffs between different approaches

Use `Tab` to toggle Thinking on and off during a session.

The way you prompt for thinking results in varying levels of thinking depth:
- "think" triggers basic extended thinking
- intensifying phrases such as "think hard", "think more", "think a lot", or "think longer" triggers deeper thinking

> **Note:** Claude will display its thinking process as italic gray text above the response.

---

## Resume Previous Conversations

Suppose you've been working on a task with Claude Code and need to continue where you left off in a later session.

Claude Code provides two options for resuming previous conversations:
- `--continue` to automatically continue the most recent conversation
- `--resume` to display a conversation picker

**Step 1: Continue the most recent conversation**

```bash
claude --continue
```

This immediately resumes your most recent conversation without any prompts.

**Step 2: Continue in non-interactive mode**

```bash
claude --continue --print "Continue with my task"
```

Use `--print` with `--continue` to resume the most recent conversation in non-interactive mode, perfect for scripts or automation.

**Step 3: Show conversation picker**

```bash
claude --resume
```

This displays an interactive conversation selector with a clean list view showing:
- Session summary (or initial prompt)
- Metadata: time elapsed, message count, and git branch

Use arrow keys to navigate and press Enter to select a conversation. Press Esc to exit.

**Tips:**
- Conversation history is stored locally on your machine
- Use `--continue` for quick access to your most recent conversation
- Use `--resume` when you need to select a specific past conversation
- When resuming, you'll see the entire conversation history before continuing
- The resumed conversation starts with the same model and configuration as the original

**How it works:**
1. **Conversation Storage**: All conversations are automatically saved locally with their full message history
2. **Message Deserialization**: When resuming, the entire message history is restored to maintain context
3. **Tool State**: Tool usage and results from the previous conversation are preserved
4. **Context Restoration**: The conversation resumes with all previous context intact

**Examples:**

```bash
# Continue most recent conversation
claude --continue

# Continue most recent conversation with a specific prompt
claude --continue --print "Show me our progress"

# Show conversation picker
claude --resume

# Continue most recent conversation in non-interactive mode
claude --continue --print "Run the tests again"
```

---

## Run Parallel Claude Code Sessions with Git Worktrees

Suppose you need to work on multiple tasks simultaneously with complete code isolation between Claude Code instances.

**Step 1: Understand Git worktrees**

Git worktrees allow you to check out multiple branches from the same repository into separate directories. Each worktree has its own working directory with isolated files, while sharing the same Git history. Learn more in the [official Git worktree documentation](https://git-scm.com/docs/git-worktree).

**Step 2: Create a new worktree**

```bash
# Create a new worktree with a new branch
git worktree add ../project-feature-a -b feature-a

# Or create a worktree with an existing branch
git worktree add ../project-bugfix bugfix-123
```

This creates a new directory with a separate working copy of your repository.

**Step 3: Run Claude Code in each worktree**

```bash
# Navigate to your worktree
cd ../project-feature-a

# Run Claude Code in this isolated environment
claude
```

**Step 4: Run Claude in another worktree**

```bash
cd ../project-bugfix
claude
```

**Step 5: Manage your worktrees**

```bash
# List all worktrees
git worktree list

# Remove a worktree when done
git worktree remove ../project-feature-a
```

**Tips:**
- Each worktree has its own independent file state, making it perfect for parallel Claude Code sessions
- Changes made in one worktree won't affect others, preventing Claude instances from interfering with each other
- All worktrees share the same Git history and remote connections
- For long-running tasks, you can have Claude working in one worktree while you continue development in another
- Use descriptive directory names to easily identify which task each worktree is for
- Remember to initialize your development environment in each new worktree according to your project's setup. Depending on your stack, this might include:
  - JavaScript projects: Running dependency installation (`npm install`, `yarn`)
  - Python projects: Setting up virtual environments or installing with package managers
  - Other languages: Following your project's standard setup process

---

## Use Claude as a Unix-style Utility

### Add Claude to Your Verification Process

Suppose you want to use Claude Code as a linter or code reviewer.

**Add Claude to your build script:**

```json
// package.json
{
    "scripts": {
        "lint:claude": "claude -p 'you are a linter. please look at the changes vs. main and report any issues related to typos. report the filename and line number on one line, and a description of the issue on the second line. do not return any other text.'"
    }
}
```

**Tips:**
- Use Claude for automated code review in your CI/CD pipeline
- Customize the prompt to check for specific issues relevant to your project
- Consider creating multiple scripts for different types of verification

### Pipe In, Pipe Out

Suppose you want to pipe data into Claude, and get back data in a structured format.

**Pipe data through Claude:**

```bash
cat build-error.txt | claude -p 'concisely explain the root cause of this build error' > output.txt
```

**Tips:**
- Use pipes to integrate Claude into existing shell scripts
- Combine with other Unix tools for powerful workflows
- Consider using --output-format for structured output

### Control Output Format

Suppose you need Claude's output in a specific format, especially when integrating Claude Code into scripts or other tools.

**Use text format (default)**

```bash
cat data.txt | claude -p 'summarize this data' --output-format text > summary.txt
```

This outputs just Claude's plain text response (default behavior).

**Use JSON format**

```bash
cat code.py | claude -p 'analyze this code for bugs' --output-format json > analysis.json
```

This outputs a JSON array of messages with metadata including cost and duration.

**Use streaming JSON format**

```bash
cat log.txt | claude -p 'parse this log file for errors' --output-format stream-json
```

This outputs a series of JSON objects in real-time as Claude processes the request. Each message is a valid JSON object, but the entire output is not valid JSON if concatenated.

**Tips:**
- Use `--output-format text` for simple integrations where you just need Claude's response
- Use `--output-format json` when you need the full conversation log
- Use `--output-format stream-json` for real-time output of each conversation turn

---

## Create Custom Slash Commands

Claude Code supports custom slash commands that you can create to quickly execute specific prompts or tasks.

For more details, see the Slash commands reference page.

### Create Project-Specific Commands

Suppose you want to create reusable slash commands for your project that all team members can use.

**Step 1: Create a commands directory in your project**

```bash
mkdir -p .claude/commands
```

**Step 2: Create a Markdown file for each command**

```bash
echo "Analyze the performance of this code and suggest three specific optimizations:" > .claude/commands/optimize.md
```

**Step 3: Use your custom command in Claude Code**

```
> /optimize
```

**Tips:**
- Command names are derived from the filename (e.g., `optimize.md` becomes `/optimize`)
- You can organize commands in subdirectories (e.g., `.claude/commands/frontend/component.md` creates `/component` with "(project:frontend)" shown in the description)
- Project commands are available to everyone who clones the repository
- The Markdown file content becomes the prompt sent to Claude when the command is invoked

### Add Command Arguments with $ARGUMENTS

Suppose you want to create flexible slash commands that can accept additional input from users.

**Step 1: Create a command file with the $ARGUMENTS placeholder**

```bash
echo 'Find and fix issue #$ARGUMENTS. Follow these steps: 1. Understand the issue described in the ticket 2. Locate the relevant code in our codebase 3. Implement a solution that addresses the root cause 4. Add appropriate tests 5. Prepare a concise PR description' > .claude/commands/fix-issue.md
```

**Step 2: Use the command with an issue number**

In your Claude session, use the command with arguments.

```
> /fix-issue 123
```

This will replace $ARGUMENTS with "123" in the prompt.

**Tips:**
- The $ARGUMENTS placeholder is replaced with any text that follows the command
- You can position $ARGUMENTS anywhere in your command template
- Other useful applications: generating test cases for specific functions, creating documentation for components, reviewing code in particular files, or translating content to specified languages

### Create Personal Slash Commands

Suppose you want to create personal slash commands that work across all your projects.

**Step 1: Create a commands directory in your home folder**

```bash
mkdir -p ~/.claude/commands
```

**Step 2: Create a Markdown file for each command**

```bash
echo "Review this code for security vulnerabilities, focusing on:" > ~/.claude/commands/security-review.md
```

**Step 3: Use your personal custom command**

```
> /security-review
```

**Tips:**
- Personal commands show "(user)" in their description when listed with `/help`
- Personal commands are only available to you and not shared with your team
- Personal commands work across all your projects
- You can use these for consistent workflows across different codebases

---

## Ask Claude About Its Capabilities

Claude has built-in access to its documentation and can answer questions about its own features and limitations.

### Example Questions

```
> can Claude Code create pull requests?
```

```
> how does Claude Code handle permissions?
```

```
> what slash commands are available?
```

```
> how do I use MCP with Claude Code?
```

```
> how do I configure Claude Code for Amazon Bedrock?
```

```
> what are the limitations of Claude Code?
```

> **Note:** Claude provides documentation-based answers to these questions. For executable examples and hands-on demonstrations, refer to the specific workflow sections above.

**Tips:**
- Claude always has access to the latest Claude Code documentation, regardless of the version you're using
- Ask specific questions to get detailed answers
- Claude can explain complex features like MCP integration, enterprise configurations, and advanced workflows

---

## Next Steps

Clone the [Claude Code reference implementation](https://github.com/anthropics/claude-code/tree/main/.devcontainer) for a development container setup.

---

> To find navigation and other pages in the Claude Code documentation, fetch the llms.txt file at: https://code.claude.com/docs/llms.txt
