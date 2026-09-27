#!/usr/bin/env python3
"""Explicit active monitor path required. Dry-run default; never restarts services."""
import argparse,datetime,pathlib,shutil,subprocess
p=argparse.ArgumentParser();p.add_argument('--monitor',type=pathlib.Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
s=a.monitor.read_text(); marker='// managed-zalo-voice-intake-v1'
if marker in s: print('already_patched');raise SystemExit(0)
changes=[('const rawBody = message.content?.trim();','let rawBody = message.content?.trim() || (voiceUrl(message) ? "[Tin nhắn thoại]" : "");'),('const commandBody = message.commandContent?.trim() || rawBody;','let commandBody = message.commandContent?.trim() || rawBody;')]
anchor='\tconst fromLabel = isGroup ? groupName || `group:${chatId}` : senderName || `user:${senderId}`;'
insert='''\t// Transcribe only after sender/group/mention admission; never log URL or transcript.
\ttry {
\t\tconst voiceText = await transcribeVoice(message);
\t\tif (voiceText) { rawBody = voiceText; commandBody = voiceText; runtime.log("[zalouser-audio] transcription ok"); }
\t} catch { rawBody = "[Không phiên âm được tin nhắn thoại: bước tải audio hoặc STT thất bại. Không suy đoán nội dung.]"; commandBody = rawBody; runtime.log("[zalouser-audio] transcription failed"); }
'''
changes.append((anchor,insert+anchor))
for old,new in changes:
 if s.count(old)!=1:raise SystemExit('unsupported_anchor; no changes')
 s=s.replace(old,new)
s=marker+'\nimport { voiceUrl, transcribeVoice } from "./zalo_voice_intake.mjs";\n'+s
print('candidate_ready')
if not a.apply:raise SystemExit(0)
b=pathlib.Path('/root/_Backups/zalo-voice-intake')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');b.mkdir(parents=True,mode=0o700)
shutil.copy2(a.monitor,b/a.monitor.name)
helper=a.monitor.parent/'zalo_voice_intake.mjs'
if helper.exists():shutil.copy2(helper,b/helper.name)
shutil.copy2(pathlib.Path(__file__).with_name('zalo_voice_intake.mjs'),helper)
tmp=a.monitor.with_name('voice-candidate.mjs');tmp.write_text(s)
subprocess.run(['node','--check',str(tmp)],check=True);subprocess.run(['node','--check',str(helper)],check=True)
shutil.copymode(a.monitor,tmp);tmp.replace(a.monitor)
print('backup='+str(b))
