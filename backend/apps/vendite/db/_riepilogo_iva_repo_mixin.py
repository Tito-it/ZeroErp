# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per la lettura del riepilogo IVA dei
#        documenti vendita dalle viste `vw_<doc>_riepilogo_iva_dettaglio`.
#        Estrazione regola-del-2 (memoria feedback_regola_del_2_estrai_bb):
#        il metodo era clonato identico in preventivi e ordini, e il DDT
#        sarebbe stata la terza copia. Il calcolo fiscale (ROUND 2
#        sull'aggregato per aliquota, DPR 633/72 art. 21 + DM 24/12/93)
#        vive interamente nella vista DB: qui solo lettura, nessun
#        ricalcolo Python.
#
#        Differenze di shape tra viste (parametrizzate, non unificate):
#        la vista preventivi espone un `id` tecnico (riga fisica di
#        `preventivi_riepiloghi_iva` mantenuta da trigger); le viste
#        derivate on-the-fly (ordini, ddt) no — chiave logica
#        `<doc>_id + iva_id`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import rows_to_list


class RiepilogoIvaRepositoryMixin:
    """Building block lettura riepilogo IVA per repository documento.

    Le sottoclassi devono definire gli attributi di classe:

    - ``_riepilogo_iva_vista``: nome FQN della vista (es.
      ``"vendite.vw_ordini_riepilogo_iva_dettaglio"``).
    - ``_riepilogo_iva_fk_documento``: colonna FK al documento (es.
      ``"ordine_id"``).
    - ``_riepilogo_iva_con_id``: True se la vista espone l'`id` tecnico
      (solo preventivi). Default False.
    """

    _riepilogo_iva_vista: str
    _riepilogo_iva_fk_documento: str
    _riepilogo_iva_con_id: bool = False

    # Scopo: Riepilogo IVA del documento, una riga per gruppo aliquota
    #        (natura/esigibilita/split NULL dove la vista non li gestisce).
    #        Lettura pura dello stato corrente: il mantenimento (trigger o
    #        vista derivata) e' interamente a carico del DB.
    def list_riepilogo_iva(self, documento_id: int) -> list[dict[str, Any]]:
        col_id = "id, " if self._riepilogo_iva_con_id else ""
        fk = self._riepilogo_iva_fk_documento
        sql = f"""
            SELECT {col_id}{fk}, iva_id, iva_codice, iva_descrizione,
                   iva_aliquota, natura_id, natura_codice,
                   esigibilita, split_payment,
                   imponibile, imposta, arrotondamento, totale_riga
              FROM {self._riepilogo_iva_vista}
             WHERE {fk} = %s
             ORDER BY iva_aliquota NULLS LAST, iva_id NULLS LAST
        """  # noqa: S608 — vista/FK da attributi di classe letterali della sottoclasse, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento_id])
            return rows_to_list(cursor)
