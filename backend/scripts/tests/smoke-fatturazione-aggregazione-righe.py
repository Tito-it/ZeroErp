# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.db._helpers import coerce_jsonb_dict, rows_to_list

from apps.vendite.services import _kit_meta as kit_meta
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    chiave_di_commessa,
    costruisci_base_fatturazione,
    crea_articolo_di_prova,
    crea_attivita_di_commessa,
    crea_lotto_di_prova,
)


FAIL: list[str] = []

# Quanti kit rappresentano le attivita' componente dello smoke (meta `qta_padre`).
KIT_QTA_PADRE = Decimal("1")


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


print("\n=== SMOKE aggregazione righe fattura (percorso Python reale) ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore: `vendite.fatturazione_lotti` e `vendite.fatture`
        # sono RLS. Senza GUC le query tornano 0 righe e lo smoke mentirebbe.
        apri_contesto_smoke(cur)

        # La base della fixture si COSTRUISCE dalle radici di prova
        # (brief-be-utenti-di-sviluppo T-7b): niente attivita' esistente da
        # copiare, che su un database nuovo non c'e'.
        marker = uuid.uuid4().hex[:8]
        t = costruisci_base_fatturazione(cur, marker=marker)
        print(f"base: commessa {t['commessa_id']}, articolo {t['articolo_id']}, "
              f"BA {t['billing_account_id']}\n")

        # --- lotto dedicato -------------------------------------------------
        lock_batch_id = str(uuid.uuid4())
        lotto_id = crea_lotto_di_prova(cur, t, codice=f"SMOKE-{marker}", lock_batch_id=lock_batch_id)

        # --- fixture: 5 attivita' -------------------------------------------
        # A1 e A2 condividono la chiave di gruppo -> devono fondersi in UNA riga.
        # A3 ha prezzo diverso -> riga separata (il prezzo sta nella chiave).
        # K1 e K2 sono componenti dello stesso kit -> riga padre + componenti.
        # ⭐ Ogni chiave nomina il documento della provenienza, qui la commessa
        #    (giro C.3 di brief-db-sorgente-documento-e-riga): l'etichetta dello
        #    smoke ne e' il suffisso. Anche la chiave del padre del kit, da cui
        #    i componenti ereditano la loro (`#CMP:`).
        def _chiave(etichetta: str) -> str:
            return chiave_di_commessa(cur, t, t["commessa_id"], etichetta)

        kit_padre_segment = _chiave(f"SMOKE:{marker}:R:1")
        af = {}
        for nome, seg, qta, prezzo, meta in [
            ("A1", _chiave(f"SMOKE:{marker}:A1"), Decimal("0.333333"), Decimal("10.00"), "{}"),
            ("A2", _chiave(f"SMOKE:{marker}:A2"), Decimal("0.333333"), Decimal("10.00"), "{}"),
            ("A3", _chiave(f"SMOKE:{marker}:A3"), Decimal("2.000000"), Decimal("99.00"), "{}"),
        ]:
            _ca, af[nome] = crea_attivita_di_commessa(
                cur, t, segment_key=seg, lock_batch_id=lock_batch_id,
                quantita=qta, prezzo=prezzo, meta=meta,
            )

        # I due componenti di kit: stesso articolo del padre non e' possibile
        # (uno solo per istanza, R9), quindi si distinguono per segment_key.
        # Il secondo articolo si COSTRUISCE, con la UoM del padre: pescarlo
        # dal catalogo dava un articolo qualunque, o nessuno su un database
        # nuovo (brief-be-utenti-di-sviluppo T-7b).
        altro, _uom = crea_articolo_di_prova(cur, prefisso="SMOKE-KIT", uom_id=t["uom_id"])
        for nome, art, esposizione in [("K1", altro, "VALORIZZATO"),
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
            # `segment_key` va anche nel meta dell'AF: e' da li' che il
            # servizio riconosce il componente (il push lo copia sempre).
            _ca, af[nome] = crea_attivita_di_commessa(
                cur, t, segment_key=seg, lock_batch_id=lock_batch_id,
                articolo_id=art, quantita=Decimal("2.000000"), prezzo=Decimal("5.00"),
                meta=json.dumps(meta_kit),
                meta_attivita=json.dumps({**meta_kit, kit_meta.META_KEY_SEGMENT_KEY: seg}),
            )

        print(f"lotto {lotto_id}, {len(af)} attivita' fatturabili create\n")

    # --- ESECUZIONE del percorso reale --------------------------------------
    elaborate = FattureRigheService().generate_fatture_righe(lotto_id)
    print(f"generate_fatture_righe -> {elaborate} attivita' elaborate\n")

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, r.riga_nr, r.qta, r.prezzo_unitario, r.imponibile_riga,
                   r.kit_key,
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
        # ⭐ Righe per NOME, col lettore comune: un indice di posizione si
        #    sposta in silenzio quando la SELECT perde o guadagna una colonna
        #    (e' successo col ritiro delle `sorgente_*`, G-4).
        # Il driver puo' restituire `jsonb` come stringa: stessa coercion che
        # applica il repository (e' il difetto che questo smoke ha scoperto).
        righe = rows_to_list(cur)
        for r in righe:
            r["meta"] = coerce_jsonb_dict(r["meta"])
        for r in righe:
            print(f"  riga {r['riga_nr']}: qta={r['qta']} x {r['prezzo_unitario']}"
                  f" = {r['imponibile_riga']} | kit={r['kit_key']}"
                  f" | n_attivita={r['meta'].get('n_attivita')}")
        print()

        # 1) aggregazione
        aggregata = [r for r in righe if r["meta"].get("n_attivita") == 2 and r["kit_key"] is None]
        check("1) due attivita' stessa chiave -> UNA riga", len(aggregata) == 1,
              f"righe aggregate trovate: {len(aggregata)}")

        if aggregata:
            ag = aggregata[0]
            # 7) somma esatta: 0.333333 + 0.333333 = 0.666666, NON 0.667
            check("7) quantita' aggregata non arrotondata",
                  ag["qta"] == Decimal("0.666666"), f"qta={ag['qta']}")
            # Il vecchio check 2 («riga aggregata senza sorgente singola») e'
            # ritirato: la riga di fattura non ha piu' colonne di provenienza
            # (G-4, brief-db-sorgente-documento-e-riga). La tracciabilita' la
            # prova il check 3, su attivita_fatturabili.fattura_riga_id.
            # 5) importo dal trigger
            atteso = (ag["qta"] * ag["prezzo_unitario"]).quantize(Decimal("0.01"))
            check("5) importo calcolato dal DB", ag["imponibile_riga"] == atteso,
                  f"{ag['imponibile_riga']} atteso {atteso}")

            cur.execute(
                "SELECT id, fattura_riga_id, fatturato, stato_esecuzione "
                "FROM vendite.attivita_fatturabili WHERE id = ANY(%s) ORDER BY id",
                [[af["A1"], af["A2"]]],
            )
            att = cur.fetchall()
            check("3) entrambe le attivita' puntano alla riga",
                  len({a[1] for a in att}) == 1 and att[0][1] == ag["id"],
                  f"fattura_riga_id={[a[1] for a in att]}")
            check("4) attivita' fatturate e COMPLETED",
                  all(a[2] and a[3] == "COMPLETED" for a in att),
                  str([(a[2], a[3]) for a in att]))

        # 6) prezzo diverso -> riga separata
        prezzi = {r["prezzo_unitario"] for r in righe if r["kit_key"] is None}
        check("6) prezzo diverso -> riga separata",
              Decimal("99.00") in prezzi and Decimal("10.00") in prezzi,
              f"prezzi distinti: {sorted(prezzi)}")

        # 8) snapshot kit
        kit_righe = [r for r in righe if r["kit_key"] is not None]
        check("8) snapshot kit congelato sulla riga",
              len(kit_righe) == 2
              and all(r["kit_esposizione"] is not None
                      and r["kit_articolo_padre_id"] is not None
                      and r["kit_descrizione_padre"] is not None for r in kit_righe),
              f"righe kit: {len(kit_righe)}")

        # 9) la vista di esposizione
        fattura_id = righe[0]["fattura_id"]
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
              all(r["kit_qta"] == KIT_QTA_PADRE and r["kit_uom_id"] == t["uom_id"]
                  for r in kit_righe),
              str([(r["kit_qta"], r["kit_uom_id"]) for r in kit_righe]))
        check("8b) il modo e' congelato col suo codice",
              sorted(r["kit_esposizione"] for r in kit_righe) == ["DESCRITTIVO", "VALORIZZATO"],
              str(sorted(r["kit_esposizione"] for r in kit_righe)))

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
              and padre[0][2] == next(r["imponibile_riga"] for r in kit_righe
                                      if r["kit_esposizione"] == "DESCRITTIVO")
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
    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
