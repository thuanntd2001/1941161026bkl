#!/usr/bin/env python3

import argparse
import os
import re
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import json

import paramiko


# --------------------------------------------------
# Configuration
# --------------------------------------------------

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
UTC_TZ = ZoneInfo("UTC")

FILENAME_PATTERN = re.compile(
    r"ge-(\d{8}T\d{6}Z)--(\d{8}T\d{6}Z)\.mp4"
)


# --------------------------------------------------
# Parse CLI arguments
# --------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download IP camera MP4 recordings over SFTP."
    )

    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.config/ipipcam/config.json"),
        help="Path to JSON configuration file",
    )

    parser.add_argument(
    "--here",
    action="store_true",
    help="Download files directly into the current working directory",
)

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument("--today", action="store_true")
    group.add_argument("--last", type=int, metavar="MINUTES")
    group.add_argument("--date", metavar="YYYY-MM-DD")
    group.add_argument("--all", action="store_true")

    parser.add_argument("--start", metavar="YYYY-MM-DD HH:MM")
    parser.add_argument("--end", metavar="YYYY-MM-DD HH:MM")

    args = parser.parse_args()

    # Load connection settings
    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot load config file: {exc}")

    required = ("host", "port", "username", "remote_dir")
    missing = [key for key in required if key not in config]

    if missing:
        parser.error(
            f"Missing config fields: {', '.join(missing)}"
        )

    args.host = config["host"]
    args.port = int(config["port"])
    args.username = config["username"]
    args.password = config.get("password") or os.environ.get(
        "SFTP_PASSWORD"
    )
    args.remote_dir = config["remote_dir"]
    args.output_dir = config.get("output_dir", "./videos")

    if not args.password:
        parser.error(
            "Set password in config.json or SFTP_PASSWORD environment variable"
        )

    if args.last is not None and args.last <= 0:
        parser.error("--last must be greater than zero")

    custom_range = args.start is not None or args.end is not None

    if custom_range:
        if not args.start or not args.end:
            parser.error("--start and --end must be used together")
        if args.today or args.last is not None or args.date or args.all:
            parser.error(
                "--start/--end cannot be combined with another mode"
            )

    return args


# --------------------------------------------------
# Parse recording timestamps from remote filenames
# --------------------------------------------------

def parse_media_filename(filename):
    match = FILENAME_PATTERN.fullmatch(filename)

    if not match:
        return None, None

    fmt = "%Y%m%dT%H%M%SZ"

    try:
        start_dt = datetime.strptime(
            match.group(1), fmt
        ).replace(tzinfo=UTC_TZ)

        end_dt = datetime.strptime(
            match.group(2), fmt
        ).replace(tzinfo=UTC_TZ)

    except ValueError:
        return None, None

    if end_dt <= start_dt:
        return None, None

    return start_dt, end_dt


# --------------------------------------------------
# Generate human-readable local filename
# --------------------------------------------------

def human_vn_filename(filename):
    start_utc, end_utc = parse_media_filename(filename)

    if start_utc is None:
        return filename

    start_vn = start_utc.astimezone(VN_TZ)
    end_vn = end_utc.astimezone(VN_TZ)

    return (
        f"{start_vn:%Y-%m-%d_%H-%M-%S}"
        f"__{end_vn:%H-%M-%S}.mp4"
    )


# --------------------------------------------------
# Calculate requested time range
# --------------------------------------------------

def get_time_range(args):
    now = datetime.now(VN_TZ)

    if args.all:
        return None, None

    if args.today:
        start = datetime.combine(
            now.date(), time.min, tzinfo=VN_TZ
        )
        end = start + timedelta(days=1)
        return start, end

    if args.last is not None:
        return now - timedelta(minutes=args.last), now

    if args.date:
        try:
            day = datetime.strptime(
                args.date, "%Y-%m-%d"
            ).date()
        except ValueError:
            raise SystemExit(
                "Invalid --date. Expected YYYY-MM-DD."
            )

        start = datetime.combine(
            day, time.min, tzinfo=VN_TZ
        )
        end = start + timedelta(days=1)
        return start, end

    if args.start and args.end:
        fmt = "%Y-%m-%d %H:%M"

        try:
            start = datetime.strptime(
                args.start, fmt
            ).replace(tzinfo=VN_TZ)

            end = datetime.strptime(
                args.end, fmt
            ).replace(tzinfo=VN_TZ)

        except ValueError:
            raise SystemExit(
                "Invalid time format. Use YYYY-MM-DD HH:MM."
            )

        if end <= start:
            raise SystemExit(
                "--end must be later than --start."
            )

        return start, end

    return None, None


