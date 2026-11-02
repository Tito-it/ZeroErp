# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi dei job handler della coda fatturazione
#        (FATTURAZIONE_GIRO C-3, FATTURAZIONE_NUMERA C-4). Estrazione regola
#        del 2 (ok Tid 2026-07-21): `_parse_competenza` era duplicata nei due
#        handler, identica salvo il codice errore — qui parametrizzato.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping, Sequence

import hashlib
from datetime import date, datetime
from typing import Any

from apps.core.services.coda_lavori.drain_engine import contesto_terminale
from apps.core.services.error_manager import ErrorManager, ServiceError

# Job type dei lavori di fatturazione lanciati dall'app su `dbops.coda_lavori`
# (vocabolario seedato in `dbops.coda_lavori_tipi`). Costanti UNICHE
# (estrazione regola del 2, ok Tid 2026-07-23): prima i letterali vivevano
# duplicati tra l'enqueue delle view (C-3/C-4) e il registry degli esiti del
# cockpit — un refuso in uno dei punti avrebbe silenziosamente scollegato
# l'accodamento dal pannello che lo racconta.
JOB_TYPE_FATTURAZIONE_GIRO = "FATTURAZIONE_GIRO"
JOB_TYPE_FATTURAZIONE_NUMERA = "FATTURAZIONE_NUMERA"
JOB_TYPES_FATTURAZIONE_APP = (
    JOB_TYPE_FATTURAZIONE_GIRO,
    JOB_TYPE_FATTURAZIONE_NUMERA,
)


# Scopo: Normalizza `competenza_mese` (ISO YYYY-MM-DD) al 1° del mese. Errore
#        parlante col codice del job chiamante su valore mancante/invalido
#        (fallimento di dominio registrato in `ultimo_errore`, non eccezione
#        generica — guida Tracciamento).
def parse_competenza_mese(raw: Any, *, error_code: str) -> date:
    ErrorManager.require(
        bool(raw),
        code=error_code,
        message="Payload senza `competenza_mese`.",
        context=contesto_terminale(),
    )
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date().replace(day=1)  # noqa: DTZ007 — si legge una DATA (formato stretto), non un istante: il fuso non c'entra
    except ValueError as exc:
        raise ServiceError(
            code=error_code,
            message="`competenza_mese` non valida (atteso YYYY-MM-DD).",
            detail=str(raw),
            context=contesto_terminale(),
        ) from exc


# Scopo: Legge una data ISO (`YYYY-MM-DD`) FACOLTATIVA dal payload di un job di
#        fatturazione: `None`/vuoto -> None, valore malformato -> ServiceError
#        col codice del chiamante.
# ⛔ ESISTE PERCHE' `parse_competenza_mese` NON VA BENE, e la differenza e' di
#    quelle che non sollevano niente: quella funzione fa `.replace(day=1)`,
#    perche' una competenza E' un mese. Riusarla per la data documento
#    trasformerebbe un 25/08 dichiarato dall'operatore in un 01/08 — cioe'
#    scriverebbe sui documenti una data che nessuno ha scelto, proprio nel
#    cantiere che nasce per togliere le date che nessuno ha scelto.
# ⚠️ Nessun `.replace()` qui, e nessun default: assente vuol dire NON
#    DICHIARATA, che non e' un sinonimo di «oggi».
def parse_data_iso(raw: Any, *, error_code: str, campo: str) -> date | None:
    if raw in (None, ""):
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()  # noqa: DTZ007 — si legge una DATA (formato stretto), non un istante: il fuso non c'entra
    except ValueError as exc:
        raise ServiceError(
            code=error_code,
            message=f"`{campo}` non valida (atteso YYYY-MM-DD).",
            detail=str(raw),
            context=contesto_terminale(),
        ) from exc


# Numero massimo di gruppi fatturabili selezionabili in una emissione mirata.
# Non e' una regola fiscale: e' il tetto oltre il quale «selezione mirata» non
# vuol piu' dire niente e conviene il giro di massa. Cap esplicito invece che
# silenziosamente illimitato (il payload finisce in un jsonb di coda).
MAX_GRUPPI_EMISSIONE_MIRATA = 200


