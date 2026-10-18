# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura unica della diagnostica di dominio da un'eccezione DB —
#        codice (CONSTRAINT), campo da correggere (COLUMN) e bersaglio
#        (DATATYPE), piu' il BB `diagnostica_db` che li legge in una volta.
# Note: Modulo volutamente senza dipendenze interne (lo importano
#       error_translator, error_manager e payload_helpers: qualsiasi import
#       verso quei moduli creerebbe un ciclo).
# ------------------------------------------------------------

"""Da dove arriva il codice errore di dominio, e in che ordine.

Dal 2026-08-05 `script.fn_log_and_raise_error` fa viaggiare il codice in un
campo STRUTTURATO dell'eccezione (`RAISE ... USING CONSTRAINT = p_error_code`),
non piu' solo nel testo. Il contratto e':

    SQLSTATE = 'P0001' + `constraint_name` valorizzato  =  errore di dominio

Prima esisteva solo il ripiego a regex, ed e' importante capire perche'
funzionava quasi sempre pur non essendo una difesa: il driver allega al testo
dell'eccezione anche lo *statement chiamante*, dove il codice compare scritto a
mano (`PERFORM script.fn_log_and_raise_error(..., 'E_XXX', ...)`). Il backend
leggeva il SORGENTE della chiamata, non il dato — e falliva sulle guard che il
codice lo passano da una variabile (`v_motivi -> 0 ->> 'codice'`: le transizioni
di stato di ordini, commesse, preventivi, lotti, resi) e sui codici a catalogo
senza prefisso `E_`.

⚠️ **Il ripiego a regex resta, e non e' un residuo da togliere**: nel DB vivo ci
sono ~135 `RAISE EXCEPTION` diretti in ~46 funzioni che non passano dall'helper.
Per quelli il campo esce vuoto e il testo e' l'unica strada. Si potra' togliere
il giorno in cui quei RAISE saranno zero — cantiere a se'.

⭐ **I canali strutturati sono TRE**, e sono nati uno per volta dalla stessa
mossa: `CONSTRAINT` porta il **codice** (2026-08-05), `COLUMN` porta il **campo
da correggere** (2026-08-08), `DATATYPE` porta il **bersaglio** — su quale cosa
l'errore e' successo (2026-08-23). Chi ne aggiunge un quarto guardi questi tre:
il patto e' sempre lo stesso, «`P0001` + casella valorizzata».

Riferimenti: `docs/it/dev/work-done/brief-db-codice-errore-strutturato.md` e
`docs/it/dev/work-in-progress/brief-db-bersaglio-errore.md` (§4.4, §7-bis).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Convenzione codici applicativi: `E_<DOMINIO>_<DETTAGLIO>`.
# ⚠️ Non vede i codici a catalogo senza prefisso (`PRATICHE_*`, `PREV_*`,
# `ERRORE_PARAMETRI`, ...): e' un limite del RIPIEGO, non del campo strutturato,
# ed e' una delle ragioni per cui il campo esiste.
# Il gruppo di cattura e' ridondante con `group(0)` ma tiene compatibile chi
# usava `DB_ERROR_CODE_RE.search(...).group(1)` (alias in payload_helpers).
APP_ERROR_CODE_RE = re.compile(r"\b(E_[A-Z][A-Z0-9_]+)\b")

# SQLSTATE di `RAISE EXCEPTION` senza ERRCODE esplicito: l'unico su cui il campo
# `constraint_name` puo' essere un codice applicativo.
SQLSTATE_RAISE_EXCEPTION = "P0001"


# Scopo: Estrae il codice di dominio dal campo strutturato dell'eccezione DB.
#        Ritorna None se l'eccezione non viene dall'helper DB (o se il campo e'
#        vuoto), lasciando decidere al chiamante se ripiegare sul testo.
def structured_db_error_code(exc: BaseException) -> str | None:
    return codice_strutturato_del_driver(getattr(exc, "__cause__", None))


# Scopo: Lo SQLSTATE di un errore del DRIVER (psycopg), o None se l'oggetto non
#        ne porta uno: non e' un errore del driver, oppure e' un errore lato
#        client (connessione mai aperta), che uno SQLSTATE non ce l'ha.
# ⚠️ Riceve l'errore del driver, non quello di Django: e' la lettura che le
#    funzioni qui sopra fanno sulla `__cause__`, messa in una sede sola per chi
#    l'errore del driver lo ha gia' in mano (`job_run`, che lo cerca lungo la
#    catena delle cause).
def sqlstate_del_driver(err: object) -> str | None:
    return getattr(err, "sqlstate", None) or getattr(err, "pgcode", None) or None


# Scopo: Il codice di dominio dal campo strutturato di un errore del DRIVER: il
#        contratto «`P0001` + `constraint_name` valorizzato». E' il corpo di
#        `structured_db_error_code`, che lo chiama sulla `__cause__`.
def codice_strutturato_del_driver(cause: object) -> str | None:
    sqlstate = sqlstate_del_driver(cause)
    # ⚠️ Il guard sullo SQLSTATE non e' prudenza, e' necessario: su una
    # violazione di vincolo vera (classe 23xxx) `constraint_name` contiene il
    # nome del vincolo DB (`uq_...`, `fk_...`). Prenderlo per un codice
    # applicativo scavalcherebbe `map_integrity_error` — che quei vincoli li
    # traduce in codici di dominio — e produrrebbe un codice inesistente,
    # quindi un 500 al posto di un 409 parlante.
    if sqlstate != SQLSTATE_RAISE_EXCEPTION:
        return None
    diag = getattr(cause, "diag", None)
    # ⚠️ `or None`: quando il codice viene da un'espressione che vale NULL il
    # campo arriva come STRINGA VUOTA, non come None. Senza questo si
    # propagherebbe un codice vuoto invece di ripiegare sul testo.
    return getattr(diag, "constraint_name", None) or None


# Un nome di colonna/campo plausibile. Non e' difesa da un attacco — il nome lo
# scrive chi ha scritto la funzione PL/pgSQL — e' il guard che impedisce a un
# valore inatteso di rimbalzare al client dentro l'envelope.
_COLUMN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


# Scopo: ⭐ IL CAMPO CHE L'OPERATORE DEVE CORREGGERE, dal campo strutturato
#        `COLUMN` dell'eccezione. E' il gemello di `structured_db_error_code`:
#        stesso meccanismo, altro campo del protocollo.
#
#        DA DOVE ARRIVA, e sono due strade che convergono:
#
#        1. `RAISE ... USING COLUMN = 'partita_iva'` in PL/pgSQL — la strada
#           deliberata (piano BE §12, passo 4). Non serve un parametro nuovo di
#           `script.fn_log_and_raise_error`: l'opzione e' gia' nel protocollo,
#           esattamente come `CONSTRAINT` porta gia' il codice dal 2026-08-05;
#        2. PostgreSQL da solo, su una violazione **NOT NULL** (SQLSTATE 23502),
#           dove `column_name` e' la colonna che manca. Li' il campo e' vero
#           senza che nessuno lo scriva.
#
#        ⚠️ QUI NON SERVE IL GUARD SULLO SQLSTATE che `structured_db_error_code`
#        ha su `constraint_name`, e la ragione va detta perche' l'asimmetria
#        sorprende: `constraint_name` su un 23xxx contiene il nome del VINCOLO
#        (`uq_...`), che scambiato per un codice applicativo produrrebbe un 500.
#        `column_name` invece contiene sempre e solo un nome di colonna: su un
#        23502 e' il campo mancante, che e' proprio cio' che serve. Non c'e'
#        nessun secondo significato da cui difendersi.
#
#        ⚠️ Il nome e' quello della COLONNA. Nella quasi totalita' dei casi
#        coincide con la chiave del payload; dove il service rinomina, il client
#        non trovera' l'input e non evidenziera' nulla — inerte, non sbagliato.
def structured_db_error_field(exc: BaseException) -> str | None:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None)
    # `or None`: come per il codice, un campo che nasce da un'espressione NULL
    # arriva come stringa vuota.
    nome = getattr(diag, "column_name", None) or None
    if nome is None or not _COLUMN_RE.match(nome):
        return None
    return nome


# Scopo: Cerca un codice applicativo `E_*` nel testo dell'eccezione (ripiego
#        storico, valido per i RAISE diretti che non passano dall'helper).
def app_error_code_from_text(message: str) -> str | None:
    match = APP_ERROR_CODE_RE.search(message)
    return match.group(0) if match else None


# Scopo: Il codice di dominio di un'eccezione DB, campo strutturato per primo e
#        testo come ripiego. `text` esplicito per i chiamanti che hanno gia' il
#        testo in mano e non vogliono ricalcolare `str(exc)`.
def db_error_code(exc: BaseException, *, text: str | None = None) -> str | None:
    code = structured_db_error_code(exc)
    if code is not None:
        return code
    return app_error_code_from_text(text if text is not None else str(exc))


# Scopo: Diagnostica psycopg dell'eccezione DB (o None se non e' un errore DB
#        con causa psycopg). Centralizza il doppio `getattr` che i chiamanti
#        ripetevano per leggere message_primary/detail/hint.
def db_diag(exc: BaseException) -> Any | None:
    return getattr(getattr(exc, "__cause__", None), "diag", None)


# ⭐ IL BERSAGLIO — terzo canale strutturato, dal 2026-08-23 lato DB.
#
# Un tipo di entita' logica e' MAIUSCOLO_CON_UNDERSCORE (`FATTURA`, `TASK_RUN`,
# `DDT_VENDITA`): e' un codice di `config.tipi_entita`, non un nome di tabella —
# il §4.2 del brief vieta espressamente che il nome della tabella esca di qui.
_TIPO_ENTITA_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,30}$")
# L'identificativo e' un intero oppure un uuid: `config.tipi_entita.key_selector`
# dichiara quale dei due, ma qui non serve saperlo — serve solo che non sia
# testo arbitrario in viaggio verso il client.
#
# ⚠️ E' la regex che scrive il database, con UNA differenza deliberata: qui si
# pretende almeno un carattere alfanumerico. La sua ammette un `-` nudo, e un
# `FATTURA:-` produrrebbe un pulsante «Apri Fattura -» che apre un pannello
# vuoto — cioe' precisamente il vicolo cieco che il §4.3 vieta. Un bersaglio
# scartato non fa danno; uno che promette una destinazione inesistente si'.
_ID_ENTITA_RE = re.compile(r"^(?=.*[0-9a-fA-F])[0-9a-fA-F-]{1,36}$")

# ⛔ Il tetto e' CINQUE, ed e' lo stesso numero scritto dentro
# `script.fn_log_and_raise_error`: oltre, il frontend non disegna piu' un gesto
# ma un elenco. Si ripete qui perche' le due meta' dello stesso canale vanno
# guardate uguale — come gia' per la regex di `COLUMN`.
MAX_BERSAGLI = 5


@dataclass(frozen=True)
class Bersaglio:
    """Su QUALE cosa l'errore e' successo: un tipo logico e un identificativo."""

    tipo: str
    id: str

    # Scopo: La forma che viaggia nell'envelope API. ⚠️ Le chiavi sono INGLESI
    #        (`type`/`id`) come tutte quelle dell'envelope, e la traduzione
    #        avviene qui e in nessun altro posto.
    def to_envelope(self) -> dict[str, str]:
        return {"type": self.tipo, "id": self.id}


# Scopo: ⭐ IL BERSAGLIO dell'errore, dal campo strutturato `DATATYPE`
#        dell'eccezione. Terzo della famiglia, dopo il codice (`CONSTRAINT`,
#        05/08) e il campo da correggere (`COLUMN`, 08/08).
#
#        Forma sul canale: `TIPO:id[,TIPO:id]`, al massimo cinque elementi.
#        Stringa vuota = nessun bersaglio (e' il caso normale, non un difetto).
#
#        ⛔ QUI IL GUARD SULLO SQLSTATE SERVE, al contrario di `COLUMN`, e la
#        ragione e' la stessa che lo rende necessario su `CONSTRAINT`: fuori da
#        `P0001` quel campo lo riempie PostgreSQL da se'. Su un `22P02`
#        («invalid input syntax for type integer») `datatype_name` contiene il
#        nome di un tipo PostgreSQL, non un tipo di entita' logica: senza guard
#        si manderebbe il frontend ad aprire un `integer`.
#        Il patto e' quello gia' scritto due volte: «`P0001` + casella
#        valorizzata = bersaglio».
#
#        ⚠️ Un elemento malformato si SCARTA e non fa perdere gli altri: la
#        meta' che scrive ha la stessa regola (un bersaglio storto lascia la
#        casella vuota e non distrugge mai l'errore di dominio). Un canale
#        d'errore non puo' essere quello che rompe l'errore.
def structured_db_error_target(exc: BaseException) -> tuple[Bersaglio, ...]:
    cause = getattr(exc, "__cause__", None)
    if sqlstate_del_driver(cause) != SQLSTATE_RAISE_EXCEPTION:
        return ()
    diag = getattr(cause, "diag", None)
    # `or ""`: come per il codice e per il campo, un valore che nasce da
    # un'espressione NULL arriva come STRINGA VUOTA, non come None.
    grezzo = getattr(diag, "datatype_name", None) or ""
    if not grezzo:
        return ()
    bersagli: list[Bersaglio] = []
    for pezzo in grezzo.split(","):
        tipo, separatore, identificativo = pezzo.partition(":")
        if not separatore:
            continue
        if not _TIPO_ENTITA_RE.match(tipo) or not _ID_ENTITA_RE.match(identificativo):
            continue
        bersagli.append(Bersaglio(tipo=tipo, id=identificativo))
        if len(bersagli) >= MAX_BERSAGLI:
            break
    return tuple(bersagli)


# Scopo: I bersagli nella forma che esce dal confine — `[{"type", "id"}]` —
#        oppure `None` quando non ce ne sono.
#
# ⭐ ESISTE PERCHE' ERA IN TRE COPIE (rilevato in revisione, 2026-08-24):
#    l'envelope, il blob del runner e il `meta` della riga persistita facevano
#    ognuno la propria `[b.to_envelope() for b in ...] or None`. Tre produttori
#    diversi della stessa forma sono tre punti in cui divergere — proprio dove
#    il consumatore a video e' UNO SOLO.
#
# ⚠️ `None` e non `[]`, ed e' la stessa disciplina che il team DB ha scritto nel
#    pilota: una chiave presente e vuota non vuol dire «nessun bersaglio», e chi
#    la riceve dovrebbe interrogarla prima di usarla. L'assenza si dice
#    togliendo la chiave.
def bersagli_envelope(
    targets: tuple[Bersaglio, ...] | None,
) -> list[dict[str, str]] | None:
    return [b.to_envelope() for b in targets] if targets else None


@dataclass(frozen=True)
class DiagnosticaDb:
    """Tutto cio' che un errore del database dice, letto UNA volta.

    ⭐ Perche' esiste, ed e' un difetto misurato il 2026-08-24. I punti in cui un
    `DatabaseError` diventa un `ServiceError` sono CINQUE, e ognuno leggeva un
    sottoinsieme diverso della diagnostica:

      1. `ErrorTranslator._from_database_error` — l'errore NUDO al middleware
      2. `payload_helpers.translate_db_errors` — 46 punti di chiamata
      3. `ErrorManager.raise_from_database_error` — 9
      4. `pipeline_step_executor._run_per_fattura_task` — la strada del pilota
      5. `pratiche._raise_known_db_error` — 12

    Conseguenza: `hint` arrivava all'envelope da **tre** strade su cinque e
    `fields` da **UNA**, quindi i 136 binding di `campiErrati` sul frontend non
    si illuminavano mai su un errore nato in PL/pgSQL. Il canale c'era, era il
    trasporto a perderlo.

    ⚠️ Il quinto e' stato trovato DOPO gli altri quattro, col roll-out del
    2026-08-24 — ed e' la ragione per cui questo elenco va riletto invece che
    dato per completo: un BB unifica la LETTURA, non il trasporto, e un punto
    di traduzione nuovo va cercato.

    ⛔ E c'e' un sesto appiattimento che NON passa di qui, perche' non produce un
    `ServiceError`: il blob `errore` di `pipeline_runner._drive_lotto_until_done`,
    che mette il fallimento dentro una risposta **200**.

    ⚠️ Nessun campo qui e' «nuovo»: sono le stesse letture di prima, messe in
    una sede sola perche' non possano piu' divergere.
    """

    testo: str
    sqlstate: str | None
    codice_strutturato: str | None
    codice: str | None
    messaggio: str | None
    detail: str | None
    hint: str | None
    campo: str | None
    bersagli: tuple[Bersaglio, ...]

    # Scopo: `True` quando il codice viene dal campo strutturato, cioe' quando
    #        `script.fn_log_and_raise_error` ha GIA' scritto la sua riga in
    #        `dbops.error_log`. Chi logga deve saperlo per non fare il doppione
    #        (decisione DB+BE del 2026-08-19).
    @property
    def gia_scritto_dal_database(self) -> bool:
        return self.codice_strutturato is not None

    # Scopo: Ritentabile: serializzazione e deadlock, e nient'altro.
    @property
    def retryable(self) -> bool:
        return self.sqlstate in {"40001", "40P01"}

    # Scopo: I campi del form da correggere, nella forma dell'envelope.
    @property
    def fields(self) -> tuple[str, ...] | None:
        return (self.campo,) if self.campo else None


# Scopo: ⭐ IL BB: la diagnostica di dominio di un'eccezione DB, letta una volta
#        sola. Sostituisce le quattro letture parziali che i punti di
#        traduzione facevano ciascuno per conto proprio.
#
#        ⚠️ `text` esplicito per i chiamanti che hanno gia' il testo in mano.
def diagnostica_db(exc: BaseException, *, text: str | None = None) -> DiagnosticaDb:
    cause = getattr(exc, "__cause__", None)
    diag = getattr(cause, "diag", None)
    testo = text if text is not None else (str(exc) or "")
    codice_strutturato = structured_db_error_code(exc)
    return DiagnosticaDb(
        testo=testo,
        sqlstate=sqlstate_del_driver(cause),
        codice_strutturato=codice_strutturato,
        codice=codice_strutturato or app_error_code_from_text(testo),
        messaggio=getattr(diag, "message_primary", None) or None,
        detail=getattr(diag, "message_detail", None) or None,
        hint=getattr(diag, "message_hint", None) or None,
        campo=structured_db_error_field(exc),
        bersagli=structured_db_error_target(exc),
    )
