#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: IL PASSO B-7 — «niente nuovi codici generici», nella sola forma in cui
#        e' costruibile.
#
# ── PERCHE' NON E' UN CANCELLO SULLO STATO ──────────────────────────────
#   Il B-7 era scritto come un blocco: «un codice nuovo non deve coprire piu'
#   condizioni». Per applicarlo servirebbe saper dire, di ogni codice, se e'
#   generico. Lo strumento che lo sa dire — dbops.vw_codici_errore_forme_-
#   condizione — ne legge 75 su 344: gli altri 269 li dichiara illeggibili.
#
#   ⚠️ Un cancello che capisce un caso su cinque boccia a caso e passa a caso.
#   E boccerebbe anche i codici legittimamente trasversali (E_PERMESSO_NEGATO e'
#   ovunque per costruzione). Dopo due blocchi sbagliati qualcuno lo spegne — e
#   un presidio spento e' peggio di uno assente, perche' nel frattempo ha
#   convinto tutti di esserci.
#
# ── LA FORMA CHE FUNZIONA: SI PRESIDIA IL CAMBIAMENTO ───────────────────
#   Non «questo codice e' generico?» (serve il 100% di copertura) ma «questo
#   codice ha acquistato una condizione che non aveva?» — che la misura sa dire
#   con certezza sui 75 che legge.
#
#   ⭐ Ed e' il modo in cui gli accumulatori si formano davvero: nessuno crea un
#   codice generico di proposito. Si prende un codice che c'e' gia' e lo si usa
#   «anche per questo caso qui», una volta sola, e sembra ragionevole. La
#   sessantottesima volta e' E_GENERICO.
#
#   Stesso schema del pgtap-baseline: un file committato con lo stato noto, e la
#   CI che fallisce sul delta.
#
#     - un codice acquista una famiglia NOTA che non aveva  -> ROSSO
#     - un codice NUOVO nasce con 2+ famiglie note          -> ROSSO (nasce storto)
#     - un codice PERDE una famiglia (si e' ristretto)      -> blu, ma la
#       baseline va stretta SUBITO: finche' non lo e', quella famiglia resta
#       dichiarata ammessa e il presidio non la vedrebbe tornare
#     - un codice sparisce dallo scatto                     -> blu, si allinea
#
#   ⚠️ `IGNOTO` non entra mai nel confronto: e' la misura che dichiara di non
#   sapere. Se entrasse, un codice che passa da «non so» a «so» sembrerebbe un
#   peggioramento.
#
# ── ⚠️ IL LIMITE, DETTO QUI E NON SCOPERTO DOPO ─────────────────────────
#   Presidia i 75 codici che la misura sa leggere, non i 344. Non e' una
#   copertura totale ed e' inutile fingere il contrario: e' il rubinetto sui
#   codici vivi e leggibili, ed e' molto piu' di quello che c'era prima (niente).
#
# ── ⚠️ LA BASELINE E' MISURATA SU UN DATABASE ───────────────────────────
#   La misura legge `pg_proc`. Il DB di sviluppo NON e' ricostruito da zero e
#   puo' avere funzioni che la CI non ha: confrontare una corsa in CI con una
#   baseline presa in sviluppo produrrebbe finte regressioni. E' lo stesso
#   difetto delle due baseline pgTAP. Si sceglie con CODICI_BASELINE.
#
# USO
#   scripts/codici-errore-baseline.sh            # confronta, esce 1 sul delta
#   scripts/codici-errore-baseline.sh --update   # rigenera la baseline
# ------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BASELINE="${CODICI_BASELINE:-$ROOT_DIR/db/baseline-codici-errore-famiglie.tsv}"
QUERY="$ROOT_DIR/scripts/sql/codici_errore_famiglie_snapshot.sql"

PSQL=(psql --no-psqlrc -qAt -F$'\t' -v ON_ERROR_STOP=1)
[ -n "${PGHOST:-}" ]     || PSQL+=(-h localhost)
[ -n "${PGPORT:-}" ]     || PSQL+=(-p 5432)
[ -n "${PGUSER:-}" ]     || PSQL+=(-U "${DB_USER:-zeroerp_app}")
[ -n "${PGDATABASE:-}" ] || PSQL+=(-d "${DB_NAME:-zeroerp}")

UPDATE=0
for arg in "$@"; do
  case "$arg" in
    --update) UPDATE=1 ;;
    -h|--help) sed -n '2,60p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
    *) echo "Opzione sconosciuta: $arg" >&2; exit 2 ;;
  esac
done

ORA="$(mktemp)"; trap 'rm -f "$ORA"' EXIT
"${PSQL[@]}" -f "$QUERY" > "$ORA"

