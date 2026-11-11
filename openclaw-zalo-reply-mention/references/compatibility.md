# Version-specific reference implementation

Observed on Linux in Docker: OpenClaw `2026.11.3` (build `847611d`) with `@openclaw/zalouser` `2026.11.3`. The accompanying patch was derived from that build and includes both the inbound reply callback and the durable outbound path. Offline tests passed there; the owner later reported a tagged reply, but native rendering was not independently verified. The durable path and Windows/macOS have not been verified end-to-end. This is an unsupported local bundle patch, not a stable API.

## What it changes

- Passes only the current inbound `senderId` and `senderName`, never `quotedOwnerId`, into a group reply; DMs remain unchanged.
- For group durable delivery, carries the sender plus account/group IDs in an extra field of outbound `identity`; the plugin checks account and group match before using it. The current version's queue projects this field into durable storage. This is an internal implementation detail: inspect and retest the host's full delivery and retry paths before relying on it. Do not claim it is an official extension point.
- Adds a prefix after Markdown rendering and attaches `mentions: [{uid, pos: 0, len}]` using UTF-16 string lengths; shifts styles and retains the mention in the first chunk. Native `zca-js` sending must receive the entity for text, image caption and voice text. If the sender ID/name is unavailable, the patch does not fabricate a tag.
- Only ordinary reply paths are covered; tool sends, background messages, hooks, provider updates, retries, and delivery-queue behavior require separate testing. Version changes can invalidate the patch or overwrite it.

## Apply only after inspection and consent

Use Git and Node.js available in the target runtime. The patch contains **no credentials** and is relative to the plugin's `dist/.setup` directory. Locate the active plugin directory from the runtime's actual installation and verify `package.json` and OpenClaw versions; do not assume npm/project paths or container host paths are identical.

1. Privately back up all four affected `.mjs` files. Do not change configuration or Zalo sessions. Save a rollback plan; do not replace live credential databases from backup.
2. From the plugin `dist/.setup` directory, with an absolute path to `zalouser-2026.11.3.patch`, run `git apply --check <patch-path>`. A failure means stop and adapt/retest, not force apply. Review the diff against the actual source. A passing context check is necessary but not sufficient to establish compatibility.
3. Apply with `git apply <patch-path>` only after authorization and after quiescing the gateway if required. Verify all four files and run `node --check` for each. Run the portable offline test script with the path to the patched directory and to the installed OpenClaw `plugin-sdk/text-chunking.js` module. For example, on any OS with Node:

   `node <skill-dir>/scripts/test-mention.mjs <patched-setup-dir> <absolute-text-chunking-module>`

   The test uses mocks for delivery, not a real Zalo connection or the full durable runtime. Investigate and roll back on failure. Verify delivery queue serialization and native API behavior independently.
4. Restart only the gateway using the installed service manager after the owner permits interruption. Probe all accounts and request an owner-led group test. Backups must remain private. If health regresses, restore only the plugin files, restart the same gateway and re-probe; do not reset or replace sessions.

Use appropriate PowerShell quoting on Windows; Linux/macOS shell examples cannot be pasted blindly. For Docker, perform checks inside the container and back up its persistent volume. If Git, Node, the plugin or supervisor differ or are unavailable, stop rather than claiming universal compatibility.