# Scopo: Normalizza e valida la lista dei GRUPPI FATTURABILI di una emissione
#        mirata. Obiettivo: un perimetro sbagliato deve fallire con un 400
#        parlante, mai degenerare in un perimetro vuoto (= giro di massa) o in
#        chiavi spazzatura che filtrerebbero zero righe senza dirlo.
#        Deduplica preservando l'ordine (la chiave di dedup dei job dipende dal
#        contenuto, non dall'ordine in cui l'operatore ha spuntato le righe:
#        l'ordinamento avviene nel digest).
# Risultato: tupla di chiavi valide, oppure None se il chiamante non ha chiesto
#        alcun perimetro (assenza di criterio = comportamento odierno).
def parse_gruppi(raw: Any, *, error_code: str) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        raise ServiceError(
            code=error_code,
            message="`gruppi` deve essere una lista di chiavi gruppo fatturabile.",
            detail=f"tipo ricevuto: {type(raw).__name__}",
            context=contesto_terminale(),
        )
    chiavi: list[str] = []
    for elemento in raw:
        if not isinstance(elemento, str) or not elemento.strip():
            raise ServiceError(
                code=error_code,
                message="`gruppi` contiene una chiave non valida (attesa stringa non vuota).",
                detail=repr(elemento),
                context=contesto_terminale(),
            )
        chiave = elemento.strip()
        if chiave not in chiavi:
            chiavi.append(chiave)
    # Lista presente ma vuota: e' una richiesta ambigua («fattura niente»
    # oppure «fattura tutto»?). Si rifiuta invece di indovinare.
    if not chiavi:
        raise ServiceError(
            code=error_code,
            message="`gruppi` non puo` essere una lista vuota: omettere il campo per il giro di massa.",
            context=contesto_terminale(),
        )
    if len(chiavi) > MAX_GRUPPI_EMISSIONE_MIRATA:
        raise ServiceError(
            code=error_code,
            message=(
                "Troppi gruppi selezionati per una emissione mirata "
                f"(max {MAX_GRUPPI_EMISSIONE_MIRATA})."
            ),
            detail=f"ricevuti: {len(chiavi)}",
            context=contesto_terminale(),
        )
    return tuple(chiavi)


# Motivi per cui un gruppo fatturabile richiesto non ha prodotto lotti. Sono
# CLASSIFICAZIONI di una fotografia (`GruppoDiagnosi`), non un secondo criterio
# di ammissibilita': l'unica sede del criterio resta `fn_list_emittibili_lane`.
# Il codice finisce nell'esito del job; il testo, gia' in italiano, arriva
# all'operatore via `ultimo_errore.message` (il FE lo rende cosi' com'e').
MOTIVO_GRUPPO_SCONOSCIUTO = "GRUPPO_SCONOSCIUTO"
MOTIVO_COMMESSA_NON_EMITTIBILE = "COMMESSA_NON_EMITTIBILE"
MOTIVO_RIGHE_NON_APPROVATE = "RIGHE_NON_APPROVATE"
MOTIVO_RIGHE_RIFIUTATE = "RIGHE_RIFIUTATE"
# ⚠️ `MOTIVO_TIPO_DOC_MANCANTE` e' stato RITIRATO il 2026-08-15 e non va
# rimesso: dopo la validazione del CHECK (`20260815-30`) una riga emittibile
# senza tipo documento fiscale non puo' esistere, quindi `n_senza_tipo_doc` era
# un contatore sempre a zero e il motivo un ramo irraggiungibile. La funzione
# DB `fn_diagnostica_gruppi_fatturabili` non espone piu' quel conteggio.
MOTIVO_FUORI_COMPETENZA = "FUORI_COMPETENZA"
MOTIVO_GIA_EMESSE = "GIA_EMESSE"
MOTIVO_RIGHE_ANNULLATE = "RIGHE_ANNULLATE"
MOTIVO_NESSUNA_RIGA_CANDIDATA = "NESSUNA_RIGA_CANDIDATA"
# La corsia del gruppo si e' ROTTA durante il giro: il perimetro era valido, e'
# l'esecuzione ad essere fallita. Distinzione che vale un'azione diversa — il
# perimetro si corregge, un'esecuzione rotta si riprova.
MOTIVO_ESECUZIONE_FALLITA = "ESECUZIONE_FALLITA"
# ⭐ Il gruppo e' TRATTENUTO da un lotto ancora in gioco: nessuno ha sbagliato
# niente e non c'e' niente da correggere — quel lavoro e' gia' in mano a un
# altro giro, e si aspetta che quel giro finisca o lo rilasci.
# 🔴 Prima del 2026-09-09 questo caso cadeva su `MOTIVO_NON_DETERMINATO`, e
# l'operatore leggeva «verificare emittente e utility della commessa»: due cose
# giuste da controllare, e nessuna parola sull'unica che contava. La lane aveva
# smesso di offrire il documento (changeSet `20260909-25`) e la diagnostica
# continuava a contarlo fra i pronti — lo specchio rotto, §9.2 del brief.
MOTIVO_TRATTENUTO_DA_LOTTO = "TRATTENUTO_DA_LOTTO"
MOTIVO_NON_DETERMINATO = "NON_DETERMINATO"

