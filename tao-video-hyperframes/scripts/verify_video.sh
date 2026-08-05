#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: verify_video.sh VIDEO_PATH [REPORT_DIR] [EXPECTED_WIDTH EXPECTED_HEIGHT EXPECTED_FPS]
EOF
  exit 2
}

video_path="${1:-}"
report_dir="${2:-}"
expected_width="${3:-}"
expected_height="${4:-}"
expected_fps="${5:-}"

[[ -n "$video_path" ]] || usage
[[ -f "$video_path" ]] || { echo "ERROR: video not found: $video_path" >&2; exit 1; }
command -v ffprobe >/dev/null || { echo "ERROR: ffprobe is required" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ERROR: ffmpeg is required" >&2; exit 1; }

if [[ -z "$report_dir" ]]; then
  report_dir="$(dirname "$video_path")/verification"
fi
mkdir -p "$report_dir"

probe_json="$report_dir/ffprobe.json"
ffprobe -v error \
  -show_entries format=filename,duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels \
  -of json "$video_path" > "$probe_json"

stream_types="$(ffprobe -v error -show_entries stream=codec_type -of csv=p=0 "$video_path")"
grep -qx 'video' <<< "$stream_types" || { echo "ERROR: no video stream" >&2; exit 1; }
grep -qx 'audio' <<< "$stream_types" || { echo "ERROR: no audio stream" >&2; exit 1; }

width="$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0 "$video_path")"
height="$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$video_path")"
fps="$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$video_path")"
duration="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video_path")"

[[ -z "$expected_width" || "$width" == "$expected_width" ]] || { echo "ERROR: expected width $expected_width, got $width" >&2; exit 1; }
[[ -z "$expected_height" || "$height" == "$expected_height" ]] || { echo "ERROR: expected height $expected_height, got $height" >&2; exit 1; }

if [[ -n "$expected_fps" ]]; then
  actual_fps="$(awk -F/ '{if ($2 == 0) print $1; else printf "%.6f", $1/$2}' <<< "$fps")"
  fps_delta="$(awk -v a="$actual_fps" -v e="$expected_fps" 'BEGIN {d=a-e; if (d<0) d=-d; print d}')"
  awk -v d="$fps_delta" 'BEGIN {exit !(d <= 0.01)}' || {
    echo "ERROR: expected fps $expected_fps, got $fps" >&2
    exit 1
  }
fi

ffmpeg -v error -i "$video_path" -f null -
echo "FULL_DECODE_OK"

near_end="$(awk -v d="$duration" 'BEGIN {v=d-0.7; if (v<0) v=0; printf "%.3f", v}')"
declare -a labels=("0.5s" "3s" "8s" "near_end")
declare -a timestamps=("0.5" "3" "8" "$near_end")

for index in "${!labels[@]}"; do
  label="${labels[$index]}"
  timestamp="${timestamps[$index]}"
  ffmpeg -y -v error -ss "$timestamp" -i "$video_path" -frames:v 1 -q:v 2 "$report_dir/frame_${label}.jpg"
done

sha256sum "$video_path" > "$report_dir/SHA256SUMS.txt"

printf 'VIDEO_OK\nPATH=%s\nDURATION=%s\nWIDTH=%s\nHEIGHT=%s\nFPS=%s\nREPORT_DIR=%s\n' \
  "$video_path" "$duration" "$width" "$height" "$fps" "$report_dir"
