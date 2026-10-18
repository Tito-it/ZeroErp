# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — tratto ATTIVITA' FATTURABILE -> RIGA DI FATTURA sul percorso REALE
#         (`FattureRigheService`, quello che esegue il task pipeline
#         `generate_fatture_righe`).
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fatturazione-aggregazione-righe.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE. Fino al 2026-07-28 questo tratto non era coperto da nulla che
# esercitasse il codice vivo: il pgTAP `test-porta-oneri-giro-completo-v1`
# invocava `vendite.fn_generate_fatture_righe`, cioe' la funzione SQL che
# NESSUN percorso eseguiva (rimossa col changeset 20260728-21). Le sue 3
# asserzioni sul tratto AF -> fattura erano verdi su codice morto, ed e' il
# motivo per cui i requisiti D4 (aggregazione) e D5 (snapshot kit) sono stati
# implementati sulla funzione sbagliata senza che niente lo segnalasse.
# Riferimenti: brief-be-fe-importi-riga-fattura.md §10.2 casi 7-8,
#              brief-db-ritiro-generatore-righe-fattura-sql.md §5 passo 3.
#
# IDEMPOTENZA. Nessuna pulizia da ricordare: tutto gira dentro una transazione
# con `set_rollback(True)` finale. Il fixture non tocca mai i dati esistenti —
# crea proprie righe di commessa, un proprio lotto e proprie attivita' — e alla
# fine non resta nulla. Rieseguibile all'infinito, anche in parallelo.
#
# Indice test (1..11):
#   1  due attivita' con la STESSA chiave -> UNA riga, qta sommata
#   2  la riga aggregata NON dichiara una sorgente singola
#   3  entrambe le attivita' puntano alla riga (correlazione n->1)
#   4  le attivita' risultano fatturate e COMPLETED
#   5  l'importo lo calcola il DB (trigger a20), non il servizio
#   6  prezzo diverso -> riga separata (il prezzo sta nella chiave)
#   7  la quantita' aggregata NON e' arrotondata
#   8  componente di kit -> le 4 colonne di snapshot sono congelate
#   9  la vista di esposizione produce KIT_PADRE + KIT_COMPONENTE (uno per
#      componente non NASCOSTO)
#  10  il totale della fattura non dipende da come il kit viene esposto
#  11  il VALORIZZATO porta il suo importo, legato al kit (kit_riga_nr); il
#      padre porta solo il DESCRITTIVO (brief-db-esposizione-componenti-kit-
#      in-fattura, 2026-10-01)
#  8c  quantita' e UoM del padre congelate dal meta (`kit_qta`, `kit_uom_id`):
#      la fattura non le ricava piu' dai componenti (brief-db-bom-flag-
#      quantita-e-kit-in-fattura R-BE-B2, 2026-10-02)
# ------------------------------------------------------------

import json
import uuid
from decimal import Decimal

from django.db import connection, transaction

from apps.core.db._helpers import coerce_jsonb_dict

from apps.vendite.services import _kit_meta as kit_meta
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_commessa import crea_riga_commessa
from scripts.tests._smoke_contesto import apri_contesto_smoke

# Attivita' gia' fatturata usata come TEMPLATE: da lei si ereditano
# billing account, istanza utility, uom, valuta e tipo documento, cosi' il
# fixture resta coerente con la configurazione reale dell'ambiente invece di
# inventare identificativi. Se sparisse, lo smoke lo dice subito (guard sotto).
SQL_TEMPLATE = """
    SELECT a.commessa_id, a.articolo_id, a.istanza_utility_id,
           a.billing_account_id, a.uom_id, a.valuta_id, a.tipo_doc_fiscale_id,
           a.sorgente_tipo_id, a.sorgente_origine_tipo_id, a.competenza_mese,
           c.emittente_soggetto_ruolo_id, c.utility_id
      FROM vendite.attivita_fatturabili a
      JOIN vendite.commesse c ON c.id = a.commessa_id
     WHERE a.commessa_id IS NOT NULL
     ORDER BY a.id DESC
     LIMIT 1
"""

FAIL: list[str] = []

# Quanti kit rappresentano le attivita' componente dello smoke (meta `qta_padre`).
KIT_QTA_PADRE = Decimal("1")


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: Crea una riga di commessa dedicata allo smoke. Passa dalla funzione di
#        upsert e non da un INSERT diretto, cosi' i guard di dominio (coerenza
#        BA, articolo attivo, unicita' del segment_key) restano esercitati.
def crea_commessa_attivita(cur, t, *, segment_key, articolo_id, quantita, prezzo, meta):
    return crea_riga_commessa(
        cur, commessa_id=t["commessa_id"], segment_key=segment_key,
        articolo_id=articolo_id, istanza_utility_id=t["istanza_utility_id"],
        uom_id=t["uom_id"], data_attivita=t["data"],
        competenza_mese=t["competenza_mese"], competenza_dal=t["data"],
        competenza_al=t["data"], quantita=quantita, prezzo=prezzo,
        tipo_doc_fiscale_id=t["tipo_doc_fiscale_id"], valuta_id=t["valuta_id"],
        meta=meta,
    )


