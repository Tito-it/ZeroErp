# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura del CATALOGO DEI PRESIDI (`dbops.presidi`) — per ogni vista di
#        presidio, che cosa significa una sua riga — e il conteggio onesto di
#        quelle righe (`dbops.fn_conta_presidio`).
# Note: ⭐ QUI NON C'E' NESSUN ELENCO DI VISTE, ed e' il punto del cantiere. Fino
#        al 2026-09-10 il pannello dei presidi leggeva una tupla di dieci nomi
#        scritta in `processi_repository.py`: dal giorno in cui il catalogo
#        esiste quella tupla sarebbe la SECONDA sede di un fatto che il database
#        dichiara — e la seconda diverge alla prima vista nuova, in silenzio.
#        ⭐ Non e' un'ipotesi: `dbops.vw_rls_perimetro_scoperto` e' nata il
#        2026-09-09, lo stesso giorno in cui il brief contava «trentuno viste».
#
#        ⛔ IL CONTEGGIO NON SI FA QUI. Passa SEMPRE da `dbops.fn_conta_presidio`
#        — anche dal web, dove un perimetro c'e'. Tre viste sono
#        `security_invoker` su tabelle in row level security: da un percorso
#        senza le GUC (un management command) tornano ZERO per CECITA', e su una
#        vista che deve restare vuota «zero righe» e «non ho potuto vedere» si
#        scrivono uguale. Risponde un numero, mai le righe. ⚠️ Dal 2026-10-10
#        `fn_conta_presidio` e' `SECURITY INVOKER` (la somma dei gruppi): ad
#        attraversare la RLS e' la sua sede, `fn_conta_presidio_per_variante`,
#        `SECURITY DEFINER` del proprietario.
#        ⚠️ E la colonna `perimetro` dice un'ALTRA cosa: se chi legge puo' anche
#        ELENCARE le righe. Su `DEFINER` il conteggio si mostra e le righe no.
#
#        Brief: work-done/brief-db-un-destinatario-per-i-presidi.md §8.2.
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import Any, TypedDict

from django.db import connection

from apps.core.db._helpers import rows_to_list
# ⭐ Il nome della GUC e la lingua di ripiego hanno UNA sede, il middleware che
#    la imposta: ricopiarli qui sarebbe la seconda.
from apps.core.middleware.user_language_middleware import (
    DEFAULT_LANGUAGE as LINGUA_DEFAULT,
    GUC_NAME as GUC_LINGUA,
)

# ⚠️ MIRROR DICHIARATI dei quattro `CHECK` di `dbops.presidi`, e non una seconda
#    definizione: la regola sta a database e questi nomi servono al Python per
#    poterla nominare (quali nature vanno in quale elenco del digest, quale
#    cadenza sta girando, quando si possono mostrare le righe).
# ⛔ Presidiati contro l'originale da `apps/core/tests/db/test_presidi_catalogo.py`,
#    che li confronta con i `CHECK` veri via il BB `db_e2e.valori_check`: un
#    valore in meno qui e' un presidio che sparisce da un elenco senza che
#    niente fallisca.
NATURA_ZERO = "ZERO"
NATURA_REGISTRO = "REGISTRO"
NATURA_LAVORAZIONE = "LAVORAZIONE"
NATURA_CANCELLO = "CANCELLO"
NATURA_INVENTARIO = "INVENTARIO"
NATURE = (
    NATURA_ZERO, NATURA_REGISTRO, NATURA_LAVORAZIONE,
    NATURA_CANCELLO, NATURA_INVENTARIO,
)

CADENZA_GIORNALIERA = "GIORNALIERA"
CADENZA_SETTIMANALE = "SETTIMANALE"
CADENZA_MAI = "MAI"
CADENZE = (CADENZA_GIORNALIERA, CADENZA_SETTIMANALE, CADENZA_MAI)

PERIMETRO_LIBERO = "LIBERO"
PERIMETRO_DEFINER = "DEFINER"
PERIMETRI = (PERIMETRO_LIBERO, PERIMETRO_DEFINER)

