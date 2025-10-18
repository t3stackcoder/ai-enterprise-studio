# Git Quick Reference

## Common Commands (In Order)

### Check Status
```bash
git status
```
Shows what files have changed, what's staged, and what's not tracked.

### Stage Changes
```bash
# Stage all changes (new, modified, deleted files)
git add -A

# Stage specific file
git add <filename>

# Stage all files in current directory
git add .
```

### Commit Changes
```bash
git commit -m "Your commit message"
```

### View Commit History
```bash
git log --oneline
```

### Create a New Branch
```bash
git checkout -b <branch-name>
```

### Switch Branches
```bash
git checkout <branch-name>
```

### Push to Remote
```bash
# First time push (set upstream)
git push -u origin <branch-name>

# After that
git push
```

### Pull Latest Changes
```bash
git pull
```

### Discard Uncommitted Changes
```bash
# Discard all changes
git reset --hard

# Discard changes to specific file
git checkout -- <filename>
```

## Typical Workflow

1. Make changes to your code
2. `git status` - See what changed
3. `git add -A` - Stage all changes
4. `git commit -m "Description of changes"` - Commit
5. `git push` - Push to remote (if set up)

## Tips

- Commit often with clear messages
- Always check `git status` before committing
- Use meaningful commit messages (what and why)
