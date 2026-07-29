# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — CONTRATTO fra il context builder della fattura e il template
#         PUBBLICATO: verifica che il PDF contenga davvero i valori, non che
#         il render non sollevi.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fatturazione-render-stampa.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE. Il template legge il context con `.get()`, che DISINNESCA
# StrictUndefined: una chiave sbagliata non e' un errore di render, e' un
# trattino stampato in fattura. E' successo due volte:
#   1) il template chiedeva `quantita`/`sconto_perc`/`importo_riga` mentre il
#      repository esponeva `qta`/`sconto_percentuale`/`imponibile_riga`
#      -> tre colonne su otto stampavano "-" su ogni fattura del sistema;
#   2) l'importo di riga non veniva calcolato da nessuno -> totali a 0,00.
# In entrambi i casi il PDF veniva generato, la coda di stampa diventava FATTO,
# e nessun controllo se ne accorgeva. Lo smoke C-9 conta le righe di stampa
# prodotte: un PDF di soli trattini lo supera.
#
# COSA PRESIDIA. Che ogni valore presente nel context ARRIVI nella cella
# corrispondente del documento renderizzato. Non asserisce importi attesi — quelli
# dipendono dai dati — ma la CORRISPONDENZA context -> output, che e' il
# contratto che si e' rotto.
#
# IDEMPOTENZA. Sola lettura: nessuna scrittura, nessun documento persistito,
# nessuna riga in coda. Rieseguibile sempre.
#
# Indice test (1..8):
#   1  esiste una versione PUBBLICATA del template fattura
#   2  il context espone le chiavi di contratto delle righe
#   3  il render Jinja non solleva (StrictUndefined attivo)
#   4  ogni riga del context compare nel documento con quantita' e importo
#   5  nessuna cella numerica stampa "-" dove il context ha un valore
#   6  i totali di testata compaiono nella LORO sezione del documento
#   7  il PDF si genera e non e' un guscio vuoto
#   8  auto-verifica: il presidio del caso 5 e' vivo (mutazione controllata)
# ------------------------------------------------------------

import re
from datetime import date

from django.db import connection

from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.render_service import _render_html_with_jinja, render_pdf
from apps.vendite.services.fattura_document_context_builder import (
    FatturaDocumentContextBuilder,
)

# Codice del template documento da collaudare. E' il `codice` di
# `documenti.template_documenti`, non un id: gli id cambiano fra ambienti.
TEMPLATE_CODICE = "Fattura"

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Estrae le celle della tabella righe dal documento renderizzato,
#        ripulite dal markup. Una lista di celle per riga.
def celle_per_riga(html):
    blocco = re.search(r"Righe fattura.*?</table>", html, re.S)
    if not blocco:
        return []
    righe = re.findall(r"<tr[^>]*>(.*?)</tr>", blocco.group(0), re.S)
    out = []
    for tr in righe[1:]:  # [0] e' l'intestazione
        celle = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        ]
        if celle:
            out.append(celle)
    return out


print("\n=== SMOKE render stampa fattura (contratto context <-> template) ===\n")