# ⭐ CHI LO SPEGNE (`chk_presidi_chi_agisce`, brief-db-presidi-cosa-significa-
#    cosa-fare D-3). L'ORDINE DELLA TUPLA E' UN DATO: e' quello in cui il digest
#    raggruppa i presidi accesi — prima cio' che chi legge puo' sistemare da se',
#    poi cio' che va inoltrato.
# ⚠️ `NULL` e' ammesso dal modello solo sugli `INVENTARIO`
#    (`chk_presidi_chi_agisce_se_allarma`), che non si accendono: chi legge
#    tratta comunque il `None`, e lo mette in fondo.
CHI_AGISCE_AMMINISTRATORE = "AMMINISTRATORE"
CHI_AGISCE_SISTEMISTA = "SISTEMISTA"
CHI_AGISCE_SVILUPPO = "SVILUPPO"
CHI_AGISCE = (CHI_AGISCE_AMMINISTRATORE, CHI_AGISCE_SISTEMISTA, CHI_AGISCE_SVILUPPO)

# Il nome della vista arriva da una TABELLA e finisce interpolato nell'SQL che
# ne legge le righe. ⛔ Il `CHECK chk_presidi_vista_qualificata` lo garantisce
# gia' a database: questo e' il secondo giro di chiave, la stessa difesa che il
# progetto applica a ogni identificatore interpolato (`PartitionedNoteRepository`,
# `emittente_scope_helpers`). Una difesa sola su un dato che viene da fuori dal
# codice e' una difesa che qualcuno, un giorno, sposta.
_VISTA_AMMESSA = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

# Quante righe di esempio si consegnano per presidio: il pannello serve a dire
# CHE c'e' qualcosa e a farsi un'idea, non a essere una lista paginata.
RIGHE_PER_PRESIDIO = 20


# Scopo: una riga del catalogo dei presidi, con le due cose che il catalogo NON
#        contiene e che si leggono insieme a lei: la descrizione scritta sulla
#        vista e se quella vista esiste ancora.
class RigaPresidio(TypedDict):
    vista: str
    natura: str
    colonna_stato: str | None
    stato_atteso: str | None
    registro: str | None
    presidiato_da: str | None
    cadenza: str
    perimetro: str
    nota: str
    # ⭐ LA COLONNA DELLA VISTA CHE DICE LA CAUSA DI OGNI RIGA (dal 2026-10-09):
    #    quando c'e', le righe sono guasti diversi, e testo e «chi agisce» si
    #    leggono per causa (`cause_del_presidio`). ⛔ Il nome si legge da qui,
    #    mai scritto nel codice.
    colonna_variante: str | None
    # ⭐ IL TESTO PER CHI AGISCE (`dbops.presidi_testi`, dal 2026-10-06): cosa
    #    vuol dire una riga e cosa fare per spegnerla, nella lingua di chi legge
    #    con ripiego su `it`. La `nota` e la `descrizione` restano scritte per
    #    chi MANTIENE il presidio: sono un altro lettore, non un doppione.
    # ⚠️ `None` quando il presidio non ha testo (un `INVENTARIO`, o una vista in
    #    attesa di catalogo): chi rende ripiega sulla descrizione, mai sul vuoto.
    chi_agisce: str | None
    significato: str | None
    azione: str | None
    # ⭐ La prosa che il team DB ha scritto sulla vista: e' li' che sta la
    #    differenza fra «DEVE restare VUOTA» e «e' un registro che deve CALARE».
    #    Si legge da `obj_description`, non si ricopia.
    descrizione: str | None
    # ⚠️ Una vista a catalogo che non esiste piu' e' un difetto da DIRE, non da
    #    far esplodere: il pgTAP lo presidia, ma un digest che muore su una riga
    #    stantia smette di riferire anche tutte le altre.
    esiste: bool
    # ⛔ Vedi `_IN_ATTESA_DI_CATALOGO`: `False` solo per il debito dichiarato,
    #    che dal 2026-09-10 e' a zero righe — quindi oggi vale sempre `True`.
    a_catalogo: bool


# Scopo: un gruppo di righe di un presidio con la stessa CAUSA, col testo e il
#        «chi agisce» di quella causa (`dbops.presidi_cause` + `presidi_testi`).
# ⚠️ `causa` None = la riga non dice la sua causa; una causa che il catalogo non
#    conosce arriva col suo nome e senza testo. In tutti e due i casi
#    `significato`, `azione` e `chi_agisce` sono None, e ⛔ non si ripiega sul
#    testo del presidio: darebbe il rimedio di un altro guasto (§5.4.2).
class CausaPresidio(TypedDict):
    causa: str | None
    chi_agisce: str | None
    significato: str | None
    azione: str | None
    # ⭐ Quante righe del presidio hanno questa causa, da
    #    `dbops.fn_conta_presidio_per_variante` (R-2, 2026-10-10): il numero
    #    vero, non quello del campione. ⚠️ Mai meno delle `righe` consegnate:
    #    conteggio e campione sono due letture, e fra l'una e l'altra puo'
    #    accendersi una riga (`cause_del_presidio`).
    conteggio: int
    # Le righe del CAMPIONE con questa causa: possono essere zero anche con
    # `conteggio` > 0 (la causa sta oltre il campione, o il perimetro non le
    # lascia elencare).
    righe: list[dict[str, Any]]


