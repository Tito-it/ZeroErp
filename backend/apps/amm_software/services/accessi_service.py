# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service dell'area «Accessi» di Amm. Software (brief-db-be-fe-area-
#        accessi): le liste «Altri accessi» e «Di sistema» e le azioni della
#        CREDENZIALE — blocco e sblocco dell'amministratore — che valgono per
#        tutte le sue vesti e quindi non stanno sotto `/operatori/` (A-4, A-5).
# Note: il secondo fattore della credenziale ha il suo servizio
#       (`apps.core.services.secondo_fattore_service`); qui c'e' solo
#       l'esistenza della credenziale che le sue view chiedono.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.amm_software.db.accessi_repository import STATI_ACCESSO, TIPI_SISTEMA, AccessiRepository
from apps.amm_software.services.amm_software_service import E_AMM_VALIDAZIONE
from apps.core.db.secondo_fattore_repository import STATI_DEVICE
from apps.core.services.auth_constants import RUOLO_APPLICATIVO
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_enum_param
from apps.core.services.permissions_cache import invalidate_user
from apps.core.services.revoca_token import blocca_token_sessioni

E_CREDENZIALE_NON_TROVATA = "E_CREDENZIALE_NON_TROVATA"

# Le vesti per il filtro «Accessi»: i tipi che una veste VIVA puo' avere
# (`RUOLO_APPLICATIVO`, senza la voce storica DISABILITATO: come filtro
# troverebbe sempre niente).
_RUOLI_FILTRABILI: tuple[str, ...] = RUOLO_APPLICATIVO


class AccessiService:
    """Liste dell'area Accessi e azioni della credenziale."""

    def __init__(self) -> None:
        self._repo = AccessiRepository()

    # Scopo: Le credenziali di categoria ALTRO, paginate, con i filtri della
    #        lista. I valori a vocabolario si validano: un valore estraneo e'
    #        un 400, non una lista vuota che sembra un dato.
    def list_accessi_altri(
        self,
        *,
        ruolo_applicativo: str | None,
        stato_accesso: str | None,
        secondo_fattore_stato: str | None,
        **params: Any,
    ) -> tuple[list[dict[str, Any]], int]:
        fn = "AccessiService.list_accessi_altri"
        validate_enum_param(ruolo_applicativo, allowed=_RUOLI_FILTRABILI, param_name="ruolo_applicativo",
                            error_code=E_AMM_VALIDAZIONE, function_name=fn)
        validate_enum_param(stato_accesso, allowed=STATI_ACCESSO, param_name="stato_accesso",
                            error_code=E_AMM_VALIDAZIONE, function_name=fn)
        validate_enum_param(secondo_fattore_stato, allowed=STATI_DEVICE, param_name="secondo_fattore_stato",
                            error_code=E_AMM_VALIDAZIONE, function_name=fn)
        return self._repo.list_accessi_altri(
            ruolo_applicativo=ruolo_applicativo,
            stato_accesso=stato_accesso,
            secondo_fattore_stato=secondo_fattore_stato,
            **params,
        )

    # Scopo: Le credenziali di categoria SISTEMA, paginate (sola lettura, A-6).
    def list_accessi_sistema(self, *, tipo: str | None, **params: Any) -> tuple[list[dict[str, Any]], int]:
        validate_enum_param(tipo, allowed=TIPI_SISTEMA, param_name="tipo",
                            error_code=E_AMM_VALIDAZIONE, function_name="AccessiService.list_accessi_sistema")
        return self._repo.list_accessi_sistema(tipo=tipo, **params)

    # Scopo: Lo stato di una credenziale per il pannello delle sue azioni, con
    #        la capability del blocco (`can_block` + motivo e chiave quando e'
    #        spento, dalla check del DB: vedi il repository).
    #        404 `E_CREDENZIALE_NON_TROVATA` se non esiste.
    def get_credenziale(self, auth_user_id: int) -> dict[str, Any]:
        cred = self._repo.get_credenziale(auth_user_id)
        ErrorManager.require(
            cred is not None,
            code=E_CREDENZIALE_NON_TROVATA,
            message=f"Credenziale {auth_user_id} non trovata.",
            context={"auth_user_id": auth_user_id},
        )
        assert cred is not None
        return cred

    # Scopo: Blocca la credenziale (verbo `script.fn_blocca_credenziale`) e
    #        chiude TUTTE le sue sessioni, nella stessa transazione: un blocco
    #        con le sessioni ancora vive non e' un blocco. Il verbo pretende il
    #        SUPER_ADMIN e il motivo, e il suo guard l'anti-lockout: i rifiuti
    #        arrivano dal DB col loro codice.
    # ⚠️ La cache dei permessi si invalida a COMMIT avvenuto (come la
    #    disattivazione dell'operatore): prima, una richiesta concorrente la
    #    ricaricherebbe dallo stato non ancora bloccato.
    def blocca_credenziale(self, auth_user_id: int, motivo: str | None) -> dict[str, Any]:
        self.get_credenziale(auth_user_id)
        with transaction.atomic():
            self._repo.blocca_credenziale(auth_user_id, motivo)
            blocca_token_sessioni(auth_user_id)
            transaction.on_commit(lambda: invalidate_user(auth_user_id))
        return self.get_credenziale(auth_user_id)

    # Scopo: Elimina una credenziale che non ha mai avuto una veste (verbo
    #        `script.fn_elimina_credenziale`, brief-db-elimina-credenziale-
    #        senza-veste). Il verbo pretende il SUPER_ADMIN e solleva il primo
    #        motivo della check (`E_CREDENZIALE_CON_VESTI`, `_CON_STORIA`,
    #        `_STORIA_NON_VERIFICABILE`): i rifiuti arrivano dal DB col loro
    #        codice, qui non se ne tiene una copia.
    # ⚠️ Le sessioni non si chiudono a mano: una credenziale senza veste non ha
    #    un'identita' attiva, quindi nessun token che passi l'autenticazione;
    #    i token in lista Django perdono il riferimento (SET NULL). La cache
    #    dei permessi si invalida a COMMIT avvenuto, come per il blocco.
    def elimina_credenziale(self, auth_user_id: int) -> dict[str, Any]:
        self.get_credenziale(auth_user_id)
        with transaction.atomic():
            self._repo.elimina_credenziale(auth_user_id)
            transaction.on_commit(lambda: invalidate_user(auth_user_id))
        return {"status": "ok", "auth_user_id": auth_user_id}

    # Scopo: Toglie il blocco dell'amministratore (`script.fn_sblocca_credenziale`,
    #        idempotente). Le sessioni chiuse dal blocco non si riaprono: la
    #        persona entra di nuovo con la sua password.
    def sblocca_credenziale(self, auth_user_id: int) -> dict[str, Any]:
        self.get_credenziale(auth_user_id)
        with transaction.atomic():
            self._repo.sblocca_credenziale(auth_user_id)
            transaction.on_commit(lambda: invalidate_user(auth_user_id))
        return self.get_credenziale(auth_user_id)
