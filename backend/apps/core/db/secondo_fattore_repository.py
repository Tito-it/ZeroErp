# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore (TOTP) della credenziale: lettura del device e
#        dell'obbligo, e i verbi che li scrivono (brief-db-secondo-fattore-totp
#        §2-§4, applicati il 2026-09-29).
# Note: ⛔ Nessun SQL diretto su `config.auth_totp_device`: all'app il DB da'
#       solo SELECT, ogni scrittura e' una funzione di `script` che sa CHI
#       agisce (`app.current_user_id`, la GUC del Bearer). I verbi «senza chi
#       agisce» (`registra_uso`, `consuma_recovery`) si chiamano prima del
#       login, e il backend solo dopo una password giusta. Il segreto arriva
#       qui GIA' cifrato (`crypto_service`) e i codici di recupero come
#       impronte (`totp_service`): il DB non vede mai niente in chiaro.
# ------------------------------------------------------------

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from django.db import connection

from apps.core.db._helpers import fetchone_scalar, row_to_dict

# Gli stati del device come li dice `script.fn_get_totp_device`. Sede unica:
# il cancello, il login, il secondo passo, il servizio e i serializer li
# importano da qui (regola del 2, 2026-10-02: erano quattro copie).
STATO_DEVICE_ASSENTE = "ASSENTE"
STATO_DEVICE_DA_CONFERMARE = "DA_CONFERMARE"
STATO_DEVICE_ATTIVO = "ATTIVO"
STATI_DEVICE: tuple[str, ...] = (STATO_DEVICE_ASSENTE, STATO_DEVICE_DA_CONFERMARE, STATO_DEVICE_ATTIVO)


class SecondoFattoreRepository:
    """Building block: device e obbligo del secondo fattore di una credenziale."""

    # Scopo: Lo stato del device in UNA riga anche quando non c'e':
    # `stato` (ASSENTE / DA_CONFERMARE / ATTIVO), `secret_encrypted`,
    # `ultimo_passo_usato`, `recovery_rimasti`. Il significato della riga
    # assente e' della funzione del DB.
    def get_device(self, auth_user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM script.fn_get_totp_device(%s)", [auth_user_id])
            row = row_to_dict(cursor)
        assert row is not None
        return row

    # Scopo: L'obbligo della credenziale e il suo motivo (CREDENZIALE /
    # PROFILO / None), risposta unica del DB per tutte le porte.
    def get_obbligo(self, auth_user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM script.fn_totp_obbligatorio(%s)", [auth_user_id])
            row = row_to_dict(cursor)
        assert row is not None
        return row

    # Scopo: Registra il device NON confermato (o ricomincia una
    # configurazione a meta'). Chi agisce: la credenziale stessa.
    def registra_device(
        self, auth_user_id: int, *, secret_encrypted: str, impronte_recupero: Sequence[str],
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_totp_registra_device(%s, %s, %s::jsonb)",
                [auth_user_id, secret_encrypted, json.dumps(list(impronte_recupero))],
            )

    # Scopo: Conferma il device col passo del primo codice verificato. Chi
    # agisce: la credenziale stessa.
    def conferma_device(self, auth_user_id: int, *, passo: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_totp_conferma_device(%s, %s)", [auth_user_id, passo])

    # Scopo: Anti-replay: registra il passo di un codice verificato; il DB
    # rifiuta un passo non successivo all'ultimo (E_TOTP_PASSO_GIA_USATO).
    def registra_uso(self, auth_user_id: int, *, passo: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_totp_registra_uso(%s, %s)", [auth_user_id, passo])

    # Scopo: Consuma un codice di recupero (monouso) dalla sua impronta e
    # restituisce quanti ne restano (E_TOTP_RECOVERY_NON_VALIDO se non c'e').
    def consuma_recovery(self, auth_user_id: int, *, impronta: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_totp_consuma_recovery(%s, %s)", [auth_user_id, impronta])
            return int(fetchone_scalar(cursor))

    # Scopo: Sostituisce il mazzo dei codici di recupero di un device
    # confermato. Chi agisce: la credenziale stessa.
    def rigenera_recovery(self, auth_user_id: int, *, impronte_recupero: Sequence[str]) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_totp_rigenera_recovery(%s, %s::jsonb)",
                [auth_user_id, json.dumps(list(impronte_recupero))],
            )

    # Scopo: Disabilita il secondo fattore cancellando il device. Chi agisce:
    # la credenziale stessa (motivo facoltativo) o un SUPER_ADMIN (motivo
    # obbligatorio, E_TOTP_MOTIVO_OBBLIGATORIO).
    def disabilita_device(self, auth_user_id: int, *, motivo: str | None) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_totp_disabilita_device(%s, %s)", [auth_user_id, motivo])

    # Scopo: Accende o spegne l'obbligo sulla CREDENZIALE. Chi agisce: un
    # SUPER_ADMIN. Non tocca l'obbligo che viene da un profilo.
    def imposta_obbligo(self, auth_user_id: int, *, valore: bool) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_imposta_totp_obbligatorio(%s, %s)", [auth_user_id, valore])
