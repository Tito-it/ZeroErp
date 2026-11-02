# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block della CHIAVE D'INGRESSO (L-4 del piano accessi, D-9):
#        come si trova la credenziale da cio' che la persona digita. Due
#        chiavi: il nome utente (porta admin) e l'email (portale e shop); il
#        reset password le accetta entrambe.
#        Per l'email: come si normalizza, come si trova la sua credenziale
#        (dal DB), e il backend di autenticazione Django che verifica la
#        password su quella credenziale.
#        ⭐ Regola del 2 (ok Tid 2026-10-07): la ricerca per nome utente stava
#        nel serializer del login e nel reset password; ora sta qui.
# Note: la porta admin resta sul nome utente (`ModelBackend`). Il backend qui
#       sotto risponde SOLO a `authenticate(email=..., password=...)`: Django
#       salta i backend la cui firma non accetta le credenziali passate, quindi
#       un login per nome utente non lo attraversa mai.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from apps.core.db.auth_repository import AuthRepository

_auth_repo = AuthRepository()


# Scopo: L'email come chiave d'ingresso: senza spazi ai bordi e minuscola.
# ⛔ La stessa normalizzazione per il lookup e per l'impronta del nome tentato
#    (`nome_tentato`): con due regole diverse, «Ada@x.it» e «ada@x.it»
#    avrebbero un contatore solo se la credenziale esiste, e due se non esiste
#    — l'oracolo del nome che R-7 ha chiuso (brief §13.3). Il DB confronta
#    `lower(email)` (indice unico P-2): un valore gia' minuscolo non cambia.
def normalizza_email(valore: str) -> str:
    return valore.strip().lower()


# Scopo: La credenziale (utente Django) di un nome utente, o None. La stessa
# ricerca di `ModelBackend` (`get_by_natural_key`: uguaglianza esatta, niente
# maiuscole tolte), cosi' lookup del login e `authenticate` trovano la stessa
# credenziale. Il nome arriva gia' ripulito dal chiamante (campo del
# serializer, `strip` del reset).
def credenziale_per_nome_utente(nome: str) -> User | None:
    if not nome:
        return None
    return User.objects.filter(username=nome).first()


# Scopo: La credenziale (utente Django) di un'email, o None. La regola sta nel
# DB (`AuthRepository.find_auth_user_id_per_email`): senza maiuscole, email
# doppie → `E_CREDENZIALE_EMAIL_AMBIGUA`. ⛔ Nessun `except`: un guasto del DB
# non e' «email sconosciuta» (fail-closed, come `_find_user` del login).
def credenziale_per_email(email: str) -> User | None:
    # Il controllo sul valore NORMALIZZATO: di soli spazi e' vuoto anche lui,
    # e non scomoda il DB.
    email = normalizza_email(email or "")
    if not email:
        return None
    auth_user_id = _auth_repo.find_auth_user_id_per_email(email)
    if auth_user_id is None:
        return None
    return User.objects.filter(pk=auth_user_id).first()


class CredenzialePerEmailBackend(ModelBackend):
    """Autentica con email e password (porte portale e shop, L-4).

    Eredita da `ModelBackend` le regole che non devono avere due versioni:
    `user_can_authenticate` (`is_active`) e i permessi. Cambia solo come si
    trova la credenziale.
    """

    # Scopo: La credenziale dell'email se la password e' giusta e puo' entrare,
    # altrimenti None. ⛔ La firma NON ha `**kwargs` ne' `username`: e' cio' che
    # fa saltare questo backend a Django quando il login e' per nome utente.
    # ⭐ Email sconosciuta: si calcola comunque un hash, come fa `ModelBackend`
    #    per un nome utente sconosciuto: il tempo di risposta non deve dire se
    #    l'email ha una credenziale.
    def authenticate(  # type: ignore[override]
        self, request: Any, email: str | None = None, password: str | None = None,
    ) -> User | None:
        if email is None or password is None:
            return None
        user = credenziale_per_email(email)
        if user is None:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
