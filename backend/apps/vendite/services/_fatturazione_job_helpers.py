# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condivisi dei job handler della coda fatturazione
#        (FATTURAZIONE_GIRO C-3, FATTURAZIONE_NUMERA C-4). Estrazione regola
#        del 2 (ok Tid 2026-07-21): `_parse_competenza` era duplicata nei due
#        handler, identica salvo il codice errore — qui parametrizzato.
# ------------------------------------------------------------

from __future__ import annotations

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
        return datetime.strptime(str(raw), "%Y-%m-%d").date().replace(day=1)
    except ValueError as exc:
        raise ServiceError(
            code=error_code,
            message="`competenza_mese` non valida (atteso YYYY-MM-DD).",
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
MOTIVO_NON_DETERMINATO = "NON_DETERMINATO"

# Quanti gruppi elencare per esteso nel messaggio all'operatore: oltre, il testo
# diventa illeggibile in un toast e il dettaglio resta nell'esito strutturato.
_MAX_GRUPPI_NEL_MESSAGGIO = 3


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
def classifica_gruppo_non_servito(d: dict[str, Any]) -> tuple[str, str]:
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
        return (
            MOTIVO_NON_DETERMINATO,
            f"{d['n_pronte']} attività "
            f"{_concorda(d['n_pronte'], 'risulta pronta', 'risultano pronte')} "
            "ma il gruppo non è entrato in nessun lotto: verificare emittente e "
            "utility della commessa",
        )
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
    diagnosi: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    esiti: list[dict[str, Any]] = []
    for d in diagnosi:
        motivo, testo = classifica_gruppo_non_servito(d)
        esiti.append({
            "gruppo_key": d.get("gruppo_key"),
            "commessa_codice": d.get("commessa_codice"),
            "motivo": motivo,
            "dettaglio": testo,
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


# Scopo: Digest stabile dell'insieme dei gruppi, per la chiave di BUSINESS
#        della coda. Obiettivo: due emissioni mirate sullo stesso mese e scope
#        ma con gruppi DIVERSI devono produrre due job distinti — senza questo,
#        la dedup dei job vivi assorbirebbe la seconda in silenzio, ed e' il
#        difetto piu' insidioso della slice (l'operatore vede «accodato» e non
#        succede nulla). Ordinamento prima dell'hash: lo stesso insieme
#        selezionato in ordine diverso resta lo STESSO lavoro, quindi va
#        deduplicato davvero.
# Risultato: 12 esadecimali (collisione irrilevante: la chiave e' gia' scoped
#        per job_type + mese + scope operatore), o stringa vuota senza gruppi —
#        cosi' la chiave del giro di massa resta identica a prima.
def gruppi_digest(gruppi: tuple[str, ...] | None) -> str:
    if not gruppi:
        return ""
    canonico = "\x1f".join(sorted(gruppi))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]
