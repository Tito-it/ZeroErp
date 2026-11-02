# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per l'endpoint diagnostico pricing
#        (POST /api/v1/vendite/pricing/diagnose/). Esegue 4 check
#        read-only sui 3 stadi del resolver per spiegare all'admin
#        perche' il resolver fallisce e quali asset configurare.
# ------------------------------------------------------------

from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection

from apps.core.db._helpers import row_to_dict


# Repository diagnostico pricing v5: 4 query lean read-only.
# Single round-trip per check, nessuna mutazione, nessun side-effect.
class PricingDiagnoseRepository:

    # Scopo: Restituisce dati BA + categoria collegata (codice + flag
    #        partecipa_promo). None se il BA non esiste. Usato per il check
    #        radice ("BA esiste? ha categoria?") e per ramificare gli stadi.
    def get_ba_categoria(self, ba_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                ba.id              AS ba_id,
                ba.categoria_cliente_id,
                cc.codice          AS categoria_codice,
                cc.descrizione     AS categoria_descrizione,
                COALESCE(cc.partecipa_promo, false) AS categoria_partecipa_promo
              FROM anagrafiche.billing_account ba
              LEFT JOIN anagrafiche.categorie_clienti cc
                ON cc.id = ba.categoria_cliente_id
             WHERE ba.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ba_id)])
            return row_to_dict(cursor)

    # Scopo: STADIO 0. Esiste promo articolo attiva per (articolo, uom)
    #        in data riferimento? Ritorna codice/descrizione della prima
    #        promo applicabile per messaggio leggibile, o None se nessuna.
    def find_promo_attiva(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id, codice, descrizione
              FROM vendite.promo_articoli
             WHERE articolo_id = %s::uuid
               AND uom_id = %s
               AND COALESCE(attivo, true) = true
               AND validita @> %s::date
             ORDER BY id ASC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [str(articolo_id), int(uom_id), data_riferimento])
            return row_to_dict(cursor)

    # Scopo: STADIO 1. Esiste contratto ATTIVO per (BA, utility, data)?
    #        Ritorna numero + modalita pricing del contratto. None se nessuno.
    def find_contratto_attivo(
        self,
        *,
        ba_id: int,
        utility_id: int,
        data_riferimento: date,
    ) -> dict[str, Any] | None:
        # `modalita_pricing` non e' colonna DB ma astrazione UI: la deriviamo
        # da `listino_id IS NULL` (modalita C = no listino, righe con prezzo
        # negoziato; A/B = con listino, eventualmente con override righe).
        # Il caller distingue C da A/B per spiegare il caso "articolo non
        # negoziato in contratto C".
        sql = """
            SELECT
                c.id                AS contratto_id,
                c.numero            AS contratto_numero,
                c.listino_id        AS listino_id,
                CASE
                    WHEN c.listino_id IS NULL THEN 'C'
                    ELSE 'A_O_B'
                END                 AS modalita_pricing
              -- Filtro su c.utility_id nativo (NOT NULL): coerente con
              -- fn_resolve_prezzo_listino_v2. Non usare contratti_utilities
              -- (snapshot precontrattuale opzionale) per il lookup contratto.
              FROM vendite.contratti c
              JOIN config.stati_doc_contratti sdc
                ON sdc.id = c.stato_doc_contratto_id
             WHERE c.billing_account_id = %s
               AND c.utility_id = %s
               AND sdc.codice_interno = 'ATTIVO'
               AND c.validita @> %s::date
             ORDER BY c.id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ba_id), int(utility_id), data_riferimento])
            return row_to_dict(cursor)

    # Scopo: Per modalita C: l'articolo + uom e' realmente negoziato sulla
    #        riga del contratto? Necessario per spiegare il caso
    #        "contratto C ma articolo non in righe → resolver solleva
    #        E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C".
    def contratto_riga_articolo_negoziato(
        self,
        *,
        contratto_id: int,
        articolo_id: UUID | str,
    ) -> bool:
        # `contratti_righe` non ha colonna uom: la riga rappresenta l'accordo
        # sull'articolo a livello contratto. Basta verificare l'esistenza di
        # una riga (articolo, prezzo NOT NULL).
        sql = """
            SELECT EXISTS (
                SELECT 1
                  FROM vendite.contratti_righe r
                 WHERE r.contratto_id = %s
                   AND r.articolo_id = %s::uuid
                   AND r.prezzo_unitario IS NOT NULL
                   AND COALESCE(r.attivo, true) = true
            ) AS esiste
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contratto_id), str(articolo_id)])
            row = cursor.fetchone()
        return bool(row[0]) if row else False

    # Scopo: STADIO 2. Esiste riga matrice (categoria, utility, EF, classe)
    #        attiva alla data? Ritorna codice listino mappato e classe match
    #        (esatta o fallback NULL). None se nessuna mappa.
    #        Logica match: prova prima classe esatta (se classe_utenza_id
    #        fornito), poi fallback classe NULL — coerente con il resolver.
    def find_matrice_riga(
        self,
        *,
        categoria_cliente_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None,
        data_riferimento: date,
    ) -> dict[str, Any] | None:
        # Prima query: match esatto su classe (se valorizzata).
        if classe_utenza_id is not None:
            sql_exact = """
                SELECT
                    ccl.id              AS matrice_riga_id,
                    ccl.listino_id,
                    l.codice            AS listino_codice,
                    l.descrizione       AS listino_descrizione,
                    'ESATTO'            AS classe_match
                  FROM anagrafiche.categorie_clienti_listini ccl
                  JOIN vendite.listini l
                    ON l.id = ccl.listino_id
                 WHERE ccl.categoria_cliente_id = %s
                   AND ccl.utility_id = %s
                   AND ccl.emittente_soggetto_ruolo_id = %s
                   AND ccl.classe_utenza_id = %s
                   AND ccl.validita @> %s::date
                 LIMIT 1
            """
            with connection.cursor() as cursor:
                cursor.execute(sql_exact, [
                    int(categoria_cliente_id), int(utility_id),
                    int(emittente_soggetto_ruolo_id), int(classe_utenza_id),
                    data_riferimento,
                ])
                row = row_to_dict(cursor)
            if row is not None:
                return row

        # Fallback: classe NULL.
        sql_fallback = """
            SELECT
                ccl.id              AS matrice_riga_id,
                ccl.listino_id,
                l.codice            AS listino_codice,
                l.descrizione       AS listino_descrizione,
                'FALLBACK_NULL'     AS classe_match
              FROM anagrafiche.categorie_clienti_listini ccl
              JOIN vendite.listini l
                ON l.id = ccl.listino_id
             WHERE ccl.categoria_cliente_id = %s
               AND ccl.utility_id = %s
               AND ccl.emittente_soggetto_ruolo_id = %s
               AND ccl.classe_utenza_id IS NULL
               AND ccl.validita @> %s::date
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_fallback, [
                int(categoria_cliente_id), int(utility_id),
                int(emittente_soggetto_ruolo_id), data_riferimento,
            ])
            return row_to_dict(cursor)
