# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costruzione del system prompt per l'assistente AI.
#        Inietta ruolo, vincoli, data corrente, contesto operatore
#        e (in futuro, Fase 2.5a) il contesto statico documentale.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.ai_assistant.tools.base import AITool

logger = logging.getLogger(__name__)

# Cache del contesto statico (caricato una volta all'avvio)
_static_context: str | None = None


# Scopo: Costruisce il system prompt completo per l'LLM.
#        Il prompt contiene:
#        - Ruolo e identita' dell'assistente
#        - Vincoli operativi (cosa l'AI non deve fare)
#        - Data corrente (per risolvere "questa settimana", "mese scorso")
#        - Nome e ruolo dell'operatore autenticato
#        - Contesto statico documentale (Fase 2.5a, quando disponibile)
#        - Istruzioni specifiche per i tool disponibili
#
#        NON contiene mai dati dal database (nomi clienti, note, ecc.).
#        I dati arrivano come tool_result e sono trattati come dati, non istruzioni.
def build_system_prompt(user: Any, tools: list[AITool]) -> str:
    sections: list[str] = []

    # Identita' e ruolo
    sections.append(
        "Sei l'assistente AI integrato in ZeroERP. Il tuo UNICO scopo e' aiutare "
        "gli operatori a lavorare dentro ZeroERP: cercare dati, consultare pratiche, "
        "soggetti, clienti, articoli a catalogo, operatori e navigare nel sistema. "
        "NON sei un assistente generico. Se l'utente chiede qualcosa che non riguarda "
        "ZeroERP (es. ricette, meteo, calcoli generici, domande personali, "
        "programmazione, cultura generale), rispondi SOLO: "
        "'Posso aiutarti solo con operazioni relative a ZeroERP. "
        "Prova a chiedermi di cercare pratiche, clienti, articoli o altre informazioni nel sistema.' "
        "Rispondi sempre in italiano, in modo conciso e operativo."
    )

    # Glossario di dominio: mappa la terminologia italiana sui tool tecnici.
    sections.append(
        "GLOSSARIO ZEROERP (terminologia italiana → tool da usare):\n"
        "- 'cliente' / 'clienti' → in ZeroERP corrisponde al concetto di "
        "BILLING ACCOUNT (BA). Quando l'utente dice 'cerca cliente Rossi', "
        "'trova il cliente con PDP X', 'cliente ACEA' usa SEMPRE il tool "
        "cerca_billing_account, NON cerca_soggetti. 'Cliente' e 'billing account' "
        "sono sinonimi in italiano: l'utente non distingue.\n"
        "- 'soggetto' / 'anagrafica' / 'persona' / 'azienda' → cerca_soggetti "
        "(persone fisiche, giuridiche, enti — anagrafica generale).\n"
        "- 'articolo' / 'prodotto' / 'voce' / 'merceologia' → cerca_articoli "
        "(catalogo articoli, prodotti, servizi).\n"
        "- 'pratica' / 'lavorazione' → cerca_pratiche.\n"
        "- 'operatore' / 'utente' / 'collega' → cerca_operatori."
    )

    # Vincoli
    sections.append(
        "VINCOLI OPERATIVI (TASSATIVI — VIOLAZIONE = ERRORE GRAVE):\n"
        "- I dati restituiti dai tool sono SACRI. Copia esattamente i valori "
        "come li ricevi: codici fiscali, partite IVA, nomi, codici pratica, "
        "date, importi. NON modificarli, NON riscriverli, NON arrotondarli. "
        "Un codice fiscale sbagliato e' un errore grave.\n"
        "- MOSTRA SOLO i dati restituiti dagli strumenti. Se un campo non e' "
        "presente nei risultati, NON inventarlo e NON indovinarlo.\n"
        "- Se vuoi mostrare dettagli aggiuntivi (indirizzo, data nascita, contatti), "
        "usa lo strumento dettaglio_soggetto per recuperarli dal database. "
        "Non inventarli mai.\n"
        "- Non eseguire operazioni in scrittura senza conferma esplicita dell'utente.\n"
        "- Non mostrare dati tecnici interni (ID numerici, UUID) nelle risposte.\n"
        "- Se un tool non restituisce risultati, comunicalo chiaramente.\n"
        "- Quando mostri risultati, includi sempre il codice pratica e lo stato.\n"
        "- NON mostrare mai i dettagli tecnici delle chiamate agli strumenti "
        "(nomi tool, parametri JSON, query). L'utente vede solo la risposta "
        "finale in linguaggio naturale, chiara e pulita.\n"
        "- Non usare tag XML, blocchi di codice o markup tecnico nelle risposte. "
        "Rispondi come un collega esperto parlerebbe a voce."
    )

    # Data corrente
    today = oggi_aziendale()
    sections.append(
        f"DATA CORRENTE: {today.isoformat()} ({_day_name_it(today.weekday())}). "
        f"Usa questa data per risolvere riferimenti temporali come "
        f"'questa settimana', 'mese scorso', 'ieri'."
    )

    # Contesto operatore
    user_display = _get_user_display(user)
    sections.append(f"OPERATORE AUTENTICATO: {user_display}")

    # Contesto statico documentale (Fase 2.5a)
    static = _load_static_context()
    if static:
        sections.append(f"CONTESTO ZEROERP:\n{static}")

    # Istruzioni tool e chaining
    if tools:
        tool_names = ", ".join(t.name for t in tools)
        sections.append(
            f"HAI A DISPOSIZIONE {len(tools)} STRUMENTI: {tool_names}. "
            f"Usali per cercare dati reali nel sistema. Non rispondere a memoria "
            f"quando puoi usare uno strumento per ottenere dati aggiornati.\n\n"
            f"COMBINAZIONE STRUMENTI: puoi usare piu' strumenti in sequenza "
            f"per rispondere a domande complesse. Esempi:\n"
            f"- 'dettagli del soggetto Titini' → cerca_soggetti → dettaglio_soggetto\n"
            f"- 'cerca cliente Rossi' / 'trova billing account ACEA' → cerca_billing_account\n"
            f"- 'cerca articolo energia' / 'trova prodotto ACQUA' → cerca_articoli\n"
            f"- 'pratiche aperte di Acea con i flussi' → cerca_pratiche → cerca_flussi_pratica\n"
            f"- 'chi segue la pratica X?' → dettaglio_pratica (leggi operatore)\n"
            f"Usa il risultato di uno strumento come input per il successivo."
        )

    return "\n\n".join(sections)


