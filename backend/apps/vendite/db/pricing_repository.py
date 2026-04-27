# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per il resolver prezzi v5 (pricing v5). Wrapper su:
#        - vendite.fn_resolve_prezzo_listino_v2 (resolver 3 stadi)
#        - vendite.fn_resolve_prezzo_composito (BoM ibrido A/B1/B2)
#        Gli errori di dominio sollevati dalle funzioni via
#        script.fn_log_and_raise_error (P0001) vengono propagati al service
#        che li traduce in ServiceError.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list


class PricingRepository:
    """Accesso DB al resolver prezzi v5."""

    # Scopo: Invoca `vendite.fn_resolve_prezzo_listino_v2` e restituisce la
    #        riga risolta come dict. La funzione DB ritorna 1 riga per match;
    #        se non esiste prezzo risolvibile solleva P0001 che bubble-a al
    #        service chiamante.
    def resolve_prezzo_listino_v2(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    prezzo_finale,
                    prezzo_base_snapshot,
                    tipo_variazione_applicata,
                    valore_variazione_applicata,
                    origine,
                    listino_id,
                    listino_versione_id,
                    listino_riga_id,
                    contratto_id,
                    promo_id,
                    categoria_cliente_listino_id,
                    categoria_cliente_id_snapshot,
                    classe_utenza_id_snapshot
                  FROM vendite.fn_resolve_prezzo_listino_v2(
                           %s::uuid, %s, %s, %s, %s, %s, %s
                       )
                """,
                [
                    str(articolo_id),
                    uom_id,
                    data_riferimento,
                    ba_id,
                    utility_id,
                    emittente_soggetto_ruolo_id,
                    classe_utenza_id,
                ],
            )
            result = row_to_dict(cursor)
        assert result is not None
        return result

    # Scopo: Invoca `vendite.fn_resolve_prezzo_composito`; ritorna N righe
    #        per articolo composito con componenti esposti (CASO A) oppure
    #        1 riga per articoli semplici / fallback (CASO B1/B2).
    def resolve_prezzo_composito(
        self,
        *,
        prodotto_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    componente_id,
                    uom_id,
                    prezzo_unitario,
                    iva_id,
                    descrizione_fattura,
                    esposto_in_fattura,
                    coeff_qta
                  FROM vendite.fn_resolve_prezzo_composito(
                           %s::uuid, %s, %s, %s, %s, %s, %s
                       )
                """,
                [
                    str(prodotto_id),
                    uom_id,
                    data_riferimento,
                    ba_id,
                    utility_id,
                    emittente_soggetto_ruolo_id,
                    classe_utenza_id,
                ],
            )
            return rows_to_list(cursor)
