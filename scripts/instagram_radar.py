"""Fetch a saved Apify task and prepare an evidence-based Instagram feed for Horizon.

No credentials are written to disk. All output data is public if committed to a public repo.
"""
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree.ElementTree import Element, SubElement, ElementTree

BASE = 'https://api.apify.com/v2'
OUT = Path('data/instagram_radar')


def api(method, path, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(BASE + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'Horizon-Instagram-Radar/1.0',
    })
    with urlopen(req, timeout=(150 if method == 'POST' else 45)) as res:
        return json.load(res)


def value(row, *keys, default=None):
    for key in keys:
        current = row
        for part in key.split('.'):
            current = current.get(part) if isinstance(current, dict) else None
        if current is not None and current != '':
            return current
    return default


def number(v):
    try:
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return 0


def normalize(row):
    url = value(row, 'url', 'reelUrl', 'postUrl', 'inputUrl', 'videoUrl', default='')
    shortcode = value(row, 'shortCode', 'shortcode', 'code', 'id')
    if not url and shortcode:
        url = f'https://www.instagram.com/reel/{shortcode}/'
    if 'instagram.com/' not in str(url):
        return None
    handle = str(value(row, 'ownerUsername', 'username', 'owner.username', 'user.username',
                       'creator.username', default='unknown')).lstrip('@')
    if not shortcode:
        match = re.search(r'/reel/([^/?#]+)', str(url))
        shortcode = match.group(1) if match else str(url).rstrip('/').split('/')[-1]
    published = value(row, 'timestamp', 'takenAt', 'taken_at', 'date', 'postDate', 'postedAt', 'publishedAt', 'createdAt')
    if isinstance(published, (float, int)):
        published = datetime.fromtimestamp(published / (1000 if published > 10**11 else 1), timezone.utc).isoformat()
    if isinstance(published, str):
        try:
            published = datetime.fromisoformat(published.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat()
        except ValueError:
            published = None
    caption = value(row, 'caption', 'text', 'description', default='')
    if isinstance(caption, dict):
        caption = caption.get('text', '')
    return {
        'id': str(shortcode), 'url': str(url), 'username': handle,
        'caption': str(caption)[:1200], 'published': published,
        'views': number(value(row, 'videoPlayCount', 'videoViewCount', 'playCount', 'plays', 'views', 'viewCount')),
        'likes': number(value(row, 'likesCount', 'likes', 'likeCount')),
        'comments': number(value(row, 'commentsCount', 'comments', 'commentCount')),
    }


def collect():
    token, task = os.environ.get('APIFY_TOKEN'), os.environ.get('APIFY_TASK_ID')
    if not token or not task:
        raise RuntimeError('Set APIFY_TOKEN and APIFY_TASK_ID as GitHub Actions secrets.')
    task = quote(task.strip(), safe='~')
    run = api('POST', f'/actor-tasks/{task}/runs?waitForFinish=120', token, {})['data']
    for _ in range(20):
        if run['status'] in ('SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT'):
            break
        time.sleep(10)
        run = api('GET', '/actor-runs/' + quote(run['id'], safe=''), token)['data']
    if run['status'] != 'SUCCEEDED':
        raise RuntimeError('Apify task did not succeed (status: ' + run['status'] + ').')
    dataset_id = quote(run['defaultDatasetId'], safe='')
    return api('GET', f'/datasets/{dataset_id}/items?format=json&clean=true&limit=150', token)


def persist(rows):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'history.json'
    history = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(history, dict):
        history = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        item = normalize(raw)
        if item:
            previous = history.get(item['id'], {})
            if not item['published']:
                item['published'] = previous.get('published')
            history[item['id']] = item
    history = dict(list(history.items())[-3000:])
    items = list(history.values())
    for item in items:
        others = [x['views'] for x in items if x['username'] == item['username']
                  and x['id'] != item['id'] and x['views'] > 0]
        # An isolated high-view Reel is not proof of exceptional performance.
        item['baseline_count'] = len(others)
        item['outlier_ratio'] = round(item['views'] / statistics.median(others), 2) if len(others) >= 3 and item['views'] else None
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    items.sort(key=lambda x: (x['outlier_ratio'] is not None, x['outlier_ratio'] or 0, x['views']), reverse=True)
    make_rss(items[:30])
    make_report(items)
    make_config()
    return len(rows), len(items), sum(i['outlier_ratio'] is not None for i in items)


def make_rss(items):
    root = Element('rss', {'version': '2.0'})
    ch = SubElement(root, 'channel')
    for tag, text in (('title', 'Instagram Reel Performance Radar'),
                      ('link', 'https://www.instagram.com/'),
                      ('description', 'Observed public metrics; no inferred private insights.')):
        SubElement(ch, tag).text = text
    for item in items:
        if not item['published']:
            continue  # Horizon requires actual publication dates.
        entry = SubElement(ch, 'item')
        SubElement(entry, 'title').text = '@' + item['username'] + ': ' + (item['caption'][:95] or 'Instagram Reel')
        SubElement(entry, 'link').text = item['url']
        SubElement(entry, 'guid', {'isPermaLink': 'false'}).text = item['id']
        published = datetime.fromisoformat(item['published'].replace('Z', '+00:00'))
        SubElement(entry, 'pubDate').text = format_datetime(published)
        ratio = str(item['outlier_ratio']) + 'x' if item['outlier_ratio'] else 'not established (insufficient baseline)'
        SubElement(entry, 'description').text = (
            f"Public observations: {item['views']} views; {item['likes']} likes; {item['comments']} comments; "
            f"relative to same-creator baseline: {ratio}; comparable prior reels: {item['baseline_count']}. "
            f"Caption: {item['caption']}"
        )
    ElementTree(root).write(OUT / 'reels.xml', encoding='utf-8', xml_declaration=True)


def make_report(items):
    lines = ['# Instagram Reel Radar', '',
             'Data: Apify public reel search. Ratios require at least 3 *other* observed reels from the same creator; otherwise unverified.', '',
             '| Creator | Views | Likes | Comments | Relative performance | Link |',
             '|---|---:|---:|---:|---:|---|']
    for item in items[:30]:
        ratio = f"{item['outlier_ratio']}x ({item['baseline_count']} comparisons)" if item['outlier_ratio'] else 'insufficient baseline'
        lines.append(f"| @{item['username']} | {item['views']:,} | {item['likes']:,} | {item['comments']:,} | {ratio} | [Reel]({item['url']}) |")
    (OUT / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def make_config():
    original = json.loads(Path('data/config.github.json').read_text(encoding='utf-8'))
    original['ai']['languages'] = ['fa']
    original['ai']['analysis_concurrency'] = 1
    original['ai']['enrichment_concurrency'] = 1
    original['processing'] = {'profiles_dir': 'profiles', 'default_profile': 'content-trend-radar',
                              'profile_settings': {'content-trend-radar': {'threshold': 5.0, 'topic_dedup': False}}}
    original['sources'] = {'rss': [{'name': 'Instagram reel radar',
                                   'url': 'http://127.0.0.1:8765/instagram_radar/reels.xml',
                                   'category': 'instagram-reels', 'profile': 'content-trend-radar'}]}
    original['collection'] = {'time_window_hours': 720}
    original['digest'] = {'max_items': 10, 'profile_order': ['content-trend-radar']}
    original['webhook'] = {'enabled': False}
    (OUT / 'config.json').write_text(json.dumps(original, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    source = os.environ.get('INSTAGRAM_RADAR_SAMPLE_JSON')
    incoming = json.loads(Path(source).read_text(encoding='utf-8')) if source else collect()
    if not isinstance(incoming, list):
        raise ValueError('Apify dataset must be a JSON array.')
    print('New records, total history, with a measurable baseline:', *persist(incoming))
