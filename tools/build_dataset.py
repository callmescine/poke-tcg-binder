"""Build the art-card dataset for National Pokédex #001-1025.

Primary source: PokemonTCG/pokemon-tcg-data (English sets, rarities, dex numbers, images).
Supplement: TCGdex for Black Star promos the primary source lacks, plus MEP promos identified by eye.
Cross-check: TCGdex sweep of every English card by dexId, reported to stdout.

usage: build_dataset.py PTCG_DIR TCGDEX_DIR POKEAPI_DIR OUT_JSON
"""
import csv, collections, datetime, glob, json, os, re, sys, unicodedata

PTCG, TDX, PAPI, OUT = sys.argv[1:5]
START = '2006/01/01'
MAX_DEX = 1025
REGIONS = [('Kanto', 1, 151), ('Johto', 152, 251), ('Hoenn', 252, 386), ('Sinnoh', 387, 493), ('Unova', 494, 649),
           ('Kalos', 650, 721), ('Alola', 722, 809), ('Galar', 810, 905), ('Paldea', 906, 1025)]

sets = {s['id']: s for s in json.load(open(f'{PTCG}/sets/en.json'))}

PROMO_SETS = {'dpp', 'hsp', 'bwp', 'xyp', 'smp', 'swshp', 'svp', 'fut20'}
GALLERY_SETS = {'swsh9tg', 'swsh10tg', 'swsh11tg', 'swsh12tg', 'swsh12pt5gg'}
SHINY_VAULT_SETS = {'sma', 'swsh45sv'}
CLASSIC_SETS = {'cel25c', 'me55c'}

RARITY_CAT = {
    'Special Illustration Rare': 'sir',
    'Illustration Rare': 'ir',
    'Rare Ultra': 'fullart', 'Ultra Rare': 'fullart',
    'Rare Secret': 'secret', 'Rare Rainbow': 'secret', 'Hyper Rare': 'secret', 'Mega Hyper Rare': 'secret',
    'Shiny Rare': 'shiny', 'Shiny Ultra Rare': 'shiny', 'Rare Shiny': 'shiny', 'Rare Shiny GX': 'shiny',
    'Rare Shining': 'shiny', 'Radiant Rare': 'shiny', 'Rare Holo Star': 'shiny',
    'Pikachu Rare': 'special', 'Futuristic Rare': 'special', 'MEGA_ATTACK_RARE': 'special',
    'Amazing Rare': 'special', 'Black White Rare': 'special', 'LEGEND': 'special',
}
RARITY_LABEL = {
    'Rare Ultra': 'Ultra Rare', 'Rare Secret': 'Secret Rare', 'Rare Rainbow': 'Rainbow Rare',
    'Rare Holo Star': 'Gold Star', 'Rare Shiny': 'Shiny Rare', 'Rare Shiny GX': 'Shiny Rare GX',
    'Rare Shining': 'Shining Rare', 'MEGA_ATTACK_RARE': 'Mega Attack Rare',
    'Trainer Gallery Rare Holo': 'Trainer Gallery', 'Rare Holo': 'Holo Rare', 'Rare Holo V': 'Holo Rare V',
    'Rare Holo VMAX': 'Holo Rare VMAX', 'Rare Holo VSTAR': 'Holo Rare VSTAR', 'Rare Holo EX': 'Holo Rare EX',
    'Rare Holo GX': 'Holo Rare GX', 'Rare Holo LV.X': 'Holo Rare LV.X', 'Rare Holo ex': 'Holo Rare ex',
    'Rare Prime': 'Prime', 'Rare BREAK': 'BREAK Rare',
}
NAME_FIX = {'ナッシー[Exeggutor]': 'Exeggutor (Japanese print)'}
RC_TOTAL = {'g1': 32, 'bw11': 25}
# 30th Celebration's R/RGB, G/RGB and B/RGB Mew secret rares, numbered with letters and listed as Common upstream
RGB_MEW = {('me55', 'R'), ('me55', 'G'), ('me55', 'B')}
# MEP promos that have images on Scrydex but no card data in either database yet; identified from the card images
MEP_BY_EYE = [(89, 'Mega Zeraora ex', [807]), (90, 'Mega Darkrai ex', [491]), (91, 'Mega Dragonite ex', [149]),
              (93, 'Pikachu', [25]), (94, 'Alolan Exeggutor', [103]), (95, 'Lucario', [448]), (96, 'Moltres', [146]),
              (97, 'Articuno', [144]), (98, 'Zapdos', [145]), (99, 'Greninja ex', [658]), (100, 'Sylveon ex', [700]),
              (101, 'Nidorina', [30]), (102, 'Victini', [494]), (103, 'Zeraora', [807]), (104, 'Mewtwo', [150]),
              (105, 'Mew', [151]), (106, 'Ditto', [132]), (107, 'Pikachu ex', [25]), (108, 'Espeon ex', [196]),
              (109, 'Pikachu ex', [25]), (110, 'Umbreon ex', [197])]


