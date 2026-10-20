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
# CONTESTO. `dev.smoke` (BB `_smoke_contesto`), super admin: il perimetro e'
# largo, e ogni template si risolve per l'emittente della SUA fattura.
#
# IDEMPOTENZA. Nessun documento persistito, nessuna riga in coda. I casi 1-8
# sono di SOLA LETTURA; il caso 9 (piano rate, aggiunto il 2026-08-02) genera
# le rate dentro `transaction.atomic()` e fa ROLLBACK — vedi la sua nota per
# il perche' non sia evitabile. Rieseguibile sempre.
#
# Indice test (1..9):
#   1  esiste una versione PUBBLICATA del template fattura
#   2  il context espone le chiavi di contratto delle righe
#   3  il render Jinja non solleva (StrictUndefined attivo)
#   4  ogni riga del context compare nel documento con quantita' e importo
#   4b i componenti dei kit compaiono sotto il loro padre (righe `row-componente`)
#   5  nessuna cella numerica stampa "-" dove il context ha un valore
#   6  i totali di testata compaiono nella LORO sezione del documento
#   7  il PDF si genera e non e' un guscio vuoto
#   8  auto-verifica: il presidio del caso 5 e' vivo (mutazione controllata)
#   9  il documento stampa il PIANO RATE: sezione assente prima, presente dopo
#      la generazione, coi valori del context nelle celle (su una fattura
#      pre-fiscale sua, col template del suo emittente; se ha gia' il piano se
#      ne verificano i valori)
#      ✅ prova di mutazione (2026-08-02): togliendo `importo` dal context
#         passato al template — il difetto storico, chiave sbagliata -> '-' —
#         il caso 9 diventa ROSSO e gli altri restano verdi.
# ------------------------------------------------------------

import re

from django.db import connection, transaction

from apps.config.sorgenti import SORGENTE_FATTURA
from apps.documenti.services.document_generation_service import DocumentGenerationService
from apps.documenti.services.render_service import _render_html_with_jinja, render_pdf
from apps.vendite.services.fattura_document_context_builder import (
    FatturaDocumentContextBuilder,
)
from scripts.tests._smoke_contesto import apri_contesto_smoke

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Estrae le celle della tabella righe dal documento renderizzato,
#        ripulite dal markup: `(righe di primo livello, righe dei componenti)`,
#        una lista di celle per riga.
# ⚠️ Dalla forma dei dati 3 (2026-10-02) un kit e' UNA riga del context coi
#    componenti DENTRO (`r.componenti`), e il template li stampa come righe
#    `row-componente` sotto il padre. Fino al 2026-10-18 lo smoke le contava
#    insieme: dal primo kit il confronto per posizione era sfasato, e i casi 4,
#    5 e 8 accusavano celle di un'altra riga.
def celle_per_riga(html):
    blocco = re.search(r"Righe fattura.*?</table>", html, re.S)
    if not blocco:
        return [], []
    primo, componenti = [], []
    for attr, tr in re.findall(r"<tr([^>]*)>(.*?)</tr>", blocco.group(0), re.S):
        celle = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        ]
        if not celle:
            continue  # l'intestazione ha solo <th>
        (componenti if "row-componente" in attr else primo).append(celle)
    return primo, componenti


# Scopo: Mappa campo di contratto -> indice di colonna, leggendo i <th> della
#        tabella righe RENDERIZZATA (non un elenco fisso: se il template
#        riordina le colonne la mappa segue). Serve al caso 5 per accusare la
#        cella GIUSTA: un '-' e' un difetto solo nella colonna di un campo che
#        il context valorizza — su un campo None (es. sconto NULL dei KIT
#        padre, prezzo composto) il trattino e' il comportamento corretto.
#        Lezione del 2026-08-01: il vecchio check segnalava QUALUNQUE '-' in
#        una riga con QUALCHE campo valorizzato, e il primo giro reale dalla
#        corsia pull-commesse (righe kit con sconto NULL) lo ha fatto scattare
#        a vuoto — mascherato fin li' da fixture con tutti i campi pieni.
def colonne_contratto(html, campi_header):
    blocco = re.search(r"Righe fattura.*?</tr>", html, re.S)
    if not blocco:
        return {}
    header = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip().lower()
        for h in re.findall(r"<th[^>]*>(.*?)</th>", blocco.group(0), re.S)
    ]
    mappa = {}
    for campo, etichetta in campi_header.items():
        for j, testo in enumerate(header):
            if etichetta in testo:
                mappa[campo] = j
                break
    return mappa