# Scopo: Crea l'attivita' fatturabile agganciata alla riga di commessa, gia'
#        lockata sul lotto: e' lo stato in cui il task `select_attivita` le
#        consegna al generatore.
def crea_attivita_fatturabile(cur, t, *, ca_id, lock_batch_id, quantita, prezzo, meta):
    cur.execute(
        """
        INSERT INTO vendite.attivita_fatturabili (
            articolo_id, istanza_utility_id, billing_account_id, data_attivita,
            quantita, uom_id, qta_operativa, uom_operativa_id, factor_to_base,
            prezzo_unitario, valuta_id, tipo_doc_fiscale_id,
            competenza_mese, competenza_dal, competenza_al,
            commessa_id, commessa_attivita_id,
            sorgente_tipo_id, sorgente_uid, sorgente_origine_tipo_id,
            lock_batch_id, lock_in_fatturazione, approvato,
            stato_esecuzione, prezzo_bloccato, meta
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s, 1,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, TRUE, TRUE,
            'PENDING', TRUE, %s::jsonb
        ) RETURNING id
        """,
        [
            t["articolo_id"], t["istanza_utility_id"], t["billing_account_id"], t["data"],
            quantita, t["uom_id"], quantita, t["uom_id"],
            prezzo, t["valuta_id"], t["tipo_doc_fiscale_id"],
            t["competenza_mese"], t["data"], t["data"],
            t["commessa_id"], ca_id,
            t["sorgente_tipo_id"], str(uuid.uuid4()), t["sorgente_origine_tipo_id"],
            lock_batch_id, meta,
        ],
    )
    return cur.fetchone()[0]