# Quanti gruppi elencare per esteso nel messaggio all'operatore: oltre, il testo
# diventa illeggibile in un toast e il dettaglio resta nell'esito strutturato.
_MAX_GRUPPI_NEL_MESSAGGIO = 3


# La chiave-corsia come tupla: UNA spelling della forma, non cinque annotazioni
# sparse. Se la corsia guadagna un campo, si tocca qui e `terna_key` — e il
# type checker segue.
TernaKey = tuple[Any, Any, Any]


# Scopo: Riduce una corsia (dict con le tre chiavi) alla tupla confrontabile
#        `(emittente, tipo_doc_fiscale, utility)`. Serve a incrociare le
#        `terne_pronte` della fotografia — che vengono dal DB — con le terne
#        FALLITE del giro, che il BE ha negli esiti. Le due sorgenti usano gli
#        stessi tre campi: la tupla e' il minimo comune, e non introduce una
#        terza rappresentazione della corsia.
def terna_key(d: dict[str, Any]) -> TernaKey:
    return (
        d.get("emittente_soggetto_ruolo_id"),
        d.get("tipo_doc_fiscale_id"),
        d.get("utility_id"),
    )


# Scopo: Concordanza singolare/plurale nei testi all'operatore. Banale, ma i
#        conteggi qui valgono spesso 1 («1 attività pronte» si nota, e fa
#        sembrare trascurato tutto il messaggio che lo contiene).
def _concorda(n: int, singolare: str, plurale: str) -> str:
    return singolare if n == 1 else plurale


# Scopo: Classifica UNA fotografia di gruppo non servito, in ordine di causa
#        prossima. Restituisce `(codice_motivo, testo_it)`.
#
#        Il testo NON ripete il codice commessa: lo antepone gia' il compositore
#        del messaggio, e il dato resta comunque a parte nell'esito strutturato.
#
#        L'ordine non e' arbitrario: se ci sono righe pronte a tutti gli effetti
#        (approvate, con tipo doc, entro competenza) e il gruppo non e' entrato
#        in nessuna terna, allora il blocco e' sulla TESTATA — ed e' il caso che
#        ha motivato questa diagnostica (2026-08-03: commessa rimasta BOZZA,
#        `stati_commessa.emittibile = false`, 15 attivita' di giugno invisibili
#        alla fatturazione ma presenti nella dashboard). Solo quando NON ci sono
#        righe pronte ha senso guardare perche' le righe non lo sono.
#
#        `NON_DETERMINATO` non e' una resa: e' l'unico esito onesto quando la
#        fotografia non spiega l'esclusione (es. commessa senza emittente). Meglio
#        dichiarare che non lo sappiamo che inventare una causa plausibile.
# Scopo: la coppia (motivo, frase) del gruppo trattenuto da un lotto in gioco.
#        Vive qui perche' il ramo serve in DUE punti della classificazione —
#        con e senza righe pronte — e ricopiarlo sarebbe la seconda sede di una
#        frase che deve restare una.
# ⚠️ La frase NOMINA il lotto: «trattenuto» senza dire DA COSA non e'
#    azionabile, e l'operatore non saprebbe dove andare a guardare. Il codice
#    arriva da `lotti_trattenenti`, che il DB consegna come array ordinato di
#    {id, codice} (changeSet `20260909-63`).
# ⚠️ Se i lotti fossero piu' d'uno si nomina il PRIMO e si dice che ce ne sono
#    altri: un elenco dentro una frase di toast non si legge.
def _motivo_trattenuto(d: Mapping[str, Any]) -> tuple[str, str]:
    n = d.get("n_trattenute") or 0
    lotti = d.get("lotti_trattenenti") or []
    codice = (lotti[0] or {}).get("codice") if lotti else None
    dove = f" dal lotto {codice}" if codice else ""
    altri = f" e altri {len(lotti) - 1}" if len(lotti) > 1 else ""
    return (
        MOTIVO_TRATTENUTO_DA_LOTTO,
        f"{n} attività {_concorda(n, 'è trattenuta', 'sono trattenute')}"
        f"{dove}{altri}, ancora in lavorazione: si può attendere che quel giro "
        "si chiuda, oppure togliere il documento da quel lotto",
    )