print("\n=== SMOKE render stampa fattura (contratto context <-> template) ===\n")

with connection.cursor() as cur:
    # `vendite.fatture` e' RLS: senza contesto operatore il context builder
    # solleverebbe E_NOT_FOUND su una fattura che esiste.
    apri_contesto_smoke(cur)
    # Casi 1-8 (sola lettura): la fattura reale piu' ricca, preferendo una con
    # un KIT, che il template stampa su due livelli (padre + componenti). Lo
    # stato non conta: non si scrive niente.
    cur.execute(
        """
        SELECT r.fattura_id, count(*)
          FROM vendite.fatture_righe r
         GROUP BY r.fattura_id
         ORDER BY bool_or(r.kit_key IS NOT NULL) DESC, count(*) DESC, r.fattura_id DESC
         LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("SENZA_MATERIA: nessuna fattura con righe.")
    fattura_id, n_righe = row
    # Caso 9 (genera il piano rate e annulla): una fattura PRE-FISCALE (DRAFT o
    # EMESSA: oltre la soglia il generatore rifiuta, 573) con un totale
    # positivo (con base non positiva le rate sono zero per progetto, D-D),
    # preferendo una SENZA piano: e' quella su cui si prova che la sezione
    # nasce con la generazione. ⛔ Fino al 2026-10-18 il 9 usava la fattura dei
    # casi 1-8, «quella con piu' righe», e cadeva su una DEFINITIVA.
    cur.execute(
        """
        SELECT f.id
          FROM vendite.fatture f
          JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
         WHERE s.codice_interno IN ('DRAFT', 'EMESSA')
           AND f.totale_a_pagare > 0
           AND EXISTS (SELECT 1 FROM vendite.fatture_righe r WHERE r.fattura_id = f.id)
         ORDER BY EXISTS (SELECT 1 FROM vendite.fatture_scadenze fs WHERE fs.fattura_id = f.id),
                  f.id DESC
         LIMIT 1
        """
    )
    row = cur.fetchone()
    fattura_rate_id = row[0] if row else None
    cur.execute(
        "SELECT id FROM config.sorgenti WHERE codice_interno = %s AND attivo",
        [SORGENTE_FATTURA],
    )
    sorgente_fattura_id = cur.fetchone()[0]


# Scopo: il template di una fattura e la sua versione pubblicata, come li
#        sceglie il generatore: la risoluzione a due livelli (il predefinito
#        dell'EMITTENTE della fattura, se no lo standard) per la sorgente
#        FATTURA. Ritorna `(emittente_fiscale_id, template, versione)`;
#        versione None se manca.
# ⛔ Fino al 2026-10-18 lo smoke prendeva `WHERE codice = 'Fattura'` e una riga
#    qualsiasi, ma `template_documenti` e' per emittente: poteva collaudare il
#    template di un altro.
def template_della_fattura(fid):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT ef.id
              FROM vendite.fatture f
              JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
             WHERE f.id = %s
            """, [fid],
        )
        ef_id = cur.fetchone()[0]
    # La STESSA risoluzione della stampa, dal service (non ricopiata qui: due
    # passi, la funzione DB e la rilettura della riga). Con lo standard nel
    # seed, una mancata risoluzione non e' «materia assente» ma un difetto: il
    # service solleva ServiceError col codice del DB, e lo smoke si ferma rosso.
    # La versione e' quella che la risoluzione ha scelto (P-2), riletta per id
    # come la rilegge la stampa.
    svc = DocumentGenerationService()
    tpl, versione_id = svc._resolve_template(
        None, scope=None, emittente_fiscale_id=ef_id,
        sorgente_tipo_id=sorgente_fattura_id,
        tipo_documento_output_id=None, template_documento_id=None,
    )
    ver = svc._resolve_versione_pubblicata(tpl["id"], versione_id)
    return ef_id, tpl, ver


