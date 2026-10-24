# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke F5 — la capability «riporta in lavorazione» sulla riga fattura
#        del lotto, provata sul database vero.
# Eseguito via `./manage-env.sh shell < scripts/tests/smoke-lotto-capability-reset-fattura.py`
#
# ⭐ PERCHE' UNO SMOKE E NON UN TEST DJANGO. I test di `apps/vendite/tests`
# mockano il repository: provano la catena Python e NON che il `LATERAL` su
# `script.fn_check_fattura_eliminabile_da_lotto` esista, leghi i parametri e
# ritorni le chiavi attese. Un nome di colonna sbagliato o un `jsonb` letto
# male passerebbe verde di la' e svuoterebbe il motivo a video.
#
# ⚠️ SERVE IL CONTESTO OPERATORE. `vendite.fatture` ha la RLS: senza i cinque
# GUC la lista torna ZERO righe e lo smoke sarebbe verde per sottrazione —
# «nessuna riga sbagliata» perche' nessuna riga. Il contesto si imposta qui, e
# il test 1 si rifiuta di proseguire se non ha materia.
#
# Rollback-safe: tutto dentro `transaction.atomic()` + `set_rollback(True)`.
# Nessuna scrittura comunque: la lista e' in sola lettura.
#
# Indice test (1..5):
#   1. Fixture: contesto operatore + un lotto CONGELATO e uno PRE-FISCALE
#   2. Oltre soglia: can_reset = False, con motivo macchina e chiave i18n
#   3. La chiave i18n e' quella del DB, non una inventata dal backend
#   4. Sotto soglia: can_reset = True e motivo assente
#   5. ⭐ L'invariante: il flag DERIVA dal motivo su OGNI riga letta
# ------------------------------------------------------------
from django.db import connection, transaction

from apps.vendite.db.vendite_repository import VenditeRepository

FAIL: list[str] = []


# Scopo: registra l'esito di un caso, con la frase che si legge a colpo d'occhio.
def check(nome: str, ok: bool, dettaglio: str = "") -> None:
    print(f"  [{'OK ' if ok else 'KO '}] {nome}{(' — ' + dettaglio) if dettaglio else ''}")
    if not ok:
        FAIL.append(nome)


# Scopo: righe della lista fatture di un lotto, ordinate per id come le
#        legge il test (`fattura_id`, la chiave della whitelist). I nomi sono quelli del contratto di lista
#        (`order_by`/`order_dir`, rinominati da `sort_by`/`sort_dir` il
#        2026-10-21, brief-be-verifica-documentazione-api).
def righe_lotto(lotto_id: int, limit: int = 20):
    rows, _ = VenditeRepository().list_lotto_fatture(
        lotto_id=lotto_id,
        stato_esecuzione=None,
        order_by="fattura_id",
        order_dir="asc",
        limit=limit,
        offset=0,
    )
    return rows