def classifica_gruppo_non_servito(
    d: Mapping[str, Any],
    *,
    terne_fallite: frozenset[TernaKey] = frozenset(),
) -> tuple[str, str]:
    if not d.get("n_righe"):
        return (
            MOTIVO_GRUPPO_SCONOSCIUTO,
            "nessuna attività trovata per questa chiave gruppo",
        )
    if d.get("n_pronte"):
        if d.get("commessa_emittibile") is False:
            return (
                MOTIVO_COMMESSA_NON_EMITTIBILE,
                # A video la DESCRIZIONE dello stato (regola display-fields):
                # il codice interno resta per la logica. Fallback fail-visible
                # sul codice, mai una frase monca.
                f"la commessa è in stato "
                f"{d.get('commessa_stato_descrizione') or d.get('commessa_stato_codice_interno') or '?'}"
                f", che non "
                f"ammette fatturazione ({d['n_pronte']} attività "
                f"{_concorda(d['n_pronte'], 'pronta', 'pronte')} in attesa)",
            )
        # ⚠️ DOPO la testata bloccata e PRIMA del fallback, e l'ordine e' la
        # regola. Una commessa non emittibile e' una causa CERTA e vale
        # comunque; la corsia rotta spiega il caso che restava — e che prima
        # cadeva nel fallback qui sotto, cioe' si prendeva una causa di
        # perimetro inventata («verificare emittente e utility», che sono a
        # posto) al posto di «riprova».
        # (niente prefisso `terne_fallite and`: con il set vuoto l'`any` e'
        # gia' False — un secondo guard sulla stessa condizione suggerirebbe
        # una distinzione semantica che non esiste.)
        if any(
            terna_key(t) in terne_fallite for t in (d.get("terne_pronte") or [])
        ):
            # ⚠️ Il testo NON afferma «il perimetro e' valido»: la corsia e'
            # condivisa da piu' commesse e il codice d'errore della terna non
            # viene ispezionato qui — un guasto deterministico (es. emittente
            # incoerente col billing account) sarebbe raccontato da un claim
            # troppo sicuro. Si dice cio' che E' misurato: la lavorazione si e'
            # interrotta, e il rilancio e' il primo passo — con l'uscita onesta
            # se l'errore si ripete.
            return (
                MOTIVO_ESECUZIONE_FALLITA,
                f"{d['n_pronte']} attività "
                f"{_concorda(d['n_pronte'], 'è pronta', 'sono pronte')} "
                "ma la lavorazione della corsia si è interrotta durante il "
                "giro: si può rilanciare l'emissione su questo gruppo (se "
                "l'errore si ripete, verificare l'esito del giro)",
            )
        # ⭐ PRIMA del ripiego e DOPO le due cause certe, e l'ordine e' la
        #   regola: «trattenuto» e' una causa CERTA (si sa quale lotto), quindi
        #   batte il generico; ma non batte una testata bloccata, che vale
        #   comunque. ⚠️ Qui ci sono righe PRONTE *e* trattenute: il gruppo e'
        #   stato servito a meta', e la parte che non e' passata e' quella.
        if d.get("n_trattenute"):
            return _motivo_trattenuto(d)
        return (
            MOTIVO_NON_DETERMINATO,
            f"{d['n_pronte']} attività "
            f"{_concorda(d['n_pronte'], 'risulta pronta', 'risultano pronte')} "
            "ma il gruppo non è entrato in nessun lotto: verificare emittente e "
            "utility della commessa",
        )
    # ⭐ Nessuna riga pronta e qualcuna trattenuta: e' LA causa, non un ripiego.
    #   ⛔ Sta PRIMA di «non approvate» e «rifiutate» perche' quelle parlano di
    #   righe che il giro non avrebbe preso comunque, mentre questa parla di
    #   righe che il giro avrebbe preso e che un ALTRO giro sta tenendo.
    if d.get("n_trattenute"):
        return _motivo_trattenuto(d)
    if d.get("n_non_approvate"):
        return (
            MOTIVO_RIGHE_NON_APPROVATE,
            f"{d['n_non_approvate']} attività non "
            f"{_concorda(d['n_non_approvate'], 'è ancora approvata', 'sono ancora approvate')}",
        )
    if d.get("n_rifiutate"):
        # Distinta da «non ancora approvata»: la rifiutata non e' in attesa di
        # nessuno — dire all'operatore di aspettare l'approvazione lo
        # manderebbe a bussare a una porta che e' gia' stata chiusa.
        return (
            MOTIVO_RIGHE_RIFIUTATE,
            f"{d['n_rifiutate']} attività "
            f"{_concorda(d['n_rifiutate'], 'è stata rifiutata', 'sono state rifiutate')} "
            "in approvazione",
        )
    if d.get("n_fuori_competenza"):
        return (
            MOTIVO_FUORI_COMPETENZA,
            f"{d['n_fuori_competenza']} attività "
            f"{_concorda(d['n_fuori_competenza'], 'ha', 'hanno')} competenza successiva "
            "al mese richiesto: rilanciare sul mese più recente (la selezione è cumulativa)",
        )
    # «Gia' emesse»: le annullate non contano come lavoro mancante — un gruppo
    # con 3 emesse e 1 annullata E' interamente evaso, e senza questa somma
    # cadrebbe nel fallback generico.
    n_emesse = d.get("n_emesse") or 0
    n_annullate = d.get("n_annullate") or 0
    if n_emesse and n_emesse + n_annullate == d["n_righe"]:
        return (
            MOTIVO_GIA_EMESSE,
            "l'unica attività del gruppo è già stata emessa"
            if n_emesse == 1 and not n_annullate
            else f"le {n_emesse} attività del gruppo sono già state emesse"
            if n_emesse > 1 and not n_annullate
            else f"le attività del gruppo sono già state emesse ({n_emesse}) "
                 f"o annullate ({n_annullate})",
        )
    if n_annullate == d["n_righe"]:
        return (
            MOTIVO_RIGHE_ANNULLATE,
            "le attività del gruppo sono state tutte annullate",
        )
    return (
        MOTIVO_NESSUNA_RIGA_CANDIDATA,
        "nessuna attività candidabile nel perimetro richiesto",
    )


