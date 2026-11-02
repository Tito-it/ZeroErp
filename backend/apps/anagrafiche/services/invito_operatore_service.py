# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invito della veste OPERATORE. Qui resta solo cio' che e'
#        dell'operatore: il check d'invitabilita' del DB e la veste da
#        invitare. Emissione del token, reinvio, email e attivazione sono il
#        building block unico `apps.core.services.invito_veste` (L-3, regola
#        del 2): la stessa strada di portale e shop.
#        ⛔ Dal 2026-09-25 l'invito NON sovrascrive piu' la password (A-1) e
#        non accende la veste (A-3): la credenziale puo' essere di una persona
#        che e' anche cliente del portale, e la veste la accende solo
#        l'attivazione.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import jsonb_out
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.risorse_umane_core_repository import RisorseUmaneCoreRepository
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.invito_veste import PORTA_OPERATORE, InvitoVeste, maschera_email

logger = logging.getLogger("security")

E_INVITO = PORTA_OPERATORE.codice_invito

# I motivi di `fn_check_operatore_invitabile` per cui l'id indicato non nomina
# un operatore: credenziale inesistente, o credenziale senza veste OPERATORE.
# Sono un «non trovato» (404), non un dato errato (E-4 di
# analisi-be-difetti-emersi-verifica-doc-api-core, 2026-10-08) — lo stesso
# codice e la stessa lettura del dettaglio operatore
# (`AmmSoftwareService`: categoria diversa da OPERATORE → non trovato).
# Gli altri motivi (veste gia' attiva, fuori finestra, senza email, piu'
# vesti spente) restano `E_INVITO_OPERATORE`: l'operatore c'e'.
_MOTIVI_OPERATORE_NON_TROVATO = frozenset({"UTENTE_NON_TROVATO", "SENZA_VESTE_OPERATORE"})


