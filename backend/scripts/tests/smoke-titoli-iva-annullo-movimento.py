# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke T3-b — l'annullo di una forzatura sul registro plafond IVA,
#        provato sul database vero: la vista che spegne il pulsante, la madre
#        che scrive il contro-movimento, e l'accumulatore che torna a posto.
#
# ⭐ IL CASO SI COSTRUISCE, NON SI CERCA. Al 2026-08-31
# `anagrafiche.soggetti_titoli_iva` e' VUOTA — nessuno ha ancora registrato un
# titolo. Uno smoke che cercasse il soggetto passerebbe a vuoto: verde per
# sottrazione, cioe' il difetto che questo cantiere insegue da giorni. Qui il
# titolo e i movimenti si fabbricano, e alla fine si annulla tutto.
#
# ⚠️ SERVE IL CONTESTO OPERATORE: `soggetti_titoli_iva` e la sua vista hanno la
# RLS. Senza i cinque GUC la lista torna zero righe e non si distingue «non c'e'
# niente di sbagliato» da «non vedo niente».
#
# Rollback-safe: `transaction.atomic()` + `set_rollback(True)`.
#
# Indice test (1..7):
#   1. Fixture: contesto operatore + titolo e forzatura costruiti
#   2. La vista risponde, e porta le colonne dell'annullo
#   3. Sulla forzatura viva l'annullo e' AMMESSO (motivo assente)
#   4. L'accumulatore ha sommato la forzatura
#   5. L'annullo scrive un CONTRO-MOVIMENTO, non un update
#   6. ⭐ L'accumulatore torna al valore di prima — da solo
#   7. ⛔ Il secondo annullo e' RIFIUTATO, e la vista lo diceva gia'
# ------------------------------------------------------------
from decimal import Decimal

from django.db import connection, transaction

from apps.anagrafiche.db.titoli_iva_repository import TitoliIvaRepository

FAIL: list[str] = []


# Scopo: registra l'esito di un caso, leggibile a colpo d'occhio.
def check(nome: str, ok: bool, dettaglio: str = "") -> None:
    print(f"  [{'OK ' if ok else 'KO '}] {nome}{(' — ' + dettaglio) if dettaglio else ''}")
    if not ok:
        FAIL.append(nome)


# Scopo: `imponibile_utilizzato` del titolo, cioe' cio' che l'accumulatore ha
#        scritto. E' il numero che l'annullo deve riportare indietro.
def usato(titolo_id: int) -> Decimal:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT imponibile_utilizzato FROM anagrafiche.soggetti_titoli_iva WHERE id = %s",
            [titolo_id],
        )
        return cur.fetchone()[0]


