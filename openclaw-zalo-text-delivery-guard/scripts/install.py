import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SUPPORTED_VERSION = "2026.9.9"


class WatchdogBusy(RuntimeError):
    pass


RUNTIME = '''import json,os,pathlib,shutil,subprocess,sys,time
request=json.load(sys.stdin)
pid=None
for attempt in range(45):
 result=subprocess.run(["pgrep","-f","^openclaw-gateway$"],capture_output=True,text=True)
 found=result.stdout.strip().splitlines()
 if result.returncode==0 and len(found)==1:pid=found[0];break
 if len(found)>1:raise SystemExit("Multiple Gateways")
 time.sleep(1)
if not pid:raise SystemExit("Gateway unavailable")
env=dict(os.environ)
for item in pathlib.Path("/proc/"+pid+"/environ").read_bytes().split(b"\\0"):
 if b"=" in item:
  key,value=item.split(b"=",1);env[key.decode()]=value.decode()
if request=="info":
 status=pathlib.Path("/proc/"+pid+"/status").read_text()
 parent=next(line.split()[1] for line in status.splitlines() if line.startswith("PPid:"))
 manager=pathlib.Path("/proc/"+parent+"/comm").read_text().strip()
 core=pathlib.Path(shutil.which("openclaw",path=env.get("PATH"))).resolve().parent/"dist"
 print(json.dumps({"home":env.get("HOME"),"pid":int(pid),"manager":manager,"coreDist":str(core)}))
else:
 os.execvpe("timeout",["timeout","--kill-after=5s","60s","openclaw",*request],env)
'''


def command(arguments, *, input_text=None, check=True, timeout=150):
    result = subprocess.run(arguments, input=input_text, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"Command failed: {arguments[0]} (exit {result.returncode})")
    return result


def runtime(container, arguments, check=True):
    return command(["docker", "exec", "-i", container, "python3", "-c", RUNTIME], input_text=json.dumps(arguments), check=check)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Missing or ambiguous reviewed patch anchor")
    return source.replace(old, new, 1)


def patch_sources(sources, guard_path):
    imports = {
        "send": f'import {{ sendGuardedText }} from {json.dumps(guard_path)};\n',
        "monitor": f'import {{ getTextDeliveryContext }} from {json.dumps(guard_path)};\n',
        "low": f'import {{ numericErrorCode }} from {json.dumps(guard_path)};\n',
    }
    present = ["zalo-text-delivery-guard/guard.mjs" in source for source in sources.values()]
    if any(present):
        if not all(present) or any(imports[name] not in sources[name] for name in imports):
            raise ValueError("Partial or differently scoped guard installation; inspect manually")
        markers = {"send": "function preparePlainZalouserText(input)", "monitor": "bodyForAgent: textDeliveryContext ?", "low": 'errorKind: error?.name === "ZcaApiError"'}
        if any(marker not in sources[name] for name, marker in markers.items()):
            raise ValueError("Unrecognized existing guard implementation")
        return dict(sources)
    patched = dict(sources)
    patched["send"] = replace_once(patched["send"], 'import { randomUUID } from "node:crypto";\n', 'import { randomUUID } from "node:crypto";\n' + imports["send"])
    helper = '''const ZALO_TEXT_LIMIT = 2e3;
function preparePlainZalouserText(input) {
\treturn renderMarkdownWithAttributedRanges(parseSharedIR(input), {
\t\tstyleMap: {},
\t\trenderLink: (link, label) => link.href === label ? "" : ` (${link.href})`,
\t\ttrimEnd: false
\t}).text;
}'''
    patched["send"] = replace_once(patched["send"], "const ZALO_TEXT_LIMIT = 2e3;", helper)
    anchor = "\tconst { onDeliveryResult, ...transportOptions } = options;\n"
    dispatch = '''\tif (!transportOptions.mediaUrl) return sendGuardedText({
\t\tthreadId,
\t\ttext: transportOptions.textMode === "markdown" ? preparePlainZalouserText(text) : text,
\t\toptions: transportOptions,
\t\tsend: sendZaloTextMessage,
\t\tonDeliveryResult,
\t\tcreateReceipt: createZalouserSendReceipt,
\t\tcreatePartialError: createChannelPartialDeliveryError
\t});
'''
    patched["send"] = replace_once(patched["send"], anchor, anchor + dispatch)
    patched["monitor"] = imports["monitor"] + patched["monitor"]
    anchor = '\tconst normalizedTo = isGroup ? `zalouser:group:${chatId}` : `zalouser:${chatId}`;\n'
    patched["monitor"] = replace_once(patched["monitor"], anchor, anchor + "\tconst textDeliveryContext = getTextDeliveryContext(chatId, { profile: account.profile, isGroup });\n")
    patched["monitor"] = replace_once(patched["monitor"], "\t\t\tbodyForAgent: rawBody,", "\t\t\tbodyForAgent: textDeliveryContext ? `${rawBody}\\n\\n${textDeliveryContext}` : rawBody,")
    patched["low"] = replace_once(patched["low"], 'import { randomUUID } from "node:crypto";\n', 'import { randomUUID } from "node:crypto";\n' + imports["low"])
    anchor = "\t\t\terror: formatErrorMessage(error),\n\t\t\treceipt: createZalouserSendReceipt({\n\t\t\t\tmessageId: textMessageId,"
    replacement = '''\t\t\terror: formatErrorMessage(error),
\t\t\terrorCode: numericErrorCode(error?.code),
\t\t\terrorKind: error?.name === "ZcaApiError" && numericErrorCode(error?.code) !== null && numericErrorCode(error?.code) !== 0 ? "api_rejected" : "unknown",
\t\t\treceipt: createZalouserSendReceipt({
\t\t\t\tmessageId: textMessageId,'''
    patched["low"] = replace_once(patched["low"], anchor, replacement)
    old_gap = "const LISTENER_WATCHDOG_MAX_GAP_MS = 35e3;"
    new_gap = "const LISTENER_WATCHDOG_MAX_GAP_MS = 180e3;"
    if old_gap in patched["low"]:
        patched["low"] = replace_once(patched["low"], old_gap, new_gap)
    elif patched["low"].count(new_gap) != 1:
        raise ValueError("Unreviewed watchdog setting")
    return patched


