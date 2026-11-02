# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.db.lista_catalogo_repository import fetch_flag_perimetro
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


# Nome del parametro con cui l'endpoint di CONFIG di una lista riceve
# l'emittente gia' fissato dal contesto che la apre.
#
# ⭐ NEUTRO di proposito, e non `emittente_soggetto_ruolo_id`. Qui il valore non
#    filtra niente: serve solo a dire «uno e' gia' scelto». L'endpoint dei DATI
#    invece filtra davvero, e li' il nome e' quello del dominio — che nel
#    progetto e' di due famiglie diverse (`..._soggetto_ruolo_id` e' il
#    soggetto-ruolo, `emittente_fiscale_id` e' la PK: `feedback_emittente_pk_vs_
#    soggetto_ruolo`). Dare al parametro di config il nome di UNA delle due
#    obbligherebbe la lista che usa l'altra a mandare un id sotto il nome
#    sbagliato — e a quel punto il nome mentirebbe.
# ⚠️ Sta qui e non nella view perche' lo leggono in due (l'endpoint di config e
#    il client `ui-api.js`): rinominato da una parte sola, l'API concederebbe e
#    il pannello continuerebbe a sbarrare.
PARAM_EMITTENTE_ESPLICITO = "emittente_esplicito"


# Scopo: l'emittente che una richiesta FISSA, letto dalla query string.
#        `None` quando non ne fissa uno, ed e' il caso di gran lunga piu'
#        frequente.
#
# ⛔ Tre modi di NON fissare un emittente, e vanno distinti dallo zero valori:
#      · piu' valori (`?e=1&e=2`) -> e' l'ambiguita' che il cancello rifiuta;
#        leggerne uno solo, come farebbe un `.get()` distratto, la
#        trasformerebbe in un lasciapassare;
#      · valore vuoto             -> il frontend che manda `?e=` non ha scelto;
#      · valore non numerico      -> `?e=pippo` non e' un emittente.
#
# ⚠️ Non e' una validazione di autorizzazione e non pretende di esserlo: che
#    quell'emittente sia visibile lo decidono scope e RLS. Qui si decide solo se
#    la SCHERMATA e' leggibile, e una stringa che non e' un id non la rende tale.
def emittente_esplicito_da_query(query_params: Any, *, nome: str) -> int | None:
    if not nome or query_params is None:
        return None
    valori = [v for v in query_params.getlist(nome) if (v or "").strip()]
    if len(valori) != 1:
        return None
    grezzo = valori[0].strip()
    return int(grezzo) if grezzo.isdigit() else None


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
# Scopo: LA domanda, in un punto solo: «questa lista, per questa persona, in
#        questo momento, va sbarrata?». Rispondono di qui sia il cancello
#        dell'endpoint sia la chiave `richiede_scelta_emittente` dell'envelope.
#
# ⭐ ESTRATTA IL 2026-09-01, e la ragione e' l'header di questo file: i due
#    consumatori la calcolavano ognuno per conto proprio con la stessa formula
#    scritta due volte. Finche' sono uguali non si vede niente; il giorno che
#    una delle due cresce di un termine — ed e' successo oggi, con l'emittente
#    esplicito — l'endpoint e il pannello dicono cose diverse e l'operatore
#    vede una schermata sbarrata su dati che l'API gli darebbe.
#
# ⭐ TRE TERMINI, e l'ordine e' quello che costa meno:
#      1. emittente esplicito nella richiesta -> nessuna ambiguita' (in memoria);
#      2. lista certificata multi-emittente   -> nessuna ambiguita' (in memoria);
#      3. cardinalita' dello scope            -> costa una query, e va per ultima.
#
# ⚠️ Il primo termine NON e' un permesso, e non pretende di esserlo: dice solo
#    che la richiesta FISSA un emittente, quindi la schermata e' leggibile. Se
#    quell'emittente sia poi visibile lo decidono scope e RLS, che restano le
#    uniche sedi di quella risposta (vedi l'header, «cosa NON e'»).
def richiede_scelta_emittente(
    *,
    user: Any,
    multi_emittente: bool,
    perimetro_emittente: bool = True,
    emittente_esplicito: Any = None,
    cache: dict[str, Any] | None = None,
) -> bool:
    # ⭐ TRE MODI DI NON DOVER SCEGLIERE, E SONO TRE RAGIONI DIVERSE. Restano
    #    tre rami e non una condizione sola in OR: chi legge deve vedere PERCHE'
    #    si entra, non solo che si entra — il giorno che una delle tre cambia,
    #    una condizione unica costringe a rileggerle tutte per capire quale.
    #
    #    1. la richiesta FISSA un emittente     -> l'ambiguita' e' gia' sciolta;
    #    2. la lista non ha un perimetro        -> non c'e' NIENTE da scegliere
    #       (catalogo globale: nessuna riga appartiene a un emittente, §12.1);
    #    3. la lista e' certificata multi        -> l'emittente c'e', e la riga
    #       lo dice da se'.
    if emittente_esplicito is not None:
        return False
    if not perimetro_emittente:
        return False
    if multi_emittente:
        return False
    # ⚠️ Ultimo, ed e' l'unico dei quattro termini che costa una query.
    return scope_multi_emittente(user, cache=cache)


def guard_lista_per_codice(
    *,
    user: Any,
    lista_codice: str,
    cache: dict[str, Any] | None = None,
    emittente_esplicito: Any = None,
) -> None:
    # ⚠️ Una cache anche quando il chiamante non la porta (la base view non ne
    #    ha una): sotto, `richiede_scelta_emittente` ripone la stessa domanda
    #    sullo scope, e senza cache sarebbe una SECONDA query per una risposta
    #    gia' data. Con la cache e' un hit, e la formula resta in un posto solo.
    cache = {} if cache is None else cache
    if not scope_multi_emittente(user, cache=cache):
        return
    flag = fetch_flag_perimetro(lista_codice)
    ErrorManager.require(
        flag is not None,
        code=E_LISTA_NON_TROVATA,
        message="Lista non trovata.",
        detail=(
            f"lista_codice='{lista_codice}' dichiarato da una view non esiste "
            "in ui.lista_definizione (o non e' attiva)."
        ),
        context={"lista_codice": lista_codice},
        function_name="core.perimetro_emittente.guard_lista_per_codice",
    )
    # ⭐ La decisione NON si riscrive qui: e' la stessa che risponde all'envelope
    #    della config, e due copie della stessa conclusione finiscono per dire
    #    cose diverse — l'API concede e il pannello sbarra, o viceversa.
    #    Quello che questa funzione aggiunge e' solo il pezzo che il chiamante
    #    non ha in mano: i DUE flag di perimetro della lista, che nell'envelope
    #    arrivano gia' e qui vanno letti dal catalogo.
    assert flag is not None
    if not richiede_scelta_emittente(
        user=user,
        multi_emittente=flag.multi_emittente,
        perimetro_emittente=flag.perimetro_emittente,
        emittente_esplicito=emittente_esplicito,
        cache=cache,
    ):
        return
    _rifiuta(lista_codice)