with transaction.atomic():
    repo = TitoliIvaRepository()

    # ── 1. Fixture ────────────────────────────────────────────────────────
    print("\n=== 1. Fixture: il caso si costruisce ===")
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

        # Gli ingredienti: un soggetto e un emittente nel perimetro
        # dell'operatore (o la RLS non farebbe vedere il titolo appena scritto),
        # il tipo di titolo con plafond e un codice IVA.
        # ⭐ Soggetto e tipo di titolo si scelgono INSIEME, con il predicato del
        #    guard (`anagrafiche.fn_titolo_iva_ammesso` sulla natura del
        #    soggetto, dal 2026-10-10): la dichiarazione d'intento la presenta un
        #    soggetto IVA, non un privato. Prima erano due `LIMIT 1` separati e
        #    senza ordine, e il giorno in cui il primo soggetto e' stato un
        #    privato lo smoke e' andato rosso nella fixture (2026-10-15).
        cur.execute(
            """
            SELECT s.id, ef.id, t.id
              FROM anagrafiche.emittenti_fiscali ef
              -- ⚠️ Il ponte lega il SOGGETTO-RUOLO dell'emittente, non la sua
              --    PK: e' la convenzione `_sr_ids` contro `_pk_ids`, e sbagliarla
              --    qui non da' zero righe per caso — da' un errore di colonna.
              JOIN anagrafiche.emittenti_fiscali_billing_account efba
                ON efba.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
              JOIN anagrafiche.billing_account ba ON ba.id = efba.billing_account_id
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
              JOIN config.tipi_titolo_iva t
                ON t.ha_plafond IS TRUE
               AND anagrafiche.fn_titolo_iva_ammesso(t.id, s.tipo_soggetto_dettaglio_id)
             WHERE ef.attivo
             ORDER BY t.id, ef.id, s.id
             LIMIT 1
            """
        )
        base = cur.fetchone()
        cur.execute("SELECT id FROM config.iva WHERE attivo LIMIT 1")
        iva = cur.fetchone()
        if not (base and iva):
            raise SystemExit(
                f"SENZA_MATERIA: soggetto/emittente/tipo con plafond ammesso={bool(base)} "
                f"iva={bool(iva)}."
            )

        cur.execute(
            """
            INSERT INTO anagrafiche.soggetti_titoli_iva
                   (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
                    ambito, valido_dal, valido_al, plafond, attivo)
            VALUES (%s, %s, %s, %s, 'TUTTO', DATE '2026-01-01', DATE '2026-12-31',
                    10000, TRUE)
            RETURNING id
            """,
            [base[0], base[1], base[2], iva[0]],
        )
        titolo_id = cur.fetchone()[0]
    check("titolo costruito", True, f"id={titolo_id}")

    forzatura_id = repo.create_forzatura(
        titolo_id, imponibile=Decimal("250.00"),
        data_movimento="2026-06-01", motivo="smoke: forzatura da annullare",
    )
    check("forzatura costruita", True, f"id={forzatura_id}")

    # ── 2-3. Il read-side ─────────────────────────────────────────────────
    print("\n=== 2-3. La vista: colonne dell'annullo e pulsante acceso ===")
    # ⚠️ `list_movimenti` ritorna `(righe, totale)` dal 2026-09-02 (paginazione
    #   su `fetch_paged_with_total`): iterare il metodo direttamente scorre la
    #   TUPLA, non le righe.
    movimenti, _ = repo.list_movimenti(titolo_id)
    righe = {int(r["id"]): r for r in movimenti}
    check("la vista risponde", forzatura_id in righe, f"{len(righe)} righe")
    r = righe[forzatura_id]
    for col in ("is_annullo", "is_annullato", "annullo_blocco_codice",
                "annullo_blocco_reason_key", "annulla_movimento_id"):
        check(f"colonna «{col}» esposta", col in r)
    # ⭐ Motivo assente = azione AMMESSA. E' il gemello positivo: senza, una
    #    vista che risponde sempre «bloccato» passerebbe il caso 7 e sarebbe
    #    sbagliata.
    check("annullo ammesso sulla forzatura viva",
          r["annullo_blocco_codice"] is None, str(r["annullo_blocco_codice"]))

    # ── 4. L'accumulatore ─────────────────────────────────────────────────
    print("\n=== 4. L'accumulatore ha sommato ===")
    dopo_forzatura = usato(titolo_id)
    check("imponibile_utilizzato = 250", dopo_forzatura == Decimal("250.00"),
          str(dopo_forzatura))

    # ── 5-6. L'annullo ────────────────────────────────────────────────────
    print("\n=== 5-6. L'annullo: contro-movimento, non update ===")
    annullo_id = repo.annulla_movimento(forzatura_id, motivo="smoke: era sbagliata")
    check("il contro-movimento e' una RIGA NUOVA", annullo_id != forzatura_id,
          f"annullo={annullo_id} forzatura={forzatura_id}")

    movimenti, _ = repo.list_movimenti(titolo_id)
    righe = {int(x["id"]): x for x in movimenti}
    check("la forzatura risulta annullata", righe[forzatura_id]["is_annullato"] is True)
    check("il contro-movimento si dichiara annullo", righe[annullo_id]["is_annullo"] is True)
    check("e punta alla riga che annulla",
          int(righe[annullo_id]["annulla_movimento_id"]) == forzatura_id)
    # ⛔ La riga originale c'e' ANCORA: e' il punto di Q7 — «deve rimanere
    #    traccia, no delete».
    check("l'originale non e' stata cancellata", forzatura_id in righe)

    # ⭐ IL CASO CHE VALE PIU' DI TUTTI: l'accumulatore non e' stato toccato da
    #    nessuno, fa `SUM` su tutto il registro, e il contro-movimento lo
    #    riporta da solo al valore di prima. E' la ragione per cui Q7 ha
    #    scartato il flag `annullato`.
    check("l'accumulatore e' tornato a zero DA SOLO",
          usato(titolo_id) == Decimal("0.00"), str(usato(titolo_id)))

    # ── 7. Il secondo annullo ─────────────────────────────────────────────
    print("\n=== 7. Il secondo annullo e' rifiutato, e la vista lo diceva ===")
    # ⭐ Prima la vista: il motivo c'e' gia' PRIMA del clic — e' tutto il senso
    #    di avere una check pura letta anche dal read-side.
    check("la vista blocca l'annullo della riga gia' annullata",
          righe[forzatura_id]["annullo_blocco_codice"] == "GIA_ANNULLATO",
          str(righe[forzatura_id]["annullo_blocco_codice"]))
    # ⚠️ `RIGA_DI_ANNULLO` e non piu' `E_UN_ANNULLO` (changeSet `20260831-35`):
    #    quel `reason` portava per caso il prefisso `E_`, e il cancello dei
    #    codici errore lo leggeva come un CODICE senza policy — rosso su un
    #    valore che non e' un codice. Il nome nuovo dice cosa E' la riga invece
    #    di ripetere l'avverbio, cosi' non si confonde col vicino
    #    `GIA_ANNULLATO`, che dice l'opposto (quella riga e' STATA annullata).
    # ⛔ Il `reason_key` NON e' cambiato: e' un indirizzo i18n, e il testo a
    #    video resta quello di prima.
    check("e blocca l'annullo di un annullo",
          righe[annullo_id]["annullo_blocco_codice"] == "RIGA_DI_ANNULLO",
          str(righe[annullo_id]["annullo_blocco_codice"]))
    # ⚠️ E il rifiuto vero deve arrivare: se la vista dicesse «bloccato» e la
    #    madre lasciasse passare, il tooltip sarebbe una decorazione.
    try:
        with transaction.atomic():
            repo.annulla_movimento(forzatura_id, motivo="smoke: secondo tentativo")
        check("la madre RIFIUTA il secondo annullo", False, "non ha sollevato")
    except Exception as exc:  # il rifiuto e' l'esito atteso
        check("la madre RIFIUTA il secondo annullo", True,
              type(exc).__name__)

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
