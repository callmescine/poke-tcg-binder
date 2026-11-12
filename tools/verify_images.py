"""Check every card's small image URL; swap in a working fallback host where needed. usage: verify_images.py DATA_JSON"""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

PATH = sys.argv[1]
data = json.load(open(PATH))
SCRYDEX_PLACEHOLDER = 45551
SERIE = {'svp': 'sv', 'mep': 'me', 'swshp': 'swsh'}


def ok(url):
    if not url: return False
    for method in ('HEAD', 'GET'):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, method=method, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40)
            size = r.headers.get('Content-Length')
            if size is None and method == 'HEAD': continue
            size = int(size) if size is not None else len(r.read())
            return r.status == 200 and not ('scrydex' in url and size == SCRYDEX_PLACEHOLDER)
        except urllib.error.HTTPError as e:
            if e.code == 405 and method == 'HEAD': continue
            return False
        except Exception:
            return False
    return False


def fix(c):
    sid, cid = c['s'], c['i']
    lid = cid.split('-', 1)[1]
    cands = [c['im']]
    if sid in SERIE:
        cands.append(f'https://assets.tcgdex.net/en/{SERIE[sid]}/{sid}/{lid}/low.webp')
        if lid.isdigit(): cands.append(f'https://images.scrydex.com/pokemon/{sid}-{int(lid)}/small')
    cands.append(f'https://images.scrydex.com/pokemon/{cid}/small')
    for u in cands:
        if ok(u): return cid, u
    return cid, ''


with ThreadPoolExecutor(12) as ex:
    res = dict(ex.map(fix, data['cards']))
changed = sum(1 for c in data['cards'] if res[c['i']] != c['im'])
for c in data['cards']: c['im'] = res[c['i']]
json.dump(data, open(PATH, 'w'), ensure_ascii=False, separators=(',', ':'))
print('checked', len(res), 'switched host', changed)
print('still without image:', [c['i'] + ' ' + c['n'] for c in data['cards'] if not c['im']])
