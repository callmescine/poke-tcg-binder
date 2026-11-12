# Card data tools

The site's card list lives inside `index.html`, in `<script id="kai-data" type="application/json">`. These scripts rebuild it from public sources: the [Pokémon TCG API data set](https://github.com/PokemonTCG/pokemon-tcg-data), [TCGdex](https://tcgdex.dev) and [PokéAPI](https://github.com/PokeAPI/pokeapi).

## Updating the data

1. Run the whole pipeline with a new, empty folder:

   ```bash
   tools/update_data.sh ~/binder-data-$(date +%F)
   ```

   It downloads the sources, builds the list, checks every card image and writes the result into `index.html`. Most of its 10 or so minutes go to TCGdex requests.
2. Read the build output, which is also saved as `build.log` in that folder:
   - `cards:` shows the totals by category.
   - `rescued by TCGdex rarity or set numbering` lists cards the main data set files under a plain rarity but that were kept, because TCGdex names an art rarity or the card is numbered past its set's total.
   - `matched by name` lists cards that have no Pokédex number upstream and were matched to a Pokémon by name. Check any new ones.
   - `TCGdex art cards not in the dataset` lists art cards that TCGdex knows about but the build skipped. New entries usually mean a set ID missing from `MAP` or a rarity missing from `RARITY_CAT`.
3. Open `index.html` locally, spot-check the new cards, then commit it.

## When something changes

- **A new set.** If TCGdex and pokemontcg.io give it different IDs, add the pair to `MAP` in `build_dataset.py`. A new Black Star promo series goes in `PROMO_SETS`, and in `fetch_tcgdex_promos.py` if pokemontcg.io doesn't list it.
- **A new rarity name.** Add it to `RARITY_CAT`, and to `RARITY_LABEL` if it needs a friendlier name. The site's categories are `CATS` in `index.html`.
- **New Pokémon.** Raise `MAX_DEX` and `REGIONS` in `build_dataset.py`, the sweep range in `update_data.sh`, and `REGIONS` in `index.html`.
- **Hand-made entries.** `RGB_MEW`, `MEP_BY_EYE` and `NAME_FIX` cover cards that the databases list wrongly or not at all. Remove a `MEP_BY_EYE` entry once TCGdex lists that card.

## The scripts

| Script | What it does |
| --- | --- |
| `update_data.sh WORK_DIR [PAGE_HTML]` | Runs everything below in order. |
| `fetch_tcgdex_promos.py OUT_DIR` | Downloads TCGdex's Black Star promo sets (svp, mep, swshp). |
| `fetch_tcgdex_sweep.py OUT_DIR FIRST LAST` | Downloads every TCGdex card for each Pokédex number, for the cross-check. |
| `build_dataset.py PTCG_DIR TCGDEX_DIR POKEAPI_DIR OUT_JSON` | Builds the card list. |
| `verify_images.py DATA_JSON` | Checks every card image and switches to TCGdex or Scrydex where pokemontcg.io has none. |
| `page_data.py extract PAGE_HTML OUT_JSON` | Copies the data out of the page, for example to compare it with a new build. |
| `page_data.py embed DATA_JSON PAGE_HTML` | Writes data into the page. |

The PDF export draws pokemontcg.io cards from Scrydex's copy (`images.scrydex.com/pokemon/<card id>/medium`), because pokemontcg.io doesn't let pages read its images. Scrydex shows a card back for any card it doesn't have yet.
