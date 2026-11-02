# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke F3-b2 — il task `consuma_plafond_lotto`: il plafond di un titolo
#        IVA si consuma davvero, e la riga che copre solo in parte SI SPEZZA.
# Eseguito via `./manage-env.sh shell < scripts/tests/smoke-consuma-plafond-lotto.py`
#
# ⭐ PERCHE' ESISTE, E PERCHE' SOLO ADESSO. I test di
# `test_plafond_fattura_service` mockano repository e risolutore: provano la
# REGOLA (l'ordine, l'autorita' del lock, la quantita' derivata) e NON che il
# giro esista, che il seed lo invochi, che i vincoli del DB lo lascino
# scrivere. Fino al seed della pipeline il task non era invocabile da niente, e
# uno smoke avrebbe provato solo il servizio chiamato a mano — cioe' quello che
# i test gia' fanno. Ora la configurazione c'e'.
#
# ⭐ IL CASO SI COSTRUISCE, NON SI CERCA, e stavolta per DUE ragioni:
#   1. `anagrafiche.soggetti_titoli_iva` e' VUOTA — nessun titolo esiste;
#   2. le fatture con righe sono quasi tutte gia' CONGELATE (`DEFINITIVA`), e
#      il guard di congelamento rifiuterebbe la spezzatura.
#      ⛔ E NON SI PUO' SCONGELARLE: la macchina a stati rifiuta la transizione
#      `DEFINITIVA -> EMESSA` (`E_LOTTO_PARAMETRO_NON_COERENTE`), ed e' giusto
#      che la rifiuti — il modello non torna indietro da li'. Il caso si
#      costruisce quindi su una fattura che e' GIA' `EMESSA`, che e' anche il
#      momento vero in cui il task gira (prima di `numera_fatture`), e la riga
#      da spezzare si crea se non c'e'.
#
# ⚠️ SERVE IL CONTESTO OPERATORE: `fatture` e `soggetti_titoli_iva` hanno la
# RLS. Senza i cinque GUC il giro non vede niente e lo smoke sarebbe verde per
# sottrazione.
#
# Rollback-safe: `transaction.atomic()` + `set_rollback(True)`.
#
# Indice test (1..11):
#   1. ⭐ IL CABLAGGIO: il seed nomina il task e il codice sa eseguirlo
#   2. ⛔ e il task NON dichiara una `fn`: l'implementazione e' Python
#   3. ⚠️ e sta PRIMA di `numera_fatture`, su ENTRAMBE le pipeline
#   4. Fixture: fattura EMESSA + riga + titolo con capienza PARZIALE
#   5. ⚠️ IL GEMELLO, e sta prima: senza titolo il giro non tocca niente
#   6. Il titolo con capienza PARZIALE
#   7. Il giro risponde e conta cio' che ha fatto
#   8. ⭐ La riga si e' SPEZZATA, e le due parti sommano ESATTAMENTE
#   9. La parte punta alla capofila, e resta sulla stessa fattura
#  10. ⭐ Il movimento c'e', e l'accumulatore l'ha visto
#  11. ⭐ La vista le mostra come DUE RIGHE SORELLE (`PARTE_PLAFOND`)
# ------------------------------------------------------------
from decimal import Decimal

from django.db import connection, transaction

from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.pipeline_step_executor import PipelineStepExecutor
from apps.vendite.services.plafond_fattura_service import PlafondFatturaService

FAIL: list[str] = []
TASK = "consuma_plafond_lotto"


# Scopo: registra l'esito di un caso, leggibile a colpo d'occhio.
def check(nome: str, ok: bool, dettaglio: str = "") -> None:
    print(f"  [{'OK ' if ok else 'KO '}] {nome}{(' — ' + dettaglio) if dettaglio else ''}")
    if not ok:
        FAIL.append(nome)


