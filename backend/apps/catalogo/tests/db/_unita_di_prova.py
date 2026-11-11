# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UN'UNITA' DI MISURA NUOVA PER UN TEST SUL DB VERO, dalla porta
#        dell'applicazione (`catalogo_service.fn_create_unita_misura`):
#        `crea_unita_di_prova(sigla, sfx, tipologia="MASSA") -> id`. Nata nella
#        transazione del test, per costruzione non ha mappature ne'
#        conversioni: niente dipende dalle unita' presenti.
# Note: estratto il 2026-11-11 (regola del 2, ok Tid) da tre copie gia'
#       DIVERGENTI: `test_vincoli_catalogo_db`, `test_uom_storia_db`,
#       `vendite/.../test_listino_uom_compatibile_db`.
#       ⛔ Tipologia assente = test ROSSO, non saltato. Le tipologie sono un
#       seed di `80_data` (`catalogo/uom_tipi.csv`), cioe' contratto: uno
#       `SkipTest` (due copie su tre) passava a vuoto su un DB a cui il seed
#       manca, cioe' proprio quando c'e' da accorgersene.
#       ⚠️ Codice = sigla + i primi 6 caratteri del suffisso: `codice` e'
#       varchar(20), e un suffisso lungo non deve far cadere il test sulla
#       lunghezza invece che sulla regola.
#       Va chiamata dentro una transazione annullata (`apri_transazione_annullata`).
# ------------------------------------------------------------
from __future__ import annotations

from django.db import connection

from apps.catalogo.services import catalogo_service


def crea_unita_di_prova(sigla: str, sfx: str, *, tipologia: str = "MASSA") -> int:
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM catalogo.uom_tipi WHERE codice_interno = %s", [tipologia])
        tipo = cur.fetchone()
    if tipo is None:
        raise AssertionError(f"tipologia {tipologia} assente dal seed (catalogo/uom_tipi.csv)")
    riga = catalogo_service.fn_create_unita_misura(
        {"codice": f"{sigla}{sfx[:6]}", "descrizione": f"Prova {sigla}", "tipo_uom_id": tipo[0]},
    )
    return int(riga["id"])
