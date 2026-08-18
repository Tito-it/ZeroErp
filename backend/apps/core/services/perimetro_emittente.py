# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: rispondere, in UN SOLO punto, alla domanda «questa persona sta
#        guardando un emittente solo, o piu' di uno?» — e trarne il rifiuto
#        per le liste che non sanno reggere piu' emittenti.
#
#        Tre consumatori dal primo giorno, ed e' la ragione per cui il
#        building block nasce alla PRIMA occorrenza invece che alla seconda
#        (autorizzazione Tid, 2026-08-18):
#          1. `UiService.get_lista_config` — la chiave `richiede_scelta_emittente`
#             dell'envelope, che il frontend usa per mostrare il cancello;
#          2. `DomainAPIView.lista_codice` — il rifiuto sull'endpoint dei dati,
#             perche' un pannello nel browser non protegge niente;
#          3. (Fase D) il profilo `/me/`, per l'etichetta di perimetro su
#             contatori e ricerca.
#        Se ognuno se la calcolasse per conto suo, i tre prima o poi
#        risponderebbero cose diverse: e' il difetto che il cantiere
#        brief-db-perimetro-emittente-liste-e-gerarchia-ba racconta per intero.
#
# ⚠️ Cosa NON e' (P-2b): un permesso. Non decide *cosa* si puo' vedere —
#        quello lo decidono lo scope e la RLS — decide se una schermata e'
#        LEGGIBILE nella condizione in cui sta per essere aperta. Chi lo
#        implementa come controllo di autorizzazione crea una seconda via
#        d'accesso accanto a quella vera, ed e' la duplicazione che poi diverge.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.db.lista_catalogo_repository import fetch_multi_emittente
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_resolver import PermissionResolver

# Il rifiuto del cancello. Classe `NON_ESEGUIBILE` a catalogo -> 422, e NON
# 403: il diritto c'e', manca una precondizione che l'utente scioglie da se'
# scegliendo un emittente dalla combo di topbar.
E_LISTA_EMITTENTE_DA_SCEGLIERE = "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE"

# Lista dichiarata da una view ma inesistente a catalogo: e' un difetto di
# configurazione NOSTRO, non un rifiuto di perimetro. Stesso codice che usa
# `UiService` quando la lista non si risolve: una cosa sola, un codice solo.
E_LISTA_NON_TROVATA = "E_UI_LISTA_NON_TROVATA"


# Scopo: TRUE se l'utente ha piu' di un emittente nel proprio perimetro
#        effettivo (compreso «tutti»), FALSE se ne ha esattamente uno o
#        nessuno.
#
# ⚠️ La domanda si fa sulla CARDINALITA' dello scope, mai sul ruolo.
#        «Se non e' super admin» sembra equivalente e non lo e': si appoggia a
#        un'identita' invece che al perimetro effettivo, e smette di
#        proteggere il giorno in cui nasce un terzo caso (P-2b). Un super
#        admin che ha scelto un emittente attivo ha cardinalita' 1, e per
#        questa funzione e' identico a un operatore.
#
# ⚠️ I tre stati della convenzione, e nessuno dei tre si legge con un test di
#        verita' (`if ids:` fonderebbe i due estremi opposti):
#          None -> universo, cioe' TUTTI gli emittenti -> multi
#          []   -> nessun accesso                      -> NON multi
#          [x]  -> un emittente solo                   -> NON multi
#          [x, y, ...]                                 -> multi
#
# ⚠️ `[]` (nessun accesso) risponde FALSE, e non e' una svista: chi non vede
#        niente non ha nessuna ambiguita' da sciogliere, e chiedergli di
#        scegliere un emittente gli offrirebbe una tendina vuota. Il suo
#        problema — che dopo P-2a e' una configurazione mancante — si vede
#        dalla lista vuota e da `dbops.vw_operatori_senza_emittente`, non da
#        questo cancello.
def scope_multi_emittente(
    user: Any, *, cache: dict[str, Any] | None = None
) -> bool:
    ids = PermissionResolver.get_emittenti_pk_ids(user, cache=cache)
    if ids is None:
        return True
    return len(ids) > 1


# Scopo: il rifiuto vero e proprio, in un punto solo.
# ⚠️ Non decide NIENTE: chi lo chiama ha gia' stabilito che la lista non e'
#    certificata e che il perimetro e' multiplo. Esiste perche' il messaggio e
#    il codice non finiscano scritti in due posti.
def _rifiuta(lista_codice: str) -> None:
    ErrorManager.raise_error(
        code=E_LISTA_EMITTENTE_DA_SCEGLIERE,
        message=(
            "Questa lista non dice da quale emittente arriva ogni riga: "
            "scegli un emittente per entrare."
        ),
        detail=f"lista='{lista_codice}'",
        context={"lista_codice": lista_codice},
        function_name="core.perimetro_emittente.guard_lista_per_codice",
    )


# Scopo: applica il cancello a una lista, dato il suo codice. E' l'UNICA porta
#        d'ingresso: chi la chiama non deve sapere ne' come si legge il flag di
#        catalogo ne' in che ordine vanno fatte le due domande.
# ⚠️ L'ORDINE delle due domande non e' indifferente, ed e' il motivo per cui
#        questa funzione esiste invece di far leggere il catalogo al chiamante:
#        si guarda PRIMA il perimetro (una query che il resolver mette in cache
#        per richiesta) e solo se e' multiplo si va a leggere il catalogo. Nel
#        99% dei casi — ogni operatore, ogni super admin con un emittente
#        attivo — la seconda query non parte affatto. Invertirle costerebbe un
#        round-trip su OGNI apertura di lista per un cancello che non scatta
#        quasi mai.
# ⚠️ Lista sconosciuta (`None` dal catalogo): NON si rifiuta e non si tace —
#        significa che una view dichiara un `lista_codice` che non esiste, cioe'
#        un difetto di configurazione nostro. Rifiutare direbbe all'utente di
#        scegliere un emittente per un problema che non lo riguarda; tacere
#        lascerebbe il presidio spento senza che nessuno lo sappia. Si solleva
#        l'errore tecnico, che e' quello che descrive il fatto.
def guard_lista_per_codice(
    *,
    user: Any,
    lista_codice: str,
    cache: dict[str, Any] | None = None,
) -> None:
    if not scope_multi_emittente(user, cache=cache):
        return
    multi = fetch_multi_emittente(lista_codice)
    ErrorManager.require(
        multi is not None,
        code=E_LISTA_NON_TROVATA,
        message="Lista non trovata.",
        detail=(
            f"lista_codice='{lista_codice}' dichiarato da una view non esiste "
            "in ui.lista_definizione (o non e' attiva)."
        ),
        context={"lista_codice": lista_codice},
        function_name="core.perimetro_emittente.guard_lista_per_codice",
    )
    if multi:
        return
    # ⚠️ Lo scope NON si richiede: e' gia' stato risolto in testa a questa
    #    funzione. Delegare a un helper che lo ricalcolasse sarebbe costato una
    #    SECONDA query proprio nel ramo raro in cui si arriva fin qui — e senza
    #    una cache passata dal chiamante (la base view non ne ha una) sarebbe
    #    stata una query vera, non un cache hit.
    _rifiuta(lista_codice)
