"""Bounded, process-local operational counters. Never retain user identifiers."""
from collections import Counter
from threading import Lock
import time
import json
_STARTED = time.time()

_LOCK = Lock()
_BUCKETS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
_ROUTES = {}
_EVENTS = Counter()
_ALLOWED_EVENTS = {'room_created','member_joined','voting_started','results_revealed','movie_selected'}


def record_request(method, route, status, elapsed_ms):
    method = method if method in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'} else 'OTHER'
    key = (method, route)
    with _LOCK:
        if key not in _ROUTES and len(_ROUTES) >= 256:
            key = ('OTHER', 'overflow')
        entry = _ROUTES.setdefault(key, {'count':0, 'errors':0, 'duration_ms_sum':0.0, 'latency_buckets':[0] * (len(_BUCKETS)+1)})
        entry['count'] += 1
        entry['errors'] += status >= 500
        entry['duration_ms_sum'] += elapsed_ms
        bucket = next((index for index, bound in enumerate(_BUCKETS) if elapsed_ms <= bound), len(_BUCKETS))
        entry['latency_buckets'][bucket] += 1


def record_event(name):
    if name not in _ALLOWED_EVENTS:
        raise ValueError('Unknown metric event')
    with _LOCK:
        _EVENTS[name] += 1


def snapshot():
    with _LOCK:
        return {'scope':'process-local; resets on restart', 'latency_bucket_upper_bounds_ms':[*_BUCKETS, None],
            'requests':[{'method':method,'route':route,**value,'latency_buckets':list(value['latency_buckets'])} for (method,route),value in sorted(_ROUTES.items())],
            'movie_night_events':dict(_EVENTS)}


def prometheus():
    """Prometheus pulls counters before restarts; labels never contain IDs."""
    data = snapshot()
    lines = ['# TYPE reeltogether_process_start_time_seconds gauge', f'reeltogether_process_start_time_seconds {_STARTED}',
             '# TYPE reeltogether_http_requests_total counter',
             '# TYPE reeltogether_http_server_errors_total counter',
             '# TYPE reeltogether_http_duration_ms histogram']
    for row in data['requests']:
        labels = ','.join(f'{key}={json.dumps(row[key])}' for key in ('method','route'))
        lines.extend([f'reeltogether_http_requests_total{{{labels}}} {row["count"]}',
                      f'reeltogether_http_server_errors_total{{{labels}}} {row["errors"]}',
                      f'reeltogether_http_duration_ms_sum{{{labels}}} {row["duration_ms_sum"]}',
                      f'reeltogether_http_duration_ms_count{{{labels}}} {row["count"]}'])
        cumulative = 0
        for bound,count in zip(data['latency_bucket_upper_bounds_ms'],row['latency_buckets']):
            cumulative += count
            lines.append(f'reeltogether_http_duration_ms_bucket{{{labels},le="{bound if bound is not None else "+Inf"}"}} {cumulative}')
    return '\n'.join(lines) + '\n'
