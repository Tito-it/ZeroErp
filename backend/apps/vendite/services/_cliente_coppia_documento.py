# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il cliente di un documento con la coppia (istanza, utility) sulla
#        testata — preventivo, offerta, contratto — letto dal lato che il
#        payload porta, e il riconoscimento di un cambio di coppia.
# Note: ⭐ BB per la regola del 2 (ok Tid 2026-10-12, brief-db-indirizzi-
#       documento-seguono-il-cliente §8.3; offerta come terzo consumatore, ok
#       Tid 2026-10-14). Prima il preventivo lo risolveva da se'
#       (`_risolvi_cliente_preventivo`), il contratto vietava il cambio e
#       l'offerta mandava la coppia al DB cosi' com'era, lasciando alla FK
#       composta `fk_<doc>_ba_coppia` il rifiuto: tre risposte diverse alla
#       stessa domanda.
#       La FK composta resta il presidio di ultima istanza: qui l'errore si
#       dice prima, sul campo che l'operatore puo' correggere.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.anagrafiche.db.billing_account_repository import BillingAccountRepository
from apps.anagrafiche.services.billing_account_service import istanza_del_billing_account
from apps.core.services.error_manager import ErrorManager

# Le colonne della testata che dicono chi e' il cliente. Se un aggiornamento ne
# cambia una, il DB rifa' la scheda di fornitura (`trg_<doc>_m50_fornitura_
# segue_cliente_upd`) e gli indirizzi presi dall'anagrafica.
COPPIA_CLIENTE: tuple[str, ...] = ("billing_account_id", "istanza_utility_id", "utility_id")


# Scopo: il billing account della coppia (istanza, utility) di un documento,
#        letto dal lato che il payload porta. Ritorna (billing_account_id,
#        istanza_utility_id), entrambi valorizzati.
# Perimetro: dal 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2) preventivo,
#        offerta e contratto hanno sempre il BA, con la FK composta verso il BA
#        della coppia. ⭐ Non e' una scelta fra candidati: la coppia ha UN BA per
#        struttura (`uq_billing_instance_utility`), e il BA ha UNA istanza.
#        - payload col BA: l'istanza e' la sua (BB `istanza_del_billing_account`),
#          e il BA dev'essere QUELLO della coppia (istanza, utility). Se non lo
#          e' — istanza diversa da quella del BA, o BA di un'altra utility —
#          l'errore e' sul BA (`msg_ba_fuori_coppia`);
#        - payload con la sola istanza: il BA e' quello della coppia. Se la
#          coppia non ne ha, la utility non e' dichiarata sull'istanza: e' la
#          regola di `script.fn_check_utility_istanza_coerenza`, qui detta
#          prima del trigger, col codice e sul campo del chiamante.
#        `code` e' il codice di validazione del dominio (400). La utility e'
#        quella del documento: in modifica e' immutabile, quindi la passa il
#        chiamante dalla testata.
# ⚠️ Fino al 2026-10-09 un BA fuori coppia, quando la coppia non aveva BA,
#    usciva «Utility non coerente» sul campo `utility_id`: in modifica la
#    utility e' immutabile, quindi l'operatore era mandato a correggere un
#    campo che non puo' toccare.
def risolvi_cliente_coppia(
    *,
    billing_account_id: int | None,
    istanza_utility_id: int | None,
    utility_id: int,
    code: str,
    msg_ba_fuori_coppia: str,
    function_name: str,
    code_coppia_senza_ba: str | None = None,
    campo_coppia_senza_ba: str = "istanza_utility_id",
) -> tuple[int, int]:
    if billing_account_id is not None:
        istanza_utility_id = istanza_del_billing_account(
            billing_account_id,
            istanza_utility_id,
            code=code,
            function_name=function_name,
        )

    ErrorManager.require(
        istanza_utility_id is not None,
        code=code,
        message="istanza_utility_id obbligatorio.",
        detail="Specificare il billing account o l'istanza utility.",
        context={"field": "istanza_utility_id"},
        function_name=function_name,
    )
    assert istanza_utility_id is not None

    ba_della_coppia = BillingAccountRepository().get_id_by_coppia(int(istanza_utility_id), utility_id)
    if billing_account_id is not None:
        ErrorManager.require(
            ba_della_coppia == int(billing_account_id),
            code=code,
            message=msg_ba_fuori_coppia,
            context={"field": "billing_account_id"},
            detail=(
                f"billing_account_id={billing_account_id}, coppia "
                f"(istanza_utility_id={istanza_utility_id}, utility_id={utility_id}) "
                f"-> billing_account_id={ba_della_coppia}."
            ),
            function_name=function_name,
        )
        return int(billing_account_id), int(istanza_utility_id)

    ErrorManager.require(
        ba_della_coppia is not None,
        code=code_coppia_senza_ba or code,
        message="Utility non coerente con l'istanza selezionata.",
        context={"field": campo_coppia_senza_ba},
        detail=(
            f"istanza_utility_id={istanza_utility_id} non ha il billing "
            f"account per utility_id={utility_id}."
        ),
        function_name=function_name,
    )
    assert ba_della_coppia is not None
    return ba_della_coppia, int(istanza_utility_id)


# Scopo: un id confrontabile a prescindere da come arriva (int dal DB, testo
#        dal JSON); vuoto e None valgono None.
def _come_testo(valore: Any) -> str | None:
    if valore is None or valore == "":
        return None
    return str(valore)


# Scopo: l'aggiornamento cambia il cliente del documento? Vero se il payload
#        porta una colonna della coppia con un valore diverso da quello della
#        testata (`attuale`, le stesse chiavi lette dal DB).
# Perimetro: serve a chi, nella stessa richiesta, scriverebbe anche la scheda
#        di fornitura del form. Con un cambio di coppia il trigger
#        `trg_<doc>_m50_fornitura_segue_cliente_upd` l'ha appena rifatta dal
#        contatore nuovo, e quella del form e' del contatore di prima: non si
#        applica (R-BE-6 di brief-db-indirizzi-documento-seguono-il-cliente,
#        D-5 di Tid). Il confronto e' sul testo: dal JSON un id puo' arrivare "12".
def coppia_cambiata(payload: Mapping[str, Any], attuale: Mapping[str, Any]) -> bool:
    return any(
        chiave in payload and _come_testo(payload[chiave]) != _come_testo(attuale.get(chiave))
        for chiave in COPPIA_CLIENTE
    )
