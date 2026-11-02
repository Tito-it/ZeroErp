# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — IL PRIMO CARICO DALL'INVENTARIO, sul percorso REALE dei service di
#         magazzino (Lotto 2, piano-be-fe-magazzino-lotto-2-motore §8): il
#         copione di collaudo (a)…(g), eseguito prima del video.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-magazzino-inventario-primo-carico.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE. E' la versione lanciabile a mano del test sul DB provvisto
# (`apps/magazzino/tests/db/test_documento_interno_db.py`): stesso mondo
# costruito, stessi passi, ma con l'esito stampato passo per passo — quello
# che serve quando qualcosa a video non torna e si vuole vedere dove.
#
# IDEMPOTENZA. Il mondo (azienda, operatore, magazzini, articoli) nasce dai BB
# `dbops.fn_pgtap_crea_*` e tutto sta in una transazione con
# `set_rollback(True)` finale: niente persiste. Rieseguibile all'infinito.
#
# Indice test (1..12):
#   1  bozza creata sul magazzino, piano vuoto
#   2  riga 10 pezzi a 7 €: il piano la dichiara INV_INIZIALE (anteprima in DRAFT)
#   3  CONFIRM: righe congelate (E_MAG_DOCUMENTO_RIGHE_CONGELATE)
#   4  registra: 1 movimento, POSTED, qta_sistema = 0
#   5  registro: INV_INIZIALE a 7 € con sorgente INVENTARIO_RIGA; disponibilita' a 10
#   6  riga su articolo NON gestito: piano NON_POSTABILE col motivo della check
#   7  registra rifiuta TUTTO (E_MAG_ARTICOLO_NON_GESTITO): stato ancora CONFIRM
#   8  CONFIRM -> DRAFT riapre; riga senza lotto su requires_lotto: passa, i motivi la dicono
#   9  rettifica -5: RETT_NEG alla media (7), disponibilita' a 5
#  10  POSTED non si elimina, non si modifica, non torna in bozza; POSTED non si CHIEDE
#  11  l'operatore di un altro emittente: 404 e lista vuota
#  12  lookup di riga: ubicazioni del magazzino, lotti dell'articolo
# ------------------------------------------------------------

from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.magazzino.services import consultazione_service as cs
from apps.magazzino.services import magazzino_service as ms

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: esegue un'azione che DEVE essere rifiutata, in un savepoint.
def rifiuto(fn) -> str | None:
    try:
        with transaction.atomic():
            fn()
    except ServiceError as e:
        return e.code
    return None


_MONDO = (
    "CREATE TEMP TABLE _mondo AS SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m",
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
    # I verbi di registrazione chiedono l'azione (`script.fn_guard_azione`):
    # la si concede all'operatore del mondo (brief-db-magazzino-verbi-con-permesso §6).
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino')",
    "CREATE TEMP TABLE _mag AS SELECT dbops.fn_pgtap_crea_magazzino('SMK-MAG-A', false) AS mag_a,"
    " dbops.fn_pgtap_crea_magazzino('SMK-MAG-U', true) AS mag_u",
    "CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('SMK-ART-1') AS art,"
    " dbops.fn_pgtap_crea_articolo('SMK-ART-NG', false) AS art_ng,"
    " dbops.fn_pgtap_crea_articolo('SMK-ART-L', true, true) AS art_l",
    "INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)"
    " SELECT mag_u, 'UX', (SELECT id FROM config.tipi_ubicazione WHERE codice_interno = 'TIPO_UBI_STORAGE') FROM _mag",
    "INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo) SELECT art_l, 'L-SMK', current_date FROM _art",
)