# Scopo: Trasforma le fotografie dei gruppi richiesti nell'elenco strutturato dei
#        NON serviti (`n_pronte` non basta: un gruppo con righe pronte e testata
#        bloccata resta non servito). Ordine di input preservato: e' l'ordine in
#        cui l'operatore ha spuntato le righe.
def spiega_gruppi_non_serviti(
    diagnosi: Sequence[Mapping[str, Any]],
    *,
    terne_fallite: frozenset[TernaKey] = frozenset(),
) -> list[dict[str, Any]]:
    esiti: list[dict[str, Any]] = []
    for d in diagnosi:
        motivo, testo = classifica_gruppo_non_servito(d, terne_fallite=terne_fallite)
        # ⭐ Il LOTTO viaggia STRUTTURATO accanto alla frase, e non solo dentro
        #   di essa: il frontend ci costruisce il gesto «vai al lotto» senza far
        #   ricopiare un codice a chi legge.
        # ⛔ NON passa dal canale `targets` dell'envelope: quello porta il
        #   bersaglio di un ERRORE sollevato dal database, e qui non c'e' nessun
        #   errore — c'e' un esito con un elenco che il frontend gia' riceve.
        # ⚠️ `None` quando il motivo non e' il trattenuto: un id che c'e' sempre
        #   inviterebbe a disegnare un pulsante che non ha senso.
        lotti = d.get("lotti_trattenenti") or []
        primo = (lotti[0] or {}) if motivo == MOTIVO_TRATTENUTO_DA_LOTTO else {}
        esiti.append({
            "gruppo_key": d.get("gruppo_key"),
            "commessa_codice": d.get("commessa_codice"),
            "motivo": motivo,
            "dettaglio": testo,
            "lotto_id": primo.get("id"),
            "lotto_codice": primo.get("codice"),
        })
    return esiti