# --------------------------------------------------
# Create a unique folder for each request
# --------------------------------------------------

def create_request_folder(args, base_dir):
    timestamp = datetime.now(VN_TZ).strftime(
        "%Y%m%d_%H%M%S"
    )

    if args.today:
        kind = "today"

    elif args.last is not None:
        kind = f"last_{args.last}m"

    elif args.date:
        kind = f"date_{args.date.replace('-', '')}"

    elif args.start and args.end:
        start_label = datetime.strptime(
            args.start, "%Y-%m-%d %H:%M"
        ).strftime("%Y%m%d_%H%M")

        end_label = datetime.strptime(
            args.end, "%Y-%m-%d %H:%M"
        ).strftime("%Y%m%d_%H%M")

        kind = f"range_{start_label}_to_{end_label}"

    elif args.all:
        kind = "all"

    else:
        kind = "unknown"

    folder_name = f"{kind}_{timestamp}"
    output_dir = os.path.join(base_dir, folder_name)

    os.makedirs(output_dir, exist_ok=False)

    return output_dir


# --------------------------------------------------
# Download matching recordings
# --------------------------------------------------

def download_mp4s(args):
    start_filter, end_filter = get_time_range(args)

    # request_dir = create_request_folder(
    #     args, args.output_dir
    # )

    if args.here:
        base_dir = os.getcwd()
    else:
        base_dir = args.output_dir

    request_dir = create_request_folder(args, base_dir)
    os.makedirs(request_dir, exist_ok=True)


    print(f"Output folder: {request_dir}")

    if start_filter is not None:
        print(
            f"Requested range: "
            f"{start_filter:%Y-%m-%d %H:%M:%S %Z} - "
            f"{end_filter:%Y-%m-%d %H:%M:%S %Z}"
        )
    else:
        print("Requested range: all recordings")

    transport = paramiko.Transport(
        (args.host, args.port)
    )

    downloaded = 0
    skipped = 0

    try:
        transport.connect(
            username=args.username,
            password=args.password,
        )

        with paramiko.SFTPClient.from_transport(
            transport
        ) as sftp:

            filenames = sorted(
                sftp.listdir(args.remote_dir)
            )

            for filename in filenames:
                start_utc, end_utc = parse_media_filename(
                    filename
                )

                # Ignore non-matching or invalid filenames
                if start_utc is None:
                    continue

                start_vn = start_utc.astimezone(VN_TZ)
                end_vn = end_utc.astimezone(VN_TZ)

                # Select files overlapping the requested range
                if start_filter is not None:
                    if not (
                        start_vn < end_filter
                        and end_vn > start_filter
                    ):
                        continue

                remote_path = (
                    f"{args.remote_dir.rstrip('/')}/{filename}"
                )

                new_filename = human_vn_filename(filename)
                local_path = os.path.join(
                    request_dir, new_filename
                )

                try:
                    remote_size = sftp.stat(
                        remote_path
                    ).st_size

                    if (
                        os.path.isfile(local_path)
                        and os.path.getsize(local_path)
                        == remote_size
                    ):
                        print(f"Skip existing: {new_filename}")
                        skipped += 1
                        continue

                except OSError:
                    pass

                print(
                    f"Downloading: {filename}\n"
                    f"  Recording: {start_vn:%Y-%m-%d %H:%M:%S} - "
                    f"{end_vn:%Y-%m-%d %H:%M:%S} ICT\n"
                    f"  Local name: {new_filename}"
                )

                try:
                    sftp.get(remote_path, local_path)
                    downloaded += 1

                except Exception:
                    # Remove incomplete local files on failure
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except OSError:
                            pass
                    raise

        print("\nDownload finished.")
        print(f"Downloaded: {downloaded}")
        print(f"Skipped:    {skipped}")
        print(f"Saved to:   {request_dir}")

    finally:
        transport.close()


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    args = parse_args()

    try:
        download_mp4s(args)

    except (paramiko.SSHException, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
