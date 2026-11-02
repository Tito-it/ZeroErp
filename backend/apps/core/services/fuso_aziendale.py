# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL FUSO DELL'AZIENDA nel processo Python — sede unica.
#
#        Il fuso e' un DATO del database (`config.parameters.SYSTEM_FUSO_ORARIO`,
#        letto e validato da `script.fn_fuso_operativo()`), mai una costante del
#        codice: `settings.TIME_ZONE` e' 'UTC', un valore neutro, e non dice
#        niente sull'azienda. Ogni passaggio fra un istante e il calendario —
#        «che giorno e' oggi», «che ora mostro» — passa di qui, e il fuso di chi
#        esegue (processo, host, sessione PG) diventa irrilevante.
#        Regola completa: work-done/brief-be-db-fe-un-solo-fuso-aziendale.md §1.
#
#          fuso_aziendale()          -> ZoneInfo del parametro (cache di processo)
#          oggi_aziendale()          -> il giorno di adesso, nel fuso dell'azienda
#          attiva_fuso_aziendale()   -> `timezone.activate` col fuso dell'azienda
#          fuso_aziendale_forzato(n) -> context manager per i test
#
#        ⭐ UNA LETTURA PER PROCESSO (decisione T-6): il fuso si legge al primo
#        uso e non si invalida. Un cambio del parametro vale dal riavvio
#        successivo del backend; non c'e' meccanismo per il cambio a caldo.
#
#        ⛔ NESSUN RIPIEGO. Parametro assente/vuoto/sconosciuto al DB ->
#        `E_CONFIG_MANCANTE` dalla funzione DB; noto al DB ma non all'archivio
#        dei fusi di Python -> `ImproperlyConfigured`. Un ripiego a UTC o a
#        `settings.TIME_ZONE` darebbe date sbagliate senza un errore.
#
#        ⚠️ Chi converte DICHIARA il fuso: `oggi_aziendale` e
#        `locale_formatters.in_ora_locale` lo passano esplicito, non si
#        appoggiano al fuso attivato. L'attivazione (middleware, comandi) serve
#        a cio' che Django converte da se' — template, `|date`, DRF — e non e'
#        una condizione perche' i BB rispondano giusto.
# ------------------------------------------------------------

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.core.db.core_repository import CoreRepository

_lock = threading.Lock()
_fuso: ZoneInfo | None = None


# Scopo: Il fuso dell'azienda come `ZoneInfo`. Alla prima chiamata del processo
#        lo chiede al DB (`CoreRepository.get_fuso_operativo`), poi risponde
#        dalla cache. Fail-loud: vedi l'intestazione del modulo.
def fuso_aziendale() -> ZoneInfo:
    global _fuso
    fuso = _fuso
    if fuso is not None:
        return fuso
    with _lock:
        if _fuso is None:
            _fuso = _zoneinfo_da_nome(CoreRepository().get_fuso_operativo())
        return _fuso


# Scopo: Il giorno di ADESSO nel fuso dell'azienda. E' l'«oggi» di Python:
#        `date.today()` e' il giorno del processo (UTC), e il giorno del DB e'
#        `script.fn_data_operativa()` — che legge lo stesso parametro, quindi i
#        due coincidono per costruzione.
# ⚠️ Dove la data finisce comunque nel DB (data di un documento, `valido_dal`
#    di default) non la si calcola qui: la si omette e decide il DB
#    (`COALESCE(%s, script.fn_data_operativa())`), la decisione resta in un livello.
def oggi_aziendale() -> date:
    return timezone.localdate(timezone=fuso_aziendale())


# Scopo: Attiva il fuso dell'azienda per il thread corrente (richiesta,
#        comando). Lo usano `FusoAziendaleMiddleware` e `ComandoAziendale`.
def attiva_fuso_aziendale() -> None:
    timezone.activate(fuso_aziendale())


# Scopo: Nei TEST, fissa il fuso dell'azienda a `nome` per la durata del blocco
#        (e lo attiva), poi rimette com'era. Il fuso e' un'ipotesi del test, non
#        del database su cui gira: un test che asserisce un'ora o un giorno lo
#        dichiara qui. Prende il posto di `override_settings(TIME_ZONE=...)`, che
#        dal 2026-10-09 non tocca piu' il fuso dell'azienda.
@contextmanager
def fuso_aziendale_forzato(nome: str) -> Iterator[ZoneInfo]:
    global _fuso
    precedente = _fuso
    forzato = _zoneinfo_da_nome(nome)
    _fuso = forzato
    try:
        with timezone.override(forzato):
            yield forzato
    finally:
        _fuso = precedente


# Scopo: Dal nome IANA al `ZoneInfo`. Il DB ha gia' validato il nome contro
#        `pg_timezone_names`; qui si ferma solo un nome che l'archivio dei fusi
#        di Python non conosce (tzdata dell'host diverso da quello del server PG).
def _zoneinfo_da_nome(nome: str) -> ZoneInfo:
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"SYSTEM_FUSO_ORARIO = {nome!r}: fuso noto al database ma non "
            f"all'archivio dei fusi di Python (tzdata dell'host)."
        ) from exc