class InvitoOperatoreService:
    """Invito della veste operatore: verifica, emette, spedisce, reinvia."""

    def __init__(self) -> None:
        self._auth_repo = AuthRepository()
        self._ru_repo = RisorseUmaneCoreRepository()
        self._invito = InvitoVeste(auth_repo=self._auth_repo)

    # Scopo: Invia (o reinvia) l'invito della veste OPERATORE spenta.
    # L'invitabilita' la decide il DB (`fn_check_operatore_invitabile`: veste
    # spenta, nella finestra, email presente — D-8); la veste da invitare e'
    # l'unica OPERATORE spenta della credenziale. I token pendenti della veste
    # si invalidano sempre nella transazione del nuovo (BB, A-4): `reinvio`
    # serve solo al log.
    # ⭐ D-3 (2026-10-04): l'invito e' l'UNICA strada per riaccendere un
    # operatore spento. Il gesto dell'amministratore riapre la risorsa umana
    # (il rapporto) nella transazione dell'emissione; la veste (la porta)
    # resta spenta e la accende la persona attivando. Su un operatore mai
    # attivato la risorsa umana e' gia' aperta: nessuna scrittura.
    # ⛔ Il rifiuto NON compone il testo col motivo (§16 del brief
    # blocco-login, 2026-09-27): il DB manda `reason` (codice macchina) e
    # `reason_key` (chiave i18n), non una frase. Il messaggio e' quello del
    # catalogo; codice e chiave viaggiano nel contesto, per il log. A video il
    # perche' lo dice gia' il drawer, dalla stessa check (`invite_reason*`).
    def invia_invito(
        self, auth_user_id: int, invitato_da_user_id: int, *, reinvio: bool = False
    ) -> dict[str, Any]:
        check = self._check_invitabile(auth_user_id)
        ErrorManager.require(
            check.get("reason") not in _MOTIVI_OPERATORE_NON_TROVATO,
            code="E_AMM_OPERATORE_NOT_FOUND",
            message=f"Operatore {auth_user_id} non trovato.",
            context={"auth_user_id": auth_user_id, "reason": check.get("reason")},
        )
        ErrorManager.require(
            check.get("invitabile", False),
            code=E_INVITO,
            message=ErrorPolicyRegistry.resolve(E_INVITO).user_message,
            context={
                "auth_user_id": auth_user_id,
                "reason": check.get("reason"),
                "reason_key": check.get("reason_key"),
            },
        )
        email = check["email"]
        identita_id = self._veste_da_invitare(auth_user_id)

        with transaction.atomic():
            riaperta = self._ru_repo.riapri_risorsa_umana_della_veste(identita_id) > 0
            emissione = self._invito.emetti(
                PORTA_OPERATORE,
                auth_user_id=auth_user_id,
                identita_id=identita_id,
                ruolo_applicativo=RUOLO_APPLICATIVO_OPERATORE,
                invitato_da_user_id=invitato_da_user_id,
            )

        nomi = self._auth_repo.get_nomi_credenziale(auth_user_id) or {}
        # ⭐ `inviato` e' l'esito della MAIL, non della chiamata (F-3): il
        #    token c'e' comunque, e il client con `false` dice di reinviare.
        inviato = self._invito.spedisci(
            PORTA_OPERATORE,
            emissione,
            auth_user_id=auth_user_id,
            identita_id=identita_id,
            destinatario=email,
            invitato_da_user_id=invitato_da_user_id,
            # Il nome utente (D-9): il template lo scrive, e senza valore il
            # motore lascerebbe il segnaposto letterale «{{username}}».
            variabili={
                "nome": nomi.get("first_name", ""),
                "cognome": nomi.get("last_name", ""),
                "username": nomi.get("username", ""),
            },
            # Reparto dell'operatore: sceglie la casella mittente.
            unita_organizzativa_id=self._auth_repo.get_unita_organizzativa_id(auth_user_id),
        )

        logger.info(
            "security.invito_inviato user_id=%s identita_id=%s da=%s reinvio=%s is_cross=%s "
            "inviato=%s risorsa_umana_riaperta=%s",
            auth_user_id, identita_id, invitato_da_user_id, reinvio, emissione.is_cross,
            inviato, riaperta,
        )
        return {"inviato": inviato, "email": maschera_email(email), "is_cross": emissione.is_cross}

    # Scopo: Reinvia l'invito: la stessa strada (i token pendenti della veste
    # si invalidano DENTRO la transazione del nuovo; prima era una scrittura
    # separata, e se l'emissione falliva la persona restava senza link, A-4).
    def reinvia_invito(self, auth_user_id: int, invitato_da_user_id: int) -> dict[str, Any]:
        return self.invia_invito(auth_user_id, invitato_da_user_id, reinvio=True)

    # Scopo: La veste OPERATORE spenta da invitare. Il check del DB ha gia'
    # escluso quella attiva; il modello ammette piu' vesti spente sullo stesso
    # ruolo (l'unique vale solo WHERE attivo), e sceglierne una a caso
    # deciderebbe per la prima che capita: con piu' di una si rifiuta.
    def _veste_da_invitare(self, auth_user_id: int) -> int:
        spente = [
            v for v in self._auth_repo.find_identita_per_ruolo(
                auth_user_id, RUOLO_APPLICATIVO_OPERATORE
            )
            if not v["attivo"]
        ]
        ErrorManager.require(
            len(spente) == 1,
            code=E_INVITO,
            message=(
                "Identita operatore da invitare non trovata."
                if not spente else
                "Piu' identita operatore spente sulla stessa credenziale: "
                "richiede intervento manuale."
            ),
            context={"auth_user_id": auth_user_id, "vesti_spente": len(spente)},
        )
        return int(spente[0]["id"])

    # Scopo: Chiama fn_check_operatore_invitabile e ritorna il risultato JSONB
    # `{invitabile, reason, reason_key, email}` (dal `20260927-01`).
    # Il ripiego ha la stessa forma: non invitabile, senza un motivo del DB da
    # riportare (nessun codice inventato qui).
    def _check_invitabile(self, auth_user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_check_operatore_invitabile(%s)", [auth_user_id])
            row = cursor.fetchone()
            if row and row[0]:
                return jsonb_out(row[0])
        return {"invitabile": False, "reason": None, "reason_key": None, "email": None}
