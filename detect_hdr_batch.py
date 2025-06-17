import os
import subprocess
import json
import sys

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.webm', '.avi', '.ts', '.m4v')

def run_ffprobe(file_path, args):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0'] + args + [file_path]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
        return output
    except subprocess.CalledProcessError:
        return ""

def run_ffprobe_json(file_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=side_data_list', '-of', 'json', file_path]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return json.loads(output)
    except subprocess.CalledProcessError:
        return {}

def analyze_file(file_path):
    pix_fmt = run_ffprobe(file_path, ['-show_entries', 'stream=pix_fmt', '-of', 'default=nw=1:nk=1'])
    primaries = run_ffprobe(file_path, ['-show_entries', 'stream=color_primaries', '-of', 'default=nw=1:nk=1'])
    transfer = run_ffprobe(file_path, ['-show_entries', 'stream=transfer_characteristics', '-of', 'default=nw=1:nk=1'])
    side_data = run_ffprobe_json(file_path)

    mastering = any("Mastering display metadata" in d.get("side_data_type", "") for d in side_data.get("streams", [{}])[0].get("side_data_list", []))
    light_level = any("Content light level metadata" in d.get("side_data_type", "") for d in side_data.get("streams", [{}])[0].get("side_data_list", []))

    likely_hdr = (
        'bt2020' in primaries.lower() or
        'smpte2084' in transfer.lower() or
        'arib-std-b67' in transfer.lower() or
        mastering or light_level
    )

    if likely_hdr:
        label = 'HDR'
    elif '10' in pix_fmt:
        label = 'SDR (10-bit)'
    else:
        label = 'SDR'

    return {
        'file': file_path,
        'pix_fmt': pix_fmt or '[none]',
        'primaries': primaries or '[none]',
        'transfer': transfer or '[none]',
        'mastering_metadata': mastering,
        'light_level_metadata': light_level,
        'label': label
    }

def scan_folder(folder_path):
    results = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                full_path = os.path.join(root, file)
                result = analyze_file(full_path)
                results.append(result)
    return results

def print_results(results):
    for res in results:
        print(f"\nFile: {os.path.basename(res['file'])}")
        print(f"  Pixel format         : {res['pix_fmt']}")
        print(f"  Color primaries      : {res['primaries']}")
        print(f"  Transfer characteristics: {res['transfer']}")
        print(f"  Mastering metadata   : {'YES' if res['mastering_metadata'] else 'NO'}")
        print(f"  Light level metadata : {'YES' if res['light_level_metadata'] else 'NO'}")
        print(f"  ->  Likely: {res['label']}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python detect_hdr_batch.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print("Error: Provided path is not a folder.")
        sys.exit(1)

    results = scan_folder(folder)
    print_results(results)
