# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository del risolutore IVA di riga. Wrapper unico su
#        `vendite.fn_resolve_iva_riga`, il GUSCIO che smista per paese
#        (D21) e ritorna il composito del trattamento fiscale (D18).
#
#        ⛔ RITORNA UNA LISTA, SEMPRE. La funzione e' set-returning: una
#        riga nel caso ordinario, DUE quando il plafond di un titolo
#        finisce a meta' riga (P2 del brief madre), nell'ordine
#        «prima la quota coperta dal titolo, poi il resto». Un
#        `fetchone()` qui non fallisce: prende la parte coperta e butta
#        il resto, cioe' applica un'esenzione a un imponibile che non ne
#        ha diritto. E' il motivo per cui questo modulo espone una lista
#        e non un dict.
#
#        ⚠️ La funzione e' SECURITY INVOKER e legge
#        `anagrafiche.soggetti_titoli_iva`, che ha la RLS: un chiamante
#        senza contesto emittente legge ZERO titoli e ottiene l'aliquota
#        ordinaria IN SILENZIO. Il guard sta nel service (P3), non qui.
#
#        Brief: docs/it/dev/work-in-progress/
#               brief-be-fe-iva-fase-3-consumatori-risolutore.md (F2-a)
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import rows_to_list

__all__ = ["IvaResolverRepository"]


# Le dieci colonne del composito, nell'ordine del `RETURNS TABLE`. Elencate
# e non `SELECT *` perche' l'ordine di un RETURNS TABLE e' contratto: se un
# giorno ne arriva un'undicesima, qui si vede.
_COLONNE = """
    r.quota,
    r.iva_id,
    r.aliquota,
    r.natura_codice,
    r.is_reverse_charge,
    r.esigibilita,
    r.split_payment,
    r.riferimento_normativo,
    r.origine,
    r.titolo_iva_id
"""

_SQL = f"""
    SELECT {_COLONNE}
      FROM vendite.fn_resolve_iva_riga(
               %s::uuid,      -- p_articolo_id
               %s::date,      -- p_data_riferimento
               %s::numeric,   -- p_imponibile
               %s::bigint,    -- p_billing_account_id
               %s::integer,   -- p_utility_id
               %s::uuid,      -- p_soggetto_id
               %s::bigint     -- p_emittente_fiscale_id
           ) AS r
"""  # noqa: S608 — colonne dalla costante di modulo _COLONNE, valori come parametri


class IvaResolverRepository:
    # Scopo: Invoca il guscio `vendite.fn_resolve_iva_riga` e restituisce la
    #        RIPARTIZIONE come lista di dict, nell'ordine prodotto dal DB.
    #
    #        ⭐ `imponibile=None` NON e' un caso degenere: e' la modalita'
    #        ANTEPRIMA, ed e' quella che i DOCUMENTI usano sempre (P1). Senza
    #        importo la spezzatura non e' calcolabile e la funzione non la
    #        inventa: torna UNA riga con `quota` a NULL, che dice quale
    #        trattamento vale «sul primo euro». E' cio' che rende vera la
    #        regola «sui documenti le righe non si spezzano»: non e' il BE a
    #        garantirla, e' il ramo che il DB gia' aveva.
    #
    #        ⚠️ I tre parametri di contesto del dispatch (paese emittente,
    #        paese cliente, cessione di beni) NON si passano: il guscio li
    #        DERIVA quando non arrivano (D20), e derivarli qui vorrebbe dire
    #        ripetere tre lookup in ogni punto che risolve l'IVA.
    def resolve(
        self,
        *,
        articolo_id: UUID | str,
        data_riferimento: date,
        imponibile: Decimal | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        soggetto_id: UUID | str | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                _SQL,
                [
                    str(articolo_id),
                    data_riferimento,
                    imponibile,
                    billing_account_id,
                    utility_id,
                    str(soggetto_id) if soggetto_id is not None else None,
                    emittente_fiscale_id,
                ],
            )
            return rows_to_list(cursor)
