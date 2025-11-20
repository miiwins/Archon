# Claude Code Bug Report: Hung ripgrep Processes at Startup

## Summary

Claude Code spawns multiple `rg` (ripgrep) processes during startup that hang indefinitely with 80-100% CPU usage when scanning for slash commands. These processes use inefficient glob patterns that cause full filesystem scans.

## Environment

- **Claude Code Version**: 2.0.32
- **OS**: Linux (Ubuntu) 6.11.0-29-generic
- **Architecture**: x86_64
- **Shell**: bash
- **Working Directory**: `/home/juergen/archon`

## Affected Configuration

```
.claude/commands/
├── archon/ (8 commands)
├── prp-any-agent/ (2 commands)
└── prp-claude-code/ (4 commands)

Total: 13 slash command files (92K)
```

## Problem Description

### Observed Behavior

When starting Claude Code in a project with custom slash commands, multiple ripgrep processes are spawned that:

1. Run with 80-100% CPU usage
2. Continue indefinitely (observed running for over 1 hour)
3. Use inefficient search patterns
4. Run as root user (despite Claude Code running as normal user)

### Example Hung Processes

```bash
CPU%   MEM%   VIRT    RES     PID     USER   TIME+      Command
100    0      39.7M   3.86M   398922  root   01:03:52   rg --files --hidden --case-sensitive --no-require-git -g /home/juergen/archon/.claude/commands/archon/archon-ui-consistency-review.md -g !**/.git [...]

90.3   0      42.2M   5.04M   398908  root   01:03:04   rg --files --hidden --case-sensitive --no-require-git -g /home/juergen/archon/.claude/commands/archon/archon-rca.md -g !**/.git [...]

87.5   0      39.7M   5.03M   399051  root   01:02:34   rg --files --hidden --case-sensitive --no-require-git -g /home/juergen/archon/.claude/commands/prp-claude-code/prp-story-task-execute.md -g !**/.git [...]

80.6   0      42.2M   4.98M   399068  root   01:03:28   rg --files --hidden [similar pattern] [...]
```

## Root Cause Analysis

### Inefficient Pattern Usage

The command structure is contradictory:

```bash
rg --files -g /full/path/to/specific/file.md
```

**Problem**: This combination:
- `--files` lists ALL files in the directory tree
- `-g` tries to filter by a specific absolute path
- Results in a full filesystem scan with post-filtering

**Expected behavior**: Should directly read the file or use `find` with `-path` for exact matches.

### Missing Timeouts

The indexing operation has no timeout mechanism, allowing processes to run indefinitely.

### Permission Escalation

Processes run as `root` despite Claude Code being started by a normal user (`juergen`). This suggests either:
- A sudo wrapper in the initialization code
- Or container/docker execution context

## Reproduction Steps

1. Create a project with custom slash commands:
   ```bash
   mkdir -p myproject/.claude/commands/custom
   echo "---" > myproject/.claude/commands/custom/test.md
   echo "description: Test command" >> myproject/.claude/commands/custom/test.md
   echo "---" >> myproject/.claude/commands/custom/test.md
   ```

2. Start Claude Code in the project:
   ```bash
   cd myproject
   claude
   ```

3. Monitor processes:
   ```bash
   watch -n 1 'ps aux | grep "rg.*\.claude"'
   ```

4. Observe multiple `rg` processes with high CPU usage

**Note**: The issue appears to be more severe with:
- Multiple nested command directories
- Longer file paths
- Projects with large directory trees (e.g., node_modules present)

## Expected Behavior

Slash command indexing should:
1. Complete within 1-2 seconds
2. Use direct file reads instead of `rg --files`
3. Have a timeout (max 5 seconds)
4. Not require root permissions
5. Cache results to avoid re-scanning on every operation

### Suggested Fix

Replace:
```bash
rg --files -g /full/path/to/command.md
```

With either:
```bash
# Option 1: Direct file check
test -f /full/path/to/command.md && cat /full/path/to/command.md

# Option 2: Efficient find
find .claude/commands -name "*.md" -type f

# Option 3: Proper ripgrep usage (if needed)
rg --files .claude/commands --glob "*.md"
```

## Workarounds

### Immediate Fix
```bash
# Kill hung processes
pkill -9 -f "rg.*\.claude"
```

### Monitoring Script
```bash
#!/bin/bash
# Kill rg processes running longer than 5 minutes
for pid in $(ps aux | grep "rg.*\.claude" | awk '$10 > "00:05:00" {print $2}'); do
    kill -9 $pid
done
```

### Reduce Command Count
Temporarily disable unused slash commands:
```bash
mv .claude/commands .claude/commands.backup
mkdir .claude/commands
# Copy back only essential commands
```

## Impact

- **Severity**: High
- **Performance**: 300-400% CPU usage (multiple cores maxed out)
- **User Experience**: Claude Code becomes unresponsive during indexing
- **Resource Usage**: Can consume significant CPU for extended periods
- **Frequency**: Occurs on every startup with custom slash commands

## Additional Context

### Project Structure
The affected project (Archon) is a large monorepo with:
- React frontend (`archon-ui-main/`)
- Python backend (`python/`)
- Multiple service directories
- Total ~92K in `.claude/commands`

### Slash Command Examples
Commands are properly formatted with frontmatter:
```markdown
---
description: Generate Root Cause Analysis report
argument-hint: <issue description>
allowed-tools: Bash(*), Read, Grep, Write
---

# Command content here...
```

## Logs/Traces

Full process details captured:
```bash
ps aux | grep "rg.*\.claude"
# Output shows processes running as root with full command arguments
# (See "Observed Behavior" section above)
```

## Suggested Improvements

1. **Replace file scanning**: Use direct file reads or efficient glob patterns
2. **Add timeouts**: Maximum 5 seconds for command indexing
3. **Implement caching**: Cache command metadata, invalidate on file changes
4. **Add logging**: Debug logs for command discovery process
5. **Fix permissions**: Don't require root for file reads
6. **Progressive loading**: Load commands asynchronously without blocking
7. **File watchers**: Use `inotify` instead of repeated scans

## Related Issues

This may be related to how Claude Code discovers and loads custom slash commands at initialization time. The issue suggests the command discovery logic needs refactoring for better performance and reliability.

---

**Reporter**: @juergen (via Claude Code session)
**Date**: 2025-11-04
**Report Generated**: Automatically via `/archon:archon-rca` workflow