def q(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


with transaction.atomic():
    repo = VenditePipelineRepository()

    # ── 1-3. Il cablaggio ─────────────────────────────────────────────────
    print("\n=== 1-3. Il cablaggio: seed e codice si conoscono ===")
    righe_cfg = q(
        """
        SELECT fp.id,
               jsonb_agg(x.t ->> 'task' ORDER BY x.ord),
               bool_or((x.t -> 'params' ->> 'fn') IS NOT NULL)
          FROM vendite.fatturazione_pipeline fp,
               LATERAL jsonb_array_elements(fp.processi) WITH ORDINALITY AS x(t, ord)
         WHERE fp.stato_doc_fiscale_id = 8 AND fp.attivo
         GROUP BY fp.id
        """
    )
    check("lo step DEFINITIVA e' configurato", bool(righe_cfg), f"{len(righe_cfg)} pipeline")
    for pid, tasks, ha_fn in righe_cfg:
        check(f"pipeline {pid}: il task c'e'", TASK in tasks, str(tasks))
        # ⛔ Senza `fn` l'implementazione e' PYTHON. Una `fn` dichiarata qui
        #    farebbe cercare una madre SQL che non esiste — ed e' il difetto
        #    che su questa stessa pipeline e' gia' costato un giro
        #    (`fn_generate_fatture_righe`, ritirata il 2026-07-28).
        check(f"pipeline {pid}: nessuna `fn` dichiarata", not ha_fn)
        # ⚠️ PRIMA di `numera_fatture`: dopo, la fattura e' oltre la soglia di
        #    congelamento e la spezzatura verrebbe RIFIUTATA.
        if TASK in tasks and "numera_fatture" in tasks:
            check(f"pipeline {pid}: sta prima di numera_fatture",
                  tasks.index(TASK) < tasks.index("numera_fatture"),
                  str(tasks))
    # ⭐ E il codice sa eseguirlo: il seed e il registry sono le due meta' che
    #    possono divergere, e un task configurato senza gestore fallirebbe a
    #    giro avviato invece che qui.
    check("il backend ha il gestore",
          f"{TASK}_default" in PipelineStepExecutor().handler_registry)
    check("ed e' dichiarato come task PYTHON",
          repo.ALLOWED_TASK_FUNCTIONS.get(TASK, "assente") is None)

    # ── 4. Fixture ────────────────────────────────────────────────────────
    print("\n=== 4. Fixture: il caso si costruisce ===")
    ident = q(
        """
        SELECT i.id, i.auth_user_id, i.soggetto_ruolo_id, u.username
          FROM anagrafiche.identita_digitali i
          JOIN auth_user u ON u.id = i.auth_user_id
         WHERE i.ruolo_applicativo = 'OPERATORE' AND i.attivo LIMIT 1
        """
    )
    if not ident:
        raise SystemExit("SENZA_MATERIA: nessuna identita OPERATORE attiva.")
    d = ident[0]
    for k, v in (
        ("app.current_user_id", str(d[1])), ("app.current_identita_id", str(d[0])),
        ("app.ruolo_applicativo", "OPERATORE"), ("app.soggetto_ruolo_id", str(d[2])),
        ("app.jwt_user", d[3]),
    ):
        q("SELECT set_config(%s, %s, true)", [k, v])

    # ⭐ UNA FATTURA GIA' NON CONGELATA, e sola nel suo lotto. Il primo giro di
    #    questo smoke provava a SCONGELARNE una: la macchina a stati rifiuta la
    #    transizione `DEFINITIVA → EMESSA` (`E_LOTTO_PARAMETRO_NON_COERENTE`), ed
    #    e' giusto che la rifiuti — il modello non torna indietro da li'. Il caso
    #    si costruisce dove lo stato lo consente gia'.
    # ⚠️ La 2263 e' esclusa per nome: e' la fattura che non va numerata, e
    #    benche' qui non si numeri e si annulli tutto, non la si tocca.
    scelto = q(
        """
        SELECT lf.lotto_id, f.id, f.billing_account_id
          FROM vendite.fatturazione_lotti_fatture lf
          JOIN vendite.fatture f ON f.id = lf.fattura_id
          JOIN config.stati_doc_fiscale sf ON sf.id = f.stato_doc_fiscale_id
         WHERE NOT sf.congela_fiscale
           AND f.id <> 2263
           AND (SELECT count(*) FROM vendite.fatturazione_lotti_fatture x
                 WHERE x.lotto_id = lf.lotto_id) = 1
         ORDER BY f.id LIMIT 1
        """
    )
    if not scelto:
        raise SystemExit(
            "SENZA_MATERIA: nessuna fattura NON congelata sola nel suo lotto."
        )
    lotto_id, fattura_id, ba_id = scelto[0]
    check("fattura non congelata", True, f"lotto={lotto_id} fattura={fattura_id}")

    # ⚠️ Se non ha righe utili se ne costruisce UNA: senza, non c'e' niente da
    #    spezzare e lo smoke passerebbe a vuoto. `imponibile_riga` NON si
    #    scrive — lo calcola il DB da qta x prezzo, ed e' proprio la formula che
    #    il servizio inverte per derivare la quantita' della parte.
    esistenti = q(
        """
        SELECT count(*) FROM vendite.fatture_righe
         WHERE fattura_id = %s AND riga_capofila_id IS NULL
           AND articolo_id IS NOT NULL AND imponibile_riga > 0
        """,
        [fattura_id],
    )[0][0]
    if not esistenti:
        art = q(
            "SELECT a.id, a.uom_id FROM catalogo.articoli a "
            "WHERE a.attivo AND a.uom_id IS NOT NULL LIMIT 1"
        )
        iva_base = q("SELECT id FROM config.iva WHERE attivo ORDER BY id LIMIT 1")
        if not (art and iva_base):
            raise SystemExit("SENZA_MATERIA: nessun articolo attivo con uom, o nessuna IVA.")
        nr = repo.get_next_fattura_riga_nr(fattura_id)
        q(
            """
            INSERT INTO vendite.fatture_righe
                   (fattura_id, riga_nr, articolo_id, descrizione, uom_id, qta,
                    prezzo_unitario, iva_id, dest_billing_account_id)
            VALUES (%s, %s, %s, 'smoke plafond', %s, 10, 10.00, %s, %s)
            """,
            [fattura_id, nr, art[0][0], art[0][1], iva_base[0][0], ba_id],
        )
        check("riga costruita", True, f"riga_nr={nr}")

    riga = q(
        """
        SELECT id, qta, imponibile_riga, iva_id
          FROM vendite.fatture_righe
         WHERE fattura_id = %s AND riga_capofila_id IS NULL
           AND articolo_id IS NOT NULL AND imponibile_riga > 0
         ORDER BY imponibile_riga DESC LIMIT 1
        """,
        [fattura_id],
    )[0]
    riga_id, qta0, imponibile0, iva0 = riga
    check("riga bersaglio", True, f"id={riga_id} qta={qta0} imponibile={imponibile0}")

    # ── 5. Il gemello, e sta QUI di proposito ─────────────────────────────
    print("\n=== 5. Il gemello: senza titolo il giro non tocca niente ===")
    # ⚠️ Senza questo caso un giro che spezzasse SEMPRE passerebbe tutto il
    #    resto. Sta PRIMA della costruzione del titolo, e non dopo averlo
    #    spento: a titolo consumato `trgfn_prevent_deactivate_if_children`
    #    rifiuta la disattivazione — figli prima del padre — e il gemello
    #    sarebbe morto contro un guard invece di provare qualcosa.
    prima_righe = q(
        "SELECT count(*) FROM vendite.fatture_righe WHERE fattura_id = %s",
        [fattura_id],
    )[0][0]
    esito0 = PlafondFatturaService(repo).consuma_lotto(lotto_id)
    dopo_righe = q(
        "SELECT count(*) FROM vendite.fatture_righe WHERE fattura_id = %s",
        [fattura_id],
    )[0][0]
    check("senza titolo: nessuna riga nuova", prima_righe == dopo_righe,
          f"{prima_righe} vs {dopo_righe}")
    check("senza titolo: nessuna spezzatura, nessun movimento",
          esito0["righe_spezzate"] == 0 and esito0["movimenti"] == 0, str(esito0))

    # ── 6. Il titolo con capienza parziale ────────────────────────────────
    print("\n=== 6. Il titolo: capienza PARZIALE ===")
    # ⭐ CAPIENZA PARZIALE: meta' dell'imponibile della riga. E' l'unico modo di
    #    provare la SPEZZATURA — con capienza piena la riga resta una sola e il
    #    caso non discriminerebbe.
    ctx = repo.batch_get_fattura_iva_context([fattura_id])[fattura_id]
    plafond = (imponibile0 / 2).quantize(Decimal("0.01"))
    soggetto = q(
        """
        SELECT s.id FROM anagrafiche.billing_account ba
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
          JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
         WHERE ba.id = %s
        """,
        [ba_id],
    )
    tipo = q("SELECT id FROM config.tipi_titolo_iva WHERE ha_plafond IS TRUE LIMIT 1")
    iva_alt = q("SELECT id FROM config.iva WHERE attivo AND id <> %s LIMIT 1", [iva0 or 0])
    if not (soggetto and tipo and iva_alt):
        raise SystemExit(
            f"SENZA_MATERIA: soggetto={bool(soggetto)} tipo={bool(tipo)} iva={bool(iva_alt)}."
        )
    titolo_id = q(
        """
        INSERT INTO anagrafiche.soggetti_titoli_iva
               (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
                ambito, valido_dal, valido_al, plafond, attivo)
        VALUES (%s, %s, %s, %s, 'TUTTO', %s, %s, %s, TRUE)
        RETURNING id
        """,
        [soggetto[0][0], ctx["emittente_fiscale_id"], tipo[0][0], iva_alt[0][0],
         ctx["data_riferimento"], ctx["data_riferimento"], plafond],
    )[0][0]
    check("titolo con capienza PARZIALE", True,
          f"id={titolo_id} plafond={plafond} su imponibile={imponibile0}")

    # ── 7-10. Il giro ──────────────────────────────────────────────────────
    print("\n=== 7-10. Il giro: consuma e spezza ===")
    esito = PlafondFatturaService(repo).consuma_lotto(lotto_id)
    check("il giro risponde", esito["fatture"] == 1, str(esito))
    check("una riga spezzata", esito["righe_spezzate"] == 1, str(esito))
    check("un movimento scritto", esito["movimenti"] == 1, str(esito))

    parti = q(
        """
        SELECT id, qta, iva_id, riga_capofila_id, fattura_id
          FROM vendite.fatture_righe
         WHERE id = %s OR riga_capofila_id = %s
         ORDER BY riga_capofila_id NULLS FIRST
        """,
        [riga_id, riga_id],
    )
    check("due righe dove ce n'era una", len(parti) == 2, f"{len(parti)}")
    if len(parti) == 2:
        capofila, parte = parti
        # ⭐ IL CASO CHE VALE PIU' DI TUTTI: le quantita' derivate possono non
        #    essere tonde, ma la loro somma DEVE essere esatta — o il documento
        #    fiscale perde o guadagna merce.
        check("le due parti sommano esattamente la riga",
              capofila[1] + parte[1] == qta0,
              f"{capofila[1]} + {parte[1]} vs {qta0}")
        check("la parte punta alla capofila", parte[3] == riga_id)
        check("e resta sulla stessa fattura", parte[4] == capofila[4] == fattura_id)
        check("le due parti hanno IVA DIVERSE",
              capofila[2] != parte[2], f"{capofila[2]} vs {parte[2]}")
        check("la capofila porta l'IVA del titolo",
              capofila[2] == iva_alt[0][0], str(capofila[2]))

    usato = q(
        "SELECT imponibile_utilizzato FROM anagrafiche.soggetti_titoli_iva WHERE id = %s",
        [titolo_id],
    )[0][0]
    # ⭐ L'accumulatore non lo scrive nessuno: e' la SOMMA del registro,
    #    riportata da un trigger. Se qui non torna la capienza, il movimento non
    #    e' stato scritto davvero.
    check("l'accumulatore ha visto il consumo", usato == plafond, f"{usato} vs {plafond}")

    # ── 11. La vista ──────────────────────────────────────────────────────
    print("\n=== 11. La vista: due righe SORELLE, non un padre e un figlio ===")
    esposte = q(
        """
        SELECT tipo_riga, livello, ordinamento, imponibile
          FROM vendite.vw_fattura_righe_esposte
         WHERE fattura_id = %s
           AND (fatture_righe_id = %s OR riga_capofila_id = %s)
         ORDER BY tipo_riga
        """,
        [fattura_id, riga_id, riga_id],
    )
    check("la vista le espone entrambe", len(esposte) == 2, str(len(esposte)))
    if len(esposte) == 2:
        tipi = {r[0] for r in esposte}
        check("una e' PARTE_PLAFOND", "PARTE_PLAFOND" in tipi, str(tipi))
        # ⛔ ENTRAMBE a livello 0: `livello 1` in questa vista significa «riga
        #    descrittiva SENZA importo», e il codice che fa «salta il livello 1»
        #    esiste — su una fattura spezzata perderebbe la seconda parte senza
        #    nessun errore, con un totale semplicemente piu' basso.
        check("entrambe a livello 0", all(r[1] == 0 for r in esposte),
              str([r[1] for r in esposte]))
        check("entrambe portano un IMPORTO", all(r[3] is not None for r in esposte),
              str([r[3] for r in esposte]))
        # ⚠️ Stesso `ordinamento`: e' cio' che le tiene adiacenti anche se fra
        #    loro cade un'altra riga dello stesso articolo.
        check("stesso ordinamento", len({r[2] for r in esposte}) == 1,
              str([r[2] for r in esposte]))

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