def categorize(sid, c):
    r, num = c.get('rarity') or '', c['number']
    if sid in CLASSIC_SETS: return 'classic'
    if (sid, num) in RGB_MEW: return 'secret'
    if sid in GALLERY_SETS: return 'gallery'
    if sid in SHINY_VAULT_SETS: return 'shiny'
    if sid in PROMO_SETS: return 'promo'
    if sid == 'cel25' and num == '25': return 'secret'  # gold Mew, mislabelled as Holo Rare upstream
    if r in RARITY_CAT: return RARITY_CAT[r]
    if num.startswith('RC'): return 'special'  # Radiant Collection
    if num.startswith(('SH', 'SL')): return 'shiny'  # DP-era shiny secrets, Call of Legends shiny legendaries
    return None


def display_number(sid, num):
    st = sets.get(sid)
    if sid == 'svp': return 'SVP ' + num.zfill(3)
    if sid == 'mep': return 'MEP ' + num
    if sid in PROMO_SETS: return num
    if sid in CLASSIC_SETS: return num  # reprints keep their original card number
    if (sid, num) in RGB_MEW: return f'{num}/RGB'
    m = re.match(r'^([A-Z]+)(\d+)$', num)
    if m:
        pre = m.group(1)
        if pre == 'RC' and sid in RC_TOTAL: return f'{num}/RC{RC_TOTAL[sid]}'
        if st and st.get('printedTotal') and pre in ('TG', 'GG', 'SV'):
            return f"{num}/{pre}{st['printedTotal']}"
        return num
    if st and st.get('printedTotal') and num.isdigit():
        width = 3 if st['releaseDate'] >= '2020/01/01' else 1
        return f"{num.zfill(width)}/{str(st['printedTotal']).zfill(width)}"
    return num


def norm_num(n):
    n = n.upper().replace('SVP ', '').replace('MEP ', '')
    m = re.match(r'^([A-Z]*)0*(\d+)([A-Z]?)$', n)
    return f'{m.group(1)}{int(m.group(2))}{m.group(3)}' if m else n


# --- Pokémon names and types -------------------------------------------------------
names = {int(r['pokemon_species_id']): r['name'] for r in csv.DictReader(open(f'{PAPI}/pokemon_species_names.csv'))
         if r['local_language_id'] == '9' and int(r['pokemon_species_id']) <= MAX_DEX}
tnames = {r['id']: r['identifier'] for r in csv.DictReader(open(f'{PAPI}/types.csv'))}
ptypes = collections.defaultdict(list)
for r in csv.DictReader(open(f'{PAPI}/pokemon_types.csv')):
    i = int(r['pokemon_id'])
    if i <= MAX_DEX: ptypes[i].append((int(r['slot']), tnames[r['type_id']]))
assert len(names) == MAX_DEX, len(names)
pokemon = [{'id': i, 'n': names[i].replace('’', "'"), 't': [t for _, t in sorted(ptypes[i])]} for i in range(1, MAX_DEX + 1)]


def plain(s):
    s = unicodedata.normalize('NFD', s.replace('’', "'")).encode('ascii', 'ignore').decode().lower()
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s).strip() + ' '


# longest names first, so "Mewtwo" wins over "Mew" and "Iron Hands" over shorter matches
NAME_INDEX = sorted(((plain(n), i) for i, n in names.items()), key=lambda x: -len(x[0]))
resolved_by_name = []


def dex_for(c):
    dex = [d for d in (c.get('nationalPokedexNumbers') or []) if d]
    if dex or not c.get('supertype', '').startswith('Pok'): return dex
    card = plain(c['name'])
    for key, i in NAME_INDEX:
        if key in card:
            resolved_by_name.append(f"{c['id']} {c['name']} -> #{i} {names[i]}")
            return [i]
    return []