# Scopo: Compone il messaggio che l'operatore legge quando l'emissione mirata non
#        produce nulla. Un elenco puntato non passa dal toast: si sceglie la forma
#        «N su M, poi i primi tre per esteso». Il resto vive nell'esito.
def messaggio_gruppi_non_serviti(
    spiegazioni: list[dict[str, Any]], *, totale_richiesti: int,
) -> str:
    # ⚠️ Si contano i GRUPPI DISTINTI, non le righe. Dal 2026-08-15 la
    # fotografia ha grana `(gruppo_key, commessa_id)`: un documento che
    # alimentasse due commesse produce DUE righe per lo stesso gruppo, e
    # contarle direbbe «4 gruppi su 3» — un numero piu' grande del totale
    # richiesto, cioe' visibilmente sbagliato proprio nel messaggio che deve
    # spiegare. E' lo stesso caso per cui il DB ha cambiato la grana: oggi non
    # capita (zero gruppi multi-commessa), ma il conteggio non deve dipendere
    # da quel fatto.
    n_gruppi = len({s.get("gruppo_key") for s in spiegazioni})
    testa = (
        f"Nessun lotto prodotto: {n_gruppi} gruppi su {totale_richiesti} "
        "non sono fatturabili."
        if n_gruppi != 1
        else "Nessun lotto prodotto: il gruppo richiesto non è fatturabile."
    )
    dettagli = [
        f"{s.get('commessa_codice') or s.get('gruppo_key')}: {s['dettaglio']}"
        for s in spiegazioni[:_MAX_GRUPPI_NEL_MESSAGGIO]
    ]
    if len(spiegazioni) > _MAX_GRUPPI_NEL_MESSAGGIO:
        dettagli.append(f"e altri {len(spiegazioni) - _MAX_GRUPPI_NEL_MESSAGGIO}")
    return f"{testa} " + "; ".join(dettagli) + "."


# Scopo: Digest stabile di un INSIEME di chiavi, per la chiave di BUSINESS
#        della coda.
#
# ⭐ Obiettivo: due atti MIRATI sullo stesso mese e scope ma su insiemi DIVERSI
#    devono produrre due job distinti. Senza, la dedup dei job vivi assorbe il
#    secondo in silenzio — l'operatore legge «accodato» e non succede niente. E'
#    il difetto piu' insidioso di questa famiglia di verbi.
#
# ⚠️ ORDINAMENTO PRIMA DELL'HASH: lo stesso insieme spuntato in ordine diverso
#    e' lo STESSO lavoro, e quello va deduplicato davvero.
#
# ⚠️ `str()` su ogni elemento: l'insieme puo' essere di chiavi testuali (i
#    gruppi fatturabili) o di id numerici (i lotti selezionati). ⛔ E l'ordine e'
#    quello delle STRINGHE, non dei numeri: e' indifferente al risultato — serve
#    solo che sia deterministico — ma va saputo, perche' `[2, 10]` e `[10, 2]`
#    danno lo stesso digest mentre l'ordine canonico interno e' `10, 2`.
#
# Risultato: 12 esadecimali (collisione irrilevante: la chiave e' gia' scoped
#        per job_type + mese + scope operatore), o stringa vuota su insieme
#        assente — cosi' la chiave del giro di massa resta identica a prima.
#
# ⭐ Generalizzato il 2026-08-26 (regola del 2, ok Tid): nato per i gruppi
#    dell'emissione mirata, serve identico alla numerazione su selezione di
#    lotti. Due copie divergerebbero sul punto che conta — se ordinano prima di
#    hashare — e la seconda perderebbe silenziosamente job legittimi.
def insieme_digest(valori) -> str:
    if not valori:
        return ""
    canonico = "\x1f".join(sorted(str(v) for v in valori))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]


# Scopo: Normalizza e valida la lista dei LOTTI di una numerazione su selezione.
#        Stessa disciplina di `parse_gruppi`, con cui condivide il motivo di
#        esistere: un perimetro sbagliato deve fallire con un 400 parlante, mai
#        degenerare in «tutti» o in un insieme che non trova nulla senza dirlo.
# ⛔ Lista presente ma VUOTA = rifiuto, non «nessun filtro»: e' una richiesta
#        ambigua («numera niente» oppure «numera tutto»?), e su un atto fiscale
#        indovinare non e' ammesso. Chi vuole il mese intero omette il campo.
# Risultato: tupla di id positivi deduplicati (ordine preservato), oppure None
#        se il chiamante non ha chiesto alcuna selezione.
def parse_lotti(raw: Any, *, error_code: str) -> tuple[int, ...] | None:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        raise ServiceError(
            code=error_code,
            message="`lotti` deve essere una lista di id di lotto.",
            detail=f"tipo ricevuto: {type(raw).__name__}",
            context=contesto_terminale(),
        )
    ids: list[int] = []
    for elemento in raw:
        # ⚠️ `bool` e' sottoclasse di `int`: senza il primo controllo, `True`
        #    passerebbe come lotto numero 1.
        if isinstance(elemento, bool) or not isinstance(elemento, int) or elemento <= 0:
            raise ServiceError(
                code=error_code,
                message="`lotti` contiene un id non valido (atteso intero maggiore di zero).",
                detail=repr(elemento),
                context=contesto_terminale(),
            )
        if elemento not in ids:
            ids.append(elemento)
    if not ids:
        raise ServiceError(
            code=error_code,
            message=(
                "`lotti` non puo` essere una lista vuota: omettere il campo per "
                "numerare l'intero mese."
            ),
            context=contesto_terminale(),
        )
    return tuple(ids)