# Scopo: una riga di `dbops.fn_conta_presidio_per_variante`.
class ConteggioVariante(TypedDict):
    variante: str | None
    conteggio: int


# ⚠️ IL DEBITO DICHIARATO DELLE VISTE NON ANCORA A CATALOGO — oggi A ZERO.
#    Qui stanno le viste che il pannello interroga e che il catalogo non conosce
#    ancora: si portano come riga dichiarata, con la STESSA forma che il team DB
#    applichera'. Toglierle dal pannello nell'attesa sarebbe la cosa peggiore —
#    una spia decisa e non ancora iscritta resterebbe spenta, e una spia spenta
#    non presidia niente.
# ⭐ SVUOTATA il 2026-09-10: `maintenance.vw_job_run_da_guardare` — l'unica voce
#    che ci sia mai stata — e' stata iscritta dal team DB (brief
#    §10.2, changeSet `20260910-35..37`), e il debito e' PAGATO.
#    Il verso di ritiro ha funzionato da se':
#    `test_il_debito_delle_viste_in_attesa_e_rientrato` e' diventato rosso il
#    giorno dell'apply e ha detto quale riga cancellare.
# ⛔ IL MECCANISMO NON SI CANCELLA INSIEME ALLA RIGA, ed e' una scelta: un
#    registro vuoto non e' un registro inutile, e' un registro in pari — la
#    stessa ragione per cui `dbops.codici_errore_senza_policy` resta a zero
#    righe invece di essere droppata. La prossima vista decisa e non ancora
#    applicata entra qui, non in un `if` sparso nel pannello.
# ⚠️ Finche' resta vuota, il ramo «non a catalogo» di `conta()` e
#    `_decora_in_attesa` non li percorre nessuno: sono DORMIENTI, non morti.
_IN_ATTESA_DI_CATALOGO: tuple[RigaPresidio, ...] = ()

# ⭐ La lingua del testo si sceglie COME per `config.messaggi_errore`
#    (`script.fn_get_messaggio`): la GUC che il middleware imposta per richiesta,
#    poi `it`. ⚠️ `NULLIF` perche' il middleware, a fine richiesta, la riporta a
#    stringa vuota e non la toglie: su una connessione riusata il vuoto vuol dire
#    «nessuna lingua», non una lingua che si chiama ''.
# ⛔ Il ripiego e' PER PRESIDIO, non per pagina: una traduzione che manca su una
#    vista sola fa parlare in italiano quella vista, non tutto il pannello.
# ⚠️ Dal management command del digest la GUC non c'e': si legge `it`, che e'
#    la lingua obbligatoria (il pgTAP `dbops/test-presidi-testi-v1` la pretende).
# ⛔ `variante IS NULL` e' il testo DEL PRESIDIO (dal 2026-10-09,
#    brief-db-presidio-processi-testo-per-causa §5.4): dove il catalogo dichiara
#    `colonna_variante`, `presidi_testi` porta anche un testo per ogni causa
#    delle righe, nella stessa (vista, lingua). Senza il filtro il `LIMIT 1`
#    pescherebbe una riga qualsiasi fra il generico e le cause — cioe' il
#    rimedio di una causa a caso scritto come testo dell'intero presidio.
# ⭐ UNA SEDE SOLA PER LA SCELTA DELLA LINGUA, due lettori: il testo del
#    presidio (`variante IS NULL`) e il testo di ogni causa (`variante = causa`).
#    Cambia solo QUALE testo si cerca; la cascata «lingua richiesta, poi `it`» e'
#    la stessa, e due copie divergerebbero al primo ritocco.
def _testo_per_lingua(condizione_variante: str) -> str:
    return f"""
    CROSS JOIN (
        SELECT COALESCE(NULLIF(current_setting(%s, true), ''), %s) AS richiesta,
               %s::text                                           AS ripiego
    ) lingua
    LEFT JOIN LATERAL (
        SELECT pt.significato, pt.azione
          FROM dbops.presidi_testi pt
         WHERE pt.vista = p.vista
           AND {condizione_variante}
           AND pt.lingua IN (lingua.richiesta, lingua.ripiego)
         ORDER BY (pt.lingua = lingua.richiesta) DESC
         LIMIT 1
    ) t ON TRUE
"""  # noqa: S608 — la condizione e' una costante del modulo, i valori sono parametri


