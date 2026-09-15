"""Bounded concurrent read-only HTTP check; does not bypass rate limits."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import json
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:3020')
parser.add_argument('--requests', type=int, default=60)
parser.add_argument('--concurrency', type=int, default=5)
args = parser.parse_args()
if not 1 <= args.concurrency <= 20 or not 10 <= args.requests <= 200:
    parser.error('Use 1–20 workers and 10–200 requests')
paths = ['/api/movies/browse?page_size=24', '/api/search?q=Star&page_size=24', '/api/movies/browse?genre=Drama&page_size=24']

def fetch(index):
    started = time.perf_counter()
    try:
        with urlopen(args.base_url.rstrip('/') + paths[index % len(paths)], timeout=20) as response:
            data = json.load(response)
            status = response.status if isinstance(data.get('items'), list) else 'invalid-body'
    except HTTPError as error:
        status = error.code
    except (URLError, OSError, ValueError):
        status = 'request-error'
    return status, (time.perf_counter() - started) * 1000

started = time.perf_counter()
with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
    results = list(executor.map(fetch, range(args.requests)))
elapsed = time.perf_counter() - started
times = sorted(duration for _, duration in results)
report = {'requests': args.requests, 'concurrency': args.concurrency, 'status_counts': dict(Counter(str(status) for status, _ in results)),
    'p50_ms': round(statistics.median(times), 2), 'p95_ms': round(times[min(len(times)-1, int(len(times)*.95))], 2),
    'elapsed_seconds': round(elapsed, 2), 'requests_per_second': round(len(results)/elapsed, 2),
    'scope': 'Bounded local concurrent read workload; not a production capacity certification.'}
print(json.dumps(report, indent=2))
raise SystemExit(0 if all(status == 200 for status, _ in results) else 1)