MAP = {'sv01': 'sv1', 'sv02': 'sv2', 'sv03': 'sv3', 'sv03.5': 'sv3pt5', 'sv04': 'sv4', 'sv04.5': 'sv4pt5', 'sv05': 'sv5',
       'sv06': 'sv6', 'sv06.5': 'sv6pt5', 'sv07': 'sv7', 'sv08': 'sv8', 'sv08.5': 'sv8pt5', 'sv09': 'sv9',
       'sv10.5b': 'zsv10pt5', 'sv10.5w': 'rsv10pt5', 'swsh3.5': 'swsh35', 'swsh4.5': 'swsh45', 'swsh4.5sv': 'swsh45sv',
       'swsh10.5': 'pgo', 'swsh12.5': 'swsh12pt5', 'swsh12.5gg': 'swsh12pt5gg', 'sm3.5': 'sm35', 'sm7.5': 'sm75',
       'me01': 'me1', 'me02': 'me2', 'me02.5': 'me2pt5', 'me03': 'me3', 'me04': 'me4', 'me05': 'me5', '30th': 'me55',
       '30th-c': 'me55c', 'fut2020': 'fut20', 'cel25cc': 'cel25c', 'hgssp': 'hsp'}
# second opinion: when the main database files a card under a plain rarity but TCGdex names an art rarity, trust TCGdex
TDX_CAT = {'Illustration rare': ('ir', 'Illustration Rare'), 'Special illustration rare': ('sir', 'Special Illustration Rare'),
           'Hyper rare': ('secret', 'Hyper Rare'), 'Mega Hyper Rare': ('secret', 'Mega Hyper Rare'), 'Secret Rare': ('secret', 'Secret Rare'),
           'Shiny rare': ('shiny', 'Shiny Rare'), 'Shiny Ultra Rare': ('shiny', 'Shiny Ultra Rare'), 'Shiny rare V': ('shiny', 'Shiny Rare V'),
           'Shiny rare VMAX': ('shiny', 'Shiny Rare VMAX'), 'Radiant Rare': ('shiny', 'Radiant Rare'), 'Amazing Rare': ('special', 'Amazing Rare'),
           'Black White Rare': ('special', 'Black White Rare'), 'LEGEND': ('special', 'LEGEND')}
tdx_rarity = {}
for f in glob.glob(f'{TDX}/sweep/*.json'):
    for c in json.load(open(f)):
        tdx_rarity[(MAP.get(c['set']['id'], c['set']['id']), norm_num(c['localId']))] = c.get('rarity')
second_opinion = []


# --- primary source -------------------------------------------------------------------
cards, seen = [], set()
for f in sorted(glob.glob(f'{PTCG}/cards/en/*.json')):
    sid = os.path.basename(f)[:-5]
    st = sets[sid]
    if st['releaseDate'] < START: continue
    for c in json.load(open(f)):
        dex = dex_for(c)
        if not any(1 <= d <= MAX_DEX for d in dex): continue
        cat = categorize(sid, c)
        r = c.get('rarity') or 'Promo'
        label = 'Secret Rare (gold)' if (sid == 'cel25' and c['number'] == '25') else RARITY_LABEL.get(r, r)
        if not cat:
            tr = tdx_rarity.get((sid, norm_num(c['number'])))
            m = re.match(r'^(\d+)$', c['number'])
            if tr in TDX_CAT:
                cat, label = TDX_CAT[tr]
            elif m and st.get('printedTotal') and int(m.group(1)) > st['printedTotal']:
                cat, label = 'secret', 'Secret Rare'  # numbered past the set total, whatever the listed rarity
            else:
                continue
            second_opinion.append(f"{c['id']} {c['name']}: {c.get('rarity')} -> {label}")
        # upstream tags every Sword & Shield secret VMAX/VSTAR as rainbow, alt arts included; the card itself says Secret Rare
        if r == 'Rare Rainbow' and st['series'] == 'Sword & Shield': label = 'Secret Rare'
        if (sid, c['number']) in RGB_MEW: label = 'Secret Rare (RGB)'
        cards.append({
            'i': c['id'], 'n': NAME_FIX.get(c['name'], c['name']), 's': sid,
            'no': display_number(sid, c['number']), 'r': label, 'c': cat,
            'a': c.get('artist') or '', 'im': c['images']['small'], 'dx': dex,
        })
        seen.add((sid, norm_num(c['number'])))

# --- TCGdex promo supplement -------------------------------------------------------------
tdx_mep = json.load(open(f'{TDX}/set_mep.json'))
added = []
for f in sorted(glob.glob(f'{TDX}/cards/*.json')):
    c = json.load(open(f))
    tsid, lid = c['set']['id'], c['localId']
    if (tsid, norm_num(lid)) in seen: continue
    dex = c.get('dexId') or []
    if not any(1 <= d <= MAX_DEX for d in dex): continue
    cards.append({
        'i': c['id'], 'n': c['name'], 's': tsid,
        'no': ('SVP ' + lid.zfill(3)) if tsid == 'svp' else ('MEP ' + lid) if tsid == 'mep' else lid,
        'r': 'Promo', 'c': 'promo', 'a': c.get('illustrator') or '',
        'im': (c['image'] + '/low.webp') if c.get('image') else '', 'dx': dex,
    })
    added.append(f'{tsid}:{lid} {c["name"]}')
    seen.add((tsid, norm_num(lid)))
