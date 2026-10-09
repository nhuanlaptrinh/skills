# Rollback and partial installation

Backups default to `<backup-root>/member_<label>_sessions-70k/<UTC timestamp>/`.
They contain the original config, consistent SQLite snapshot, original cron,
and original registry (or a marker that no registry existed). Keep them private.

## Disable just this customer's automatic reset

1. Read current root cron, registry and project note, not only the old backup.
2. Remove only that customer's `member_<label>_sessions_70k` cron marker block.
   Leave every unrelated job intact. Read back cron to confirm removal.
3. Preserve the registry until you confirm no invocation remains. If removing
   its `member_<label>_sessions` entry, ensure it is this install's Zalo-only
   scope, not an unrelated maintenance job with the same name.
4. Keep the shared runner, launcher, logs and transcripts. Another customer
   may use them. Do not remove the whole Shared Watchdog Center.

This disables future resets; it does not undo a session already reset. Do not
restore the entire database over live conversations. Recovered context from
the preserved transcript archive requires explicit scope and a separately
reviewed recovery procedure.

## Restore a changed threshold or partial install

- Prefer changing this customer's registry command or re-running the installer
  with the requested threshold. Do not edit shared source constants.
- On an installer error after a backup path is printed, inspect that directory,
  current registry, runner and cron. It may have installed a runner/registry
  without scheduling cron. Never blindly overwrite current cron/registry with
  old files: reconcile only the customer's intended entry/block.
- Installer refuses an existing shared runner with different bytes. Review and
  back up all affected consumers before a controlled runtime upgrade; do not
  remove this guard simply to overwrite another customer's implementation.
- Authentication, unsupported RPC schema, missing runtime fields or a timed-out
  reset require manual review. A timeout has an uncertain outcome: re-list the
  session and verify identity before another reset. Never retry unchanged in a
  tight loop or replay old messages.
