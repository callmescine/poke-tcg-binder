"""Fetch full TCGdex card records for the Black Star promo sets. usage: fetch_tcgdex_promos.py OUT_DIR"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, 'cards'), exist_ok=True)
def get(u):
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    raise err
ids = []
for sid in ['svp', 'mep', 'swshp']:
    s = get('https://api.tcgdex.net/v2/en/sets/' + sid)
    json.dump(s, open(os.path.join(OUT, f'set_{sid}.json'), 'w'))
    ids += [c['id'] for c in s['cards']]
def one(cid):
    p = os.path.join(OUT, 'cards', cid.replace('/', '_') + '.json')
    if os.path.exists(p): return
    try:
        json.dump(get('https://api.tcgdex.net/v2/en/cards/' + urllib.request.quote(cid)), open(p, 'w'))
    except Exception as e:
        print('FAIL', cid, e)
with ThreadPoolExecutor(6) as ex: list(ex.map(one, ids))
print('promo cards fetched', len(os.listdir(os.path.join(OUT, 'cards'))), 'of', len(ids))
