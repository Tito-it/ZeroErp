# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per tabelle `*_righe_componenti` del
#        modello unificato BoM 2026-05-13. Subset di metodi comuni a tutti
#        i sorgenti (preventivi/contratti/ordini/ddt) parametrizzato su
#        nome tabella e nome FK riga padre. Estrazione Fase H (refactor-
#        componenti.md).
#
#        NON copre:
#          - `init_componenti_riga` (chiama fn DB specifica per sorgente:
#            `fn_<sorgente>_riga_componenti_init`) → resta nelle sottoclassi
#          - `preview_componenti_riga` (idem, fn DB specifica) → idem
#          - `is_articolo_composito` (helper catalogo, eventualmente
#            estraibile in `catalogo_repository` in un secondo refactor)
#          - `vendite.listini_righe_componenti`: pattern diverso (tabula
#            rasa idempotente per immutabilita' v5, no CRUD singolo).
#            Vedi `ListiniRepository.upsert_bundle_componenti` per il
#            pattern specifico listini.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import execute_dynamic_update

# Whitelist colonne UPDATE su `*_righe_componenti`. Campi struttura immutabili
# (`componente_id`, `articolo_componente_id`, `coeff_qta_snapshot`, FK riga)
# non accettati. `quantita` ricalcolato dai trigger DB. Identico per tutti i
# sorgenti (le tabelle hanno schema simmetrico per design del modello
# unificato).
COMPONENTE_UPDATE_ALLOWED: frozenset[str] = frozenset({
    "prezzo_unitario",
    "iva_id",
    "uom_operativa_id",
    "factor_to_base",
    "qta_operativa",
    "origine_prezzo",
    "prezzo_resolver_context",
    "stato_approvazione_prezzo",
    "pratica_approvazione_prezzo_id",
    "meta",
    "ordine",
    "attivo",
})