print("\n=== SMOKE magazzino — il primo carico dall'inventario (Lotto 2) ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        for passo in _MONDO:
            cur.execute(passo)
        cur.execute("SELECT mag_a, mag_u FROM _mag")
        mag_a, mag_u = (int(x) for x in cur.fetchone())
        cur.execute("SELECT art, art_ng, art_l FROM _art")
        art, art_ng, art_l = (str(x) for x in cur.fetchone())
        cur.execute("SELECT auth_user_id FROM _mondo")
        uid = int(cur.fetchone()[0])
    print(f"mondo: magazzini {mag_a} (senza ubicazioni), {mag_u} (a ubicazioni); operatore {uid}\n")

    # 1
    d = ms.crea_documento("inventari", {"magazzino_id": mag_a, "descrizione": "primo carico"})
    check("1) bozza creata, piano vuoto",
          d["stato"] == "DRAFT" and d["piano_riepilogo"]["n_righe"] == 0, f"id={d['id']}")
    # 2
    ms.crea_riga("inventari", d["id"], {"articolo_id": art, "qta_contata": "10", "costo_unitario": 7})
    piano = ms.list_piano("inventari", d["id"], limit=10)["results"]
    check("2) il piano in DRAFT dichiara INV_INIZIALE con delta 10",
          [p["esito"] for p in piano] == ["INV_INIZIALE"] and piano[0]["delta"] == Decimal("10"))
    # 3
    ms.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})
    check("3) in CONFIRM le righe sono congelate",
          rifiuto(lambda: ms.crea_riga("inventari", d["id"], {"articolo_id": art, "qta_contata": 1}))
          == "E_MAG_DOCUMENTO_RIGHE_CONGELATE")
    # 4
    esito = ms.registra_documento("inventari", d["id"])
    qta_sistema = ms.list_righe("inventari", d["id"], limit=10)["results"][0]["qta_sistema"]
    check("4) registra: 1 movimento, POSTED, qta_sistema = 0",
          esito["n_movimenti"] == 1 and esito["documento"]["stato"] == "POSTED" and qta_sistema == 0,
          f"movimenti={esito['movimenti']}")
    # 5
    mov = cs.list_movimenti(auth_user_id=uid, inventario_id=d["id"], limit=10)["results"]
    disp = cs.list_disponibilita(auth_user_id=uid, magazzino_id=mag_a, limit=10)["results"]
    check("5) registro INV_INIZIALE a 7 € da INVENTARIO_RIGA; disponibilita' 10",
          len(mov) == 1 and mov[0]["causale_codice"] == "INV_INIZIALE"
          and mov[0]["costo_unitario"] == Decimal("7") and mov[0]["sorgente_codice_interno"] == "INVENTARIO_RIGA"
          and disp and disp[0]["disponibile"] == Decimal("10"))
    # 6
    d3 = ms.crea_documento("inventari", {"magazzino_id": mag_a})
    ms.crea_riga("inventari", d3["id"], {"articolo_id": art_ng, "qta_contata": 3})
    ms.cambia_stato_documento("inventari", d3["id"], {"stato": "CONFIRM"})
    piano = ms.list_piano("inventari", d3["id"], limit=10)["results"]
    check("6) articolo non gestito: piano NON_POSTABILE col motivo",
          piano[0]["esito"] == "NON_POSTABILE"
          and piano[0]["posting_blocco_reason_key"] == "magazzino.riga.blocco.articolo_non_gestito")
    # 7
    codice = rifiuto(lambda: ms.registra_documento("inventari", d3["id"]))
    check("7) registra rifiuta tutto, stato ancora CONFIRM",
          codice == "E_MAG_ARTICOLO_NON_GESTITO"
          and ms.get_documento("inventari", d3["id"])["stato"] == "CONFIRM", codice or "")
    # 8
    ms.cambia_stato_documento("inventari", d3["id"], {"stato": "DRAFT"})
    ms.crea_riga("inventari", d3["id"], {"articolo_id": art_l, "qta_contata": 2})
    motivi = ms.motivi_riga(magazzino_id=mag_a, articolo_id=art_l, lotto_id=None, asset_id=None, ubicazione_id=None)["motivi"]
    check("8) CONFIRM -> DRAFT riapre; la riga senza lotto passa e i motivi la dicono",
          [m["reason_key"] for m in motivi] == ["magazzino.riga.blocco.lotto_obbligatorio"])
    # 9
    rt = ms.crea_documento("rettifiche", {"magazzino_id": mag_a})
    ms.crea_riga("rettifiche", rt["id"], {"articolo_id": art, "qta_delta": -5, "motivo": "ROTTURA"})
    ms.cambia_stato_documento("rettifiche", rt["id"], {"stato": "CONFIRM"})
    es = ms.registra_documento("rettifiche", rt["id"])
    mov = cs.list_movimenti(auth_user_id=uid, rettifica_id=rt["id"], limit=10)["results"]
    disp = cs.list_disponibilita(auth_user_id=uid, magazzino_id=mag_a, articolo_id=art, limit=10)["results"]
    check("9) rettifica -5: RETT_NEG alla media (7), disponibilita' 5",
          es["n_movimenti"] == 1 and mov[0]["causale_codice"] == "RETT_NEG"
          and mov[0]["costo_unitario"] == Decimal("7") and disp[0]["disponibile"] == Decimal("5"))
    # 10
    riga = ms.list_righe("inventari", d["id"], limit=10)["results"][0]
    check("10) POSTED: non si elimina, non si modifica, non torna in bozza, non si chiede",
          rifiuto(lambda: ms.elimina_documento("inventari", d["id"])) == "E_MAG_DOCUMENTO_NON_ELIMINABILE"
          and rifiuto(lambda: ms.aggiorna_riga("inventari", d["id"], riga["id"], {"qta_contata": 1})) == "E_MAG_DOCUMENTO_RIGHE_CONGELATE"
          and rifiuto(lambda: ms.cambia_stato_documento("inventari", d["id"], {"stato": "DRAFT"})) == "E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA"
          and rifiuto(lambda: ms.cambia_stato_documento("inventari", d["id"], {"stato": "POSTED"})) == "E_MAGAZZINO_VALIDATION")
    # 11
    with connection.cursor() as cur:
        cur.execute("CREATE TEMP TABLE _mondo2 AS SELECT x.* FROM dbops.fn_pgtap_crea_emittente_operatore('B2') x")
        cur.execute("SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo2))")
        cur.execute("SELECT auth_user_id FROM _mondo2")
        uid2 = int(cur.fetchone()[0])
    check("11) l'altro emittente: 404 e lista vuota",
          rifiuto(lambda: ms.get_documento("inventari", d["id"])) == "E_MAG_DOCUMENTO_NON_TROVATO"
          and ms.list_documenti("inventari", auth_user_id=uid2, limit=10)["count"] == 0)
    # 12 (di nuovo nel primo contesto)
    with connection.cursor() as cur:
        cur.execute("SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))")
    check("12) lookup: ubicazioni del magazzino U, lotti dell'articolo per lotti",
          [u["codice"] for u in ms.lookup_ubicazioni(mag_u)["results"]] == ["UX"]
          and [x["codice"] for x in ms.lookup_lotti(articolo_id=art_l, search=None)["results"]] == ["L-SMK"])

    transaction.set_rollback(True)

# ⚠️ La frase d'esito e' un CONTRATTO con `scripts/smoke-baseline.sh`, che
#    classifica dall'output: riconosce `=== ESITO: TUTTO VERDE ===` e
#    `ESITO: FALLITO`, e tutto il resto lo legge come SENZA_MATERIA — cioe'
#    «si e' fermato prima di asserire», copertura zero. Un «Tutto verde.»
#    minuscolo passava come nessuna materia (trovato il 2026-09-18 alla prima
#    corsa del runner su questo file).
print(f"\n=== ESITO: {'FALLITO — ' + '; '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
if FAIL:
    raise SystemExit(1)
print("Niente e' stato scritto (rollback).")