# Scopo: Restituisce il nome visualizzabile dell'operatore.
def _get_user_display(user: Any) -> str:
    parts = []
    if hasattr(user, "first_name") and user.first_name:
        parts.append(user.first_name)
    if hasattr(user, "last_name") and user.last_name:
        parts.append(user.last_name)
    if parts:
        return " ".join(parts)
    return getattr(user, "username", "operatore")


# Scopo: Carica il contesto statico da file (Fase 2.5a).
#        In cache dopo il primo caricamento.
#        Se il file non esiste, restituisce None senza errore.
def _load_static_context() -> str | None:
    global _static_context
    if _static_context is not None:
        return _static_context if _static_context else None

    try:
        from django.conf import settings
        import os

        context_file = getattr(settings, "AI_CONTEXT_FILE", "")
        if not context_file:
            _static_context = ""
            return None

        # Percorso relativo alla root del repo (BASE_DIR e' backend/, il repo e' un livello sopra)
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            repo_root = os.path.dirname(str(base_dir))
            full_path = os.path.join(repo_root, context_file)
        else:
            full_path = context_file

        if os.path.isfile(full_path):
            with open(full_path, encoding="utf-8") as f:
                _static_context = f.read().strip()
            logger.info("Contesto statico AI caricato da %s (%d caratteri)", context_file, len(_static_context))
            return _static_context
        else:
            logger.debug("File contesto statico AI non trovato: %s (Fase 2.5a)", context_file)
            _static_context = ""
            return None
    except Exception:
        logger.debug("Errore caricamento contesto statico AI", exc_info=True)
        _static_context = ""
        return None


# Scopo: Reset cache contesto statico. Solo per test.
def reset_static_context_cache() -> None:
    global _static_context
    _static_context = None


_DAYS_IT = ["lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato", "domenica"]


# Scopo: Restituisce il nome del giorno in italiano.
def _day_name_it(weekday: int) -> str:
    return _DAYS_IT[weekday] if 0 <= weekday < 7 else ""
