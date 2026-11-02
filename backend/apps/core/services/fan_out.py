# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `run_fan_out` — il telaio del fan-out isolato: *scopri gli item →
#        lavorali uno per uno isolando l'errore → aggrega l'esito a TRE stati*.
#        BB cross-dominio estratto con la "regola del 2" (ok Tid 2026-08-09):
#        il pattern era scritto a mano in due siti di `vendite` con policy di
#        aggregazione DIVERSE, e la divergenza era un difetto vero — il pull da
#        commessa dichiarava COMPLETATO un giro con rifiuti parziali, cosi' al
#        rilancio dello step le entita' rimaste indietro venivano saltate.
#
#        ⚠️ CONFINE con `coda_lavori/drain_engine.py` (D-1 del brief).
#        Qui: lista **effimera**, scoperta dal chiamante e consumata una volta
#        sola; chi resta indietro lo si ritrova alla prossima scoperta.
#        Li': coda **durevole** (`QueueDrainEngine`), dove l'item sopravvive al
#        run e servono claim, ownership, backoff e ritentativi.
#        Se stai per aggiungere qui un retry o un lock, l'astrazione giusta e'
#        l'altra.
#        Brief: docs/it/dev/work-done/brief-be-fan-out-isolato-e-esito-parziale.md
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

logger = logging.getLogger(__name__)

# Le tre parole dell'esito. NON sono nuove: `CommessaPushOrchestrator._compute_stato`
# le usa da sempre per il push. Il BB le rende disponibili a tutti invece di
# lasciare che ogni chiamante ne reinventi due (o, come il pull, ne usi una sola).
ESITO_COMPLETATO = "COMPLETATO"
ESITO_PARZIALE = "PARZIALE"
ESITO_ERRORE = "ERRORE"


