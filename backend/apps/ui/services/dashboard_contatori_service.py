# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Calcolo dei contatori KPI delle card home. Registry
#        `contatore_key -> callable` + risoluzione batch.
#
#        Tre invarianti di progetto:
#        1. NIENTE chiavi arbitrarie dal client. Il chiamante passa il
#           codice dashboard, non una lista di key: le key calcolate sono
#           SOLO quelle dei widget che `fn_resolve_dashboard_config` ha
#           gia' concesso all'utente. La fn DB resta la single source of
#           truth dei permessi — un utente senza area vendite non puo'
#           farsi calcolare un contatore vendite chiamando l'endpoint a
#           mano.
#        2. ISOLAMENTO per-key. Un contatore che esplode degrada la sua
#           card (`ok: false`), non oscura la home. Mai un'eccezione di
#           un singolo KPI propagata alla response.
#        3. RIUSO degli aggregati esistenti. I contatori v1 sommano i
#           riepiloghi di testata gia' calcolati dai cruscotti vendite:
#           card e cruscotto non possono divergere.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from apps.core.services.fuso_aziendale import oggi_aziendale

__all__ = ["DashboardContatoriService", "CONTATORI_REGISTRY"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Callable dei singoli contatori.
# Import di `vendite` fatti DENTRO le funzioni: lo schema `ui` e' una
# meta-API trasversale e non deve dipendere a import-time da un dominio
# di business (evita cicli e mantiene `ui` installabile da solo).
# ---------------------------------------------------------------------


# Scopo: Stock documenti aperti-non-chiusi (Situazione aperta). Somma
#        `n_documenti` delle aree del riepilogo — stesso aggregato che
#        alimenta le card del cruscotto.
def _contatore_situazione_aperta() -> int:
    from apps.vendite.services.vendite_service import fn_dash_aperto_riepilogo

    riepilogo = fn_dash_aperto_riepilogo()
    aree = riepilogo.get("aree") or []
    return sum(int(a.get("n_documenti") or 0) for a in aree)


# Scopo: Documenti fermi (Backlog). Somma `n_documenti` delle classi di
#        azionabilita' del riepilogo di Lente 2.
def _contatore_backlog_documenti_fermi() -> int:
    from apps.vendite.services.vendite_service import fn_dash_backlog_riepilogo

    riepilogo = fn_dash_backlog_riepilogo()
    classi = riepilogo.get("classi") or []
    return sum(int(c.get("n_documenti") or 0) for c in classi)


# Scopo: Attivita' da fatturare nel mese di competenza corrente (Lente 1).
#        Conta le attivita' degli stadi NON ancora fatturati, coerente con
#        `valore_da_fatturare` dei totali di mese (che esclude FATTURATA).
def _contatore_competenza_da_fatturare() -> int:
    from apps.vendite.services.vendite_service import fn_dash_competenza_mensile

    oggi = oggi_aziendale()
    riepilogo = fn_dash_competenza_mensile(anno=oggi.year)
    prefisso = f"{oggi.year:04d}-{oggi.month:02d}"

    for mese in riepilogo.get("mesi") or []:
        # `competenza_mese` e' il 1° del mese (date o stringa ISO a
        # seconda dell'adapter): il confronto su prefisso YYYY-MM regge
        # entrambi senza assumere il tipo.
        if not str(mese.get("competenza_mese") or "").startswith(prefisso):
            continue
        return sum(
            int(s.get("n_attivita") or 0)
            for s in (mese.get("stadi") or [])
            if s.get("stadio") != "FATTURATA"
        )
    # Anno presente ma mese assente: il contratto della fn garantisce 12
    # mesi, quindi qui ci si arriva solo per regressione. Zero e' la
    # risposta onesta (nessuna attivita' di competenza nel mese).
    return 0


# Registry pubblico: `contatore_key` (colonna `ui.widget.contatore_key`)
# -> callable a zero argomenti che ritorna un intero.
# Aggiungere un KPI = aggiungere una riga qui + seedare il widget con la
# stessa key. Nessun'altra modifica al BE.
CONTATORI_REGISTRY: dict[str, Callable[[], int]] = {
    "vendite.situazione_aperta.totale_aperto": _contatore_situazione_aperta,
    "vendite.backlog.documenti_fermi": _contatore_backlog_documenti_fermi,
    "vendite.competenza.da_fatturare": _contatore_competenza_da_fatturare,
}


class DashboardContatoriService:
    """Risoluzione batch dei contatori KPI di una dashboard."""

    # Scopo: Calcola i contatori dei widget visibili della dashboard per
    #        l'utente. Le key provengono dalla config risolta lato DB, mai
    #        dal client (invariante 1).
    # Risultato: dict `{contatore_key: {"valore": int|None, "ok": bool}}`.
    #        `ok=false` senza `valore` = contatore non disponibile: la card
    #        mostra lo stato degradato, le altre restano leggibili.
    def get_contatori(
        self,
        user: Any,
        dashboard_codice: str,
        *,
        config: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        if config is None:
            # Import locale: evita un ciclo con dashboard_service, che non
            # dipende da questo modulo ma vive nello stesso package.
            from apps.ui.services.dashboard_service import DashboardService

            config = DashboardService().get_dashboard_config(
                user, dashboard_codice,
            )

        keys = self._extract_keys(config)
        return {key: self._safe_compute(key) for key in keys}

    # Scopo: Estrae le `contatore_key` distinte dei widget VISIBILI della
    #        config risolta, preservando l'ordine di apparizione. I widget
    #        nascosti (merge automatico dei nuovi, o deselezionati
    #        dall'utente) non consumano una query: non sono a schermo.
    @staticmethod
    def _extract_keys(config: dict[str, Any]) -> list[str]:
        keys: list[str] = []
        for widget in config.get("widget") or []:
            if not widget.get("visibile"):
                continue
            key = widget.get("contatore_key")
            # Widget senza contatore (es. card di benvenuto non-gated):
            # legittimo, semplicemente non ha un numero da mostrare.
            if key and key not in keys:
                keys.append(key)
        return keys

    # Scopo: Esegue un singolo contatore isolando ogni fallimento
    #        (invariante 2). Una key non registrata non e' un errore del
    #        chiamante ma un disallineamento seed/registry: si degrada e
    #        si logga, senza rompere le altre card.
    @staticmethod
    def _safe_compute(key: str) -> dict[str, Any]:
        callable_ = CONTATORI_REGISTRY.get(key)
        if callable_ is None:
            logger.warning(
                "Contatore dashboard non registrato: %s "
                "(widget seedato senza callable corrispondente)",
                key,
            )
            return {"valore": None, "ok": False}
        try:
            return {"valore": int(callable_()), "ok": True}
        except Exception:
            # Volutamente ampio: qualunque fallimento di un KPI deve
            # degradare la sua card, mai la home. Lo stacktrace resta nei
            # log per la diagnosi.
            logger.exception("Contatore dashboard fallito: %s", key)
            return {"valore": None, "ok": False}
