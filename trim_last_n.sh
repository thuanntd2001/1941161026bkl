#!/bin/bash

# Default values
duration=34
auto_calculate_start=true
use_reencode=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--start)
            start_time="$2"
            auto_calculate_start=false
            shift 2
            ;;
        -d|--duration)
            duration="$2"
            shift 2
            ;;
        -r|--reencode)
            use_reencode=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            # Treat as input file if it exists
            if [ -f "$1" ]; then
                input_files=("$1")
                shift
            else
                echo "Usage: $0 [-s start_time] [-d duration] [-r] [file1 file2 ...]"
                echo "Examples:"
                echo "  $0 -s 00:01:30 -d 20 video.mp4  # Start at 1:30, keep 20s"
                echo "  $0 -r                           # Auto-calculate start, keep 34s, re-encode"
                echo "  $0                              # Auto-calculate start, keep 34s, stream copy"
                exit 1
            fi
            ;;
    esac
done

# If no files specified, process all videos in current directory
if [ ${#input_files[@]} -eq 0 ]; then
    input_files=(*.mp4 *.mkv *.mov *.avi)
    [ -e "${input_files[0]}" ] || { echo "No video files found"; exit 1; }
fi

# Create output directory
output_dir="${PWD##*/}_trimmed"
mkdir -p "$output_dir"
echo "Output directory: $output_dir"
echo "Trimming for $duration seconds (auto start: $auto_calculate_start, re-encode: $use_reencode)"

for input_file in "${input_files[@]}"; do
    # Get just the filename without path
    filename=$(basename -- "$input_file")
    output_file="$output_dir/${filename%.*}_trimmed.${filename##*.}"

    echo "Processing: $input_file → $output_dir/$filename"

    if [ "$auto_calculate_start" = true ]; then
        # Calculate start time automatically (keep last N seconds)
        duration_full=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$input_file")
        start_time=$(awk -v dur="$duration_full" -v trim="$duration" 'BEGIN {printf "%.3f", dur - trim}')
        echo "Auto-calculated start: $start_time"
    fi

    if [ "$use_reencode" = true ]; then
        # Re-encode version (slower but more reliable)
        ffmpeg -i "$input_file" -ss "$start_time" -t "$duration" -c:v libx264 -c:a aac -y "$output_file"
    else
        # Stream copy version (faster)
        ffmpeg -i "$input_file" -ss "$start_time" -t "$duration" -c copy -fflags +genpts -movflags +faststart -y "$output_file"
    fi

    if [ $? -eq 0 ]; then
        echo "Done: $output_file"
    else
        echo "Error: Failed to process $input_file"
    fi
done

echo "All videos processed! Output in: $output_dir"
