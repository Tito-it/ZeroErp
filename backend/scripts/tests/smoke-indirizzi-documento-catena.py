# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — CATENA DI RISOLUZIONE INDIRIZZI DOCUMENTO sul percorso reale:
#         `script.fn_resolve_indirizzo_documento` (Fase 0 del piano BE/FE
#         satelliti fattura, 2026-07-31). Dal 2026-10-12 il backend non la
#         chiama piu': la usa il DB, nel building block dello slot di default
#         `vendite.fn_doc_indirizzo_default` (brief-db-indirizzi-documento-
#         seguono-il-cliente). Lo smoke la interroga direttamente.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-indirizzi-documento-catena.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE. Il ripuntamento cambia il **comportamento** di cinque domini in
# esercizio (preventivi, offerte, ordini, DDT, contratti): fino a ieri la catena
# Python preferiva l'indirizzo **generico** e ignorava l'istanza del documento
# (`ORDER BY ... istanza_utility_id NULLS FIRST` — rilievo C-14c del piano DB),
# adesso vince quello **dell'istanza**. I test unitari verificano il cablaggio
# con un repo mockato; solo qui si vede quale indirizzo esce davvero dal DB.
#
# COSA PRESIDIA
#   - la catena a DUE layer (RUOLO con aggancio origine → SOGGETTO senza);
#   - la **precedenza per istanza**, cioè il caso che col vecchio codice
#     rispondeva l'indirizzo sbagliato (caso 3: è la dimostrazione del difetto);
#   - che i cinque domini condividano la stessa risoluzione (nessuno resta
#     indietro con una catena propria).
#
# IDEMPOTENZA. Tutto in transazione con `set_rollback(True)`: gli indirizzi di
# prova non persistono. Rieseguibile all'infinito.
#
# Indice test (1..7):
#   1  la funzione DB esiste con la firma attesa
#   2  layer RUOLO: snapshot canonico + origine_indirizzo_id valorizzato
#   3  PRECEDENZA ISTANZA: con due indirizzi dello stesso tipo vince quello
#      dell'istanza del documento (col vecchio codice vinceva il generico);
#      3b documento senza istanza -> generico; 3c istanza DIVERSA -> generico
#      (filtro di uguaglianza, non solo ordinamento)
#   4  layer SOGGETTO: nessun indirizzo di ruolo -> snapshot senza origine_indirizzo_id
#   5  tipo non risolvibile -> zero righe (nessun errore: decide il chiamante)
#   6  i 5 domini dichiarano il documento per lo slot di default DB
# ------------------------------------------------------------

from django.db import connection, transaction

