# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — NOTA DI CREDITO sui resi, il giro intero sul percorso REALE:
#         coda accrediti -> verbo (B1) -> rettifica in commessa -> riga di
#         fattura (B4) -> documento con natura NOTA_CREDITO -> numerazione sul
#         sezionale NC -> legame documentale (B6) -> annullo dell'accredito.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-nota-credito-resi.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE (brief-design-note-credito-resi §22 B8, §27.4).
# Nessun test automatico attraversa questo giro: i test del service mockano il
# repository, quelli del repository mockano il cursore, e i pgTAP del DB
# presidiano le funzioni una per una. Il TRATTO fra loro — la madre che scrive
# la rettifica, il generatore che ne fa una riga di fattura, la chiave che
# manda quella riga su un documento SEPARATO con natura NOTA_CREDITO, il
# sezionale che lo numera, il task che scrive il legame — non lo esercita
# nessuno. Ed e' il tratto dove un errore diventa un documento fiscale.
#
# ⚠️ PERCHE' VIENE PRIMA DELL'ENDPOINT (B2). Appena l'endpoint esiste, il verbo
# e' a portata di click e i timer di fatturazione girano ogni minuto: il primo
# errore non lo trova un test, lo trova una nota di credito emessa. P-1 e'
# applicata, quindi il fail-closed che teneva il verbo al solo SUPER_ADMIN non
# c'e' piu'.
#
# IDEMPOTENZA. Tutto dentro `transaction.atomic()` con `set_rollback(True)`
# finale: rettifiche, righe di ponte, lotto, fattura, numero e legame NON
# persistono. Nessuna pulizia preventiva da ricordare, rieseguibile
# all'infinito. ⚠️ Le SEQUENZE avanzano (numeri di fattura del sezionale NC
# compresi): e' l'unico effetto che sopravvive al rollback, ed e' innocuo —
# un progressivo con un buco, non un documento.
#
# ⚠️ SI GIRA SUI DATI VERI DELLA CODA, non su un fixture. Costruire da zero
# ordine -> DDT -> consegna -> reso -> fattura della merce sarebbe un fixture
# piu' grande del sistema in prova, e proverebbe il fixture. La coda accrediti
# di questo ambiente ha righe reali (la 24 e' il caso KIT indicato dal brief):
# quelle sono la materia giusta. Se la coda e' vuota lo smoke SALTA e lo dice.
#
# Indice test (1..14):
#   1  il verbo ritorna UNA riga per rettifica creata (RETURNS TABLE, non uno scalare)
#   2  ogni rettifica e' RETTIFICA, con quantita' NEGATIVA (D-NC-2: il segno e' nel numero)
#   3  il prezzo e' COPIATO dalla riga di fattura rettificata, mai ricalcolato (N-1)
#   4  ogni rettifica porta natura NOTA_CREDITO e il puntatore alla riga rettificata
#   5  il ponte `resi_righe_accrediti` ha una riga per coppia, con quantita' POSITIVE
#   6  la riga esce dalla coda AL VERBO (non aspetta la fattura) — §20.3
#   7  il secondo verbo sulla stessa riga e' rifiutato (E_ACCREDITO_GIA_ESEGUITO)
#   8  la rettifica diventa attivita' fatturabile per la via reale (pull da commessa)
#   9  il generatore produce righe con `riga_rettificata_id` valorizzato (B4)
#  10  🔴 il documento e' SEPARATO da quelli ordinari e ha natura NOTA_CREDITO
#  11  🔴 il documento nasce sul REGISTRO delle note di credito, non su quello fatture
#  11-bis P-5 (rev 2026-09-17): la NC ha UNA rata negativa uguale al totale, prima del numero
#  12  la numerazione assegna un numero sul sezionale NC
#  13  🔴 B6: il legame documentale viene scritto, e il rilancio e' idempotente
#  14  P-5: l'annullo toglie il ponte e la coda RISALE (la merce torna accreditabile)
#  15  🔴 KIT: la rettifica di un componente attraversa il generatore
#
# ⚠️ LA CODA SI CLASSIFICA PRIMA DI SCEGLIERE. Le sue righe non sono
# equivalenti: quelle su un articolo COMPOSITO producono una rettifica per
# componente, con `#CMP:` nel segment_key, e imboccano nel generatore il ramo
# dello snapshot kit. Il giro completo (9-13) si esercita su una riga SEMPLICE
# e il caso kit ha il test 15 tutto suo — perche' un unico test misto direbbe
# «rosso» senza dire QUALE meta' e' rotta.
# ------------------------------------------------------------