def channel_health(output):
    lines = [line for line in output.splitlines() if line.startswith(("- Zalo Personal", "- Telegram"))]
    return {"zalo": any(line.startswith("- Zalo Personal") and re.search(r"(?:,|\s)running(?:,|\s)", line) and "works" in line for line in lines),
            "telegram": any(line.startswith("- Telegram") and re.search(r"(?:,|\s)running(?:,|\s)", line) and "works" in line for line in lines),
            "zalo_authentication_failed": any("not authenticated" in line or "Đăng nhập thất bại" in line for line in lines)}


def atomic_write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
    os.replace(temporary, path)


@contextlib.contextmanager
def member_locks(label):
    registry = Path("/root/Automation/watchdog/shared_self_healing/project_config.json")
    with contextlib.ExitStack() as stack:
        lock_paths = [f"/tmp/openclaw-zalo-text-{label}.lock"]
        if registry.exists():
            entries = json.loads(registry.read_text())
            entries = entries.get("projects", entries)
            lock_paths = sorted(set(lock_paths) | {value["lock_file"] for key, value in entries.items() if key.startswith(f"member_{label}_") and isinstance(value, dict) and value.get("lock_file")})
        for path in lock_paths:
            handle = stack.enter_context(open(path, "a"))
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WatchdogBusy("Member watchdog is active; retry when idle") from error
        yield len(lock_paths)