from apps.core.db._helpers import coerce_jsonb_dict, row_to_dict
from apps.config.sorgenti import (
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from scripts.tests._smoke_indirizzo import crea_indirizzo_libero_ruolo

from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from scripts.tests._smoke_contesto import apri_contesto_smoke, seleziona_emittente_di_prova

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


print("\n=== SMOKE catena indirizzi documento (RUOLO -> SOGGETTO, per istanza) ===\n")

# --- 1) la funzione esiste con la firma attesa ---------------------------
with connection.cursor() as cur:
    cur.execute(
        """
        SELECT pg_get_function_arguments(p.oid), pg_get_function_result(p.oid)
          FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'script' AND p.proname = 'fn_resolve_indirizzo_documento'
        """
    )
    row = cur.fetchone()
check("1) fn_resolve_indirizzo_documento presente", row is not None)
if row is None:
    raise SystemExit("Prerequisito DB assente: il ripuntamento non è collaudabile.")
print(f"    args: {row[0]}\n    ret : {row[1]}\n")



# Scopo: la catena, interrogata come la interroga il building block DB.
def _risolvi(*, soggetto_ruolo_id, istanza_utility_id, tipo_codice):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT snapshot, origine_indirizzo_id, origine_soggetto_ruolo_id
              FROM script.fn_resolve_indirizzo_documento(%s, %s, %s)
            """,
            [soggetto_ruolo_id, istanza_utility_id, tipo_codice],
        )
        row = row_to_dict(cur)
    if row is not None:
        row["snapshot"] = coerce_jsonb_dict(row.get("snapshot"))
    return row


with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore (le anagrafiche non sono RLS, ma i documenti sì:
        # lo smoke resta coerente con il percorso applicativo).
        apri_contesto_smoke(cur)

        # Fixture: un soggetto_ruolo CLIENTE con billing account e istanza,
        # COSTRUITO dentro la transazione annullata dal builder delle fixture
        # (`dbops.fn_pgtap_crea_cliente_ba`). ⛔ Fino al 2026-10-18 lo smoke
        # prendeva il primo BA dei dati reali e ne cancellava gli indirizzi: un
        # documento fuori bozza che li usava (un contratto annullato) lo fermava
        # col lock delle righe, e l'esito dipendeva da cosa c'era su dbdev.
        # Sull'emittente DI PROVA, scelto come lo sceglie l'operatore:
        # `dev.smoke` e' super admin in «Tutti gli emittenti», e un BA nuovo
        # ne vuole uno.
        _ef_id, ef_sr_id = seleziona_emittente_di_prova(cur)
        cur.execute(
            "SELECT soggetto_ruolo_id, istanza_utility_id"
            "  FROM dbops.fn_pgtap_crea_cliente_ba('smoke catena indirizzi', NULL, %s)",
            [ef_sr_id],
        )
        sr_id, istanza_id = cur.fetchone()
        # Un'ALTRA istanza, per la controprova cross-istanza (3c): risolvere per
        # lei non deve pescare l'indirizzo dell'istanza sopra.
        cur.execute(
            "SELECT istanza_utility_id"
            "  FROM dbops.fn_pgtap_crea_cliente_ba('smoke catena indirizzi, altra istanza', NULL, %s)",
            [ef_sr_id],
        )
        altra_istanza_id = cur.fetchone()[0]
        print(f"fixture: soggetto_ruolo {sr_id}, istanza {istanza_id}, "
              f"altra istanza {altra_istanza_id}\n")

        # ⚠️ Il tipo NON si può fissare a mano: `anagrafiche.indirizzi` ha il
        # guard `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`, che ammette
        # solo i tipi configurati in `config.tipi_ruolo_tipi_indirizzo` per il
        # tipo_ruolo del soggetto. Per il ruolo cliente (tipo_ruolo 1) `CON`
        # NON è ammesso — lo è `FATT`, che per la fattura è anche il tipo che
        # conta. Si preferisce FATT e si ripiega sul primo ammesso.
        cur.execute(
            """
            SELECT ti.id, ti.codice_interno
              FROM config.tipi_ruolo_tipi_indirizzo trti
              JOIN config.tipi_indirizzi ti ON ti.id = trti.tipo_indirizzo_id
              JOIN anagrafiche.soggetti_ruoli sr ON sr.tipo_ruolo_id = trti.tipo_ruolo_id
             WHERE sr.id = %s
             ORDER BY (ti.codice_interno <> 'FATT'), ti.id
             LIMIT 1
            """,
            [sr_id],
        )
        tipo = cur.fetchone()
        if not tipo:
            raise SystemExit(
                "Nessun tipo indirizzo ammesso per il ruolo di questo BA: "
                "config.tipi_ruolo_tipi_indirizzo incompleta.")
        tipo_id, tipo_codice = tipo
        print(f"    tipo indirizzo usato: {tipo_codice} (id {tipo_id})\n")

        # Situazione pulita per quel tipo su questo ruolo: le righe eventuali si
        # rimuovono dentro la transazione (rollback finale, modifica effimera).
        cur.execute(
            "DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s"
            "   AND tipo_indirizzo_id = %s",
            [sr_id, tipo_id],
        )

        # --- 2) layer RUOLO: indirizzo GENERICO (istanza NULL) --------------
        # Un indirizzo NON normalizzato, nella forma che decide lo stato
        # (BB `_smoke_indirizzo`). Lo snapshot lo compone la funzione DB.
        id_generico = crea_indirizzo_libero_ruolo(
            cur, soggetto_ruolo_id=sr_id, tipo_indirizzo_id=tipo_id,
            testo="Via GENERICA 1 - smoke",
        )

    risolto = _risolvi(
        soggetto_ruolo_id=sr_id, istanza_utility_id=istanza_id, tipo_codice=tipo_codice,
    )
    check("2) layer RUOLO risolve con origine agganciata",
          risolto is not None
          and risolto["origine_indirizzo_id"] == id_generico
          and isinstance(risolto["snapshot"], dict) and risolto["snapshot"],
          f"origine={risolto and risolto['origine_indirizzo_id']} "
          f"snapshot={risolto and list(risolto['snapshot'].keys())}")

    # --- 3) ⚠️ IL CASO CHE CONTA: precedenza dell'istanza ------------------
    # Si aggiunge l'indirizzo PER ISTANZA accanto al generico. Col vecchio SQL
    # del mixin (`istanza_utility_id NULLS FIRST`) avrebbe continuato a vincere
    # il generico: è esattamente il difetto C-14c.
    with connection.cursor() as cur:
        id_istanza = crea_indirizzo_libero_ruolo(
            cur, soggetto_ruolo_id=sr_id, tipo_indirizzo_id=tipo_id,
            testo="Via ISTANZA 99 - smoke", istanza_utility_id=istanza_id,
        )

    risolto = _risolvi(
        soggetto_ruolo_id=sr_id, istanza_utility_id=istanza_id, tipo_codice=tipo_codice,
    )
    check("3) PRECEDENZA ISTANZA: vince l'indirizzo dell'istanza, non il generico",
          risolto is not None and risolto["origine_indirizzo_id"] == id_istanza,
          f"scelto={risolto and risolto['origine_indirizzo_id']} "
          f"(istanza={id_istanza}, generico={id_generico})")

    # Controprova: un documento SENZA istanza deve prendere il generico.
    risolto_senza = _risolvi(
        soggetto_ruolo_id=sr_id, istanza_utility_id=None, tipo_codice=tipo_codice,
    )
    check("3b) documento senza istanza -> indirizzo generico",
          risolto_senza is not None
          and risolto_senza["origine_indirizzo_id"] == id_generico,
          f"scelto={risolto_senza and risolto_senza['origine_indirizzo_id']}")

    # Controprova CROSS-ISTANZA: risolvendo per un'istanza DIVERSA, l'indirizzo
    # dell'istanza 3 non deve essere pescato — deve rispondere il generico.
    # È il test del filtro di UGUAGLIANZA (il 3 prova solo l'ordinamento):
    # senza, un `OR istanza IS NOT NULL` sbagliato passerebbe il caso 3
    # e servirebbe l'indirizzo di un'altra fornitura.
    if altra_istanza_id is not None:
        risolto_altra = _risolvi(
            soggetto_ruolo_id=sr_id, istanza_utility_id=altra_istanza_id,
            tipo_codice=tipo_codice,
        )
        check("3c) istanza diversa -> generico, MAI l'indirizzo dell'altra istanza",
              risolto_altra is not None
              and risolto_altra["origine_indirizzo_id"] == id_generico,
              f"scelto={risolto_altra and risolto_altra['origine_indirizzo_id']} "
              f"(l'indirizzo dell'istanza {istanza_id} è {id_istanza})")
    else:
        print("  SKIP 3c) una sola istanza nel DB: controprova cross-istanza "
              "non esercitabile")

    # --- 4) layer SOGGETTO: nessun indirizzo di RUOLO ---------------------
    with connection.cursor() as cur:
        cur.execute(
            "DELETE FROM anagrafiche.indirizzi WHERE id = ANY(%s)",
            [[id_generico, id_istanza]],
        )
        # Un tipo presente sul layer SOGGETTO ma SENZA righe sul layer RUOLO:
        # se il ruolo avesse ancora un indirizzo di quel tipo, la catena
        # risponderebbe (giustamente) dal RUOLO e l'asserzione «origine NULL»
        # sarebbe un falso rosso dipendente dai dati. ORDER BY per determinismo:
        # un LIMIT 1 nudo cambia esito da un run all'altro.
        cur.execute(
            """
            SELECT ti.codice_interno
              FROM anagrafiche.vw_indirizzi_resolved_soggetto v
              JOIN config.tipi_indirizzi ti ON ti.id = v.tipo_indirizzo_id
              JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = v.soggetto_id
             WHERE sr.id = %s
               AND NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi i
                                WHERE i.soggetto_ruolo_id = sr.id
                                  AND i.tipo_indirizzo_id = ti.id)
             ORDER BY ti.id
             LIMIT 1
            """,
            [sr_id],
        )
        tipo_sog = cur.fetchone()

    if tipo_sog:
        risolto = _risolvi(
            soggetto_ruolo_id=sr_id, istanza_utility_id=istanza_id,
            tipo_codice=tipo_sog[0],
        )
        check("4) layer SOGGETTO: snapshot senza origine_indirizzo_id",
              risolto is not None
              and risolto["origine_indirizzo_id"] is None
              and risolto["origine_soggetto_ruolo_id"] == sr_id,
              f"tipo={tipo_sog[0]} origine_ind={risolto and risolto['origine_indirizzo_id']}")
    else:
        print("  SKIP 4) il soggetto non ha indirizzi propri: layer SOGGETTO non "
              "esercitabile su questi dati")

    # --- 5) tipo non risolvibile -> None (nessun errore) ------------------
    # ⚠️ Non basta cancellare gli indirizzi di RUOLO: se il soggetto ha il suo
    # (caso 4), la catena risponde comunque — ed è il comportamento giusto.
    # Serve un tipo che NESSUNO dei due layer possiede.
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT ti.codice_interno
              FROM config.tipi_ruolo_tipi_indirizzo trti
              JOIN config.tipi_indirizzi ti ON ti.id = trti.tipo_indirizzo_id
              JOIN anagrafiche.soggetti_ruoli sr ON sr.tipo_ruolo_id = trti.tipo_ruolo_id
             WHERE sr.id = %s
               AND NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi i
                                WHERE i.soggetto_ruolo_id = sr.id
                                  AND i.tipo_indirizzo_id = ti.id)
               AND NOT EXISTS (SELECT 1 FROM anagrafiche.vw_indirizzi_resolved_soggetto v
                                WHERE v.soggetto_id = sr.soggetto_id
                                  AND v.tipo_indirizzo_id = ti.id)
             ORDER BY ti.id
             LIMIT 1
            """,
            [sr_id],
        )
        tipo_orfano = cur.fetchone()

    if tipo_orfano:
        risolto = _risolvi(
            soggetto_ruolo_id=sr_id, istanza_utility_id=istanza_id,
            tipo_codice=tipo_orfano[0],
        )
        check("5) nessuna fonte -> None, nessun errore", risolto is None,
              f"tipo={tipo_orfano[0]} ritornato={risolto}")
    else:
        print("  SKIP 5) questo soggetto ha un indirizzo per ogni tipo ammesso: "
              "il caso «nessuna fonte» non è esercitabile su questi dati")

    transaction.set_rollback(True)

# --- 6) lo slot di default e' del DB, per tutti e 5 i domini ---------------
# Il documento e' il codice della SORGENTE (grammatica unica, brief-db-
# grammatica-unica-documenti §11.4): dal 2026-10-19 non piu' i codici corti
# OFFERTA/ORDINE/DDT, che qui restavano scritti a mano e davano rosso.
repos = {
    SORGENTE_PREVENTIVO: PreventiviRepository,
    SORGENTE_OFFERTA_COMMERCIALE: OfferteRepository,
    SORGENTE_ORDINE_VENDITA: OrdiniRepository,
    SORGENTE_DDT_VENDITA: DdtRepository,
    SORGENTE_CONTRATTO: ContrattiRepository,
}
# Attributi DI CLASSE del mixin: si leggono dalla classe, senza istanziare.
errati = {n: getattr(cls, "_indirizzi_documento", None)
          for n, cls in repos.items()
          if getattr(cls, "_indirizzi_documento", None) != n}
check("6) i 5 domini dichiarano il documento per fn_doc_indirizzo_default", not errati,
      str(errati) if errati else "preventivo, offerta, ordine, ddt, contratto")

print("\n=== ROLLBACK eseguito: nessun indirizzo di prova persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
