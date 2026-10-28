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
# ⭐ LA MATERIA SI COSTRUISCE (rev 2026-10-28, ok Tid). Fino a quel giorno lo
# smoke girava sulla coda accrediti REALE («costruire ordine -> DDT -> reso ->
# fattura sarebbe un fixture piu' grande del sistema in prova»): su dbdev la
# coda aveva una sola riga semplice e nessun kit, e i test 14 e 15 SALTAVANO —
# copertura zero, letta come SENZA_MATERIA nella baseline. E' la forma del
# «verde per sottrazione» (AGENTS.md, corollario sui test): un ramo che si
# distingue solo quando la coda ha un kit si prova COSTRUENDO il kit.
# Il fixture non si scrive qui: lo danno i builder del DB, gli stessi dei pgTAP
# dell'accredito (`dbops.fn_pgtap_crea_ddt_da_ordine`, `fn_pgtap_fattura_attivita`,
# `fn_pgtap_crea_reso`), sull'emittente di prova. Tre PARTITE separate —
# merce consegnata 10, fatturata 10, resa 3, accredito dovuto 3 — perche'
# l'accredito di una non possa pareggiare l'altra:
#   A  semplice -> il giro completo (1-13)
#   B  semplice -> l'annullo (14)
#   K  kit di due componenti -> la rettifica per componente (15). La parentela
#      del kit vive nel `segment_key` (`#CMP:`) e nel meta (contratto
#      apps/vendite/services/_kit_meta.py): e' scritta come la scrive il push
#      della bolla, come fa il pgTAP test-accredito-kit-meta-v1.
#
# Indice test (0..15):
#   0  la materia costruita e' in coda, con l'accredito dovuto atteso
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
# ⚠️ LE PARTITE NON SONO EQUIVALENTI. Quella del kit produce una rettifica per
# componente, con `#CMP:` nel segment_key, e imbocca nel generatore il ramo
# dello snapshot kit. Il giro completo (9-13) si esercita sulla partita
# SEMPLICE e il kit ha il test 15 tutto suo — perche' un unico test misto
# direbbe «rosso» senza dire QUALE meta' e' rotta. La classificazione si
# VERIFICA comunque (test 0): una partita costruita come kit che non producesse
# rettifiche `#CMP:` farebbe passare il 15 per la ragione sbagliata.
# ------------------------------------------------------------

import json
import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services import resi_service
from apps.vendite.services._kit_meta import (
    META_KEY_COEFF_QTA,
    META_KEY_COMPONENTE_DI,
    META_KEY_ESPOSIZIONE,
    META_KEY_QTA_PADRE,
    META_KEY_UOM_PADRE,
    segment_key_componente,
)
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_commessa import crea_riga_commessa
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    costruisci_base_fatturazione,
    crea_articolo_di_prova,
    crea_lotto_di_prova,
)

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


# Scopo: gli step che il giro vero fa PRIMA del numero, sulle fatture di un
#        lotto: ricalcolo IVA, poi piano rate. Non e' una formalita':
#        `fn_assign_numero_fattura` RIFIUTA un documento senza totali, senza
#        riepilogo IVA o, se il totale non e' zero, senza piano rate che quadri.
#        «La numerazione consuma un progressivo e nextval non torna indietro»,
#        quindi la coerenza si verifica prima di prendere il numero.
# ⛔ Fino al 2026-10-18 lo smoke saltava il piano rate sulla nota: «sull'NC le
#    rate non servono, il guard le chiede solo se il totale e' positivo». Dalla
#    rev 2026-09-17 (P-5) il guard chiede «<> 0»: la nota di credito ha UNA
#    rata negativa uguale al totale, e lo smoke si fermava su «piano rate
#    assente».
def chiudi_per_numerazione(repo, lotto_id):
    repo.run_ricalcola_iva_lotto_task(lotto_id=lotto_id)
    repo.run_genera_scadenze_lotto_task(lotto_id=lotto_id)