import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services import resi_service
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import crea_lotto_di_prova

FAIL: list[str] = []
SKIP: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Segnala un caso NON esercitabile su questo ambiente. Saltare e dirlo e'
#        onesto; saltare in silenzio farebbe leggere «tutto verde» a una
#        copertura che non c'e' stata.
def skip(label, motivo):
    print(f"  SKIP {label} — {motivo}")
    SKIP.append(label)


# Scopo: porta le rettifiche di una riga di reso fino a un LOTTO pronto per il
#        generatore: pull da commessa (via reale), lotto dedicato, lock delle
#        sole attivita' dello smoke. Ritorna (lotto_id, righe AF).
# ⚠️ Il lock e' l'unico passo scavalcato: `select_attivita` lo metterebbe su
#    TUTTE le attivita' del perimetro, e qui serve restringere lo scope allo
#    smoke — non cambia il percorso del generatore, che e' cio' che si prova.
# ⭐ Sede unica: il giro principale e la prova sul kit facevano gli stessi tre
#    passi in due copie, e due copie di un fixture divergono come qualunque
#    altra cosa — con l'aggravante che un fixture divergente fa passare il test
#    per una ragione diversa da quella per cui passa il sistema.
def prepara_lotto(cur, ca_ids, *, marker):
    cur.execute(
        "SELECT commessa_id FROM vendite.commesse_attivita WHERE id = %s",
        [ca_ids[0]],
    )
    commessa_id = cur.fetchone()[0]
    cur.execute(
        "SELECT inserted_rows FROM vendite.fn_emit_attivita_fatturabili_da_commessa(%s)",
        [commessa_id],
    )
    cur.fetchone()
    cur.execute(
        """
        SELECT af.id, af.commessa_attivita_id, af.quantita, af.natura_doc_id,
               af.tipo_movimento, af.fattura_riga_rettificata_id,
               af.competenza_mese, af.tipo_doc_fiscale_id, af.billing_account_id
          FROM vendite.attivita_fatturabili af
         WHERE af.commessa_attivita_id = ANY(%s)
         ORDER BY af.id
        """,
        [ca_ids],
    )
    af_righe = cur.fetchall()
    if not af_righe:
        return None, []

    lock_batch_id = str(uuid.uuid4())
    # Utility ed emittente del lotto sono quelli della commessa del reso.
    cur.execute(
        """
        SELECT ba.utility_id, c.emittente_soggetto_ruolo_id
          FROM vendite.commesse c
          JOIN anagrafiche.billing_account ba ON ba.id = c.billing_account_id
         WHERE c.id = %s
        """,
        [commessa_id],
    )
    utility_id, emittente_sr_id = cur.fetchone()
    lotto_id = crea_lotto_di_prova(
        cur,
        {"competenza_mese": af_righe[0][6], "tipo_doc_fiscale_id": af_righe[0][7],
         "utility_id": utility_id, "emittente_sr_id": emittente_sr_id},
        codice=f"SMOKE-NC-{marker}-{uuid.uuid4().hex[:8]}", lock_batch_id=lock_batch_id,
    )
    cur.execute(
        "UPDATE vendite.attivita_fatturabili"
        "   SET lock_batch_id = %s, lock_in_fatturazione = TRUE"
        " WHERE id = ANY(%s)",
        [lock_batch_id, [int(a[0]) for a in af_righe]],
    )
    return lotto_id, af_righe