class ComponentiRepositoryMixin:
    """Building block CRUD componenti BoM per repository sorgente.

    Le sottoclassi devono definire 2 attributi di classe:

    - ``_componenti_table_name``: nome FQN tabella (es.
      ``"vendite.preventivi_righe_componenti"``).
    - ``_componenti_fk_riga``: nome colonna FK alla riga padre (es.
      ``"riga_preventivo_id"`` o ``"riga_contratto_id"``).

    I metodi `init_componenti_riga` e `preview_componenti_riga` restano
    nelle sottoclassi perche' chiamano fn DB specifiche per sorgente.
    Sottoclassi tipiche includono anche `is_articolo_composito` (lookup
    `catalogo.articoli.is_composito`) e `get_emittente_sr_id_by_fiscale_id`
    (lookup `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`) — helper
    cross-dominio non specifici componenti BoM.
    """

    _componenti_table_name: str = ""  # da definire in sottoclasse
    _componenti_fk_riga: str = ""     # da definire in sottoclasse

    # Scopo: Lista componenti BoM di una riga padre con denormalizzazioni
    # articolo/uom/iva + flag `obbligatorio` / modo `esposizione_in_fattura` (JOIN
    # runtime su `articoli_componenti` — BoM immutabile per design, no
    # snapshot necessario).
    #
    # `solo_attivi=True` (default backcompat): solo componenti `attivo=TRUE`
    # (vista compatta retro-compatibile, expander tabella righe).
    # `solo_attivi=False`: include opzionali disattivati — usato dall'EDIT
    # panel per consentire riattivazione.
    def list_componenti_riga(
        self, riga_id: int, *, solo_attivi: bool = True,
    ) -> list[dict[str, Any]]:
        filtro_attivo = "AND c.attivo = TRUE" if solo_attivi else ""
        sql = f"""
            SELECT
                c.id,
                c.{self._componenti_fk_riga},
                c.articolo_componente_id,
                c.componente_id,
                a.codice                AS componente_codice,
                a.descrizione           AS componente_descrizione,
                c.coeff_qta_snapshot,
                c.quantita,
                c.uom_operativa_id,
                um.codice               AS uom_codice,
                c.factor_to_base,
                c.qta_operativa,
                c.prezzo_unitario,
                c.iva_id,
                iva.codice              AS iva_codice,
                iva.aliquota_iva        AS iva_aliquota,
                c.origine_prezzo,
                c.prezzo_resolver_context,
                c.stato_approvazione_prezzo,
                c.pratica_approvazione_prezzo_id,
                c.meta,
                c.ordine,
                c.attivo,
                ac.obbligatorio,
                ac.esposizione_in_fattura
              FROM {self._componenti_table_name} c
              LEFT JOIN catalogo.articoli a    ON a.id  = c.componente_id
              LEFT JOIN catalogo.unita_misura um ON um.id = c.uom_operativa_id
              LEFT JOIN config.iva iva         ON iva.id = c.iva_id
              LEFT JOIN catalogo.articoli_componenti ac
                     ON ac.id = c.articolo_componente_id
             WHERE c.{self._componenti_fk_riga} = %s
               {filtro_attivo}
             ORDER BY c.ordine NULLS LAST, c.id
        """  # noqa: S608 — `_componenti_*` sono attributi di classe whitelisted
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return rows_to_list(cursor)

    # Scopo: Lookup singolo componente per id. None se inesistente.
    # Stesse denormalizzazioni di `list_componenti_riga`.
    def get_componente(self, componente_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT
                c.id,
                c.{self._componenti_fk_riga},
                c.articolo_componente_id,
                c.componente_id,
                a.codice                AS componente_codice,
                a.descrizione           AS componente_descrizione,
                c.coeff_qta_snapshot,
                c.quantita,
                c.uom_operativa_id,
                um.codice               AS uom_codice,
                c.factor_to_base,
                c.qta_operativa,
                c.prezzo_unitario,
                c.iva_id,
                iva.codice              AS iva_codice,
                iva.aliquota_iva        AS iva_aliquota,
                c.origine_prezzo,
                c.prezzo_resolver_context,
                c.stato_approvazione_prezzo,
                c.pratica_approvazione_prezzo_id,
                c.meta,
                c.ordine,
                c.attivo,
                ac.obbligatorio,
                ac.esposizione_in_fattura
              FROM {self._componenti_table_name} c
              LEFT JOIN catalogo.articoli a    ON a.id  = c.componente_id
              LEFT JOIN catalogo.unita_misura um ON um.id = c.uom_operativa_id
              LEFT JOIN config.iva iva         ON iva.id = c.iva_id
              LEFT JOIN catalogo.articoli_componenti ac
                     ON ac.id = c.articolo_componente_id
             WHERE c.id = %s
        """  # noqa: S608 — attributi di classe whitelisted
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

    # Scopo: Update componente (prezzo, origine, stato approvazione, meta).
    # Whitelist colonne RIGIDA (`COMPONENTE_UPDATE_ALLOWED`): dal 2026-09-26
    # una chiave fuori lista (campi struttura compresi) e' `ValueError` del BB,
    # non piu' uno scarto silenzioso — i service la rifiutano prima con un 400.
    def update_componente(self, componente_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            self._componenti_table_name, componente_id, kwargs,
            allowed=COMPONENTE_UPDATE_ALLOWED,
        )

    # Scopo: Soft delete componente (`attivo=FALSE`). Il trigger DB di
    # ricalcolo padre lo esclude dalla SUM (filtro `attivo`). Idempotente:
    # se gia' soft-deleted ritorna False senza errore.
    def delete_componente(self, componente_id: int) -> bool:
        sql = (
            f"UPDATE {self._componenti_table_name} "  # noqa: S608 — tabella da attributo di classe letterale della sottoclasse
            f"SET attivo = FALSE WHERE id = %s AND attivo = TRUE"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return cursor.rowcount > 0

    # Scopo: Hard delete TUTTI i componenti di una riga padre. Usato quando
    # l'articolo padre cambia: i vecchi componenti non hanno piu' senso,
    # vanno purged prima del re-init. Naming `purge_*` per distinguere
    # esplicitamente dal pattern soft-delete `delete_*`.
    #
    # Nota: NON serve un helper "soft cascade" sui componenti — l'eliminazione
    # della riga padre passa per HARD DELETE in entrambi i sorgenti
    # (preventivi+contratti) e la FK `ON DELETE CASCADE` su
    # `*_righe_componenti.riga_<sorgente>_id` pulisce automaticamente lato DB.
    def purge_componenti_riga(self, riga_id: int) -> int:
        sql = (
            f"DELETE FROM {self._componenti_table_name} "  # noqa: S608 — tabella/FK da attributi di classe letterali della sottoclasse
            f"WHERE {self._componenti_fk_riga} = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return cursor.rowcount
