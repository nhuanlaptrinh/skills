#!/usr/bin/env bash
set -euo pipefail

project_dir="${1:-/root/Apps/04_Nha_May_San_Xuat_Video}"
drive_root_id="${2:-15MckQPMHapn2195kj5v67DuEG-bxEwEx}"
drive_remote="${RCLONE_DRIVE_REMOTE:-gdrive:}"

required_files=(
  "AGENTS.md"
  "CLAUDE.md"
  "index.html"
  "package.json"
  "logo1.png"
  "input/khong_biet_code_tao_video_ai_hang_loat.txt"
  "input/khong_biet_code_tao_video_ai_hang_loat_heygen.mp3"
)

project_ready() {
  [[ -d "$project_dir" ]] || return 1
  local required_file
  for required_file in "${required_files[@]}"; do
    [[ -f "$project_dir/$required_file" ]] || return 1
  done
}

if project_ready; then
  printf 'PROJECT_READY\nPATH=%s\n' "$project_dir"
  exit 0
fi

command -v rclone >/dev/null || {
  echo "ERROR: rclone is required to download the Google Drive source" >&2
  exit 1
}

rclone listremotes | grep -qx "$drive_remote" || {
  echo "ERROR: configured rclone remote not found: $drive_remote" >&2
  exit 1
}

mkdir -p "$project_dir"
echo "PROJECT_MISSING_OR_INCOMPLETE: downloading from Google Drive"
rclone copy "$drive_remote" "$project_dir" \
  --drive-root-folder-id "$drive_root_id" \
  --create-empty-src-dirs \
  --checkers 8 \
  --stats 10s \
  --progress

project_ready || {
  echo "ERROR: Google Drive download finished but required project files are still missing" >&2
  exit 1
}

file_count="$(find "$project_dir" -type f | wc -l | tr -d ' ')"
byte_count="$(du -sb "$project_dir" | awk '{print $1}')"
printf 'PROJECT_DOWNLOADED\nPATH=%s\nFILES=%s\nBYTES=%s\n' "$project_dir" "$file_count" "$byte_count"
