"""Read or replace the card data embedded in index.html.

usage: page_data.py extract PAGE_HTML OUT_JSON
       page_data.py embed DATA_JSON PAGE_HTML
"""
import json, re, sys

BLOCK = re.compile(r'(<script id="kai-data" type="application/json">)(.*?)(</script>)', re.S)


def find(page):
    m = BLOCK.search(page)
    if not m: sys.exit('no <script id="kai-data"> block in the page')
    return m


if len(sys.argv) != 4 or sys.argv[1] not in ('extract', 'embed'): sys.exit(__doc__)
mode, src, dst = sys.argv[1:4]
if mode == 'extract':
    data = json.loads(find(open(src, encoding='utf-8').read()).group(2))  # JSON reads the page's <\/ escapes as </
    json.dump(data, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(dst, len(data['cards']), 'cards')
else:
    data = json.load(open(src, encoding='utf-8'))
    page = open(dst, encoding='utf-8').read()
    m = find(page)
    # </ would end the script tag early, so it goes in as <\/
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    open(dst, 'w', encoding='utf-8').write(page[:m.start(2)] + blob + page[m.end(2):])
    print(dst, len(data['cards']), 'cards embedded')