emittente_fiscale_id, template, versione = template_della_fattura(fattura_id)
print(f"fattura {fattura_id} ({n_righe} righe), template {template['codice']!r} "
      f"(id {template['id']}, emittente {emittente_fiscale_id})\n")

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
except Exception as exc:  # lo smoke deve riportare, non propagare
    reso = False
    html = ""
    check("3) il render Jinja non solleva", False, f"{type(exc).__name__}: {exc}")
if reso:
    check("3) il render Jinja non solleva", True)

celle, celle_componenti = celle_per_riga(html)

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

# 4b) i componenti dei kit: tante righe `row-componente` quanti i componenti
#     del context, ognuna con la quantita' del suo componente, nell'ordine.
componenti_ctx = [c for r in righe_ctx for c in (r.get("componenti") or [])]
diversi = [
    f"componente {k + 1}: quantita={c.get('quantita')} non nella riga"
    for k, c in enumerate(componenti_ctx)
    if k < len(celle_componenti) and c.get("quantita") is not None
    and str(c.get("quantita")) not in " | ".join(celle_componenti[k])
]
check("4b) i componenti dei kit compaiono sotto il loro padre",
      not diversi and len(celle_componenti) == len(componenti_ctx),
      "; ".join(diversi[:3]) if diversi
      else f"{len(celle_componenti)} componenti resi su {len(componenti_ctx)} nel context")

# 5) nessun trattino NELLA COLONNA di un campo che il context valorizza. E' il
#    sintomo esatto del difetto d'origine: chiave sbagliata -> `.get()` torna
#    None -> "-". Il confronto e' posizionale (mappa campo->colonna dai <th>):
#    un '-' su un campo None nel context e' comportamento corretto, non difetto.
_CAMPO_HEADER = {
    "quantita": "q.ta",
    "prezzo_unitario": "prezzo",
    "sconto_percentuale": "sconto",
    "importo_riga": "importo",
}
col_di = colonne_contratto(html, _CAMPO_HEADER)
trattini = []
if len(col_di) != len(_CAMPO_HEADER):
    # Mappa incompleta = il template ha cambiato le etichette: il presidio
    # non deve degradare in silenzio a "non controllo niente".
    trattini.append(
        f"mappa campo->colonna incompleta: trovate {sorted(col_di)} "
        f"su {sorted(_CAMPO_HEADER)} — header del template cambiati?"
    )
elif len(set(col_di.values())) != len(col_di):
    # Mappa ambigua = due campi risolti sulla STESSA colonna (il match e' per
    # sottostringa sul primo <th> che contiene l'etichetta): il presidio
    # guarderebbe la cella sbagliata restando verde. Fail-loud anche qui.
    trattini.append(
        f"mappa campo->colonna ambigua: {col_di} — due etichette di "
        "_CAMPO_HEADER matchano lo stesso <th>?"
    )
for i, riga in enumerate(righe_ctx):
    if i >= len(celle):
        continue
    for campo, j in col_di.items():
        if riga.get(campo) is not None and j < len(celle[i]) and celle[i][j] == "-":
            trattini.append(
                f"riga {i + 1}: colonna '{campo}' (cella {j}) a trattino "
                f"ma il context vale {riga.get(campo)!r}"
            )
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
    # Il risolutore degli asset del generatore vero (`asset:` del template,
    # nel perimetro dell'emittente del template, solo validi oggi): un logo
    # mancante deve far fallire anche qui.
    pdf = render_pdf(
        template_versione=versione, context=ctx,
        risolvi_asset=DocumentGenerationService()._risolutore_asset(
            emittente_fiscale_id, solo_validi=True,
        ),
    )
    check("7) il PDF si genera e non e' un guscio vuoto",
          pdf.startswith(b"%PDF") and len(pdf) > 5000, f"{len(pdf)} byte")