with connection.cursor() as cur:
    # `vendite.fatture` e' RLS: senza contesto operatore il context builder
    # solleverebbe E_NOT_FOUND su una fattura che esiste.
    cur.execute(
        "SELECT set_config('app.ruolo_applicativo','OPERATORE',false),"
        "       set_config('app.current_user_id', (SELECT auth_user_id::text"
        "         FROM config.user_emittenti_fiscali LIMIT 1), false)"
    )
    # Una fattura reale CON righe: senza righe il contratto non si esercita.
    cur.execute(
        """
        SELECT r.fattura_id, count(*)
          FROM vendite.fatture_righe r
         GROUP BY r.fattura_id
         ORDER BY count(*) DESC, r.fattura_id DESC
         LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("Nessuna fattura con righe: impossibile collaudare la stampa.")
    fattura_id, n_righe = row

    cur.execute(
        "SELECT id FROM documenti.template_documenti WHERE codice = %s", [TEMPLATE_CODICE]
    )
    t = cur.fetchone()
    if not t:
        raise SystemExit(f"Template '{TEMPLATE_CODICE}' inesistente.")
    template_id = t[0]

print(f"fattura {fattura_id} ({n_righe} righe), template '{TEMPLATE_CODICE}'\n")

versione = DocumentiRepository().get_versione_pubblicata_attiva(
    template_id, today=date.today()
)
check("1) esiste una versione PUBBLICATA del template", versione is not None)
if versione is None:
    raise SystemExit("Nessuna versione pubblicata: il resto dello smoke non ha senso.")
print(f"    versione {versione['versione']} (id {versione['id']})\n")

ctx = FatturaDocumentContextBuilder().build_context(fattura_id)
righe_ctx = ctx["righe"]

# 2) chiavi di contratto — quelle che il template legge con `.get()`.
CONTRATTO = ("quantita", "prezzo_unitario", "sconto_percentuale", "importo_riga")
mancanti = [k for k in CONTRATTO if k not in righe_ctx[0]]
check("2) il context espone le chiavi di contratto", not mancanti,
      f"mancanti: {mancanti}" if mancanti else f"presenti: {', '.join(CONTRATTO)}")

# 3) render
try:
    html = _render_html_with_jinja(versione["html_template"], ctx)
    reso = True
except Exception as exc:  # noqa: BLE001 — lo smoke deve riportare, non propagare
    reso = False
    html = ""
    check("3) il render Jinja non solleva", False, f"{type(exc).__name__}: {exc}")
if reso:
    check("3) il render Jinja non solleva", True)

celle = celle_per_riga(html)

# 4) corrispondenza context -> documento, riga per riga.
#    Le righe KIT_PADRE non esistono in tabella ma sono nel context: si
#    confronta per posizione, che e' l'ordine con cui il template le stampa.
disallineate = []
for i, riga in enumerate(righe_ctx):
    if i >= len(celle):
        disallineate.append(f"riga {i + 1} assente nel documento")
        continue
    testo = " | ".join(celle[i])
    for campo in ("quantita", "importo_riga"):
        valore = riga.get(campo)
        if valore is None:
            continue  # sui componenti di kit e' NULL per costruzione
        if str(valore) not in testo:
            disallineate.append(f"riga {i + 1}: {campo}={valore} non nel documento")
check("4) ogni riga del context compare con quantita' e importo",
      not disallineate and len(celle) == len(righe_ctx),
      "; ".join(disallineate[:3]) if disallineate
      else f"{len(celle)} righe rese su {len(righe_ctx)} nel context")

# 5) nessun trattino dove il context ha un valore. E' il sintomo esatto del
#    difetto d'origine: chiave sbagliata -> `.get()` torna None -> "-".
trattini = []
for i, riga in enumerate(righe_ctx):
    if i >= len(celle):
        continue
    valorizzati = [c for c in CONTRATTO if riga.get(c) is not None]
    if valorizzati and celle[i].count("-") > 0:
        posizioni = [j for j, c in enumerate(celle[i]) if c == "-"]
        trattini.append(f"riga {i + 1}: celle {posizioni} a trattino "
                        f"con {len(valorizzati)} campi valorizzati nel context")
check("5) nessuna cella a trattino dove il context ha un valore", not trattini,
      "; ".join(trattini[:3]))

# 6) totali di testata, cercati NELLA LORO SEZIONE e non in tutto il
#    documento: un importo come "0.000000" comparirebbe ovunque, e
#    l'asserzione passerebbe anche a template rotto.
totali = ctx["fattura"]["totali"]
imponibile = totali.get("imponibile")
sezione = re.search(r"<th>Imponibile</th>.*?</table>", html, re.S)
check("6) i totali di testata compaiono nella loro sezione",
      sezione is not None and imponibile is not None
      and str(imponibile) in sezione.group(0),
      f"imponibile={imponibile}"
      + ("" if sezione else " — sezione totali non trovata nel documento"))

# 7) il PDF si genera davvero
try:
    pdf = render_pdf(template_versione=versione, context=ctx)
    check("7) il PDF si genera e non e' un guscio vuoto",
          pdf.startswith(b"%PDF") and len(pdf) > 5000, f"{len(pdf)} byte")
except Exception as exc:  # noqa: BLE001
    check("7) il PDF si genera e non e' un guscio vuoto", False,
          f"{type(exc).__name__}: {exc}")

# 8) AUTO-VERIFICA. Un presidio che non puo' fallire non presidia nulla: il
#    difetto d'origine e' sopravvissuto proprio a controlli sempre verdi. Si
#    rende lo stesso template con un context MUTATO — la chiave di contratto
#    rinominata, esattamente il difetto storico — e si pretende che il caso 5
#    lo intercetti.
ctx_rotto = {**ctx, "righe": [
    {k: v for k, v in r.items() if k != "importo_riga"} for r in righe_ctx
]}
try:
    html_rotto = _render_html_with_jinja(versione["html_template"], ctx_rotto)
    celle_rotte = celle_per_riga(html_rotto)
    intercettato = any(c.count("-") > 0 for c in celle_rotte)
except Exception:  # noqa: BLE001 — anche sollevare va bene: il difetto emerge
    intercettato = True
check("8) auto-verifica: il presidio del caso 5 e' vivo", intercettato,
      "rimuovendo `importo_riga` dal context il documento deve mostrare trattini")

print("\n--- righe rese ---")
for c in celle:
    print("   ", " | ".join(c))

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