print("\n=== SMOKE aggregazione righe fattura (percorso Python reale) ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore: `vendite.fatturazione_lotti` e `vendite.fatture`
        # sono RLS. Senza GUC le query tornano 0 righe e lo smoke mentirebbe.
        apri_contesto_smoke(cur)

        cur.execute(SQL_TEMPLATE)
        row = cur.fetchone()
        if not row:
            raise SystemExit("Nessuna attivita' fatturabile da usare come template.")
        t = {
            "commessa_id": row[0], "articolo_id": row[1], "istanza_utility_id": row[2],
            "billing_account_id": row[3], "uom_id": row[4], "valuta_id": row[5],
            "tipo_doc_fiscale_id": row[6], "sorgente_tipo_id": row[7],
            "sorgente_origine_tipo_id": row[8], "competenza_mese": row[9],
            "emittente_sr_id": row[10], "utility_id": row[11],
        }
        t["data"] = t["competenza_mese"]
        print(f"template: commessa {t['commessa_id']}, articolo {t['articolo_id']}, "
              f"BA {t['billing_account_id']}\n")

        # --- lotto dedicato -------------------------------------------------
        lock_batch_id = str(uuid.uuid4())
        marker = uuid.uuid4().hex[:8]
        cur.execute(
            """
            INSERT INTO vendite.fatturazione_lotti (
                codice, competenza_mese, utility_id, tipo_doc_fiscale_id,
                stato_doc_fiscale_id, emittente_soggetto_ruolo_id, tipo_lotto,
                stato_lotto, stato_operativo, lock_batch_id, meta
            )
            SELECT %s, %s, %s, %s,
                   (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno='DRAFT'),
                   %s, 'MASSIVO', 'IN_ESECUZIONE', 'APERTO', %s,
                   '{"smoke": true}'::jsonb
            RETURNING id
            """,
            [f"SMOKE-{marker}", t["competenza_mese"], t["utility_id"],
             t["tipo_doc_fiscale_id"], t["emittente_sr_id"], lock_batch_id],
        )
        lotto_id = cur.fetchone()[0]

        # --- fixture: 5 attivita' -------------------------------------------
        # A1 e A2 condividono la chiave di gruppo -> devono fondersi in UNA riga.
        # A3 ha prezzo diverso -> riga separata (il prezzo sta nella chiave).
        # K1 e K2 sono componenti dello stesso kit -> riga padre + componenti.
        kit_padre_segment = f"SMOKE:{marker}:R:1"
        af = {}
        for nome, seg, qta, prezzo, meta in [
            ("A1", f"SMOKE:{marker}:A1", Decimal("0.333333"), Decimal("10.00"), "{}"),
            ("A2", f"SMOKE:{marker}:A2", Decimal("0.333333"), Decimal("10.00"), "{}"),
            ("A3", f"SMOKE:{marker}:A3", Decimal("2.000000"), Decimal("99.00"), "{}"),
        ]:
            ca = crea_commessa_attivita(
                cur, t, segment_key=seg, articolo_id=t["articolo_id"],
                quantita=qta, prezzo=prezzo, meta=meta,
            )
            af[nome] = crea_attivita_fatturabile(
                cur, t, ca_id=ca, lock_batch_id=lock_batch_id,
                quantita=qta, prezzo=prezzo, meta=meta,
            )

        # I due componenti di kit: stesso articolo del padre non e' possibile
        # (uno solo per istanza, R9), quindi si distinguono per segment_key.
        cur.execute(
            "SELECT id FROM catalogo.articoli WHERE attivo IS TRUE AND id <> %s "
            "AND uom_id = %s LIMIT 2", [t["articolo_id"], t["uom_id"]],
        )
        altri = [r[0] for r in cur.fetchall()]
        kit_ok = len(altri) >= 1
        if kit_ok:
            for nome, art, esposizione in [("K1", altri[0], "VALORIZZATO"),
                                           ("K2", t["articolo_id"], "DESCRITTIVO")]:
                seg = kit_meta.segment_key_componente(kit_padre_segment, art)
                # Il meta come lo scrive il push: padre, modo di esposizione e
                # quantita' e UoM della RIGA PADRE (R-BE-B2). Senza le ultime
                # due il servizio si ferma, ed e' giusto: nessun ripiego.
                # Un kit, componenti a 2 ciascuno; la UoM e' quella del padre
                # (l'articolo del template).
                meta_kit = {
                    kit_meta.META_KEY_COMPONENTE_DI: str(t["articolo_id"]),
                    kit_meta.META_KEY_ESPOSIZIONE: esposizione,
                    kit_meta.META_KEY_QTA_PADRE: str(KIT_QTA_PADRE),
                    kit_meta.META_KEY_UOM_PADRE: t["uom_id"],
                }
                ca = crea_commessa_attivita(
                    cur, t, segment_key=seg, articolo_id=art,
                    quantita=Decimal("2.000000"), prezzo=Decimal("5.00"),
                    meta=json.dumps(meta_kit),
                )
                # `segment_key` va anche nel meta dell'AF: e' da li' che il
                # servizio riconosce il componente (il push lo copia sempre).
                meta_af = json.dumps({**meta_kit, kit_meta.META_KEY_SEGMENT_KEY: seg})
                af[nome] = crea_attivita_fatturabile(
                    cur, t, ca_id=ca, lock_batch_id=lock_batch_id,
                    quantita=Decimal("2.000000"), prezzo=Decimal("5.00"),
                    meta=meta_af,
                )

        print(f"lotto {lotto_id}, {len(af)} attivita' fatturabili create\n")

    # --- ESECUZIONE del percorso reale --------------------------------------
    elaborate = FattureRigheService().generate_fatture_righe(lotto_id)
    print(f"generate_fatture_righe -> {elaborate} attivita' elaborate\n")

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, r.riga_nr, r.qta, r.prezzo_unitario, r.imponibile_riga,
                   r.sorgente_tipo_id, r.sorgente_uid, r.kit_key,
                   r.kit_esposizione, r.kit_articolo_padre_id,
                   r.kit_descrizione_padre, r.meta, r.fattura_id,
                   r.kit_qta, r.kit_uom_id
              FROM vendite.fatture_righe r
              JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id = r.fattura_id
             WHERE lf.lotto_id = %s
             ORDER BY r.riga_nr
            """,
            [lotto_id],
        )
        # Il driver restituisce `jsonb` come stringa: stessa coercion che
        # applica il repository (e' il difetto che questo smoke ha scoperto).
        righe = [tuple(r[:11]) + (coerce_jsonb_dict(r[11]), r[12], r[13], r[14])
                 for r in cur.fetchall()]
        for r in righe:
            print(f"  riga {r[1]}: qta={r[2]} x {r[3]} = {r[4]} | kit={r[7]} "
                  f"| n_attivita={r[11].get('n_attivita')}")
        print()

        # 1) aggregazione
        aggregata = [r for r in righe if r[11].get("n_attivita") == 2 and r[7] is None]
        check("1) due attivita' stessa chiave -> UNA riga", len(aggregata) == 1,
              f"righe aggregate trovate: {len(aggregata)}")

        if aggregata:
            ag = aggregata[0]
            # 7) somma esatta: 0.333333 + 0.333333 = 0.666666, NON 0.667
            check("7) quantita' aggregata non arrotondata",
                  ag[2] == Decimal("0.666666"), f"qta={ag[2]}")
            # 2) sorgenti
            check("2) riga aggregata senza sorgente singola",
                  ag[5] is None and ag[6] is None)
            # 5) importo dal trigger
            atteso = (ag[2] * ag[3]).quantize(Decimal("0.01"))
            check("5) importo calcolato dal DB", ag[4] == atteso,
                  f"{ag[4]} atteso {atteso}")

            cur.execute(
                "SELECT id, fattura_riga_id, fatturato, stato_esecuzione "
                "FROM vendite.attivita_fatturabili WHERE id = ANY(%s) ORDER BY id",
                [[af["A1"], af["A2"]]],
            )
            att = cur.fetchall()
            check("3) entrambe le attivita' puntano alla riga",
                  len({a[1] for a in att}) == 1 and att[0][1] == ag[0],
                  f"fattura_riga_id={[a[1] for a in att]}")
            check("4) attivita' fatturate e COMPLETED",
                  all(a[2] and a[3] == "COMPLETED" for a in att),
                  str([(a[2], a[3]) for a in att]))

        # 6) prezzo diverso -> riga separata
        prezzi = {r[3] for r in righe if r[7] is None}
        check("6) prezzo diverso -> riga separata",
              Decimal("99.00") in prezzi and Decimal("10.00") in prezzi,
              f"prezzi distinti: {sorted(prezzi)}")

        # 8) snapshot kit
        if kit_ok:
            kit_righe = [r for r in righe if r[7] is not None]
            check("8) snapshot kit congelato sulla riga",
                  len(kit_righe) == 2
                  and all(r[8] is not None and r[9] is not None
                          and r[10] is not None for r in kit_righe),
                  f"righe kit: {len(kit_righe)}")

            # 9) la vista di esposizione
            fattura_id = righe[0][12]
            cur.execute(
                "SELECT tipo_riga, count(*) FROM vendite.vw_fattura_righe_esposte "
                "WHERE fattura_id = %s GROUP BY tipo_riga ORDER BY 1", [fattura_id],
            )
            esposizione = dict(cur.fetchall())
            check("9) la vista produce KIT_PADRE + KIT_COMPONENTE",
                  esposizione.get("KIT_PADRE") == 1
                  and esposizione.get("KIT_COMPONENTE") == 2,
                  str(esposizione))
            check("8c) quantita' e UoM del padre congelate dal meta",
                  all(r[13] == KIT_QTA_PADRE and r[14] == t["uom_id"] for r in kit_righe),
                  str([(r[13], r[14]) for r in kit_righe]))
            check("8b) il modo e' congelato col suo codice",
                  sorted(r[8] for r in kit_righe) == ["DESCRITTIVO", "VALORIZZATO"],
                  str(sorted(r[8] for r in kit_righe)))

            # 11) il valorizzato fuori dal padre, legato al kit
            cur.execute(
                "SELECT tipo_riga, esposizione, imponibile, kit_riga_nr, riga_nr "
                "FROM vendite.vw_fattura_righe_esposte "
                "WHERE fattura_id = %s AND kit_key IS NOT NULL", [fattura_id],
            )
            vista = cur.fetchall()
            padre = [v for v in vista if v[0] == "KIT_PADRE"]
            valorizzati = [v for v in vista if v[1] == "VALORIZZATO"]
            descrittivi = [v for v in vista if v[1] == "DESCRITTIVO"]
            check("11) valorizzato con importo, descrittivo senza, padre = descrittivo",
                  len(padre) == 1 and len(valorizzati) == 1 and len(descrittivi) == 1
                  and valorizzati[0][2] is not None and descrittivi[0][2] is None
                  and padre[0][2] == next(r[4] for r in kit_righe if r[8] == "DESCRITTIVO")
                  and valorizzati[0][3] == padre[0][3],
                  str(vista))

            # 10) invariante R18: il totale non dipende dall'esposizione.
            cur.execute(
                "SELECT (SELECT COALESCE(sum(imponibile_riga),0) FROM vendite.fatture_righe"
                "          WHERE fattura_id=%s),"
                "       (SELECT COALESCE(sum(imponibile),0) FROM vendite.vw_fattura_righe_esposte"
                "          WHERE fattura_id=%s)", [fattura_id, fattura_id],
            )
            da_tabella, da_vista = cur.fetchone()
            check("10) totale invariante fra tabella e vista", da_tabella == da_vista,
                  f"tabella={da_tabella} vista={da_vista}")
        else:
            print("  SKIP 8-10) nessun secondo articolo disponibile per il kit")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