# Scopo: un SEZIONALE delle note di credito distinto da quello delle fatture,
#        sull'emittente di prova: la natura NOTA_CREDITO dei suoi tipi
#        documento si mappa (`vendite.tipi_doc_fiscale_registri`) su un altro
#        registro dell'emittente (`script.fn_pgtap_registro_fattura`, che salta
#        lo standard). Ritorna l'id del registro.
# ⚠️ PERCHE' SI COSTRUISCE. Il provisioning (C2-12) mappa la natura NC sul
#    registro delle fatture: note e fatture in un'unica numerazione, che e'
#    ammessa. Su quella configurazione la nota sul registro fatture e' GIUSTA,
#    e il test 11 non potrebbe distinguere il difetto che presidia — un
#    sezionale NC mappato che la nota non raggiunge. Fino al 2026-10-28 il
#    test confrontava il codice con la sigla 'NC' di una installazione.
def mappa_sezionale_nc(cur, t, natura_nc):
    cur.execute("SELECT script.fn_pgtap_registro_fattura(%s)", [t["emittente_sr_id"]])
    registro_nc = int(cur.fetchone()[0])
    # ⚠️ Scollegare e POI collegare, non un UPDATE del registro: il guard della
    #    coppia unica (BEFORE UPDATE) vede ancora la riga stessa sul registro
    #    vecchio e la conta come occupante (E_REGISTRO_COPPIA_GIA_COPERTA). La
    #    strada e' quella che indica il suo hint.
    cur.execute(
        """
        DELETE FROM vendite.tipi_doc_fiscale_registri m
         USING vendite.registri_fatturazione r
         WHERE r.id = m.registro_id
           AND r.emittente_soggetto_ruolo_id = %s
           AND m.natura_doc_id = %s
        RETURNING m.tipo_doc_fiscale_id, m.serie
        """,
        [t["emittente_sr_id"], natura_nc],
    )
    coppie = cur.fetchall()
    if not coppie:
        raise SystemExit(
            "SENZA_CONTESTO: l'emittente di prova non ha una mappatura per la "
            "natura NOTA_CREDITO da spostare (provisioning C2-12).")
    for tipo_doc_id, serie in coppie:
        cur.execute(
            "INSERT INTO vendite.tipi_doc_fiscale_registri"
            " (tipo_doc_fiscale_id, registro_id, natura_doc_id, serie, meta)"
            " VALUES (%s, %s, %s, %s, '{\"smoke\": \"nota-credito-resi\"}'::jsonb)",
            [tipo_doc_id, registro_nc, natura_nc, serie],
        )
    return registro_nc


# La forma di ogni partita: consegnati e fatturati 10, resi 3 -> dovuto 3.
QTA_CONSEGNATA = Decimal(10)
QTA_RESA = Decimal(3)
PREZZO = Decimal("25.00")