except Exception as exc:
    check("7) il PDF si genera e non e' un guscio vuoto", False,
          f"{type(exc).__name__}: {exc}")

# 8) AUTO-VERIFICA. Un presidio che non puo' fallire non presidia nulla: il
#    difetto d'origine e' sopravvissuto proprio a controlli sempre verdi. Si
#    rende lo stesso template con un context MUTATO — la chiave di contratto
#    rinominata, esattamente il difetto storico — e si pretende che il
#    rilevatore POSIZIONALE del caso 5 lo intercetti: il documento mutato
#    mostra '-' nella colonna Importo la' dove il contratto VERO (righe_ctx
#    originali) ha un valore. Il confronto e' contro le righe originali per
#    costruzione: un `any('-')` generico sarebbe diventato banalmente vero
#    (i kit padre hanno lo sconto legittimamente a trattino) e il presidio
#    sarebbe morto restando verde.
ctx_rotto = {**ctx, "righe": [
    {k: v for k, v in r.items() if k != "importo_riga"} for r in righe_ctx
]}
try:
    html_rotto = _render_html_with_jinja(versione["html_template"], ctx_rotto)
    celle_rotte, _ = celle_per_riga(html_rotto)
    j_importo = col_di.get("importo_riga")
    intercettato = j_importo is not None and any(
        riga.get("importo_riga") is not None
        and i < len(celle_rotte)
        and j_importo < len(celle_rotte[i])
        and celle_rotte[i][j_importo] == "-"
        for i, riga in enumerate(righe_ctx)
    )
except Exception:  # anche sollevare va bene: il difetto emerge
    intercettato = True
check("8) auto-verifica: il presidio del caso 5 e' vivo", intercettato,
      "rimuovendo `importo_riga` dal context il documento deve mostrare '-' "
      "nella colonna Importo dove il contratto vero ha un valore")

# 9) IL PIANO RATE SUL DOCUMENTO (piano BE/FE satelliti §3.2 asserzione 7).
#    Il template ha la sezione `{% if scadenze %}` «Scadenze pagamento», e legge
#    ogni campo con `.get()` — cioe' la stessa porta da cui sono entrati i due
#    difetti storici: chiave sbagliata -> trattino stampato, PDF valido, coda
#    FATTO, nessuno se ne accorge.
#
#    ⚠️ Questo e' l'UNICO caso che SCRIVE: le rate si generano qui, si rende, e
#    la transazione fa ROLLBACK — fuori di qui nulla e' cambiato. Si collauda
#    sulla fattura `fattura_rate_id` (pre-fiscale, totale positivo, scelta
#    sopra) col template del SUO emittente.
#
#    Il controllo e' integrato e non aggiunto: su una fattura SENZA piano la
#    sezione PRIMA non esiste (`{% if scadenze %}` e' falso), DOPO la
#    generazione deve esistere e portare i valori. Un'asserzione di sola
#    presenza sarebbe passata anche su un template che stampa quattro trattini.
#    Se tutte le fatture pre-fiscali hanno gia' un piano (fino al 2026-08-02
#    non ne aveva nessuna: oggi il generatore gira nel giro di fatturazione),
#    non si rigenera: si verificano i valori del piano che c'e'.
print()
if fattura_rate_id is None:
    check("9) il documento stampa il piano rate", False,
          "SENZA_MATERIA: nessuna fattura DRAFT o EMESSA con righe e totale positivo")
