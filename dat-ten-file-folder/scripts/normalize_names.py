#!/usr/bin/env python3
import argparse
import re
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path


SKIP_DIRS = {".git", ".obsidian", ".stfolder"}


def strip_accents(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def slug(text: str) -> str:
    text = strip_accents(text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def normalize_stem(stem: str, prefix_if_missing: str = "00") -> str:
    match = re.match(r"^(\d+)[\s_\-]*(.*)$", stem)
    if match:
        number, rest = match.groups()
        rest = slug(rest)
        return f"{number}_{rest}" if rest else number

    normalized = slug(stem)
    return f"{prefix_if_missing}_{normalized}" if normalized else f"{prefix_if_missing}_file"


def normalize_dir_name(name: str, prefix_if_missing: str = "00") -> str:
    return normalize_stem(name, prefix_if_missing)


def normalize_file_name(path: Path, prefix_if_missing: str = "00") -> str:
    suffix = path.suffix.lower()
    stem = path.name[: -len(path.suffix)] if path.suffix else path.name
    return normalize_stem(stem, prefix_if_missing) + suffix


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts)


def collect_renames(root: Path, prefix_if_missing: str):
    dirs = []
    files = []

    for path in root.rglob("*"):
        if should_skip(path, root):
            continue
        if path.is_dir():
            new_name = normalize_dir_name(path.name, prefix_if_missing)
            if path.name != new_name:
                dirs.append((path, path.with_name(new_name)))
        elif path.is_file() and not path.name.startswith("."):
            new_name = normalize_file_name(path, prefix_if_missing)
            if path.name != new_name:
                files.append((path, path.with_name(new_name)))

    dirs.sort(key=lambda pair: len(pair[0].parts), reverse=True)
    return dirs, files


def find_conflicts(pairs):
    conflicts = []
    by_parent = defaultdict(list)
    for old, new in pairs:
        by_parent[old.parent].append((old, new))

    for parent, group in by_parent.items():
        names = Counter(new.name for _, new in group)
        for name, count in names.items():
            if count > 1:
                conflicts.append(f"{parent}: duplicate target {name} ({count})")
        for old, new in group:
            if new.exists() and old != new:
                conflicts.append(f"{old} -> target exists: {new}")

    return conflicts


def update_target(target: str, source_path: Path, root: Path, old_to_new_rel, old_abs_to_new_abs):
    if re.match(r"^[a-z]+://", target) or target.startswith("#"):
        return target

    anchor = ""
    path_part = target
    if "#" in target:
        path_part, anchor = target.split("#", 1)
        anchor = "#" + anchor

    decoded = urllib.parse.unquote(path_part)
    noext_map = {
        str(Path(old).with_suffix("")): str(Path(new).with_suffix(""))
        for old, new in old_to_new_rel.items()
        if old.endswith(".md")
    }

    if decoded in old_to_new_rel:
        return old_to_new_rel[decoded] + anchor
    if decoded in noext_map:
        return noext_map[decoded] + anchor

    if "/" not in decoded and "." not in decoded:
        candidate = source_path.parent / f"{decoded}.md"
        new_abs = old_abs_to_new_abs.get(candidate)
        if new_abs:
            return new_abs.stem + anchor

    candidate = (source_path.parent / decoded).resolve()
    new_abs = old_abs_to_new_abs.get(candidate)
    if new_abs:
        return new_abs.relative_to(source_path.parent).as_posix() + anchor

    return target


def update_markdown_links(root: Path, file_pairs):
    old_to_new_rel = {
        old.relative_to(root).as_posix(): new.relative_to(root).as_posix()
        for old, new in file_pairs
    }
    old_abs_to_new_abs = {old.resolve(): new.resolve() for old, new in file_pairs}

    wiki_pat = re.compile(r"\[\[([^\[\]]+)\]\]")
    mdlink_pat = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)")
    code_pat = re.compile(r"`([^`\n]+)`")

    changed_files = 0
    updated_links = 0

    for path in root.rglob("*.md"):
        if should_skip(path, root):
            continue
        text = path.read_text(encoding="utf-8")

        def repl_wiki(match):
            nonlocal updated_links
            body = match.group(1)
            if "|" in body:
                target, alias = body.split("|", 1)
                new_target = update_target(target, path, root, old_to_new_rel, old_abs_to_new_abs)
                if new_target != target:
                    updated_links += 1
                return f"[[{new_target}|{alias}]]"
            new_body = update_target(body, path, root, old_to_new_rel, old_abs_to_new_abs)
            if new_body != body:
                updated_links += 1
            return f"[[{new_body}]]"

        def repl_mdlink(match):
            nonlocal updated_links
            label, url = match.group(1), match.group(2)
            new_url = update_target(url, path, root, old_to_new_rel, old_abs_to_new_abs)
            if new_url != url:
                updated_links += 1
            return f"[{label}]({new_url})"

        def repl_code(match):
            nonlocal updated_links
            body = match.group(1)
            new_body = body
            for old_rel, new_rel in sorted(old_to_new_rel.items(), key=lambda item: len(item[0]), reverse=True):
                if old_rel in new_body:
                    new_body = new_body.replace(old_rel, new_rel)
            if new_body != body:
                updated_links += 1
            return f"`{new_body}`"

        new_text = wiki_pat.sub(repl_wiki, text)
        new_text = mdlink_pat.sub(repl_mdlink, new_text)
        new_text = code_pat.sub(repl_code, new_text)

        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed_files += 1

    return changed_files, updated_links


def check(root: Path):
    bad = []
    pattern = re.compile(r"[0-9]+_[a-z0-9_]+")
    for path in root.rglob("*"):
        if should_skip(path, root):
            continue
        if path.is_dir():
            if not pattern.fullmatch(path.name):
                bad.append(path.relative_to(root).as_posix())
        elif path.is_file() and not path.name.startswith("."):
            stem = path.name[: -len(path.suffix)] if path.suffix else path.name
            if not pattern.fullmatch(stem):
                bad.append(path.relative_to(root).as_posix())
    return bad


def main():
    parser = argparse.ArgumentParser(description="Normalize file and folder names to NN_slug format.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prefix-if-missing", default="00")
    parser.add_argument("--no-link-update", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.check:
        bad = check(root)
        print(f"bad_paths {len(bad)}")
        for item in bad:
            print(item)
        return 1 if bad else 0

    dirs, files = collect_renames(root, args.prefix_if_missing)
    conflicts = find_conflicts(dirs + files)
    print(f"folder_changes {len(dirs)}")
    print(f"file_changes {len(files)}")
    print(f"conflicts {len(conflicts)}")
    for conflict in conflicts:
        print(f"CONFLICT {conflict}")
    if conflicts:
        return 2

    for old, new in (dirs + files)[:200]:
        print(f"{old.relative_to(root)} => {new.name}")

    if args.dry_run:
        return 0

    for old, new in dirs:
        if old.exists():
            old.rename(new)

    rewritten_file_pairs = []
    for old, new in files:
        if old.exists():
            old.rename(new)
            rewritten_file_pairs.append((old, new))

    changed_files = updated_links = 0
    if rewritten_file_pairs and not args.no_link_update:
        changed_files, updated_links = update_markdown_links(root, rewritten_file_pairs)

    print(f"renamed_folders {len(dirs)}")
    print(f"renamed_files {len(rewritten_file_pairs)}")
    print(f"changed_markdown_files {changed_files}")
    print(f"updated_links {updated_links}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