# Scopo: una PARTITA di merce del cliente della base, con la sua commessa:
#        bolla CONSEGNATA da un ordine (`dbops.fn_pgtap_crea_ddt_da_ordine`),
#        le righe di commessa che il push della bolla scriverebbe (sorgente
#        DDT_VENDITA, segmento della riga di bolla), fatturate per intero
#        (`dbops.fn_pgtap_fattura_attivita`) su un lotto e NUMERATE per la via
#        vera, e il reso a credito confermato di
#        QTA_RESA (`dbops.fn_pgtap_crea_reso`). Ritorna l'id della riga di reso.
#        `componenti` dato = [(articolo_id, uom_id, coeff)]: la partita e' un
#        KIT, e le righe di commessa sono una per componente, col segmento
#        `#CMP:` e il meta del kit (`_kit_meta`: TUTTE le chiavi che il push
#        scrive — la rettifica le eredita in blocco, e il generatore rifiuta un
#        componente senza `uom_padre_id`), prezzo ripartito sui
#        coefficienti cosi' che il kit valga PREZZO a unita' padre.
# ⚠️ La fattura rettificata dev'essere NUMERATA: la nota di credito cita numero
#    e data del documento che corregge (TD04, DatiFattureCollegate), e la sua
#    numerazione rifiuta E_FATTURA_RETTIFICATA_SENZA_NUMERO. Il builder la
#    lascia in bozza, e il seguito e' del chiamante.
# ⚠️ Una commessa per partita: la prova del giro (8) emette le attivita'
#    fatturabili dell'INTERA commessa, e quelle delle altre partite finirebbero
#    nel conto della merce su cui lavorano l'annullo e il kit.
def costruisci_partita(cur, t, *, articolo_id, uom_id, componenti=None):
    cur.execute(
        "SELECT commessa_id FROM dbops.fn_pgtap_crea_commessa("
        " 'smoke nota credito', NULL, %s, p_con_sorgente_root => true)",
        [t["billing_account_id"]],
    )
    commessa_id = cur.fetchone()[0]
    cur.execute(
        "SELECT ddt_id, ddt_uid, ddt_riga_id FROM dbops.fn_pgtap_crea_ddt_da_ordine("
        " 'smoke nota credito', p_billing_account_id => %s, p_quantita => %s,"
        " p_prezzo => %s, p_articolo_id => %s, p_fatturazione_trigger => 'CONSEGNATO')",
        [t["billing_account_id"], QTA_CONSEGNATA, PREZZO, articolo_id],
    )
    ddt_id, ddt_uid, ddt_riga_id = cur.fetchone()
    cur.execute("SELECT script.fn_segment_key('DDT_VENDITA', %s::text, %s)",
                [ddt_uid, ddt_riga_id])
    segmento = cur.fetchone()[0]

    if not componenti:
        righe = [(articolo_id, uom_id, segmento, QTA_CONSEGNATA, PREZZO, "{}")]
    else:
        prezzo_cmp = PREZZO / sum(Decimal(c) for (_a, _u, c) in componenti)
        righe = [
            (c_art, c_uom, segment_key_componente(segmento, c_art),
             QTA_CONSEGNATA * c, prezzo_cmp,
             json.dumps({META_KEY_COEFF_QTA: c,
                         META_KEY_COMPONENTE_DI: str(articolo_id),
                         META_KEY_ESPOSIZIONE: "DESCRITTIVO",
                         META_KEY_QTA_PADRE: int(QTA_CONSEGNATA),
                         META_KEY_UOM_PADRE: uom_id}))
            for (c_art, c_uom, c) in componenti
        ]
    attivita = [
        crea_riga_commessa(
            cur, commessa_id=commessa_id, segment_key=seg, articolo_id=art,
            istanza_utility_id=t["istanza_utility_id"], uom_id=uom,
            data_attivita=t["data"], competenza_mese=t["competenza_mese"],
            competenza_dal=t["data"], competenza_al=t["data"],
            quantita=qta, prezzo=prezzo,
            tipo_doc_fiscale_id=t["tipo_doc_fiscale_id"], valuta_id=t["valuta_id"],
            stato_approvazione="APPROVATA", meta=meta,
            sorgente_codice="DDT_VENDITA", sorgente_uid=str(ddt_uid),
        )
        for (art, uom, seg, qta, prezzo, meta) in righe
    ]
    lotto_id = crea_lotto_di_prova(
        cur, t, codice=f"SMOKE-NC-ORIGINE-{uuid.uuid4().hex[:8]}",
        lock_batch_id=str(uuid.uuid4()),
    )
    cur.execute(
        "SELECT DISTINCT fattura_id FROM dbops.fn_pgtap_fattura_attivita("
        " 'smoke nota credito', %s, p_lotto_id => %s)",
        [attivita, lotto_id],
    )
    fatture = sorted(int(r[0]) for r in cur.fetchall())
    repo = VenditePipelineRepository()
    chiudi_per_numerazione(repo, lotto_id)
    for fattura_id in fatture:
        repo.numera_fattura_opz_emessa(fattura_id)
    cur.execute(
        "SELECT resi_riga_id FROM dbops.fn_pgtap_crea_reso("
        " 'smoke nota credito', %s, %s, p_ddt_riga_id => %s)",
        [ddt_id, QTA_RESA, ddt_riga_id],
    )
    return int(cur.fetchone()[0])


