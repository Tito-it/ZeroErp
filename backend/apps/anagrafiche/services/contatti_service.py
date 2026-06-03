# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service centralizzato per logica contatti anagrafiche.
#        Espone classify_contatto_payload() come single source of truth
#        della regola "quando un contatto inline e' considerato compilato".
#        Sostituisce 3 implementazioni divergenti precedenti
#        (clienti/fornitori/soggetti) — vedi Fase 5 refactor anagrafiche.
# ------------------------------------------------------------

"""
Riferimento brief: docs/it/dev/work-in-progress/analisi-refactor.frontend-anagrafiche.md, sezione C1.

Pattern A2 defense-in-depth: la regola e' scritta qui (backend = verita'
unica) e replicata nel composable frontend useContattoForm per UX
immediata. Se la regola cambia, cambia in un solo posto e il FE si
allinea aggiornando solo l'UX (la validazione resta enforced dal BE).

KEEP IN SYNC: le costanti _TRACKED_FIELDS e _REQUIRED_FIELDS sono
duplicate in frontend/src/core/composables/useContattoForm.js
(TRACKED_FIELDS, REQUIRED_FIELDS). Se cambi qui aggiorna anche la'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from apps.anagrafiche.error_codes import E_CONTATTO_INCOMPLETO
from apps.anagrafiche.services._validators import optional_str
from apps.core.api.payload_validators import optional_int
from apps.core.services.service_errors import ServiceError

if TYPE_CHECKING:
    from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

# Campi del contatto che indicano "l'utente ha iniziato a compilare".
# Se almeno UNO e' valorizzato, il contatto e' considerato in compilazione
# (regola A — versione Cliente, decisa come canonica).
_TRACKED_FIELDS: Final = (
    "nominativo", "email", "telefono", "cellulare", "pec",
    "tipo_contatto_id",
)

# Campi obbligatori per considerare il contatto "valido" e creabile.
# Allineati con NOT NULL DB su anagrafiche.contatti.
_REQUIRED_FIELDS: Final = ("nominativo", "tipo_contatto_id")


# Scopo: Verifica se un valore e' "valorizzato" semanticamente.
# Stringa vuota / None / 0 / False sono tutti "non valorizzato".
def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    # Per int (tipo_contatto_id): 0 e' considerato non valorizzato
    # (nessun id valido in DB; pattern coerente col guard core sui parametri).
    if isinstance(value, int) and not isinstance(value, bool):
        return value > 0
    return bool(value)


# Scopo: Classifica il payload contatto inline in uno di tre stati.
# Centralizza la regola "contatto e' compilato/parziale/vuoto" che prima
# era replicata divergente nei 3 service (cliente, fornitore, soggetto).
#
# Stati:
#   EMPTY   = nessun campo tracked valorizzato → caller decide cosa fare
#             (cliente/fornitore: skip; soggetto: errore E_CONTATTO_INCOMPLETO
#             via _require_contatto_valid, perche' il contatto e' obbligatorio)
#   PARTIAL = almeno un campo valorizzato MA mancano obbligatori (nominativo
#             o tipo_contatto_id) → caller solleva E_CONTATTO_INCOMPLETO
#   VALID   = obbligatori presenti → caller crea il contatto
def classify_contatto_payload(data: dict[str, Any] | None) -> str:
    if not data:
        return "EMPTY"
    any_filled = any(_is_filled(data.get(f)) for f in _TRACKED_FIELDS)
    if not any_filled:
        return "EMPTY"
    all_required_present = all(_is_filled(data.get(f)) for f in _REQUIRED_FIELDS)
    return "VALID" if all_required_present else "PARTIAL"


# Scopo: Calcola la lista di campi obbligatori mancanti, utile come
# error context per highlight UI (es. {"missing": ["nominativo", ...]}).
# Per None / {} ritorna tutti i required (semantica: nessun obbligatorio
# presente). Per VALID ritorna []. Coerente per qualunque stato.
def missing_required_fields(data: dict[str, Any] | None) -> list[str]:
    payload = data or {}
    return [f for f in _REQUIRED_FIELDS if not _is_filled(payload.get(f))]


# Scopo: Orchestratore contatto inline opzionale: classifica + valida + crea.
#        Centralizza il blocco identico che era duplicato in clienti_service e
#        fornitori_service (regola del 2). Stati: EMPTY → skip; PARTIAL → solleva
#        E_CONTATTO_INCOMPLETO; VALID → crea il contatto via repository.
def crea_contatto_inline_se_valido(
    sogg_repo: "SoggettiRepository",
    soggetto_id: str,
    soggetto_ruolo_id: int,
    contatto_data: dict[str, Any] | None,
) -> None:
    contatto_status = classify_contatto_payload(contatto_data)
    if contatto_status == "PARTIAL":
        raise ServiceError(
            code=E_CONTATTO_INCOMPLETO,
            message="Contatto incompleto: completa o svuota tutti i campi.",
            context={"missing": missing_required_fields(contatto_data)},
        )
    if contatto_status == "VALID":
        assert contatto_data is not None  # type narrowing per il checker
        sogg_repo.crea_contatto(
            soggetto_id,
            nominativo=contatto_data["nominativo"],
            email=optional_str(contatto_data, "email"),
            telefono=optional_str(contatto_data, "telefono"),
            cellulare=optional_str(contatto_data, "cellulare"),
            pec=optional_str(contatto_data, "pec"),
            tipo_contatto_id=optional_int(contatto_data, "tipo_contatto_id"),
            note=optional_str(contatto_data, "note"),
            soggetto_ruolo_id=soggetto_ruolo_id,
        )
