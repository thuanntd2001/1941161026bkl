import requests
import json
import time
from requests.exceptions import HTTPError
# SET
max_size = 32000
ip = "192.168.100.198"
port = 9090
target_url = f"http://{ip}:{port}"
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:158.0) Gecko/20100101 Firefox/158.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': f'target_url/',
    'Origin': f'target_url',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Priority': 'u=0'
}
delete_url = f'{target_url}/files'
start_url = f'http://{ip}:{port}/record/start'
stop_url = f'http://{ip}:{port}/record/stop'

DURATION = 600  # Recording duration in seconds
SAVEFILE = 1    # Sleep duration between operations in seconds
RETRY = 10

def get_mp4_filenames(base_url):
    try:
        # Fetch the files.json endpoint
        files_url = f"{base_url}/files.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(files_url, headers=headers)
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()
        mp4_filenames = []

        for file in data.get('files', []):
            if file.get('name', '').lower().endswith('.mp4'):
                mp4_filenames.append(file['name'])
        #get_total_mp4_size_mb
        total_size_bytes = 0

        for file in data.get('files', []):
            if file.get('name', '').lower().endswith('.mp4'):
                total_size_bytes += file.get('sizeBytes', 0)

        # Convert bytes to MB (1 MB = 1024 * 1024 bytes)
        total_size_mb = total_size_bytes / (1024 * 1024)

        return mp4_filenames,total_size_mb

    except Exception as e:
        print(f"Error occurred: {e}")
        return []

def start_rec():
    # Start recording
    print("Starting recording...")
    start_url = f'http://{ip}:{port}/record/start'
    while True:
        try:
            response = requests.post(start_url, headers=headers)
            response.raise_for_status()
            return
        except HTTPError as http_err:
            if response.status_code == 409:
                print("Error: Recording is in an invalid state (409 Conflict).")
                break
        except:
            print("Try again...")
            time.sleep(RETRY)

def stop_rec():
    # Stop recording
    print("Stopping all remains recording...")
    stop_url = f'http://{ip}:{port}/record/stop'
    while True:
        try:
            response = requests.post(stop_url, headers=headers)
            response.raise_for_status()
            break
        except HTTPError as http_err:
            if response.status_code == 409:
                print("Error: Recording is already stopped or in an invalid state (409 Conflict).")
                break
        except:
            print("Try again...")
            time.sleep(RETRY)

    print("Sleeping...")
    time.sleep(SAVEFILE)
    return

def delete_rec(min_filename):
    real_delete_url = f"{delete_url}/{min_filename}"
    while True:
        try:
            response = requests.delete(real_delete_url, headers=headers)
            response.raise_for_status()
            break
        except HTTPError as http_err:
            if response.status_code == 409:
                print("Error: Recording is in an invalid state (409 Conflict).")
                break
        except:
            print("Try again...")
            time.sleep(RETRY)

# def start_rec():
#         # Start recording
#     print("Starting recording...")
#     start_url = f'http://{ip}:{port}/record/start'
#     response = requests.post(start_url, headers=headers)
#     # response.raise_for_status()  # Raise an exception for HTTP errors
#     return
#
# def stop_rec():
#     # Stop recording
#     print("Stopping all remains recording...")
#     stop_url = f'http://{ip}:{port}/record/stop'
#     response = requests.post(stop_url, headers=headers)
#     # response.raise_for_status()
#
#     print("Sleeping...")
#     time.sleep(SAVEFILE)
#     return
#
# def delete_rec(min_filename):
#     real_delete_url = f"{delete_url}/{min_filename}"
#     response = requests.delete(real_delete_url, headers=headers)
#     # response.raise_for_status()  # Raise an exception for HTTP errors
#     print(f"Deleted: {min_filename}")


if __name__ == "__main__":
    stop_rec()


    while True:

        mp4_files,size = get_mp4_filenames(target_url)
        #info
        print("MP4 filenames list:")
        print(mp4_files)
        print("size")
        print(str (size) + " MB")

        max_filename = max(mp4_files)
        min_filename = min(mp4_files)
        print(f"Maximum filename (lex order): {max_filename}")
        print(f"Minimum filename (lex order): {min_filename}")

        #del
        if size > max_size:
            delete_rec(min_filename)

        # Start recording
        start_rec()

        # Wait for recording duration
        time.sleep(DURATION)

        # Stop recording
        stop_rec()