# Scopo: LA CORSIA con cui un giro accodato dall'applicazione verra' eseguito.
#        Una sede sola per una regola che serve in DUE momenti lontani fra loro:
#        all'ACCODAMENTO (entra nella chiave di dedup) e all'ESECUZIONE (la usa
#        l'handler). Se le due la calcolassero ognuna per conto suo, un giorno
#        direbbero cose diverse — e il sintomo sarebbe un giro deduplicato
#        contro un altro che fa un lavoro diverso.
#
# ⭐ La regola: una selezione esplicita di gruppi e' un perimetro piu' preciso
#    dell'instradamento automatico, quindi vince sulla corsia. Senza gruppi il
#    giro on-demand di massa e' «differita» — si ferma a EMESSA, gate fiscale I-7.
# ⚠️ `None` per i lavori che una corsia non ce l'hanno: la numerazione di
#    perimetro non e' un giro, e' un passo.
# ⛔ I letterali delle corsie NON si riscrivono qui: si importano dal driver, che
#    ne e' l'owner (`_MODALITA`). Import locale come nell'handler, per non
#    caricare la catena driver al boot del modulo.
def corsia_del_giro(job_type: str, *, gruppi=None) -> str | None:
    if job_type != JOB_TYPE_FATTURAZIONE_GIRO:
        return None
    from apps.vendite.services.fatturazione_driver_service import (
        MODALITA_MIRATA,
        MODALITA_ONDEMAND,
    )

    return MODALITA_MIRATA if gruppi else MODALITA_ONDEMAND


# Scopo: La CHIAVE DI BUSINESS con cui la coda deduplica i giri vivi. Una sede
#        sola, perche' i produttori sono DUE: il verbo dell'applicazione e il
#        batch notturno.
#
# ⛔ LA CORSIA E' NELLA CHIAVE, e prima non c'era (2026-09-05, decisione di Tid,
#    opzione A). Le corsie fanno cose diverse — «immediata» va fino in fondo e
#    NUMERA, «differita» si ferma a EMESSA — ma per la dedup erano lo stesso
#    lavoro: stesso tipo, stesso mese, stesso perimetro. Finche' a produrre era
#    solo l'applicazione il difetto restava LATENTE (una corsia sola in uso);
#    col batch, che le produce entrambe per la stessa azienda e lo stesso mese,
#    la seconda sarebbe stata scartata **in silenzio** — una corsia semplicemente
#    non fatturava, senza nessun errore.
# ⭐ Ed e' UNA regola, non due formati: `corsia=None` per i lavori che una corsia
#    non ce l'hanno (la numerazione di perimetro). Due formati per lo stesso tipo
#    di lavoro sarebbero la cosa che poi diverge — chi tocca uno non sa
#    dell'altro.
# ⚠️ Sul verbo dell'applicazione il valore e' determinato dal perimetro (mirata
#    se ci sono gruppi, differita altrimenti), quindi la chiave cambia FORMA e
#    non cambia COMPORTAMENTO: nessun giro che oggi si deduplica smette di farlo.
# ⛔ Il digest del perimetro mirato resta in coda e resta condizionale: senza,
#    due selezioni diverse sullo stesso mese sarebbero lo stesso job e la
#    seconda verrebbe assorbita senza dirlo.
def chiave_idempotenza_giro(
    *,
    job_type: str,
    competenza: date,
    scope_key: str,
    corsia: str | None = None,
    digest: str = "",
) -> str:
    parti = [job_type]
    if corsia:
        parti.append(corsia)
    parti.extend([competenza.isoformat(), scope_key])
    if digest:
        parti.append(digest)
    return ":".join(parti)
