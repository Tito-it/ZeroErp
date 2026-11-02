# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block della lista delle tabelle gestite in modo generico,
#        `config.tabelle_gestibili` (brief-db-pannello-config-verbo-generico,
#        D-3 §7.1 del modello): quali tabelle servono le tendine (`lookup`) e
#        quali si scrivono dal pannello (`pannello`), e a quale OGGETTO
#        appartiene ciascuna.
# Note: ⛔ Fino al 2026-09-25 la lista era la costante `REL_CONSENTITE` del
#       backend, e ne esisteva una terza copia nel frontend. La sede adesso e'
#       il DB: il verbo `config.fn_pannello_scrivi` legge la stessa riga per
#       decidere cosa si scrive e su quale oggetto si chiede il permesso. Una
#       costante qui accanto sarebbe di nuovo una seconda sede.
#       All'app la tabella e' in sola lettura: una riga nasce nel seed.
# ------------------------------------------------------------

from __future__ import annotations

from typing import TypedDict

from django.db import connection


class VoceTabellaGestibile(TypedDict):
    rel: str
    schema: str
    table: str
    app_label: str
    model_name: str
    lookup: bool
    pannello: bool


_COLONNE = (
    "codice_interno, schema_tabella, nome_tabella, app_label, model_name, lookup, pannello"
)


def _voce(row: tuple) -> VoceTabellaGestibile:
    return VoceTabellaGestibile(
        rel=row[0], schema=row[1], table=row[2], app_label=row[3],
        model_name=row[4], lookup=bool(row[5]), pannello=bool(row[6]),
    )


class TabelleGestibiliRepository:
    """Lettura di `config.tabelle_gestibili` (sola lettura per l'app)."""

    # Scopo: La voce di una `rel` (`schema.tabella`), o None se non e' in lista.
    # ⭐ Il nome `schema.tabella` che entra negli SQL dinamici del lookup e del
    # pannello viene da QUI (CHECK di forma sulla tabella), mai dal client:
    # la `rel` del client serve solo a cercare la riga.
    def voce(self, rel: str | None) -> VoceTabellaGestibile | None:
        if not rel:
            return None
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLONNE} FROM config.tabelle_gestibili WHERE codice_interno = %s",  # noqa: S608
                [rel],
            )
            row = cursor.fetchone()
        return _voce(row) if row else None

    # Scopo: Le `rel` che il lookup generico serve alle tendine.
    def rel_lookup(self) -> frozenset[str]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT codice_interno FROM config.tabelle_gestibili WHERE lookup")
            return frozenset(r[0] for r in cursor.fetchall())

    # Scopo: Le tabelle del pannello «Gestione tabelle», in ordine di `rel`.
    def voci_pannello(self) -> list[VoceTabellaGestibile]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_COLONNE} FROM config.tabelle_gestibili "  # noqa: S608
                "WHERE pannello ORDER BY codice_interno"
            )
            return [_voce(r) for r in cursor.fetchall()]
