# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
duplicate in frontend/src/anagrafiche/composables/useContattoForm.js
(TRACKED_FIELDS, REQUIRED_FIELDS). Se cambi qui aggiorna anche la'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from apps.anagrafiche.error_codes import E_CONTATTO_INCOMPLETO
from apps.anagrafiche.services._validators import create_with_constraint_mapping, optional_str
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


# Scopo: Il contatto inline OPZIONALE di una creazione (fornitore, cliente)
#        nella forma che la madre del DB riceve: EMPTY → None (nessun
#        contatto); PARTIAL → E_CONTATTO_INCOMPLETO coi campi da accendere;
#        VALID → i campi del contatto (`campi_contatto`).
# ⭐ Dal 2026-10-18 (2b-2): la scrittura la fa la madre (`fn_crea_fornitore`,
#    `fn_crea_cliente`, che chiamano `fn_crea_contatto`); qui resta la
#    classificazione, che decide SE c'e' un contatto. Prima era
#    `crea_contatto_inline_se_valido`, che lo scriveva da se'.
def contatto_inline_per_madre(contatto_data: dict[str, Any] | None) -> dict[str, Any] | None:
    contatto_status = classify_contatto_payload(contatto_data)
    if contatto_status == "PARTIAL":
        missing = missing_required_fields(contatto_data)
        raise ServiceError(
            code=E_CONTATTO_INCOMPLETO,
            message="Contatto incompleto: completa o svuota tutti i campi.",
            context={"missing": missing},
            # I campi mancanti SONO i campi da accendere: `fields` e' il canale
            # per piu' di uno (presidio C2, §3-ter).
            fields=tuple(missing),
        )
    if contatto_status == "EMPTY":
        return None
    assert contatto_data is not None  # VALID
    return campi_contatto(contatto_data)


# Scopo: I campi di un contatto VALIDO come li scrive il DB: testi ripuliti
#        (vuoto = assente), id interi; le chiavi assenti restano fuori.
def campi_contatto(contatto: dict[str, Any]) -> dict[str, Any]:
    campi = {
        "nominativo": optional_str(contatto, "nominativo"),
        "email": optional_str(contatto, "email"),
        "telefono": optional_str(contatto, "telefono"),
        "cellulare": optional_str(contatto, "cellulare"),
        "pec": optional_str(contatto, "pec"),
        "tipo_contatto_id": optional_int(contatto, "tipo_contatto_id"),
        "unita_organizzativa_id": optional_int(contatto, "unita_organizzativa_id"),
        "note": optional_str(contatto, "note"),
    }
    return {k: v for k, v in campi.items() if v is not None}


# Scopo: il contatto e' VALIDO (nominativo + tipo contatto), altrimenti
#        E_CONTATTO_INCOMPLETO coi campi mancanti da accendere. Per chi il
#        contatto lo pretende: EMPTY e PARTIAL sono lo stesso rifiuto.
def richiedi_contatto_valido(contatto: dict[str, Any] | None) -> None:
    if classify_contatto_payload(contatto) != "VALID":
        missing = missing_required_fields(contatto)
        raise ServiceError(
            code=E_CONTATTO_INCOMPLETO,
            message="Contatto obbligatorio: nominativo e tipo contatto richiesti.",
            context={"missing": missing},
            # I campi mancanti SONO i campi da accendere (presidio C2, §3-ter).
            fields=tuple(missing),
        )


# Le tre unicita' di `anagrafiche.contatti` (indici parziali): un contatto per
# tipo, sul soggetto, sul ruolo, sul ruolo per istanza. Il campo e' il tipo
# contatto: e' l'unica colonna che l'operatore sceglie (soggetto, ruolo e
# istanza li da' il contesto della pagina).
VINCOLI_CONTATTO: Final[dict[str, str | tuple[str, str]]] = {
    "uq_contatti_soggetto_tipo": (
        "Il soggetto ha gia' un contatto di questo tipo.", "tipo_contatto_id",
    ),
    "uq_contatti_ruolo_tipo_no_istanza": (
        "Il ruolo ha gia' un contatto di questo tipo.", "tipo_contatto_id",
    ),
    "uq_contatti_ruolo_istanza_tipo": (
        "Il ruolo ha gia' un contatto di questo tipo per questa istanza.", "tipo_contatto_id",
    ),
}


# Scopo: crea un contatto (del soggetto, del ruolo o del ruolo per istanza)
#        con la regola del contatto valido e le unicita' tradotte.
# ⭐ Regola del 2 (2026-10-09): stava in tre punti — `SoggettiService.
#    create_contatto`, la view `RuoloContattiView.post` e il VALID di
#    `crea_contatto_inline_se_valido` — e nessuno dei tre la scriveva intera.
#    Il contatto del soggetto non pretendeva il tipo (la colonna NOT NULL
#    rispondeva `E_DATABASE`) e nessuno traduceva le unicita' sul campo: un
#    secondo contatto dello stesso tipo era un `E_DATABASE` generico, o un 409
#    senza dire quale campo.
def crea_contatto_validato(
    sogg_repo: "SoggettiRepository",
    soggetto_id: str,
    contatto: dict[str, Any],
    *,
    soggetto_ruolo_id: int | None = None,
    istanza_utility_id: int | None = None,
) -> dict[str, Any]:
    richiedi_contatto_valido(contatto)
    campi = campi_contatto(contatto)
    risultato: dict[str, Any] = create_with_constraint_mapping(
        lambda: sogg_repo.crea_contatto(
            soggetto_id,
            **campi,
            soggetto_ruolo_id=soggetto_ruolo_id,
            istanza_utility_id=istanza_utility_id,
        ),
        VINCOLI_CONTATTO,
    )
    return risultato