if [ "$UPDATE" = 1 ]; then
  { echo "# Baseline B-7 — famiglie di condizione per codice errore."
    echo "# Rigenerata con: scripts/codici-errore-baseline.sh --update"
    echo "# ⚠️ Aggiornarla e' una DECISIONE, non una formalita': ogni riga che"
    echo "#    cambia dice che un codice ha cambiato significato."
    echo "# formato: codice <TAB> famiglie_note <TAB> n_punti"
    cat "$ORA"
  } > "$BASELINE"
  echo "✅ baseline rigenerata: $(grep -cv '^#' "$BASELINE") codici → $BASELINE"
  exit 0
fi

if [ ! -f "$BASELINE" ]; then
  echo "⛔ baseline assente: $BASELINE" >&2
  echo "   Generala con: scripts/codici-errore-baseline.sh --update" >&2
  exit 2
fi

# ⚠️ Il confronto e' per INSIEME di famiglie, non per stringa: l'ordine lo
#    garantisce gia' la query, ma affidarsi all'ordine renderebbe il presidio
#    sensibile a un dettaglio che non significa niente.
ROSSI=0
STRETTI=0
while IFS=$'\t' read -r codice fam punti; do
  [ -z "${codice:-}" ] && continue
  base=$(awk -F'\t' -v c="$codice" '$1==c {print $2}' "$BASELINE" | head -1)
  if [ -z "$base" ]; then
    n=$(awk -F, '{print NF}' <<<"$fam")
    if [ "$n" -ge 2 ]; then
      echo "🔴 NASCE GENERICO  $codice — $n famiglie note dal primo giorno: $fam ($punti punti)"
      ROSSI=$((ROSSI+1))
    fi
    continue
  fi
  nuove=$(comm -13 <(tr ',' '\n' <<<"$base" | sort) <(tr ',' '\n' <<<"$fam" | sort) | paste -sd, -)
  if [ -n "$nuove" ]; then
    echo "🔴 ACCUMULA        $codice — famiglia nuova: $nuove   (prima: $base · ora: $fam · $punti punti)"
    ROSSI=$((ROSSI+1))
  fi
  # ⚠️ ANCHE IL RESTRINGIMENTO VA DETTO, e la prima versione non lo diceva.
  #   Un codice che PERDE una famiglia e' un miglioramento, quindi non e' rosso.
  #   Ma se la baseline non viene stretta continua a DICHIARARE quella famiglia
  #   come ammessa: il giorno che qualcuno ce la rimette, il confronto la trova
  #   gia' in baseline e **tace**. La baseline marcisce nel verso permissivo, che
  #   e' il solo verso in cui un presidio marcisce senza che nessuno se ne
  #   accorga. Trovato dal primo uso vero (scorporo di E_ERRORE_PARAMETRI,
  #   2026-08-08): la misura era giusta, il confronto non la guardava.
  perse=$(comm -23 <(tr ',' '\n' <<<"$base" | sort) <(tr ',' '\n' <<<"$fam" | sort) | paste -sd, -)
  if [ -n "$perse" ]; then
    echo "🔵 RISTRETTO       $codice — non copre piu': $perse   (prima: $base · ora: $fam · $punti punti)"
    STRETTI=$((STRETTI+1))
  fi
done < "$ORA"

# Righe della baseline che non si misurano piu': non e' un rosso, e' debito da togliere.
SPARITI=0
while IFS=$'\t' read -r codice fam punti; do
  case "$codice" in ''|\#*) continue ;; esac
  if ! awk -F'\t' -v c="$codice" '$1==c {found=1} END {exit !found}' "$ORA"; then
    echo "🔵 RIENTRATO       $codice — non piu' misurabile o senza famiglie note (era: $fam)"
    SPARITI=$((SPARITI+1))
  fi
done < "$BASELINE"

TOT=$(grep -cv '^#' "$BASELINE" || true)
echo
echo "Codici presidiati: $TOT   ·   accumuli nuovi: $ROSSI   ·   ristretti: $STRETTI   ·   rientrati: $SPARITI"
if [ "$ROSSI" -gt 0 ]; then
  echo
  echo "⛔ Un codice ha acquistato un tipo di condizione che non copriva." >&2
  echo "   NON si aggiorna la baseline per far passare la CI: e' la richiesta di" >&2
  echo "   una DECISIONE — o il codice nuovo va creato, o l'uso e' legittimo e" >&2
  echo "   allora la baseline si aggiorna con la ragione nel messaggio di commit." >&2
  echo "   Criterio: docs/it/dev/api.md §Tassonomia errori." >&2
  exit 1
fi
if [ "$SPARITI" -gt 0 ] || [ "$STRETTI" -gt 0 ]; then
  echo "   → allineare con: scripts/codici-errore-baseline.sh --update"
  echo "     ⚠️ Non e' facoltativo: finche' la baseline non e' stretta, quelle"
  echo "        famiglie restano AMMESSE e il presidio non le vedrebbe tornare."
fi
echo "✅ nessun codice ha allargato il proprio significato."
