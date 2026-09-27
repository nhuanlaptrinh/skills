import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { homedir } from 'node:os';
import path from 'node:path';
const execute = promisify(execFile);
export function voiceUrl(message) {
  let count = 0;
  function scan(value, depth = 0) {
    if (++count > 500 || depth > 8) return;
    if (typeof value === 'string') {
      for (const text of value.match(/https:\/\/[^\s"<>\\]+/g) ?? []) {
        try {
          const u = new URL(text);
          if (!u.username && !u.password && (!u.port || u.port === '443') &&
              ['zdn.vn', 'flchat.vn', 'dlfl.vn'].some(h => u.hostname === h || u.hostname.endsWith('.' + h)) &&
              /\.(aac|m4a|mp3|ogg|wav)$/i.test(u.pathname)) return text;
        } catch {}
      }
    } else if (value && typeof value === 'object') {
      for (const item of Object.values(value)) { const result = scan(item, depth + 1); if (result) return result; }
    }
  }
  return scan(message);
}
export async function transcribeVoice(message, run = execute) {
  const url = voiceUrl(message);
  if (!url) return null;
  const script = path.join(homedir(), '.openclaw/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_zalo_voice.py');
  const { stdout } = await run('python3', [script, url], { timeout: 190000, maxBuffer: 12000 });
  const text = stdout.trim().slice(0, 6000);
  if (!text) throw new Error('empty_transcript');
  return '[Nội dung người dùng nói trong tin nhắn thoại]\n' + text;
}