with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore: la coda, le fatture e i lotti sono sotto RLS.
        # Senza GUC le viste tornano ZERO righe — e uno zero fail-closed
        # somiglia a un dato (memoria feedback_rls_query_contesto_sistema).
        apri_contesto_smoke(cur)

        # ── Materia: le righe della coda, accreditate una per una in un
        #    SAVEPOINT proprio e poi classificate per forma della rettifica.
        #    ⚠️ Le righe non sono indipendenti fra loro: due righe di reso
        #    sulla stessa riga di DDT condividono la partita, quindi
        #    accreditare la prima puo' azzerare il dovuto della seconda. Una
        #    riga che esce dalla coda per questo NON e' un errore dello smoke:
        #    si salta e si dice.
        cur.execute(
            """
            SELECT resi_riga_id, accredito_dovuto, etichetta
              FROM vendite.vw_resi_da_accreditare
             ORDER BY resi_riga_id
            """
        )
        coda = cur.fetchall()
        if not coda:
            raise SystemExit(
                "Coda accrediti VUOTA su questo ambiente: lo smoke non ha materia. "
                "Non e' un verde."
            )

        accreditate: dict[int, list] = {}
        for (rid, _dovuto, _etichetta) in coda:
            rid = int(rid)
            try:
                with transaction.atomic():
                    accreditate[rid] = resi_service.accredita_riga_reso(rid)["accrediti"]
            except ServiceError as exc:
                print(f"  ---  riga {rid} non accreditata ({exc.code}): "
                      "la partita e' gia' pareggiata da una riga precedente")

        if not accreditate:
            raise SystemExit("Nessuna riga della coda accreditabile: niente da provare.")

        cur.execute(
            "SELECT id, segment_key FROM vendite.commesse_attivita WHERE id = ANY(%s)",
            [[int(a["commessa_attivita_id"]) for v in accreditate.values() for a in v]],
        )
        segmenti = {int(r[0]): r[1] for r in cur.fetchall()}

        # Scopo: una riga di reso e' «kit» se anche una sola delle sue
        #        rettifiche vive su un segmento di COMPONENTE (`#CMP:`).
        def _e_kit(rid):
            return any("#CMP:" in (segmenti.get(int(a["commessa_attivita_id"])) or "")
                       for a in accreditate[rid])

        semplici = [r for r in accreditate if not _e_kit(r)]
        kit = [r for r in accreditate if _e_kit(r)]
        print(f"\ncoda accrediti: {len(coda)} righe, accreditate {len(accreditate)} — "
              f"semplici={semplici} kit={kit}\n")

        riga_id = semplici[0] if semplici else kit[0]
        # L'annullo si prova sulla riga con PIU' rettifiche: e' il caso che
        # conta (C-2 del team DB — l'annullo e' tutto-o-niente sull'INSIEME),
        # e resta esercitabile perche' quella riga non entra nel giro.
        candidati_annullo = [r for r in accreditate if r != riga_id]
        riga_annullo = (max(candidati_annullo, key=lambda r: len(accreditate[r]))
                        if candidati_annullo else None)

        # ══════════════════════════════════════════════════════════
        #  1-5 · IL VERBO (B1 + madre fn_accredita_riga_reso)
        # ══════════════════════════════════════════════════════════
        accrediti = accreditate[riga_id]
        check("1 il verbo ritorna una riga per rettifica creata",
              len(accrediti) >= 1, f"{len(accrediti)} rettifiche")

        ca_ids = [int(a["commessa_attivita_id"]) for a in accrediti]
        cur.execute(
            """
            SELECT ca.id, ca.tipo_movimento, ca.quantita, ca.prezzo_snapshot,
                   ca.natura_doc_id, ca.fattura_riga_rettificata_id,
                   ca.segment_key, ca.stato_approvazione, ca.stato_emissione,
                   ca.commessa_id, ca.competenza_mese, ca.tipo_doc_fiscale_id,
                   fr.prezzo_unitario, fr.sconto_percentuale, fr.iva_id
              FROM vendite.commesse_attivita ca
              LEFT JOIN vendite.fatture_righe fr ON fr.id = ca.fattura_riga_rettificata_id
             WHERE ca.id = ANY(%s)
             ORDER BY ca.id
            """,
            [ca_ids],
        )
        rettifiche = cur.fetchall()
        check("2 ogni rettifica e' RETTIFICA con quantita' negativa",
              bool(rettifiche) and all(r[1] == "RETTIFICA" and r[2] < 0 for r in rettifiche),
              f"{[(r[1], str(r[2])) for r in rettifiche]}")
        check("3 il prezzo e' copiato dalla riga di fattura rettificata",
              all(r[12] is not None and r[3] == r[12] for r in rettifiche),
              f"{[(str(r[3]), str(r[12])) for r in rettifiche]}")

        cur.execute("SELECT config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')")
        natura_nc = int(cur.fetchone()[0])
        check("4 natura NOTA_CREDITO + puntatore alla riga rettificata",
              all(r[4] == natura_nc and r[5] is not None for r in rettifiche))

        cur.execute(
            "SELECT qta, qta_partita, fattura_riga_rettificata_id"
            "  FROM vendite.resi_righe_accrediti WHERE resi_riga_id = %s",
            [riga_id],
        )
        ponte = cur.fetchall()
        check("5 il ponte ha una riga per coppia, con quantita' positive",
              len(ponte) == len(rettifiche) and all(p[0] > 0 and p[1] > 0 for p in ponte),
              f"{len(ponte)} righe di ponte / {len(rettifiche)} rettifiche")

        # ══════════════════════════════════════════════════════════
        #  6-7 · LA CODA SI CHIUDE AL VERBO, NON ALLA FATTURA (§20.3)
        # ══════════════════════════════════════════════════════════
        cur.execute(
            "SELECT COALESCE(SUM(accredito_dovuto),0) FROM vendite.vw_resi_da_accreditare"
            " WHERE resi_riga_id = %s",
            [riga_id],
        )
        dovuto_dopo = cur.fetchone()[0]
        check("6 la riga esce dalla coda AL VERBO (nessuna finestra temporale)",
              Decimal(dovuto_dopo) == 0, f"accredito_dovuto residuo = {dovuto_dopo}")

        # ⚠️ SAVEPOINT obbligatorio. Un errore sollevato da PL/pgSQL ABORTISCE
        #    la transazione: senza il blocco annidato (che Django traduce in
        #    SAVEPOINT) l'asserzione seguente troverebbe «transazione
        #    interrotta» e tutto il resto dello smoke morirebbe dopo il primo
        #    errore ATTESO. E' successo scrivendo questo file.
        try:
            with transaction.atomic():
                resi_service.accredita_riga_reso(riga_id)
            check("7 il secondo verbo e' rifiutato", False, "nessun errore sollevato")
        except ServiceError as exc:
            check("7 il secondo verbo e' rifiutato",
                  exc.code == "E_ACCREDITO_GIA_ESEGUITO", f"codice={exc.code}")

        # ══════════════════════════════════════════════════════════
        #  8 · DALLA COMMESSA ALL'ATTIVITA' FATTURABILE (via reale)
        # ══════════════════════════════════════════════════════════
        lotto_id, af_righe = prepara_lotto(cur, ca_ids, marker="GIRO")

        check("8 la rettifica diventa attivita' fatturabile (pull da commessa)",
              len(af_righe) == len(rettifiche)
              and all(a[4] == "RETTIFICA" and a[2] < 0 and a[3] == natura_nc
                      for a in af_righe),
              f"{len(af_righe)} AF")

        if not af_righe:
            skip("9-13 il giro di fatturazione", "nessuna attivita' fatturabile emessa")
        else:
            elaborate = FattureRigheService().generate_fatture_righe(lotto_id)
            print(f"\nlotto {lotto_id}: generate_fatture_righe -> {elaborate} attivita'\n")

            cur.execute(
                """
                SELECT fr.id, fr.fattura_id, fr.riga_rettificata_id, fr.qta,
                       fr.prezzo_unitario, fr.sconto_percentuale, fr.iva_id,
                       orig.prezzo_unitario, orig.sconto_percentuale, orig.iva_id,
                       orig.fattura_id
                  FROM vendite.fatture_righe fr
                  JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = fr.fattura_id
                  LEFT JOIN vendite.fatture_righe orig ON orig.id = fr.riga_rettificata_id
                 WHERE lf.lotto_id = %s
                 ORDER BY fr.id
                """,
                [lotto_id],
            )
            righe_nc = cur.fetchall()
            # ⚠️ Una sola condizione, esplicita: la forma
            # `A and B or C and D` in un `all(...)` e' precisamente il modo in
            # cui un'asserzione diventa verde per precedenza invece che per
            # merito. `sconto_percentuale` e `iva_id` si confrontano
            # cosi' come sono — NULL == NULL e' vero in Python, ed e' il caso
            # normale (nessuno sconto sulla riga originale).
            def _riga_specchio(r):
                return (r[2] is not None      # riga_rettificata_id valorizzato
                        and r[3] < 0          # quantita' negativa
                        and r[4] == r[7]      # prezzo copiato
                        and r[5] == r[8]      # sconto copiato
                        and r[6] == r[9])     # aliquota IVA copiata

            check("9 le righe portano `riga_rettificata_id` e copiano prezzo/sconto/IVA",
                  bool(righe_nc) and all(_riga_specchio(r) for r in righe_nc),
                  f"{len(righe_nc)} righe")

            fatture_nc = {int(r[1]) for r in righe_nc}
            fatture_orig = {int(r[10]) for r in righe_nc if r[10] is not None}
            check("10 il documento e' SEPARATO da quello che rettifica",
                  bool(fatture_nc) and not (fatture_nc & fatture_orig),
                  f"NC={sorted(fatture_nc)} rettificate={sorted(fatture_orig)}")

            cur.execute(
                """
                SELECT f.id, f.natura_doc_id, f.registro_id, r.codice, f.numero, f.serie
                  FROM vendite.fatture f
                  JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
                 WHERE f.id = ANY(%s)
                """,
                [sorted(fatture_nc)],
            )
            testate = cur.fetchall()
            check("10-bis la testata dichiara natura NOTA_CREDITO",
                  bool(testate) and all(t[1] == natura_nc for t in testate),
                  f"{[(t[0], t[1]) for t in testate]}")
            check("11 il documento nasce sul registro delle note di credito",
                  bool(testate) and all(t[3] == "NC" for t in testate),
                  f"{[(t[0], t[3]) for t in testate]}")

            # ── 12 · numerazione (la sola parte irreversibile in esercizio:
            #    qui vive dentro la transazione che verra' annullata).
            # ⚠️ Prima vanno chiusi gli step che il giro vero fa prima del
            #    numero — ricalcolo IVA, poi piano rate — e non e' una
            #    formalita': `fn_assign_numero_fattura` RIFIUTA un documento
            #    senza totali, senza riepilogo IVA o, se il totale non e' zero,
            #    senza piano rate che quadri. «La numerazione consuma un
            #    progressivo e nextval non torna indietro», quindi la coerenza
            #    si verifica prima di prendere il numero.
            # ⛔ Fino al 2026-10-18 lo smoke saltava il piano rate: «sull'NC le
            #    rate non servono, il guard le chiede solo se il totale e'
            #    positivo». Dalla rev 2026-09-17 (P-5) il guard chiede «<> 0»:
            #    la nota di credito ha UNA rata negativa uguale al totale, e lo
            #    smoke si fermava su «piano rate assente».
            repo = VenditePipelineRepository()
            repo.run_ricalcola_iva_lotto_task(lotto_id=lotto_id)
            repo.run_genera_scadenze_lotto_task(lotto_id=lotto_id)
            cur.execute(
                """
                SELECT f.id, f.totale_a_pagare, count(fs.id),
                       coalesce(sum(fs.importo), 0), bool_and(fs.importo < 0)
                  FROM vendite.fatture f
                  LEFT JOIN vendite.fatture_scadenze fs ON fs.fattura_id = f.id
                 WHERE f.id = ANY(%s)
                 GROUP BY f.id, f.totale_a_pagare
                """,
                [sorted(fatture_nc)],
            )
            piani = cur.fetchall()
            check("11-bis P-5: la nota di credito ha UNA rata negativa uguale al totale",
                  bool(piani) and all(
                      p[1] is not None and p[1] < 0 and p[2] == 1 and p[3] == p[1] and p[4]
                      for p in piani),
                  f"{[(p[0], str(p[1]), p[2], str(p[3])) for p in piani]}")
            for fattura_id in sorted(fatture_nc):
                repo.numera_fattura_opz_emessa(fattura_id)
            cur.execute(
                "SELECT f.id, f.numero, f.anno, r.codice FROM vendite.fatture f"
                "  JOIN vendite.registri_fatturazione r ON r.id = f.registro_id"
                " WHERE f.id = ANY(%s)",
                [sorted(fatture_nc)],
            )
            numerate = cur.fetchall()
            check("12 la numerazione assegna un numero sul sezionale NC",
                  bool(numerate) and all(n[1] is not None and n[3] == "NC" for n in numerate),
                  f"{[(n[0], n[1], n[3]) for n in numerate]}")

            # ── 13 · B6: il legame documentale, per la via del task.
            coppie = sum(repo.popola_fatture_rettifiche(f) for f in sorted(fatture_nc))
            cur.execute(
                "SELECT fattura_id, rettificata_id FROM vendite.fatture_rettifiche"
                " WHERE fattura_id = ANY(%s) ORDER BY 1,2",
                [sorted(fatture_nc)],
            )
            legami = cur.fetchall()
            rilancio = sum(repo.popola_fatture_rettifiche(f) for f in sorted(fatture_nc))
            check("13 il legame documentale viene scritto",
                  coppie >= 1 and len(legami) >= 1,
                  f"{coppie} coppie: {[(int(l[0]), int(l[1])) for l in legami]}")
            check("13-bis il rilancio del task e' idempotente",
                  rilancio == 0, f"secondo giro: {rilancio} coppie aggiunte")

        # ══════════════════════════════════════════════════════════
        #  15 · KIT · la rettifica di un COMPONENTE attraversa il generatore
        # ══════════════════════════════════════════════════════════
        # ⚠️ Tutto dentro un SAVEPOINT proprio, annullato subito: il lotto e le
        #    attivita' fatturabili di questa prova non devono disturbare il
        #    test 14, che lavora sulle stesse rettifiche.
        if not kit:
            skip("15 la rettifica di un componente di kit",
                 "nessuna riga di coda su articolo composito")
        else:
            riga_kit = kit[0]
            ca_kit = [int(a["commessa_attivita_id"]) for a in accreditate[riga_kit]]
            esito_kit = None
            try:
                with transaction.atomic():
                    lotto_kit, af_kit = prepara_lotto(cur, ca_kit, marker="KIT")
                    # Fixture degenere: senza attivita' fatturabili il
                    # generatore non e' stato attraversato, e dirlo e' diverso
                    # dal dare la colpa al generatore con l'errore che
                    # produrrebbe un lotto None.
                    if not af_kit:
                        esito_kit = "nessuna attivita' fatturabile per le rettifiche del kit"
                    else:
                        FattureRigheService().generate_fatture_righe(lotto_kit)
                    transaction.set_rollback(True)
            except ServiceError as exc:
                esito_kit = f"{exc.code}: {exc.detail or exc}"
            check("15 la rettifica di un componente di kit attraversa il generatore",
                  esito_kit is None, esito_kit or "")

        # ══════════════════════════════════════════════════════════
        #  14 · P-5 · L'ANNULLO (cio' che B2-bis andra' a vestire)
        # ══════════════════════════════════════════════════════════
        if riga_annullo is None:
            skip("14 l'annullo dell'accredito", "una sola riga in coda: nessuna materia")
        else:
            esito2 = {"accrediti": accreditate[riga_annullo]}
            cur.execute(
                "SELECT COALESCE(SUM(accredito_dovuto),0) FROM vendite.vw_resi_da_accreditare"
                " WHERE resi_riga_id = %s",
                [riga_annullo],
            )
            dovuto_accreditato = Decimal(cur.fetchone()[0])
            cur.execute(
                "SELECT count(*) FROM vendite.fn_annulla_accredito_riga_reso(%s, %s)",
                [riga_annullo, "smoke: annullo di prova"],
            )
            tolte = int(cur.fetchone()[0])
            cur.execute(
                "SELECT count(*) FROM vendite.resi_righe_accrediti WHERE resi_riga_id = %s",
                [riga_annullo],
            )
            ponte_dopo = int(cur.fetchone()[0])
            cur.execute(
                "SELECT COALESCE(SUM(accredito_dovuto),0) FROM vendite.vw_resi_da_accreditare"
                " WHERE resi_riga_id = %s",
                [riga_annullo],
            )
            dovuto_risalito = Decimal(cur.fetchone()[0])
            check("14 l'annullo toglie il ponte e la coda RISALE",
                  tolte == len(esito2["accrediti"]) and ponte_dopo == 0
                  and dovuto_accreditato == 0 and dovuto_risalito > 0,
                  f"tolte={tolte} ponte={ponte_dopo} dovuto {dovuto_accreditato}->{dovuto_risalito}")

    # Niente persiste: rettifiche, ponte, lotto, fattura, numero e legame
    # spariscono con la transazione.
    transaction.set_rollback(True)

print("\n" + "=" * 60)
if SKIP:
    print(f"SALTATI: {len(SKIP)} — {SKIP}")
if FAIL:
    print(f"ROSSI: {len(FAIL)}")
    for f in FAIL:
        print(f"  - {f}")
    raise SystemExit(1)
print("SMOKE NOTA DI CREDITO: tutto verde (nessuna scrittura persistita)")
