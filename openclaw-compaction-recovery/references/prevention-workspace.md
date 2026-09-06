# Workspace guidance for tool-heavy sessions

Read existing scoped instructions, back up the workspace AGENTS file, and merge only when workspace-policy changes are authorized. Do not append duplicates: update the existing context-budget section if present. Preserve owner, routing, approval and privacy instructions. Roll this policy change back separately from the config helper's manifest.

Suggested short section:

```markdown
## Context budget for tool-heavy tasks

- Keep diagnostic tool output around 2,000 characters per response; expand only a relevant excerpt when necessary. Save full build/render/ffmpeg logs to task-local files and inspect bounded excerpts.
- Find filenames or matching lines before reading file ranges. Exclude dependencies, generated assets, binary media and archived sessions; never recursively dump a project, config or transcript into context.
- For media tasks, prefer canonical file paths, durations, dimensions and a few selected frames. Avoid repeated inline/base64 payloads and do not replay processed attachments just to reconstruct progress.
- Before a large next phase, checkpoint decisions, output paths and remaining work in a concise task-local note. Do not repeatedly reload session history already summarized. Never copy private DM history into a group.
- Respect context-pressure warnings. Do not keep retrying the same broad reads, disable safety guards or silently reset the session. Use semantic compaction when needed; /new is a user-controlled fresh start, not a permanent fix.
```

This limits requested behavior rather than enforcing a hard byte cap. If oversized output continues, inspect the exact tool's supported output-limit settings, worker/task design, and model/provider latency. Do not invent unsupported configuration keys, globally remove tools, or add an unreviewed always-on plugin.
