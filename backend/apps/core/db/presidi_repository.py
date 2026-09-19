# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#        scrivono uguale. La funzione e' `SECURITY DEFINER` del proprietario e
#        risponde un numero, mai le righe.
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

# ⚠️ MIRROR DICHIARATI dei tre `CHECK` di `dbops.presidi`, e non una seconda
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
        params: list[Any] = []
        if cadenze is not None:
            condizioni.append("p.cadenza = ANY(%s)")
            params.append(list(cadenze))
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT {_COLONNE_CATALOGO}
                  FROM dbops.presidi p
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
                conteggio = self.conta(riga)
                righe = (
                    self.prime_righe(riga, limite=righe_per_presidio)
                    if (con_righe and conteggio) else []
                )
            except Exception as exc:  # noqa: BLE001 — isolamento per presidio
                # ⚠️ Solo se e' inutilizzabile: questo giro sta dentro una
                #    richiesta web, e chiudere una connessione sana e' un
                #    effetto collaterale che non ci si aspetta da una lettura.
                connection.close_if_unusable_or_obsolete()
                esito.append({
                    "vista": riga["vista"],
                    "descrizione": riga["descrizione"],
                    "conteggio": None,
                    "righe": [],
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
                "conteggio": conteggio,
                "righe": righe,
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