def execute(arguments):
    info = json.loads(runtime(arguments.container, "info").stdout)
    if info["home"] != arguments.member_home or info["manager"] != "supervisord":
        raise ValueError("Actual HOME or Gateway manager does not match supplied member")
    data = Path(arguments.member_data_dir).resolve()
    state = data / ".openclaw"
    if not (state / "openclaw.json").is_file():
        raise ValueError("member-data-dir must directly contain active .openclaw")
    mounts = json.loads(command(["docker", "inspect", arguments.container]).stdout)[0]["Mounts"]
    matches = [mount for mount in mounts if mount["Destination"] == arguments.member_home and Path(mount["Source"]).resolve() == data]
    if len(matches) != 1:
        raise ValueError("Supplied member directory does not match the active HOME Docker mount")
    config_hash = digest((state / "openclaw.json").read_bytes())
    version = runtime(arguments.container, ["--version"]).stdout
    inspection = runtime(arguments.container, ["plugins", "inspect", "zalouser"]).stdout
    if f"OpenClaw {SUPPORTED_VERSION}" not in version or f"Version: {SUPPORTED_VERSION}" not in inspection or "Status: enabled" not in inspection:
        raise ValueError("Only enabled official core/plugin 2026.9.9 is reviewed")
    source = re.findall(r"^Source: (.*?/dist/index\.js)$", inspection, re.MULTILINE)
    if len(source) != 1:
        raise ValueError("Active Zalo source is ambiguous")
    entry = source[0].replace("~/", arguments.member_home.rstrip("/") + "/", 1)
    home = PurePosixPath(arguments.member_home)
    relative = PurePosixPath(entry).relative_to(home)
    host_entry = data / str(relative)
    host_entry.resolve().relative_to(data)
    setup = host_entry.parent / ".setup"
    monitor_files = [path for path in setup.glob("monitor-*.mjs") if "async function deliverZalouserReply(params)" in path.read_text()]
    if len(monitor_files) != 1:
        raise ValueError("Native Zalo monitor is ambiguous")
    monitor = monitor_files[0]
    sender_import = re.findall(r'import \{ n as sendMessageZalouser \} from "\./(send-[^/]+\.mjs)";', monitor.read_text())
    if len(sender_import) != 1:
        raise ValueError("Sender import anchor changed")
    sender = setup / sender_import[0]
    low_import = re.findall(r'import \{[^\n]*v as sendZaloTextMessage[^\n]*\} from "\./([^/]+\.mjs)";', sender.read_text())
    if len(low_import) != 1:
        raise ValueError("Low-level sender import anchor changed")
    files = {"send": sender, "monitor": monitor, "low": setup / low_import[0]}
    for path in files.values():
        if not path.is_file() or path.resolve().parent != setup.resolve():
            raise ValueError("Bundle path escaped the active setup directory")
    original = {name: path.read_text() for name, path in files.items()}
    tool_home = str(home / ".openclaw/tools/zalo-text-delivery-guard")
    tool_host = state / "tools/zalo-text-delivery-guard"
    patched = patch_sources(original, tool_home + "/guard.mjs")
    baseline = channel_health(runtime(arguments.container, ["channels", "status", "--probe"]).stdout)
    runtime(arguments.container, ["config", "validate"])
    doctor = runtime(arguments.container, ["plugins", "doctor"], check=False)
    if digest((state / "openclaw.json").read_bytes()) != config_hash:
        raise RuntimeError("Config changed during preflight")
    helper = (ASSETS / "guard.mjs").read_bytes()
    if (tool_host / "guard.mjs").exists() and (tool_host / "guard.mjs").read_bytes() != helper:
        raise ValueError("Different existing delivery guard payload; review before overwriting")
    changed = any(original[name] != patched[name] for name in files) or not (tool_host / "guard.mjs").exists()
    manifest = {"schema": 1, "version": SUPPORTED_VERSION, "pluginSetup": str(PurePosixPath(entry).parent / ".setup"), "coreDist": info["coreDist"], "files": {name: path.name for name, path in files.items()},
                "sources": {name: str(PurePosixPath(entry).parent / ".setup" / path.name) for name, path in files.items()}, "guardHash": digest(helper), "bundleHashes": {name: digest(patched[name].encode()) for name in files}}
    report = {"member": arguments.member_label, "container": arguments.container, "mode": "apply" if arguments.apply else "dry-run", "code_change": changed, "version": SUPPORTED_VERSION, "baseline": baseline, "preexisting_doctor_diagnostic": doctor.returncode != 0}
    if not arguments.apply:
        print(json.dumps(report))
        return
    backup = Path("/root/_Backups") / f"{arguments.member_label}-zalo-text-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    backup.mkdir(mode=0o700)
    for name, path in files.items():
        atomic_write(backup / (name + ".mjs"), path.read_bytes(), 0o600)
    atomic_write(backup / "openclaw.json", (state / "openclaw.json").read_bytes(), 0o600)
    for label, database in [("state", state / "state/openclaw.sqlite"), ("main-agent", state / "agents/main/agent/openclaw-agent.sqlite")]:
        if database.exists():
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as source_db, sqlite3.connect(str(backup / (label + ".sqlite"))) as target_db:
                source_db.backup(target_db)
            os.chmod(backup / (label + ".sqlite"), 0o600)
    if tool_host.exists():
        shutil.copytree(tool_host, backup / "previous-tools")
    atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode(), 0o600)
    report["backup"] = str(backup)
    temporary = "/tmp/zalo-text-delivery-guard-" + uuid.uuid4().hex
    mutated = False
    try:
        with tempfile.TemporaryDirectory(prefix="zalo-text-guard-") as directory:
            staged = Path(directory)
            for name, path in files.items():
                atomic_write(staged / path.name, patched[name].encode())
            for asset in ["guard.mjs", "test_guard.mjs"]:
                shutil.copy2(ASSETS / asset, staged / asset)
            candidate = {**manifest, "sources": {name: temporary + "/" + path.name for name, path in files.items()}}
            atomic_write(staged / "deployment.json", json.dumps(candidate).encode())
            command(["docker", "exec", arguments.container, "mkdir", "-m", "700", "-p", temporary])
            command(["docker", "cp", str(staged) + "/.", arguments.container + ":" + temporary])
            for name in [path.name for path in files.values()] + ["guard.mjs", "test_guard.mjs"]:
                command(["docker", "exec", arguments.container, "node", "--check", temporary + "/" + name])
            tests = command(["docker", "exec", arguments.container, "node", "--experimental-vm-modules", "--test", temporary + "/test_guard.mjs"], check=False)
            if tests.returncode:
                print(tests.stdout[-6000:], file=sys.stderr)
                print(tests.stderr[-1000:], file=sys.stderr)
                raise RuntimeError("Staged offline acceptance suite failed; active bundles not modified")
            if not re.search(r"(?:# |ℹ )pass 15\b", tests.stdout):
                raise RuntimeError("Offline acceptance suite did not run all 15 cases")
        for name, path in files.items():
            if path.read_text() != original[name]:
                raise RuntimeError("Bundle changed during staging; refusing overwrite")
        mutated = True
        for asset in ["guard.mjs", "test_guard.mjs"]:
            atomic_write(tool_host / asset, (ASSETS / asset).read_bytes())
        atomic_write(tool_host / "deployment.json", json.dumps(manifest, indent=2).encode())
        for name, path in files.items():
            if original[name] != patched[name]:
                atomic_write(path, patched[name].encode(), path.stat().st_mode & 0o777)
        if changed:
            command(["docker", "exec", arguments.container, "supervisorctl", "restart", "openclaw-gateway"])
        runtime(arguments.container, ["config", "validate"])
        after_doctor = runtime(arguments.container, ["plugins", "doctor"], check=False)
        if after_doctor.returncode and (after_doctor.returncode != doctor.returncode or after_doctor.stdout != doctor.stdout):
            raise RuntimeError("New plugin validation diagnostic")
        after = None
        for attempt in range(3):
            after = channel_health(runtime(arguments.container, ["channels", "status", "--probe"]).stdout)
            if not any(baseline[name] and not after[name] for name in ["zalo", "telegram"]):
                break
            time.sleep(8)
        else:
            raise RuntimeError("Previously healthy channel regressed after reload")
        final_info = json.loads(runtime(arguments.container, "info").stdout)
        if final_info["manager"] != "supervisord" or digest((state / "openclaw.json").read_bytes()) != config_hash:
            raise RuntimeError("Gateway ownership or config changed")
        report.update({"offline_tests_passed": 15, "config_unchanged": True, "after": after, "gateway_pid": final_info["pid"], "restarted": changed})
        atomic_write(backup / "result.json", json.dumps(report, indent=2).encode(), 0o600)
        print(json.dumps(report))
    except Exception:
        if mutated:
            command(["docker", "exec", arguments.container, "supervisorctl", "stop", "openclaw-gateway"], check=False)
            for name, path in files.items():
                atomic_write(path, (backup / (name + ".mjs")).read_bytes(), path.stat().st_mode & 0o777)
            if (backup / "previous-tools").exists():
                for path in (backup / "previous-tools").rglob("*"):
                    if path.is_file():
                        atomic_write(tool_host / path.relative_to(backup / "previous-tools"), path.read_bytes(), path.stat().st_mode & 0o777)
            command(["docker", "exec", arguments.container, "supervisorctl", "start", "openclaw-gateway"])
        print(json.dumps({"member": arguments.member_label, "backup": str(backup), "rolled_back": mutated}), file=sys.stderr)
        raise
    finally:
        command(["docker", "exec", arguments.container, "rm", "-rf", temporary], check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--member-data-dir", required=True)
    parser.add_argument("--member-home", required=True)
    parser.add_argument("--member-label", required=True)
    parser.add_argument("--lock-wait-seconds", type=int, default=180)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", arguments.member_label):
        parser.error("Invalid member label")
    if arguments.container != "user-" + arguments.member_label:
        parser.error("Container must match user-<member-label> so watchdog locks target the same member")
    if arguments.lock_wait_seconds < 0 or arguments.lock_wait_seconds > 600:
        parser.error("Lock wait must be between 0 and 600 seconds")
    if arguments.apply:
        deadline = time.monotonic() + arguments.lock_wait_seconds
        while True:
            try:
                with member_locks(arguments.member_label):
                    execute(arguments)
                break
            except WatchdogBusy:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(3)
    else:
        execute(arguments)


if __name__ == "__main__":
    main()