with transaction.atomic():
    # ── 1. Fixture ────────────────────────────────────────────────────────
    print("\n=== 1. Fixture ===")
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.auth_user_id, i.soggetto_ruolo_id, u.username
              FROM anagrafiche.identita_digitali i
              JOIN auth_user u ON u.id = i.auth_user_id
             WHERE i.ruolo_applicativo = 'OPERATORE' AND i.attivo
             LIMIT 1
            """
        )
        ident = cur.fetchone()
        if not ident:
            raise SystemExit("SENZA_MATERIA: nessuna identita OPERATORE attiva.")
        for chiave, valore in (
            ("app.current_user_id", str(ident[1])),
            ("app.current_identita_id", str(ident[0])),
            ("app.ruolo_applicativo", "OPERATORE"),
            ("app.soggetto_ruolo_id", str(ident[2])),
            ("app.jwt_user", ident[3]),
        ):
            cur.execute("SELECT set_config(%s, %s, true)", [chiave, valore])
        check("contesto operatore impostato", True, f"identita {ident[0]}")

        # I due soggetti: uno oltre la soglia di congelamento e uno sotto.
        # ⚠️ La soglia si legge da `congela_fiscale`, non da una lista di stati
        #    scritta qui: sarebbe la copia che questo lavoro ha appena tolto.
        cur.execute(
            """
            SELECT fl.id
              FROM vendite.fatturazione_lotti fl
              JOIN config.stati_doc_fiscale sl ON sl.id = fl.stato_doc_fiscale_id
             WHERE sl.congela_fiscale
               AND EXISTS (SELECT 1 FROM vendite.fatturazione_lotti_fatture lf
                            WHERE lf.lotto_id = fl.id)
             LIMIT 1
            """
        )
        r = cur.fetchone()
        lotto_congelato = r[0] if r else None

        cur.execute(
            """
            SELECT fl.id
              FROM vendite.fatturazione_lotti fl
              JOIN config.stati_doc_fiscale sl ON sl.id = fl.stato_doc_fiscale_id
              JOIN vendite.fatturazione_lotti_fatture lf ON lf.lotto_id = fl.id
              JOIN vendite.fatture f ON f.id = lf.fattura_id
              JOIN config.stati_doc_fiscale sf ON sf.id = f.stato_doc_fiscale_id
             WHERE NOT sl.congela_fiscale AND NOT sf.congela_fiscale
             LIMIT 1
            """
        )
        r = cur.fetchone()
        lotto_aperto = r[0] if r else None

    if lotto_congelato is None or lotto_aperto is None:
        raise SystemExit(
            "SENZA_MATERIA: servono un lotto oltre soglia e uno sotto soglia, "
            f"trovati congelato={lotto_congelato} aperto={lotto_aperto}."
        )
    check("un lotto oltre soglia e uno sotto", True,
          f"congelato={lotto_congelato} aperto={lotto_aperto}")

    # ── 2-3. Oltre soglia: spenta, e col motivo ───────────────────────────
    print("\n=== 2-3. Oltre la soglia: azione spenta, e il motivo c'e' ===")
    rows_c = righe_lotto(lotto_congelato)
    if not rows_c:
        raise SystemExit("SENZA_MATERIA: il lotto congelato non espone righe (RLS?).")
    r0 = rows_c[0]
    check("can_reset_fattura = False", r0["can_reset_fattura"] is False,
          f"fattura {r0['fattura_id']}")
    check("il motivo macchina c'e'", bool(r0["can_reset_fattura_reason"]),
          str(r0["can_reset_fattura_reason"]))
    # ⛔ Il tooltip senza chiave e' un pulsante grigio che non spiega niente:
    #    indistinguibile da un bug. E' il caso che api.md §Capability esiste
    #    per evitare.
    check("la chiave i18n c'e'", bool(r0["can_reset_fattura_reason_key"]),
          str(r0["can_reset_fattura_reason_key"]))
    # ⭐ La chiave arriva dal DB e non la compone il backend: se un giorno il
    #    backend cominciasse a costruirla, questo confronto se ne accorge.
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT m.value ->> 'reason_key'
              FROM jsonb_array_elements(
                       script.fn_check_fattura_eliminabile_da_lotto(%s, %s)
                   ) WITH ORDINALITY AS m(value, ord)
             ORDER BY m.ord LIMIT 1
            """,
            [r0["lotto_id"], r0["fattura_id"]],
        )
        attesa = cur.fetchone()
    check("la chiave e' quella che il DB dichiara",
          bool(attesa) and attesa[0] == r0["can_reset_fattura_reason_key"],
          f"db={attesa[0] if attesa else None}")

    # ── 4. Sotto soglia: accesa ───────────────────────────────────────────
    print("\n=== 4. Sotto la soglia: azione ammessa ===")
    rows_a = righe_lotto(lotto_aperto)
    if not rows_a:
        raise SystemExit("SENZA_MATERIA: il lotto aperto non espone righe (RLS?).")
    # ⚠️ Il gemello positivo NON e' ornamentale: senza, un'implementazione che
    #    risponde sempre «no» passerebbe i test 2-3 e sarebbe sbagliata.
    ammesse = [r for r in rows_a if r["can_reset_fattura"] is True]
    check("almeno una riga ammessa", bool(ammesse),
          f"{len(ammesse)} su {len(rows_a)}")
    if ammesse:
        check("sull'ammessa il motivo e' assente",
              ammesse[0]["can_reset_fattura_reason"] is None)

    # ── 5. L'invariante ───────────────────────────────────────────────────
    print("\n=== 5. Il flag DERIVA dal motivo, su ogni riga ===")
    # ⛔ E' il caso che discrimina davvero: due sorgenti per la stessa risposta
    #    sono due risposte che prima o poi differiscono, e la divergenza
    #    sarebbe MUTA — un pulsante acceso su un gesto che il DB rifiuta.
    tutte = rows_c + rows_a
    incoerenti = [
        r for r in tutte
        if r["can_reset_fattura"] is not (r["can_reset_fattura_reason"] is None)
    ]
    check("flag == (motivo assente) su tutte le righe", not incoerenti,
          f"{len(tutte)} righe, {len(incoerenti)} incoerenti")

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