# Scopo: Normalizza un'eccezione nel messaggio a una riga usato ovunque nel
#        giro: `esito.errori`, log applicativo, e — nei chiamanti — log di
#        dominio e meta del task_run. SEDE UNICA del formato: un run logger che
#        formattasse per conto suo divergerebbe dal meta alla prima modifica.
def messaggio_eccezione(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


@dataclass(frozen=True)
class FanOutItemErrore:
    """Un singolo item fallito: posizione, item originale, messaggio normalizzato
    e — dal 2026-09-17 — l'eccezione INTERA.

    ⭐ `eccezione` (regola del 2, ok Tid 2026-09-17): chi risponde un esito PER
    RIGA a un operatore vuole il `ServiceError` com'e' — codice, campo,
    `ui_action`, suggerimento — non la stringa `"TypeError: …"`. Due consumatori
    (l'archiviazione delle code e «righe da rate») se la tenevano ciascuno in
    un dizionario laterale popolato con un `try/except/raise` dentro `process`,
    piu' un ripiego per il caso in cui l'eccezione nascesse FUORI da `process`
    (il savepoint stesso), che il dizionario non vedeva. Qui il BB la cattura
    nello stesso `except` che scrive `messaggio`: non c'e' un secondo canale da
    tenere in passo, e il caso «fuori da `process`» e' coperto per costruzione.
    ⚠️ `messaggio` resta: e' la forma per i log e i meta dei task_run
    (`messaggio_eccezione`, sede unica del formato), e i lettori che vogliono
    solo una riga di testo non devono formattare da soli.
    """

    indice: int
    item: Any
    messaggio: str
    # Sempre valorizzata: il BB la cattura nello stesso `except` del messaggio.
    # NON opzionale di proposito — un `None` sarebbe un caso da gestire in ogni
    # consumatore per un evento che non puo' succedere.
    eccezione: Exception


@dataclass
class FanOutEsito:
    """Esito aggregato di un giro di fan-out."""

    totale: int
    # Un elemento per ogni item RIUSCITO, nell'ordine: e' cio' che `process` ha
    # restituito. Serve al chiamante per applicare gli effetti collaterali
    # "solo se e' andata bene" (tracciare un id, accodare un input al batch)
    # SENZA metterli dentro il savepoint — dove un rollback non li annullerebbe,
    # perche' sono strutture Python e non righe di database.
    risultati: list[Any] = field(default_factory=list)
    errori: list[FanOutItemErrore] = field(default_factory=list)

    # Scopo: Quanti item sono andati a buon fine.
    @property
    def ok(self) -> int:
        return len(self.risultati)

    # Scopo: Quanti item sono falliti.
    @property
    def falliti(self) -> int:
        return len(self.errori)

    # Scopo: L'esito in una parola. Lista VUOTA = COMPLETATO: "niente da fare"
    #        e' un successo, non un errore. ⚠️ `_compute_stato` del push
    #        risponde ERRORE sulla lista vuota, ed e' corretto li': per lui
    #        "nessun handler risolto" e' una configurazione sbagliata, non un
    #        giro senza lavoro. Sono due domande diverse: non appianarle.
    @property
    def esito(self) -> str:
        if not self.errori:
            return ESITO_COMPLETATO
        if self.ok == 0:
            return ESITO_ERRORE
        return ESITO_PARZIALE

    # Scopo: Il giro e' finito ma qualcuno e' rimasto indietro. E' il caso che
    #        NON va confuso con il successo: chi lo ignora perde gli item falliti.
    @property
    def parziale(self) -> bool:
        return self.esito == ESITO_PARZIALE

    # ⛔ `tutti_falliti` NON C'E' PIU' (2026-09-07), ed e' sparito col suo unico
    #    lettore. Era `self.esito == ESITO_ERRORE`, e a leggerlo era il ramo del
    #    pull commesse che sollevava quando fallivano TUTTE: quel ramo e' stato
    #    tolto (brief-db-esito-gruppo-lotto P-5), perche' il `raise` faceva
    #    rollback e si portava via le marcature dei documenti caduti.
    # ⭐ Il FATTO resta e non si e' perso niente: `esito == ESITO_ERRORE` dice la
    #    stessa cosa, e' cio' che i consumatori gia' leggono (`esito.esito`
    #    viaggia nei payload di `resi_service` e della coda lavori) ed e'
    #    presidiato dai test di questo file. Ciò che e' sparito e' un alias con
    #    zero lettori — API di un BB condiviso che sembra in uso e non lo e'.

    # Scopo: I messaggi degli item falliti, per comporre detail/report senza
    #        che il chiamante ricicli la struttura interna.
    def messaggi_errore(self) -> list[str]:
        return [e.messaggio for e in self.errori]


class FanOutRunLogger:
    """Diario del giro: il BB sa QUANDO chiamare, il chiamante sa DOVE scrivere.

    Classe base con implementazioni NO-OP, deliberatamente non un Protocol: i
    tre metodi sono OPZIONALI per contratto (si eredita e si sovrascrive solo
    cio' che serve), e un Protocol li dichiarerebbe tutti obbligatori — la firma
    mentirebbe sul contratto, e un type checker boccerebbe ogni implementazione
    parziale. Il runtime accetta comunque il puro duck-typing (`_chiama_logger`
    risolve i metodi via getattr), utile per i mock nei test.

    E' la parte che, lasciata fuori dal BB, il prossimo chiamante
    dimenticherebbe di replicare — ma tenerla dentro per intero costringerebbe
    `core` a conoscere `commesse_push_log` e i logger di dominio.
    """

    # Scopo: Inizio giro, con la dimensione del lavoro scoperto.
    def start(self, *, totale: int) -> None:
        pass

    # Scopo: Un item e' fallito. Chiamato DOPO il rollback del suo savepoint.
    def item_failed(self, *, item: Any, indice: int, exc: Exception) -> None:
        pass

    # Scopo: Fine giro, con l'esito aggregato.
    def end(self, *, esito: FanOutEsito) -> None:
        pass


# Scopo: Invoca un metodo del run logger senza che un difetto del DIARIO possa
#        affondare il LAVORO. Un logger rotto deve produrre una riga di log, non
#        far fallire un giro che stava andando bene.
def _chiama_logger(run_logger: Any, metodo: str, **kwargs: Any) -> None:
    if run_logger is None:
        return
    fn = getattr(run_logger, metodo, None)
    if fn is None:
        return
    try:
        fn(**kwargs)
    except Exception:  # pragma: no cover - difesa, non comportamento
        logger.exception("run_logger.%s fallito: il giro prosegue.", metodo)


# Scopo: Esegue `process` su ogni item isolando i fallimenti, e restituisce
#        l'esito aggregato a tre stati (COMPLETATO / PARZIALE / ERRORE).
#
#        Perimetro e contratto — le regole che si dimenticano:
#        - La DISCOVERY resta fuori: `items` arriva gia' risolto. Il chiamante
#          conosce i propri filtri di perimetro, il BB no e non deve.
#        - `process` segnala il fallimento SOLLEVANDO. Nessun valore di ritorno
#          viene interpretato come esito: un `False` ambiguo e' il modo in cui
#          questi telai marciscono. Cio' che `process` restituisce finisce in
#          `esito.risultati` e serve solo al chiamante.
#        - Il BB NON decide cosa fare dell'esito: lo restituisce. Sollevare,
#          marcare un task_run o scrivere un report e' scelta del dominio.
#        - Nessun retry, nessun lock, nessuna concorrenza: vedi il confine con
#          `QueueDrainEngine` nell'intestazione del modulo.
#
#        `on_success(item, risultato)` — l'aggancio per gli effetti collaterali
#        che valgono SOLO SE l'item e' atterrato: si chiama a savepoint gia'
#        rilasciato, cioe' quando il lavoro dell'item e' definitivo. E' la
#        versione "durante il giro" di `esito.risultati`, e serve quando l'item
#        successivo dipende da cio' che ha prodotto il precedente (il caso vero:
#        una cache di lookup condivisa fra gli item).
#        ⚠️ Perche' non basta scrivere quelle strutture dentro `process`: un
#        rollback annulla le righe di database, **non** un `append` o una voce
#        di dizionario. Un item che cade dopo aver popolato una cache lascia
#        dentro un id ormai inesistente, e a quel punto anche l'item gemello
#        successivo fallisce — un errore che si propaga da solo.
#        ⚠️ `on_success` NON e' protetto: se solleva, il giro si interrompe. E'
#        voluto — il lavoro dell'item e' gia' committato e non e' piu' annullabile,
#        quindi un difetto qui e' un errore di programmazione, non un item
#        fallito. Ci si mettono registrazioni in memoria, non lavoro rischioso.
#
#        `items` viene materializzato in lista: serve `totale` prima di partire
#        (per il diario) e la lista va percorsa una volta sola in modo
#        prevedibile — un generatore consumato a meta' da un errore renderebbe
#        l'esito irriproducibile.
def run_fan_out(
    items: Iterable[Any],
    process: Callable[[Any], Any],
    *,
    isola_in_transazione: bool = True,
    on_success: Callable[[Any, Any], None] | None = None,
    run_logger: FanOutRunLogger | None = None,
) -> FanOutEsito:
    elenco = list(items)
    esito = FanOutEsito(totale=len(elenco))
    _chiama_logger(run_logger, "start", totale=esito.totale)

    for indice, item in enumerate(elenco):
        try:
            if isola_in_transazione:
                # Savepoint per item: il fallimento di uno annulla SOLO le sue
                # scritture, senza corrompere quelle degli item precedenti.
                with transaction.atomic():
                    risultato = process(item)
            else:
                # Chi isola per conto proprio (o non scrive) evita il savepoint:
                # annidarlo su un chiamante che ne apre gia' uno per item
                # aggiungerebbe un livello inutile a ogni giro.
                risultato = process(item)
        except Exception as exc:
            # Lo stack si logga qui una volta per tutte: entrambi i siti storici
            # lo facevano, ed e' la prima cosa che si perde riscrivendo il ciclo.
            # La repr TRONCATA dell'item da' l'identita' (id, segment_key…) che
            # il solo indice non porta: i siti storici la loggavano, e il log
            # applicativo e' il primo posto dove si guarda.
            logger.exception("fan-out: item %s (%.200r) fallito.", indice, item)
            esito.errori.append(
                FanOutItemErrore(
                    indice=indice,
                    item=item,
                    messaggio=messaggio_eccezione(exc),
                    eccezione=exc,
                )
            )
            _chiama_logger(run_logger, "item_failed", item=item, indice=indice, exc=exc)
        else:
            # Fuori dal savepoint per costruzione: il risultato entra solo se
            # l'item e' atterrato davvero.
            esito.risultati.append(risultato)
            if on_success is not None:
                # Deliberatamente FUORI dal try: qui il savepoint e' gia'
                # rilasciato e il lavoro dell'item non e' piu' annullabile —
                # mascherare un errore come "item fallito" direbbe una bugia.
                on_success(item, risultato)

    _chiama_logger(run_logger, "end", esito=esito)
    return esito
