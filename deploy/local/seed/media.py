"""Download real files, retaining source metadata, then create codec fixtures."""
import concurrent.futures as cf
import json
import re
import subprocess
import time
from urllib.parse import urljoin
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
MEDIA = ROOT / 'data' / 'media'
MEDIA.mkdir(parents=True, exist_ok=True)


def download(url, name):
    path = MEDIA / name
    if path.exists() and path.stat().st_size > 100:
        return name
    for attempt in range(6):
        try:
            r = requests.get(url, timeout=90)
            r.raise_for_status()
            path.write_bytes(r.content)
            return name
        except requests.RequestException:
            if attempt == 5:
                raise
            time.sleep(2 + attempt)


def main():
    listing = requests.get('https://picsum.photos/v2/list?limit=100', timeout=60).json()
    (MEDIA / 'photo-sources.json').write_text(json.dumps(listing, ensure_ascii=False, indent=2), encoding='utf8')
    def photo(item):
        return download(f"https://picsum.photos/id/{item['id']}/640/480", f"photo-{item['id']}.jpg")
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        for n, name in enumerate(pool.map(photo, listing)):
            if n % 10 == 0:
                print(f'downloaded photos: {n + 1}/100', flush=True)
    sources = []
    for kind in ['mp4', 'webm', 'mp3', 'wav', 'gif', 'png', 'webp']:
        page = f'https://samplelib.com/sample-{kind}.html'
        html = requests.get(page, timeout=60).text
        links = re.findall(r'href=["\x27]([^"\x27]+)', html)
        links = list(dict.fromkeys(urljoin(page, x) for x in links if x.split('?')[0].endswith('.' + kind)))
        if not links:
            print(f'No download for {kind}; deriving fixture from downloaded source', flush=True)
            continue
        # Video and audio files are intentionally short to keep uploads practical.
        url = links[0]
        if kind == 'mp4' and len(links) >= 3:
            url = links[2]
        name = f'sample.{kind}'
        download(url, name)
        sources.append({'file': name, 'url': url, 'page': page})
        print(f'downloaded {name}', flush=True)
    (MEDIA / 'sample-sources.json').write_text(json.dumps(sources, indent=2), encoding='utf8')
    def convert(source, dest, args):
        if (MEDIA / dest).exists():
            return
        cmd = ['docker', 'run', '--rm', '--network', 'none', '-v', f'{MEDIA}:/data',
               'mwader/static-ffmpeg:latest', '-hide_banner', '-loglevel', 'error', '-y',
               '-i', f'/data/{source}', *args, f'/data/{dest}']
        subprocess.run(cmd, check=True)
        print(f'converted {dest}', flush=True)
    photo_name = f"photo-{listing[10]['id']}.jpg"
    convert(photo_name, 'photo.png', [])
    convert(photo_name, 'photo.webp', [])
    convert('sample.mp4', 'motion.gif', ['-t', '3', '-vf', 'fps=8,scale=320:-1'])
    convert('sample.mp4', 'clip.mp4', ['-t', '5', '-vf', 'scale=480:-2', '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-movflags', '+faststart'])
    convert('clip.mp4', 'clip.mov', ['-c', 'copy'])
    convert('clip.mp4', 'clip.webm', ['-c:v', 'libvpx-vp9', '-b:v', '250k', '-c:a', 'libopus'])
    for ext, codec in [('ogg', 'libvorbis'), ('flac', 'flac'), ('m4a', 'aac'), ('aac', 'aac'), ('wav', 'pcm_s16le')]:
        convert('sample.mp3', f'audio.{ext}', ['-t', '5', '-c:a', codec])
    print('MEDIA READY', flush=True)


if __name__ == '__main__':
    main()