else:
    _ef_rate, _tpl_rate, versione_rate = template_della_fattura(fattura_rate_id)
    if versione_rate is None:
        check("9) il documento stampa il piano rate", False,
              f"l'emittente della fattura {fattura_rate_id} non ha un template "
              "di default pubblicato")
    else:
        ctx_prima = FatturaDocumentContextBuilder().build_context(fattura_rate_id)
        ha_piano_prima = bool(ctx_prima.get("scadenze"))
        sezione_prima = re.search(
            r"Scadenze pagamento.*?</table>",
            _render_html_with_jinja(versione_rate["html_template"], ctx_prima), re.S,
        )
        with transaction.atomic():
            if not ha_piano_prima:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT termine_pagamento_id FROM vendite.fatture WHERE id = %s",
                        [fattura_rate_id],
                    )
                    h_term = cur.fetchone()[0]
                    # Fixture di RENDERING, non di dominio: se la testata non
                    # porta il termine (fatture anteriori alla catena 3b) se ne
                    # mette uno di catalogo. Qui si collauda il TEMPLATE — che la
                    # risoluzione del termine sia corretta lo presidia
                    # `smoke-fattura-scadenze.py`.
                    if h_term is None:
                        cur.execute(
                            "SELECT id FROM config.termini_pagamento"
                            " WHERE attivo AND numero_rate > 1"
                            " ORDER BY numero_rate DESC, id LIMIT 1"
                        )
                        t_row = cur.fetchone()
                        if t_row:
                            cur.execute(
                                "UPDATE vendite.fatture SET termine_pagamento_id = %s"
                                " WHERE id = %s", [t_row[0], fattura_rate_id],
                            )
                    # Anche la MODALITA': il generatore copia
                    # `meta.modalita_codice` dalla testata, e su una testata NULL
                    # la colonna «Modalita» stampa un trattino LEGITTIMO, che
                    # renderebbe il caso cieco proprio sulla colonna piu' esposta
                    # al difetto storico.
                    cur.execute(
                        "UPDATE vendite.fatture SET modalita_pagamento_id = COALESCE("
                        "  modalita_pagamento_id,"
                        "  (SELECT id FROM config.modalita_pagamento ORDER BY id LIMIT 1))"
                        " WHERE id = %s", [fattura_rate_id],
                    )
                    cur.execute("SELECT * FROM vendite.fn_genera_scadenze_fattura(%s)",
                                [fattura_rate_id])
                    cur.fetchone()

            ctx_scad = FatturaDocumentContextBuilder().build_context(fattura_rate_id)
            scadenze_ctx = ctx_scad.get("scadenze") or []
            html_scad = _render_html_with_jinja(versione_rate["html_template"], ctx_scad)
            sezione = re.search(r"Scadenze pagamento.*?</table>", html_scad, re.S)

            assenti = []
            if sezione:
                testo = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sezione.group(0)))
                # Tutte e quattro le colonne della sezione, `modalita_codice`
                # inclusa.
                for s in scadenze_ctx:
                    for campo in ("nr", "data", "importo", "modalita_codice"):
                        valore = s.get(campo)
                        if valore is not None and str(valore) not in testo:
                            assenti.append(f"rata {s.get('nr')}: {campo}={valore}")
                mancanti_mod = [s.get("nr") for s in scadenze_ctx
                                if not s.get("modalita_codice")]
                if mancanti_mod and not ha_piano_prima:
                    assenti.append(
                        f"modalita_codice assente nel context per le rate {mancanti_mod}: "
                        "il generatore non l'ha copiata dalla testata"
                    )
            check("9) il documento stampa il piano rate",
                  (ha_piano_prima or sezione_prima is None) and sezione is not None
                  and len(scadenze_ctx) > 0 and not assenti,
                  f"fattura {fattura_rate_id}: {len(scadenze_ctx)} rate nel context, sezione "
                  f"{'assente' if not sezione else 'presente'} "
                  + ("(piano gia' presente: valori verificati, niente rigenerato) "
                     if ha_piano_prima else
                     f"(prima della generazione: {'assente' if not sezione_prima else 'PRESENTE'}) ")
                  + (f"— valori non stampati: {'; '.join(assenti[:3])}" if assenti else ""))
            if sezione:
                print("\n--- sezione «Scadenze pagamento» resa ---")
                for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", sezione.group(0), re.S)[1:]:
                    celle_s = [
                        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                        for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                    ]
                    if celle_s:
                        print("   ", " | ".join(celle_s))

            transaction.set_rollback(True)
        print("\n    (rollback: nessuna rata persistita)")

print("\n--- righe rese ---")
for c in celle:
    print("   ", " | ".join(c))
for c in celle_componenti:
    print("    (componente)", " | ".join(c))

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
