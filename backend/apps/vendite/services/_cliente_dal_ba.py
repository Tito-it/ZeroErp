# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Il cliente di un documento esecutivo e' quello del suo billing
#        account», lato Python: la voce della mappa vincoli che traduce la
#        rete FK composta (`fk_<doc>_ba_cliente`) nel codice del BB a DB.
# Note: ⭐ La regola la applica il DB (BB `script.fn_cliente_dal_billing_account`,
#       chiamato dai `trgfn_<doc>_normalize`, brief-db-esecutivi-ba-coppia),
#       che risponde PRIMA col suo codice. La FK composta e' la rete sotto:
#       qui la si traduce nello STESSO codice, cosi' l'API dice una cosa sola
#       chiunque abbia rifiutato la riga.
# ------------------------------------------------------------

from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK

# Il codice del BB a DB: ruolo (o destinatario) e utility diversi da quelli
# del billing account.
E_DOC_CLIENTE_DIVERSO_DA_BA = "E_DOC_CLIENTE_DIVERSO_DA_BA"

# Voce `(codice, messaggio, campo)` per le mappe `fk_constraints` di
# `make_db_errors_translator`, sotto il nome della FK composta del documento.
# ⭐ UNA sede per tre service (ordini, DDT, resi — regola del 2): fino al
#    2026-10-10 ognuno la ricopiava con la sua frase, e le frasi divergevano.
#    Il messaggio e' quello a catalogo del codice, non uno scritto qui.
# ⚠️ Il campo e' `billing_account_id`: e' l'unico che l'operatore sceglie; ruolo
#    e utility sono copie che scrive il DB.
FK_CLIENTE_DIVERSO_DA_BA: tuple[str, str, str] = (
    E_DOC_CLIENTE_DIVERSO_DA_BA,
    USER_MESSAGE_FALLBACK[E_DOC_CLIENTE_DIVERSO_DA_BA],
    "billing_account_id",
)