with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore: la coda, le fatture e i lotti sono sotto RLS.
        # Senza GUC le viste tornano ZERO righe — e uno zero fail-closed
        # somiglia a un dato (memoria feedback_rls_query_contesto_sistema).
        apri_contesto_smoke(cur)

        # ── Materia: tre partite costruite sull'emittente di prova (vedi in
        #    testa). Lo smoke da qui in poi vede solo il suo perimetro.
        t = costruisci_base_fatturazione(cur, marker="NC-RESI")
        cur.execute("SELECT config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')")
        natura_nc = int(cur.fetchone()[0])
        registro_nc = mappa_sezionale_nc(cur, t, natura_nc)
        riga_id = costruisci_partita(
            cur, t, articolo_id=t["articolo_id"], uom_id=t["uom_id"])
        riga_annullo = costruisci_partita(
            cur, t, articolo_id=t["articolo_id"], uom_id=t["uom_id"])
        padre_id, padre_uom = crea_articolo_di_prova(cur, prefisso="SMOKE-NC-KIT")
        componenti = [
            (*crea_articolo_di_prova(cur, prefisso=f"SMOKE-NC-CMP{n}"), coeff)
            for n, coeff in ((1, 2), (2, 3))
        ]
        riga_kit = costruisci_partita(
            cur, t, articolo_id=padre_id, uom_id=padre_uom, componenti=componenti)
        costruite = {"semplice": riga_id, "annullo": riga_annullo, "kit": riga_kit}

        # ══════════════════════════════════════════════════════════
        #  0 · LA MATERIA E' IN CODA (come il test 1 dei pgTAP dell'accredito)
        # ══════════════════════════════════════════════════════════
        # ⚠️ Senza questa prova un fixture che non entra in coda farebbe
        #    fallire il verbo con un errore che sembra suo.
        cur.execute(
            "SELECT resi_riga_id, accredito_dovuto FROM vendite.vw_resi_da_accreditare"
            " WHERE resi_riga_id = ANY(%s)",
            [list(costruite.values())],
        )
        dovuti = {int(r[0]): Decimal(r[1]) for r in cur.fetchall()}
        check("0 la materia costruita e' in coda con l'accredito dovuto atteso",
              all(dovuti.get(r) == QTA_RESA for r in costruite.values()),
              str({k: str(dovuti.get(r)) for k, r in costruite.items()}))
        if FAIL:
            raise SystemExit(
                "=== ESITO: FALLITO — la materia costruita non e' in coda: "
                "il resto non proverebbe niente ===")

        accreditate: dict[int, list] = {
            r: resi_service.accredita_riga_reso(r)["accrediti"] for r in costruite.values()
        }

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

        check("0-bis le partite sono della forma costruita (semplici senza #CMP:, kit con)",
              not _e_kit(riga_id) and not _e_kit(riga_annullo) and _e_kit(riga_kit)
              and len(accreditate[riga_kit]) == len(componenti),
              f"rettifiche kit={len(accreditate[riga_kit])}")

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
            # Il sezionale della nota e' quello mappato per la natura NC
            # (costruito distinto, vedi mappa_sezionale_nc), e NON quello della
            # fattura che rettifica.
            cur.execute(
                "SELECT DISTINCT registro_id FROM vendite.fatture WHERE id = ANY(%s)",
                [sorted(fatture_orig)],
            )
            registri_orig = {int(r[0]) for r in cur.fetchall()}
            check("11 il documento nasce sul registro delle note di credito",
                  bool(testate) and all(int(f[2]) == registro_nc for f in testate)
                  and registro_nc not in registri_orig,
                  f"{[(f[0], f[3]) for f in testate]} sezionale NC={registro_nc} "
                  f"registri rettificati={sorted(registri_orig)}")

            # ── 12 · numerazione (la sola parte irreversibile in esercizio:
            #    qui vive dentro la transazione che verra' annullata).
            repo = VenditePipelineRepository()
            chiudi_per_numerazione(repo, lotto_id)
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
                "SELECT f.id, f.numero, f.anno, r.codice, r.id FROM vendite.fatture f"
                "  JOIN vendite.registri_fatturazione r ON r.id = f.registro_id"
                " WHERE f.id = ANY(%s)",
                [sorted(fatture_nc)],
            )
            numerate = cur.fetchall()
            check("12 la numerazione assegna un numero sul sezionale NC",
                  bool(numerate) and all(n[1] is not None and int(n[4]) == registro_nc
                                         for n in numerate),
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
    print("=== ESITO: FALLITO ===")
    raise SystemExit(1)
# ⚠️ La forma della riga e' il contratto di scripts/smoke-baseline.sh, che
#    classifica dall'output: fino al 2026-10-28 la chiusura era «tutto verde»
#    in minuscolo, e lo smoke non e' mai stato letto VERDE. Un passo saltato
#    e' copertura zero: niente «TUTTO VERDE».
if SKIP:
    print("=== ESITO: PARZIALE (passi saltati, nessuna scrittura persistita) ===")
else:
    print("=== ESITO: TUTTO VERDE (nessuna scrittura persistita) ===")
