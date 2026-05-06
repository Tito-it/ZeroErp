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
        # Wrapper LEFT JOIN sulle 4 entita' referenziate dal return della
        # funzione (listino, listino_versione, contratto, promo, categoria
        # cliente) per esporre codice/descrizione denormalizzati. Single
        # round-trip: la funzione DB resta unica source-of-truth, il JOIN
        # decora le colonne id senza alterare la semantica.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.prezzo_finale,
                    r.prezzo_base_snapshot,
                    r.tipo_variazione_applicata,
                    r.valore_variazione_applicata,
                    r.origine,
                    r.listino_id,
                    l.codice                AS listino_codice,
                    l.descrizione           AS listino_descrizione,
                    r.listino_versione_id,
                    lv.codice_versione      AS listino_versione_codice,
                    r.listino_riga_id,
                    r.contratto_id,
                    c.numero                AS contratto_numero,
                    r.promo_id,
                    pa.codice               AS promo_codice,
                    pa.descrizione          AS promo_descrizione,
                    r.categoria_cliente_listino_id,
                    r.categoria_cliente_id_snapshot,
                    cc.codice               AS categoria_cliente_codice,
                    cc.descrizione          AS categoria_cliente_descrizione,
                    r.classe_utenza_id_snapshot,
                    clu.descrizione         AS classe_utenza_descrizione
                  FROM vendite.fn_resolve_prezzo_listino_v2(
                           %s::uuid, %s, %s, %s, %s, %s, %s
                       ) r
                  LEFT JOIN vendite.listini l
                    ON l.id = r.listino_id
                  LEFT JOIN vendite.listini_versioni lv
                    ON lv.id = r.listino_versione_id
                  LEFT JOIN vendite.contratti c
                    ON c.id = r.contratto_id
                  LEFT JOIN vendite.promo_articoli pa
                    ON pa.id = r.promo_id
                  LEFT JOIN anagrafiche.categorie_clienti cc
                    ON cc.id = r.categoria_cliente_id_snapshot
                  LEFT JOIN config.classi_utenze clu
                    ON clu.id = r.classe_utenza_id_snapshot
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
