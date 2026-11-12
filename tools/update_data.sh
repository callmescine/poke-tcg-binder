#!/usr/bin/env bash
# Rebuild the card data from its sources and write it into the page.
# usage: tools/update_data.sh WORK_DIR [PAGE_HTML]
# WORK_DIR holds the downloads, data.json and build.log. Use a new, empty folder each time: the TCGdex
# fetchers skip files that already exist, so an old folder would rebuild from old data.
# PAGE_HTML defaults to the site's index.html.
set -euo pipefail
TOOLS="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?usage: tools/update_data.sh WORK_DIR [PAGE_HTML]}"
PAGE="${2:-$TOOLS/../index.html}"
mkdir -p "$WORK/ptcg" "$WORK/pokeapi" "$WORK/tcgdex"

echo "Downloading the Pokémon TCG data set..."
curl -sSfL -m 600 "https://codeload.github.com/PokemonTCG/pokemon-tcg-data/zip/refs/heads/master" -o "$WORK/ptcg/repo.zip"
unzip -q -o "$WORK/ptcg/repo.zip" -d "$WORK/ptcg"

echo "Downloading Pokémon names and types from PokéAPI..."
for f in pokemon_species_names pokemon_types types; do
  curl -sSf -m 120 "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/$f.csv" -o "$WORK/pokeapi/$f.csv"
done

echo "Fetching promo cards and the cross-check sweep from TCGdex (several minutes)..."
python3 -I "$TOOLS/fetch_tcgdex_promos.py" "$WORK/tcgdex"
python3 -I "$TOOLS/fetch_tcgdex_sweep.py" "$WORK/tcgdex/sweep" 1 1025

echo "Building the card list..."
python3 -I "$TOOLS/build_dataset.py" "$WORK/ptcg/pokemon-tcg-data-master" "$WORK/tcgdex" "$WORK/pokeapi" "$WORK/data.json" | tee "$WORK/build.log"

echo "Checking every card image..."
python3 -I "$TOOLS/verify_images.py" "$WORK/data.json"

python3 -I "$TOOLS/page_data.py" embed "$WORK/data.json" "$PAGE"
