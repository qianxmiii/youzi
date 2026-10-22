# Repository contribution rules

These rules apply to every Git commit and push in this repository.

## Required pre-commit review

1. Run `git status` and inspect both the staged and unstaged `git diff`.
2. Summarize the intended change and separate unrelated worktree changes.
3. Stage only explicitly selected files, listing each path. Never use `git add .`,
   `git add -A`, or another broad staging command.
4. Exclude temporary files, caches, build artifacts, editor settings, logs,
   databases, backups, and unrelated changes.
5. Scan every candidate file for secrets and sensitive data, including:
   API keys, tokens, passwords, cookies, database credentials or connection
   strings, `.env*` files, private keys, certificates, authorization files,
   customer personal data, shipment numbers, quotations, costs, billing data,
   SQLite databases, backups, and logs.
6. Verify that `.gitignore` covers `.env*`, database files, logs, caches, build
   artifacts, Python virtual environments, `node_modules`, and local IDE files.
7. Before staging or committing, report:
   - the exact candidate file list;
   - a concise change summary;
   - the proposed commit message;
   - any sensitive information, anomaly, or unrelated file found.
8. Wait for the user's explicit confirmation before running `git add`,
   `git commit`, `git push`, `git rebase`, `git reset`, or deleting files.
9. If sensitive information is found, stop before staging, committing, or
   pushing. Identify the affected file and risk, recommend remediation, and
   require a fresh user confirmation after remediation.
10. After confirmation, create one clear commit for the approved scope and push
    it to the current branch.
11. Never use `--force` or `--force-with-lease` unless the user explicitly
    authorizes that exact operation.

## Documentation and changelog rules

These documentation rules apply to all work in `youzi_v2/`, independently of
whether a commit is requested.

- Follow [the changelog policy](youzi_v2/docs/changelog-policy.md) when editing
  `youzi_v2/CHANGELOG.md` or its annual archives.
- Check relevant documentation after code changes. Add changelog entries only
  for completed user-visible changes or important upgrade requirements; do not
  create an entry for every edit, internal refactor, or cosmetic adjustment.
- Preserve migration, configuration, dependency, and compatibility requirements;
  keep implementation details in the corresponding technical documentation.
- Never put actual prices, costs, customer data, shipment identifiers, or secrets
  in changelogs or archives. Keep this policy authoritative rather than copying
  divergent versions into editor-specific rules.
