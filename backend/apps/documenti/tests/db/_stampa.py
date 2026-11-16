# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il controllo «una stampa nasce col suo PDF principale» si giudica
#        al COMMIT (constraint trigger differito
#        `trg_documenti_generati_a10_guard_file_principale_ins`, giro 1 di
#        brief-db-revisione-documenti, D20): il servizio scrive prima la
#        stampa e poi il PDF, nella stessa transazione.
#        ⚠️ Le fixture `dbops.fn_pgtap_*` chiudono con `SET CONSTRAINTS ALL
#        IMMEDIATE`: un test che le chiama nella stessa transazione in cui poi
#        stampa vedrebbe il controllo scattare sull'INSERT della stampa, prima
#        del PDF — una rottura che in produzione non esiste (nessun percorso
#        dell'applicazione rende i vincoli immediati, verificato sul catalogo
#        il 2026-11-16). Qui si riporta quel solo vincolo al suo momento.
#        Regola del 2: i quattro test della stampa sul DB vero.
#
#        `tipo_asset_che_ammette`: il tipo di risorsa che ammette un formato,
#        letto dall'abbinamento del DB (giro 2, D15): il DB rifiuta la risorsa
#        in un formato che il suo tipo non ammette
#        (E_DOCUMENTI_FORMATO_NON_AMMESSO). Regola del 2, ok Tid 2026-11-16:
#        era la stessa query in tre test sul DB vero.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

VINCOLO_FILE_PRINCIPALE = "documenti.trg_documenti_generati_a10_guard_file_principale_ins"


# Scopo: Il controllo del PDF principale torna differito, come nella
#        transazione di una richiesta vera. Da chiamare DOPO le fixture pgTAP.
def giudica_la_stampa_al_commit(cur: Any) -> None:
    cur.execute(f"SET CONSTRAINTS {VINCOLO_FILE_PRINCIPALE} DEFERRED")


# Scopo: L'id di un tipo di risorsa che ammette il formato `mime`, dal seed
#        degli abbinamenti (contratto, non popolazione). Nessun tipo e' un
#        seed rotto: il test si ferma qui, col motivo, e non piu' avanti con
#        un errore del DB che non lo dice.
def tipo_asset_che_ammette(cur: Any, mime: str) -> int:
    cur.execute(
        """
        SELECT ab.asset_tipo_id
          FROM documenti.tipi_asset_documento_formati ab
          JOIN config.formati_file ff ON ff.id = ab.formato_file_id
         WHERE ff.mime_type = %s
         ORDER BY ab.asset_tipo_id
         LIMIT 1
        """,
        [mime],
    )
    riga = cur.fetchone()
    if riga is None:
        raise AssertionError(f"nessun tipo di risorsa ammette {mime!r}: il seed degli abbinamenti manca")
    return int(riga[0])