for n, name, dex in MEP_BY_EYE:
    if ('mep', str(n)) in seen: continue
    cards.append({'i': f'mep-{n:03d}', 'n': name, 's': 'mep', 'no': f'MEP {n:03d}', 'r': 'Promo', 'c': 'promo',
                  'a': '', 'im': f'https://images.scrydex.com/pokemon/mep-{n}/small', 'dx': dex})
    added.append(f'mep:{n} {name} (by eye)')
    seen.add(('mep', str(n)))
print(f'TCGdex and by-eye promo supplement: {len(added)} cards')

# --- set table ---------------------------------------------------------------------------
set_out = {}
for sid in {c['s'] for c in cards}:
    if sid in sets:
        st = sets[sid]
        set_out[sid] = {'n': st['name'], 'e': st['series'], 'd': st['releaseDate'].replace('/', '-'),
                        'sym': st.get('images', {}).get('symbol', '')}
    elif sid == 'mep':
        set_out[sid] = {'n': 'Mega Evolution Black Star Promos', 'e': 'Mega Evolution', 'd': tdx_mep.get('releaseDate', '2025-09-26'),
                        'sym': (tdx_mep['symbol'] + '.png') if tdx_mep.get('symbol') else ''}
    if sid in PROMO_SETS or sid == 'mep':
        set_out[sid]['p'] = 1

cards.sort(key=lambda c: (set_out[c['s']]['d'], c['s'], c['no']), reverse=True)
json.dump({'generated': datetime.date.today().isoformat(), 'pokemon': pokemon, 'sets': set_out, 'cards': cards},
          open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))

print('cards:', len(cards), dict(collections.Counter(c['c'] for c in cards)))
print('rescued by TCGdex rarity or set numbering:', second_opinion)
print('matched by name (no dex number upstream):', len(resolved_by_name))
for line in resolved_by_name: print('   ', line)
for reg, lo, hi in REGIONS:
    arts = {c['i'] for c in cards if c['c'] != 'promo' and any(lo <= d <= hi for d in c['dx'])}
    promos = {c['i'] for c in cards if c['c'] == 'promo' and any(lo <= d <= hi for d in c['dx'])}
    print(f'{reg:7s} #{lo:04d}-{hi:04d}: {len(arts):4d} art cards, {len(promos):3d} promos')

# --- cross-check against TCGdex -------------------------------------------------------------
ART_TDX = {'Illustration rare', 'Special illustration rare', 'Ultra Rare', 'Secret Rare', 'Hyper rare', 'Mega Hyper Rare',
           'Shiny rare', 'Shiny Ultra Rare', 'Shiny rare V', 'Shiny rare VMAX', 'Radiant Rare', 'Amazing Rare',
           'Rare Holo Star', 'Black White Rare', 'LEGEND'}
by_key = {(c['s'], norm_num(c['no'].split('/')[0])): c for c in cards}
missing, disagree = [], []
for f in glob.glob(f'{TDX}/sweep/*.json'):
    for c in json.load(open(f)):
        tsid = c['set']['id']
        psid = MAP.get(tsid, tsid)
        if psid not in sets: continue  # Pocket, McDonald's, trainer kits and pre-2006 sets
        st = sets[psid]
        if st['releaseDate'] < START: continue
        have = by_key.get((psid, norm_num(c['localId'])))
        rar = c.get('rarity')
        if rar in ART_TDX and not have:
            n = re.match(r'^0*(\d+)$', c['localId'])
            secret = bool(n and st.get('printedTotal') and int(n.group(1)) > st['printedTotal'])
            if rar != 'Ultra Rare' or secret:  # TCGdex calls every EX/GX/V "Ultra Rare"; only secret-numbered ones are art cards
                missing.append(f"{tsid}:{c['localId']} {c['name']} [{rar}]")
        if have and have['c'] in ('ir', 'sir') and rar not in ('Illustration rare', 'Special illustration rare'):
            disagree.append(f"{tsid}:{c['localId']} {c['name']} ours={have['r']} tcgdex={rar}")
print('\nTCGdex art cards not in the dataset:', len(missing))
for m in sorted(set(missing)): print('   ', m)
print('IR/SIR rarity disagreements:', disagree)