_TESTO_PER_LINGUA = _testo_per_lingua("pt.variante IS NULL")
# ⛔ Il ripiego per lingua resta DENTRO la causa: una causa senza la riga nella
#    lingua chiesta parla `it` della STESSA causa, mai il testo generico — che
#    darebbe il rimedio sbagliato, cioe' il difetto del brief §1 (§5.4.2).
_TESTO_PER_CAUSA = _testo_per_lingua("pt.variante = c.causa")
_TESTO_PER_LINGUA_PARAMS = (GUC_LINGUA, LINGUA_DEFAULT, LINGUA_DEFAULT)

_COLONNE_CATALOGO = """
    p.vista,
    p.natura,
    p.colonna_stato,
    p.stato_atteso,
    p.registro,
    p.presidiato_da,
    p.cadenza,
    p.perimetro,
    p.nota,
    p.colonna_variante,
    p.chi_agisce,
    t.significato,
    t.azione,
    obj_description(to_regclass(p.vista), 'pg_class') AS descrizione,
    (to_regclass(p.vista) IS NOT NULL)               AS esiste,
    TRUE                                             AS a_catalogo
"""


class PresidiRepository:
    """Il catalogo dei presidi e il conteggio delle loro righe."""

    # Scopo: Le righe ATTIVE del catalogo, filtrate per cadenza quando chi legge
    #        sta girando a una cadenza precisa (il digest) e non filtrate quando
    #        gli serve tutto (il pannello).
    #
    # ⭐ IL FILTRO SULLA CADENZA E' ANCHE IL FILTRO SUL DIGEST, e non serve un
    #    elenco di nature: il `CHECK chk_presidi_fuori_digest_cadenza_mai`
    #    garantisce a database che INVENTARIO e CANCELLO abbiano cadenza `MAI`.
    #    ⇒ Chiedere «cosa guardo stanotte» e' una domanda sola, e la risposta la
    #    da' il catalogo. Un elenco di nature da escludere qui sarebbe la stessa
    #    regola scritta due volte, e la seconda copia non conosce la natura che
    #    nascera' domani.
    # ⚠️ `obsoleto_dal` E `attivo` sono due assenze diverse: la prima RITIRA una
    #    vista dal catalogo, la seconda la spegne per un motivo scritto. Il
    #    lettore le tratta uguale — non c'e' niente da guardare in nessuno dei
    #    due casi — ma chi guarda il catalogo deve vederle distinte.
    def list_catalogo(
        self, *, cadenze: tuple[str, ...] | None = None,
    ) -> list[RigaPresidio]:
        condizioni = ["p.attivo", "p.obsoleto_dal IS NULL"]
        # ⚠️ I parametri del join vengono PRIMA, nell'ordine in cui compaiono.
        params: list[Any] = [*_TESTO_PER_LINGUA_PARAMS]
        if cadenze is not None:
            condizioni.append("p.cadenza = ANY(%s)")
            params.append(list(cadenze))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_COLONNE_CATALOGO}
                  FROM dbops.presidi p
                  {_TESTO_PER_LINGUA}
                 WHERE {' AND '.join(condizioni)}
                """,  # noqa: S608 — frammenti costanti, i valori sono parametri
                params,
            )
            righe: list[RigaPresidio] = rows_to_list(cursor)  # type: ignore[assignment]

        # ⚠️ Il debito dichiarato entra QUI, dopo il catalogo, e rispetta lo
        #    stesso filtro di cadenza: e' una riga come le altre finche' non lo
        #    diventa davvero.
        in_attesa = [
            riga for riga in _IN_ATTESA_DI_CATALOGO
            if cadenze is None or riga["cadenza"] in cadenze
        ]
        if in_attesa:
            righe.extend(self._decora_in_attesa(in_attesa))
        # ⚠️ L'ordine si da' QUI e non anche in SQL: il debito dichiarato si
        #    mescola alle righe di catalogo, quindi un `ORDER BY` a database
        #    sarebbe comunque da rifare — e due ordinamenti sullo stesso elenco
        #    sono due regole che un giorno diranno cose diverse.
        return sorted(righe, key=lambda r: r["vista"])

    # Scopo: Quante righe di questa vista CHIEDONO UN INTERVENTO.
    #
    # ⛔ Passa da `dbops.fn_conta_presidio` e non da un `count(*)` scritto qui, e
    #    vale ANCHE dal web: la funzione applica il filtro (colonna_stato,
    #    stato_atteso) letto dal catalogo — «diverso dallo stato atteso», cosi'
    #    uno stato nuovo cade nell'allarme e non nel silenzio — e attraversa la
    #    row level security dove la vista da sola tornerebbe zero per cecita'.
    #    Un conteggio scritto qui sarebbe la seconda sede di quel filtro.
    # ⚠️ L'UNICA eccezione e' il debito di `_IN_ATTESA_DI_CATALOGO`: la funzione
    #    RIFIUTA una vista che il catalogo non conosce (`E_PRESIDIO_NON_A_CATALOGO`),
    #    ed e' giusto che lo faccia — li' si conta diretto.
    # ⭐ Dal 2026-09-10 quel debito e' a ZERO, quindi questo ramo e' DORMIENTE:
    #    non lo percorre nessuno finche' non entra una vista nuova in attesa.
    # ⛔ E non si toglie: e' l'unica strada per cui una spia gia' decisa e non
    #    ancora iscritta resta ACCESA invece di sparire dal pannello.
    def conta(self, riga: RigaPresidio) -> int:
        vista = self._vista_valida(riga["vista"])
        with connection.cursor() as cursor:
            if riga["a_catalogo"]:
                cursor.execute("SELECT dbops.fn_conta_presidio(%s)", [vista])
            else:
                cursor.execute(f"SELECT count(*) FROM {vista}")  # noqa: S608
            valore = cursor.fetchone()
        assert valore is not None  # count e fn_conta_presidio tornano una riga
        return int(valore[0])

    # Scopo: Quante righe di questa vista chiedono un intervento, PER VALORE
    #        della colonna che il catalogo nomina in `colonna_variante` (R-2 del
    #        brief-db-presidio-processi-testo-per-causa, 2026-10-10).
    #
    # ⭐ E' la SEDE del conteggio a database: `fn_conta_presidio` ne e' la
    #    somma, quindi filtro e perimetro sono gli stessi per costruzione.
    # ⚠️ Una riga per valore presente, i valori a zero non escono; `variante`
    #    NULL e' un gruppo a se' («causa non indicata»). Su un presidio senza
    #    variante risponde una riga sola `(NULL, n)`.
    # ⛔ `SELECT … FROM fn(…)` e non `SELECT fn(…)`: la seconda consegna la tupla
    #    in un campo solo (§7.4 del brief).
    def conta_per_variante(self, riga: RigaPresidio) -> list[ConteggioVariante]:
        vista = self._vista_valida(riga["vista"])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT variante, conteggio "
                "FROM dbops.fn_conta_presidio_per_variante(%s)",
                [vista],
            )
            return [
                {"variante": variante, "conteggio": int(conteggio)}
                for variante, conteggio in cursor.fetchall()
            ]

    # Scopo: Il conteggio di un presidio e, dove il catalogo nomina una
    #        `colonna_variante`, i conteggi per causa da cui discende: UNA
    #        lettura sola. `(n, None)` per un presidio senza cause.
    #
    # ⭐ Il totale e' la SOMMA dei conteggi per causa, non una seconda lettura
    #    di `fn_conta_presidio`: quella funzione ne e' gia' la somma a database,
    #    e due letture prese in due momenti potevano dire un totale e delle
    #    cause che non tornano. Cosi' tornano per costruzione.
    # ⚠️ Solo per le viste a catalogo: quelle in attesa passano da `conta`, e
    #    la funzione per causa le rifiuterebbe come `fn_conta_presidio`.
    def conta_presidio(
        self, riga: RigaPresidio,
    ) -> tuple[int, list[ConteggioVariante] | None]:
        if riga["a_catalogo"] and riga["colonna_variante"]:
            conteggi = self.conta_per_variante(riga)
            return sum(c["conteggio"] for c in conteggi), conteggi
        return self.conta(riga), None

    # Scopo: Le prime righe di una vista, per chi le puo' vedere.
    #
    # ⛔ Su `perimetro = DEFINER` NON si elencano, e il guard sta qui e non nel
    #    chiamante: quelle viste attraversano una tabella in row level security,
    #    e il conteggio onesto arriva da una funzione che le righe non le
    #    restituisce apposta. Elencarle da un percorso qualsiasi vorrebbe dire
    #    consegnare righe fuori perimetro — o, dal web, un elenco piu' corto del
    #    numero mostrato accanto, che si legge come un difetto e non come un
    #    perimetro.
    def prime_righe(
        self, riga: RigaPresidio, *, limite: int = RIGHE_PER_PRESIDIO,
    ) -> list[dict[str, Any]]:
        if riga["perimetro"] != PERIMETRO_LIBERO:
            return []
        vista = self._vista_valida(riga["vista"])
        # ⛔ `LIMIT` non positivo: PostgreSQL rifiuta il negativo e lo zero
        #    consegna zero righe, che qui si leggerebbe come «la vista e' vuota»
        #    — cioe' come un dato. Si porta a uno: un esempio o niente.
        limite = max(1, int(limite))
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {vista} LIMIT %s", [limite])  # noqa: S608
            return rows_to_list(cursor)

    # Scopo: Le CAUSE accese di un presidio, ognuna col suo conteggio, il suo
    #        testo, il suo «chi agisce» e le righe del campione che le
    #        appartengono. `[]` se il presidio non dichiara `colonna_variante`:
    #        allora vale il testo del presidio, come prima.
    #
    # ⭐ L'unica sede del raggruppamento: pannello e digest lo chiedono qui, e non
    #    possono raccontare la stessa causa in due modi.
    # ⭐ SI PARTE DAI CONTEGGI, non dal campione (§6.4.2 del brief, dal
    #    2026-10-10): ogni causa accesa arriva, anche quella che sta oltre le
    #    prime righe o su una vista che non si elenca. Raggruppare il solo
    #    campione dava numeri sbagliati, e una causa oltre la quinta riga non
    #    arrivava mai a chi la deve spegnere.
    # ⚠️ Conteggio e campione sono DUE letture: una riga accesa fra l'una e
    #    l'altra porta una causa che i conteggi non hanno, o una in piu' di
    #    quante ne contavano. Non si scarta (e' un guasto vero): il gruppo nasce
    #    o cresce, e il suo conteggio non e' mai meno delle righe che mostra.
    # ⭐ L'ordine e' quello della funzione (per valore, il NULL in coda): un
    #    riordino qui sarebbe una seconda regola.
    # ⭐ I conteggi per causa li riceve da `conta_presidio` (la stessa lettura
    #    del totale), non li rilegge: `None` = presidio senza cause.
    def cause_del_presidio(
        self, riga: RigaPresidio, righe: list[dict[str, Any]],
        conteggi: list[ConteggioVariante] | None,
    ) -> list[CausaPresidio]:
        colonna = riga["colonna_variante"]
        if not colonna or conteggi is None:
            return []
        if not conteggi and not righe:
            return []
        testi = self.testi_delle_cause(riga["vista"])

        def _gruppo(causa: str | None, conteggio: int) -> CausaPresidio:
            # ⛔ Causa NULL o fuori catalogo: testo e «chi agisce» a None, mai
            #    quelli del presidio — sarebbero il rimedio di un altro guasto.
            testo = testi.get(causa) if causa is not None else None
            return {
                "causa": causa,
                "chi_agisce": testo["chi_agisce"] if testo else None,
                "significato": testo["significato"] if testo else None,
                "azione": testo["azione"] if testo else None,
                "conteggio": conteggio,
                "righe": [],
            }

        gruppi: dict[str | None, CausaPresidio] = {
            c["variante"]: _gruppo(c["variante"], c["conteggio"]) for c in conteggi
        }
        for r in righe:
            valore = r.get(colonna)
            # ⚠️ La funzione consegna la variante come testo (`::text`): la
            #    colonna della vista puo' avere un tipo suo.
            causa = None if valore is None else str(valore)
            if causa not in gruppi:
                gruppi[causa] = _gruppo(causa, 0)
            gruppi[causa]["righe"].append(r)
        for g in gruppi.values():
            g["conteggio"] = max(g["conteggio"], len(g["righe"]))
        return list(gruppi.values())

    # Scopo: Il catalogo delle cause di un presidio: per ogni causa chi la spegne
    #        e il testo, nella lingua di chi legge con ripiego su `it` della
    #        stessa causa.
    # ⚠️ LEFT JOIN sul testo: una causa senza testo e' un pgTAP rosso
    #    (`test-presidi-testi-v1` 16), ma se succede la causa arriva lo stesso,
    #    col suo «chi agisce» e il testo a None — non sparisce.
    def testi_delle_cause(self, vista: str) -> dict[str, dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT c.causa, c.chi_agisce, t.significato, t.azione
                  FROM dbops.presidi p
                  JOIN dbops.presidi_cause c ON c.vista = p.vista
                  {_TESTO_PER_CAUSA}
                 WHERE p.vista = %s
                """,  # noqa: S608 — frammenti costanti, i valori sono parametri
                [*_TESTO_PER_LINGUA_PARAMS, vista],
            )
            return {r["causa"]: r for r in rows_to_list(cursor)}

    # Scopo: Lo stato dei presidi per il PANNELLO: per ogni vista che deve
    #        restare vuota, quante righe ha, che cosa significa e le prime.
    #
    # ⭐ LE VISTE SONO QUELLE DI NATURA `ZERO`, LETTE DAL CATALOGO (decisione di
    #    Tid, 2026-09-10). Sono gli allarmi veri — «questa vista deve restare
    #    vuota» — e `LAVORAZIONE`, `CANCELLO` e `INVENTARIO` non lo sono: una
    #    coda con righe e' lavoro in corso, non un guasto, e un pannello che
    #    mostra righe verdi insegna a leggere il verde come debito.
    # ⛔ Prima erano una TUPLA DI DIECI NOMI in `processi_repository.py`: dal
    #    giorno in cui il catalogo esiste, quella tupla era la seconda sede dello
    #    stesso fatto. ⚠️ E le due non coincidevano: cinque `ZERO` a catalogo non
    #    le guardava nessuno, e una vista `LAVORAZIONE` stava fra gli allarmi.
    # ⭐ E il CONTEGGIO cambia, in meglio: passando da `dbops.fn_conta_presidio`
    #    una vista con `colonna_stato` conta le sole righe DIVERSE dallo stato
    #    atteso — cioe' il pannello smette di mostrare come allarme un debito
    #    gia' dichiarato.
    # ⛔ E l'isolamento e' per presidio, come nel digest: una vista che non si
    #    legge diventa una riga che lo DICE, non un 500 che spegne la schermata
    #    intera. ⚠️ Chiude anche la connessione, perche' un presidio puo' non
    #    limitarsi a fallire: puo' portarsela via.
    # ⭐ `con_righe=False` e' la lettura LEGGERA per il pallino della topbar
    #    (piano-be-fe-osservabilita-pallino-e-superfici §2.2, 2026-09-18): stesso
    #    giro, stesso isolamento, stesse righe — senza `prime_righe`. E' un
    #    parametro e non un secondo metodo perche' il giro e' UNO: una copia
    #    «senza righe» divergerebbe dalla prima al primo campo nuovo della riga,
    #    e il pallino direbbe una cosa e il pannello un'altra.
    def stato_presidi(
        self, *, righe_per_presidio: int = RIGHE_PER_PRESIDIO,
        con_righe: bool = True,
    ) -> list[dict[str, Any]]:
        esito: list[dict[str, Any]] = []
        for riga in self.list_catalogo():
            if riga["natura"] != NATURA_ZERO:
                continue
            try:
                conteggio, conteggi = self.conta_presidio(riga)
                righe = (
                    self.prime_righe(riga, limite=righe_per_presidio)
                    if (con_righe and conteggio) else []
                )
                # ⚠️ Anche senza righe (perimetro DEFINER): le cause e i loro
                #    numeri arrivano dalla funzione, non dall'elenco. La lettura
                #    leggera del pallino non le chiede.
                cause = (
                    self.cause_del_presidio(riga, righe, conteggi)
                    if (con_righe and conteggio) else []
                )
            except Exception as exc:  # isolamento per presidio
                # ⚠️ Solo se e' inutilizzabile: questo giro sta dentro una
                #    richiesta web, e chiudere una connessione sana e' un
                #    effetto collaterale che non ci si aspetta da una lettura.
                connection.close_if_unusable_or_obsolete()
                esito.append({
                    "vista": riga["vista"],
                    "descrizione": riga["descrizione"],
                    # ⭐ Il significato si consegna (dice COSA non si e'
                    #    potuto guardare); l'azione e chi agisce NO: rimediano
                    #    a righe accese, e qui il guasto e' la lettura — chi
                    #    legge non deve «rilanciare i lotti» di un presidio
                    #    che non si e' visto.
                    "significato": riga["significato"],
                    "azione": None,
                    "chi_agisce": None,
                    "conteggio": None,
                    "righe": [],
                    "cause": [],
                    "troncato": False,
                    "elencabili": riga["perimetro"] == PERIMETRO_LIBERO,
                    "errore": str(exc),
                    # ⛔ Non letto = chiede un occhio, sempre: il verde qui vuol
                    #    dire «visto e vuoto», e questo non e' stato visto.
                    "da_guardare": True,
                })
                continue
            esito.append({
                # ⚠️ Il nome esce QUALIFICATO anche a video: due schemi diversi
                #    possono avere viste omonime, e un pannello che ne mostra
                #    una sola meta' manderebbe a guardare quella sbagliata.
                "vista": riga["vista"],
                # ⭐ Qui la prosa e' il COMMENT della vista e non la `nota` del
                #    catalogo: il pannello ha lo spazio per il contratto intero,
                #    a differenza di un messaggio di posta.
                "descrizione": riga["descrizione"],
                # ⭐ Il testo per chi agisce (brief-db-presidi-cosa-significa-
                #    cosa-fare §6): il pannello lo mette DAVANTI alla
                #    descrizione, che resta come dettaglio tecnico.
                "significato": riga["significato"],
                "azione": riga["azione"],
                "chi_agisce": riga["chi_agisce"],
                "conteggio": conteggio,
                "righe": righe,
                # ⭐ Le stesse righe per CAUSA, col rimedio accanto (brief-db-
                #    presidio-processi-testo-per-causa §5.4.3): vuoto dove il
                #    presidio ha un testo solo. Il pannello rende queste invece
                #    di `righe` quando ci sono.
                "cause": cause,
                # ⚠️ «Troncato» presuppone che le righe siano state chieste: su
                #    una vista con perimetro l'elenco e' vuoto per contratto, e
                #    un `troncato` vero li' fa scrivere a video «prime 0 righe».
                "troncato": bool(righe) and conteggio > len(righe),
                # ⭐ E si dice PERCHE' l'elenco manca: senza, «non elencabile» e
                #    «non c'e' niente da elencare» si leggono uguali — che e'
                #    la stessa confusione fra zero e cecita' da cui nasce
                #    `dbops.fn_conta_presidio`.
                "elencabili": riga["perimetro"] == PERIMETRO_LIBERO,
                "errore": None,
                # ⭐ «Chiede un occhio?» si decide QUI, nella riga, e il client
                #    lo legge: e' la stessa domanda che la testata conta
                #    (`con_righe` + `non_letti`), e un predicato ricopiato nel
                #    pannello (com'era il 2026-09-15) sarebbe la seconda sede —
                #    la scheda e il numero potrebbero dire due cose.
                "da_guardare": conteggio > 0,
            })
        return esito

    # ══════════════════════════════════════════════════════════
    #  Interno
    # ══════════════════════════════════════════════════════════

    # Scopo: Rifiuta un nome di vista che non ha la forma `schema.oggetto`.
    # ⛔ Non e' prudenza contro un input dell'utente — qui non ne arrivano: e' il
    #    presidio contro un catalogo modificato a mano da un percorso che il
    #    `CHECK` non ha attraversato. Un refuso interpolato non da' un errore di
    #    sintassi: da' una query su un'altra cosa.
    def _vista_valida(self, vista: str) -> str:
        if not _VISTA_AMMESSA.match(vista or ""):
            raise ValueError(
                f"nome di vista non ammesso nel catalogo dei presidi: {vista!r} "
                f"(atteso schema.oggetto, minuscole)"
            )
        return vista

    # Scopo: Completa le righe del debito dichiarato con le due cose che il
    #        catalogo avrebbe letto dal database: la descrizione della vista e
    #        se esiste. ⚠️ Senza, quelle righe si distinguerebbero a video dalle
    #        altre per un motivo che non c'entra niente col loro contenuto.
    def _decora_in_attesa(
        self, righe: tuple[RigaPresidio, ...] | list[RigaPresidio],
    ) -> list[RigaPresidio]:
        nomi = [self._vista_valida(r["vista"]) for r in righe]
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT v AS vista,
                       obj_description(to_regclass(v), 'pg_class') AS descrizione,
                       (to_regclass(v) IS NOT NULL)                AS esiste
                  FROM unnest(%s::text[]) AS v
                """,
                [nomi],
            )
            letto = {r["vista"]: r for r in rows_to_list(cursor)}
        return [
            {**riga, 
                "descrizione": letto.get(riga["vista"], {}).get("descrizione"),
                "esiste": bool(letto.get(riga["vista"], {}).get("esiste"))
            }
            for riga in righe
        ]
