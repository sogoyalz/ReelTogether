"""Small sequential catalog benchmark, not a concurrency/load test."""
import argparse
import json
import statistics
import time
from urllib.request import urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:3020')
parser.add_argument('--samples', type=int, default=25)
args = parser.parse_args()
if not 5 <= args.samples <= 100:
    parser.error('samples must be between 5 and 100')
url = args.base_url.rstrip('/') + '/api/movies/browse?page_size=24&sort=hype'
times = []
for i in range(args.samples + 3):
    started = time.perf_counter()
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)
        assert response.status == 200 and 'items' in payload
    if i >= 3:
        times.append((time.perf_counter() - started) * 1000)
ordered = sorted(times)
print(json.dumps({
    'url': url, 'catalog_size': payload['total'], 'samples': args.samples,
    'concurrency': 1, 'warmup_requests': 3,
    'p50_ms': round(statistics.median(times), 2),
    'p95_ms': round(ordered[min(len(ordered)-1, int(len(ordered)*.95))], 2),
    'max_ms': round(max(times), 2),
    'scope': 'Local Docker HTTP smoke benchmark, including frontend proxy; not production capacity evidence.',
}, indent=2))
