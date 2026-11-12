"""Fetch every English TCGdex card for a range of National Pokédex numbers, for cross-checking.
usage: fetch_tcgdex_sweep.py OUT_DIR FIRST LAST"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
OUT, FIRST, LAST = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(OUT, exist_ok=True)
Q = '{ cards(filters: {dexId: %d}, pagination: {page: %d, itemsPerPage: 250}) { id localId name rarity dexId set { id name } } }'
def post(q):
    for i in range(5):
        try:
            req = urllib.request.Request('https://api.tcgdex.net/v2/graphql', data=json.dumps({'query': q}).encode(),
                                         headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            return json.load(urllib.request.urlopen(req, timeout=90))
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    raise err
def one(dex):
    p = os.path.join(OUT, f'{dex:04d}.json')
    if os.path.exists(p): return dex, -1
    allc, page = [], 1
    while True:
        r = post(Q % (dex, page))
        if 'errors' in r: print('ERR', dex, str(r['errors'][0])[:120]); break
        cs = r['data']['cards'] or []
        allc += cs
        if len(cs) < 250: break
        page += 1
    json.dump(allc, open(p, 'w'))
    return dex, len(allc)
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(one, range(FIRST, LAST + 1)))
print('sweep done', FIRST, LAST, 'cards', sum(n for _, n in res if n > 0))
