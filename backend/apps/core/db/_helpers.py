# Helper condivisi per tutti i repository DB.

from __future__ import annotations

import json
import logging
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any

from django.db import connection
from psycopg.postgres import types as _tipi_postgres

from apps.core.api.constants import MAX_LIMIT
from apps.core.services.error_manager import ErrorManager


logger = logging.getLogger(__name__)


def iso_or_none(value: Any) -> str | None:
    """Timestamp/date → ISO 8601, preservando None (colonne nullable).

    Regola del 2 (2026-07-22): estratto alla 3ª copia della closure `_iso`
    nei mapping riga→dict dei repository (coda lavori elenca/dettaglio,
    coda stampa).
    """
    return value.isoformat() if value is not None else None


# Scopo: L'ULTIMA CORSA CONCLUSA di un job come UN oggetto — data ed esito
#        insieme, dalla stessa riga — o `None` se il job non ne ha mai conclusa
#        una. E' la forma comune delle tre sedi che riassumono le corse
#        (`MaintenanceRepository.job_liveness` / `.list_job_summary` sul
#        giornale dei run, `CodaLavoriRepository.summary_per_job_type` sulla
#        coda lavori), e sta qui perche' il pannello degli esiti le FONDE in una
#        lista sola: una forma diversa per sorgente e' esattamente cio' che il
#        template non puo' vedere.
# ⛔ Nasce il 2026-09-14 al posto di un `last_ok` accanto a un `last_run_at`:
#    due campi da due corse diverse (l'ultima avviata e l'ultima conclusa) che
#    a video si leggevano come una — «<adesso> (ok)» con l'ok della corsa
#    precedente. Un esito senza la sua data e' il campo che invita a ricucire.
# ⚠️ `ok` passa cosi' com'e' (`bool | None`): `job_run_log.ok` e' nullable e
#    nessun CHECK lo lega a `ended_at`, quindi una corsa chiusa senza esito
#    scritto e' un caso che il modello ammette — chi rende lo dice, non lo
#    trasforma in un fallimento.
def corsa_conclusa(
    started_at: Any, ended_at: Any, ok: bool | None,
) -> dict[str, Any] | None:
    if started_at is None:
        return None
    return {
        "started_at": iso_or_none(started_at),
        "ended_at": iso_or_none(ended_at),
        "ok": ok,
    }


# Gli OID dei tipi che il backend Django per psycopg 3 consegna come TESTO fuori
# dall'ORM: `jsonb` come `str`, `jsonb[]` come lista di `str`. Il `json` (114)
# arriva gia' decodificato e non serve toccarlo (provato su dbdev, 2026-10-28).
# Gli OID dal registro dei tipi di psycopg, non scritti a mano.
_OID_JSONB = _tipi_postgres["jsonb"].oid
_OID_JSONB_ARRAY = _tipi_postgres["jsonb"].array_oid


# Scopo: Le colonne del cursore, coi decodificatori delle colonne jsonb.
#        Ritorna (nomi, {indice: decodifica}): la decodifica e' scelta dal TIPO
#        che il DB dichiara in `cursor.description`, non da un elenco di nomi.
# ⭐ E' la sede unica della regola «il jsonb arriva come testo» per i lettori a
#    dizionari (`row_to_dict`, `rows_to_list`, `extract_paginated` e chi li usa):
#    chi scrive una query non deve ricordarsi di decodificare. Fino al
#    2026-10-28 se lo ricordava ogni punto da se', e chi se ne dimenticava
#    consegnava `meta` come testo alle API e ai modelli di stampa, o rifiutava
#    la ristampa fedele di ogni documento (brief-modello-documento-vendita
#    §15.17.3).
# ⚠️ Le letture PER POSIZIONE (`fetchone()`/`fetchall()` letti a indice)
#    restano fuori: ricevono ancora il testo e decodificano da se'.
def _colonne_e_decodifiche(cursor) -> tuple[list[str], dict[int, Any]]:
    nomi: list[str] = []
    decodifiche: dict[int, Any] = {}
    for i, c in enumerate(cursor.description):
        nomi.append(c.name)
        # `getattr`: un descrittore senza tipo (i cursori finti dei test) non
        # ha colonne jsonb da decodificare.
        tipo = getattr(c, "type_code", None)
        if tipo == _OID_JSONB:
            decodifiche[i] = jsonb_out
        elif tipo == _OID_JSONB_ARRAY:
            decodifiche[i] = _jsonb_array_out
    return nomi, decodifiche


# Scopo: un `jsonb[]` (lista di testi JSON) con ogni elemento decodificato;
#        NULL e gli elementi NULL restano `None`.
def _jsonb_array_out(value: Any) -> Any:
    if value is None:
        return None
    return [jsonb_out(v) for v in value]


# Scopo: una riga del cursore come dict, coi jsonb decodificati.
def _riga_dict(nomi: list[str], decodifiche: dict[int, Any], row: Any) -> dict[str, Any]:
    riga = dict(zip(nomi, row, strict=True))
    for i, decodifica in decodifiche.items():
        riga[nomi[i]] = decodifica(row[i])
    return riga


def row_to_dict(cursor) -> dict[str, Any] | None:
    """Converte la riga corrente (fetchone) in dict {colonna: valore}.

    Restituisce None se non ci sono righe. Le colonne jsonb arrivano
    decodificate (vedi `_colonne_e_decodifiche`).
    """
    row = cursor.fetchone()
    if row is None:
        return None
    nomi, decodifiche = _colonne_e_decodifiche(cursor)
    return _riga_dict(nomi, decodifiche, row)


def rows_to_list(cursor) -> list[dict[str, Any]]:
    """Converte tutte le righe (fetchall) in lista di dict.

    Le colonne jsonb arrivano decodificate (vedi `_colonne_e_decodifiche`).
    """
    nomi, decodifiche = _colonne_e_decodifiche(cursor)
    return [_riga_dict(nomi, decodifiche, row) for row in cursor.fetchall()]


def coerce_jsonb_dict(value: Any) -> dict[str, Any]:
    """Coercion difensiva jsonb -> dict (il driver puo' restituire jsonb come str).

    Promozione regola-del-2 del clone nato in pratiche_repository (2026-06-11)
    e replicato in ui_admin/vendite: JSON malformato o non-oggetto -> {} (mai
    raise: i chiamanti sono path di lettura/display, non validazione input).
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def jsonb_out(value: Any) -> Any:
    """Decodifica una colonna jsonb letta da cursor RAW, preservando NULL.

    Il backend Django per psycopg 3 NON decodifica i jsonb fuori dall'ORM:
    arrivano come `str`. Variante NULL-PRESERVING di `coerce_jsonb_dict`
    (che invece coercizza None/malformato a `{}`): qui None resta None
    (es. `scope` NULL = job SISTEMA, `ultimo_errore` NULL = nessun errore)
    e il JSON e' garantito valido dal tipo colonna — un decode error e' un
    bug da far esplodere, non da mascherare. Nata dal bug scoperto dallo
    smoke C-9 «parte alta» (2026-07-22): il worker della coda generica
    riceveva payload/scope come stringa e l'handler moriva al primo `.get`.
    """
    if isinstance(value, str):
        return json.loads(value)
    return value


# Il nome di colonna (con alias facoltativo) che `predicato_giorno_operativo`
# accetta: finisce interpolato nell'SQL, quindi si ferma qui tutto il resto.
_COLONNA_ISTANTE = re.compile(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?")


# Scopo: IL FILTRO PER GIORNO su una colonna ISTANTE (`timestamptz`): «la
#        colonna cade nei giorni da `da` ad `a`, inclusi» — nel fuso
#        dell'AZIENDA, non della sessione. Ritorna `(sql, params)`: un
#        frammento da mettere in AND e i suoi parametri, nell'ordine.
#        Brief un-solo-fuso-aziendale B-4 (decisione di Tid, 2026-10-09).
#
#        ⭐ I confini li calcola il DB (`script.fn_inizio_giorno_operativo`,
#        sede unica del fuso): `col >= inizio(da) AND col < inizio(a + 1)`.
#        La funzione sta sui CONFINI e non sulla colonna, cosi' il predicato
#        resta servito dall'indice sulla colonna.
#        ⭐ UNA forma per ogni sede: l'SQL e' costante (non dipende da quali
#        filtri ci sono), con la guardia `%s::date IS NULL OR …`. Django lega i
#        parametri lato client, quindi il planner vede un letterale e la
#        guardia si semplifica: col valore resta il solo confronto (indice),
#        senza valore il ramo sparisce.
#        ⛔ MAI `col >= %s::date` (la mezzanotte della SESSIONE, UTC), mai
#        `col::date` (il giorno della sessione, e niente indice), mai il `+1
#        giorno` calcolato in Python: sono le quattro forme che questo BB ritira.
# ⚠️ Per una colonna `date` confrontata con una data non serve: non ha il
#    difetto (decisione 2 del brief). Serve dove la colonna e' un istante.
def predicato_giorno_operativo(
    colonna: str, da: date | None, a: date | None,
) -> tuple[str, list[date | None]]:
    if not _COLONNA_ISTANTE.fullmatch(colonna):
        raise ValueError(f"colonna non ammessa nel filtro per giorno: {colonna!r}")
    sql = (
        f"(%s::date IS NULL OR {colonna} >= script.fn_inizio_giorno_operativo(%s::date))"
        f" AND (%s::date IS NULL OR {colonna} < script.fn_inizio_giorno_operativo(%s::date + 1))"
    )
    return sql, [da, da, a, a]


def escape_ilike(value: str) -> str:
    """Escapa i metacaratteri ILIKE (`%`, `_`, `\\`) nel termine di ricerca.

    Senza escape l'input utente agisce da wildcard (es. cercare "BA_123" o
    "50%" matcha oltre l'atteso). L'escape del backslash va fatto per primo.
    Regola del 2: estratto dai lookup billing_account / istanze_utility /
    soggetti-ruoli che lo duplicavano localmente.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# Scopo: il pattern «contiene» di una ricerca `ILIKE`: termine ripulito dagli
#        spazi, metacaratteri escapati, `%` ai due lati. `None` se il termine e'
#        assente o vuoto — il chiamante lo usa col suo `%s::text IS NULL OR`.
# ⛔ E' l'UNICO modo di costruire il pattern. Fino al 2026-09-26 la riga
#    `f"%{search.strip()}%"` era scritta a mano in 18 punti e `escape_ilike`
#    in 5: nei 18 un `%` o un `_` scritti dall'utente facevano da jolly
#    («50%» trovava ogni riga che contiene 50, «A_1» anche «AB1»). Un difetto che non da'
#    errore, da' solo righe in piu'.
def pattern_contiene(termine: str | None) -> str | None:
    if termine is None:
        return None
    pulito = termine.strip()
    if not pulito:
        return None
    return f"%{escape_ilike(pulito)}%"


# Soglia di progetto delle ricerche che NON sono una lista a catalogo: il 400
# di `require_min_search_length` (ricerca universale, lookup), i tool
# dell'assistente. ⛔ Non il resolver soggetti: cerca con la lista
# `anagrafiche.soggetti`, e ne usa la soglia a catalogo (§6 b del brief sotto).
# ⛔ Non e' la soglia delle liste configurabili: quella e' un fatto della LISTA
#    (`ui.lista_definizione.ricerca_min_caratteri`, brief-db-be-fe-ricerca-
#    soglia-per-lista) e il BB `add_ricerca_full_condition` la legge dal
#    catalogo (`soglia_ricerca`). Un numero scritto qui per le liste sarebbe la
#    seconda sede dello stesso fatto — com'era fino al 2026-09-26, con
#    quattordici `min_caratteri=1` nei repository e nessuno nel frontend.
RICERCA_MIN_CARATTERI = 3

_NOME_COLONNA = re.compile(r"^[a-z_][a-z0-9_]*$")


@dataclass(frozen=True)
class RicercaFull:
    """Cosa si PUO' cercare in una lista configurabile: la dichiarazione del repository.

    `lista_codice` e' il codice della lista a catalogo (`ui.lista_definizione`),
    `colonne` le colonne che il repository SA cercare in quella query:

    - **tupla** di `campo_sorgente` quando sono colonne semplici della relazione
      nel `FROM` (`("numero", "ba_codice")` → `v.numero`, `v.ba_codice`, con
      l'alias passato al BB);
    - **mappa** `campo_sorgente → espressione SQL` quando il nome del catalogo
      e' un nome di USCITA (`{"ba_codice": "ba.codice"}`): stessa forma delle
      whitelist di ordinamento. ⭐ Il valore e' la stessa espressione che la
      `SELECT` proietta con quel nome: si cerca su cio' che si mostra.

    ⭐ Codice lista e colonne stanno in UNA dichiarazione apposta: una chiamata
    non puo' cosi' passare le colonne di una lista col codice di un'altra.

    ⚠️ La validazione e' qui e non nel BB: un nome sbagliato esplode
    all'IMPORT del modulo, non al primo operatore che cerca.
    """

    lista_codice: str
    colonne: tuple[str, ...] | Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.lista_codice:
            raise RuntimeError("RicercaFull: lista_codice vuoto")
        # ⚠️ `("numero")` e' una STRINGA, non una tupla: iterata darebbe una
        #    colonna per lettera, tutte valide per il controllo dei nomi.
        if isinstance(self.colonne, str):
            raise RuntimeError(
                f"RicercaFull {self.lista_codice}: colonne e' una stringa, serve una tupla o una mappa"
            )
        # Congelata su una copia: validata qui, non deve poter cambiare dopo
        # (una mappa del modulo modificata a runtime salterebbe il controllo).
        congelate = (
            MappingProxyType(dict(self.colonne)) if isinstance(self.colonne, Mapping)
            else tuple(self.colonne)
        )
        object.__setattr__(self, "colonne", congelate)
        if not self.colonne:
            raise RuntimeError(f"RicercaFull {self.lista_codice}: nessuna colonna di ricerca")
        for nome in self.colonne:
            # Chiavi scritte nel codice, non input utente: il controllo
            # trasforma un errore di dichiarazione in un errore chiaro.
            if not _NOME_COLONNA.match(nome):
                raise RuntimeError(f"RicercaFull {self.lista_codice}: colonna non valida {nome!r}")
        if isinstance(self.colonne, Mapping):
            for nome, espressione in self.colonne.items():
                if not str(espressione).strip():
                    raise RuntimeError(f"RicercaFull {self.lista_codice}: espressione vuota per {nome!r}")

    # Scopo: `campo_sorgente → espressione SQL`, con l'alias per la forma a tupla.
    def espressioni(self, alias: str) -> dict[str, str]:
        if isinstance(self.colonne, Mapping):
            return dict(self.colonne)
        return {c: f"{alias}.{c}" for c in self.colonne}


# Scopo: le colonne in cui l'utente CORRENTE puo' cercare in una lista, lette
#        dal catalogo a ogni ricerca e gia' filtrate dai permessi di colonna
#        (una `BLOCCATO` non esce; utente e veste dalle GUC di sessione).
# ⚠️ `SELECT … FROM`, non `SELECT ui.fn_…(…)`: la seconda forma restituisce
#    ogni riga come una tupla in un campo solo (brief-db-ricerca-full-colonne-
#    permessi §6). Lista assente o spenta → `E_UI_LISTA_NON_TROVATA`, che si
#    propaga: e' un errore di dichiarazione nel repository, non un ripiego.
# ⭐ Pubblica dal 2026-09-23: la legge anche la configurazione risolta della
#    lista (`ui_service.get_lista_config`, chiave `ricerca_full`), perche' la
#    casella di ricerca si mostra solo se c'e' dove cercare (Tid). Una sola sede
#    della lettura: il BB e la configurazione non possono dire cose diverse.
def colonne_ricerca_accese(lista_codice: str) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT campo_sorgente FROM ui.fn_lista_colonne_ricerca_full(%s)",
            [lista_codice],
        )
        return [r[0] for r in cursor.fetchall()]


# Scopo: la soglia della ricerca libera di una lista: sotto questo numero di
#        caratteri (dopo lo `strip`) il termine non filtra. E' un fatto della
#        LISTA — una tabella di configurazione a codici corti cerca da uno, un
#        archivio che cresce da tre — e sta nel catalogo accanto alle colonne
#        (decisione di Tid del 2026-09-24).
# ⭐ Una fonte, due lettori: questa e la configurazione della schermata (chiave
#    `ricerca_min_caratteri` di `ui.fn_resolve_lista_config`), da cui il
#    frontend decide se mandare il termine. Tutte e due leggono la riga dal BB
#    DB `ui.fn_lista_da_codice`.
# ⚠️ `SELECT … FROM`: `SELECT ui.fn_lista_da_codice(…)` da' la riga intera come
#    una tupla in un campo solo. Colonna NOT NULL: nessun ripiego qui — lista
#    assente o spenta e' `E_UI_LISTA_NON_TROVATA`, come per le colonne.
def soglia_ricerca(lista_codice: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(%s)",
            [lista_codice],
        )
        return int(fetchone_scalar(cursor))


# Scopo: l'utente per cui la connessione sta agendo: la GUC `app.current_user_id`
#        che `JwtAuditAuthentication` imposta per la RLS. `None` se vuota (fuori
#        da una richiesta autenticata, o su un canale che non l'ha dichiarata).
# ⚠️ Il nome e' `app.current_user_id`, NON `app.auth_user_id`: e' quello delle
#    policy RLS. Col nome sbagliato `current_setting(…, true)` risponde NULL e
#    chi legge conclude «nessun utente» — un difetto che i mock non vedono,
#    perche' i mock non hanno GUC.
# ⭐ Regola del 2 (2026-09-24, brief-be-ricerca-full-liste-residue §12): la
#    leggevano `pagamenti_repository.emittente_nel_perimetro` e la guardia di
#    contesto di `ui_service.get_lista_config_per_video`.
def utente_di_sessione() -> int | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT NULLIF(current_setting('app.current_user_id', true), '')::int")
        row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def add_ricerca_full_condition(
    conditions: list[str],
    params: list[Any],
    termine: str | None,
    ricerca: RicercaFull,
    *,
    alias: str = "v",
) -> None:
    """La ricerca libera di una lista: un OR di `ILIKE` sulle colonne accese.

    Aggiunge a `conditions`/`params` la condizione
    `((v.a)::text ILIKE %s OR (v.b)::text ILIKE %s ...)` col termine escapato
    (`escape_ilike`) e racchiuso fra `%`. Termine vuoto → non aggiunge niente
    e il catalogo non si legge: aprire una lista senza cercare non costa niente
    in piu'. Termine piu' corto della soglia della lista (`soglia_ricerca`,
    dopo lo `strip`) → non aggiunge niente, e le colonne non si leggono.

    ⭐ **La soglia e' della lista, non di chi chiama** (brief-db-be-fe-ricerca-
    soglia-per-lista): la legge il catalogo, come le colonne, e la stessa
    colonna arriva al frontend nella configurazione della lista. Fino al
    2026-09-26 era un argomento `min_caratteri`, passato a 1 da quattordici
    repository e ignorato dal frontend: «KG» sulle unita' di misura partiva
    senza `search`, e la lista restava intera.

    ⭐ **Due sedi, due domande** (brief-be-ricerca-full-liste-residue §2):
    cosa si PUO' cercare lo dice il codice (`ricerca`, la dichiarazione del
    repository); cosa si CERCA adesso, per questo utente, lo dice il catalogo
    (`ui.fn_lista_colonne_ricerca_full`), letto a ogni ricerca. La ricerca
    cade sull'intersezione:

    - l'amministratore spegne una colonna → sparisce subito dalla ricerca;
    - la accende e il repository la conosce → entra subito;
    - la accende e il repository NON la conosce → ignorata, con un `warning`
      che la nomina. ⛔ Mai SQL costruito da un nome di catalogo: il trigger
      a10 valida il `campo_sorgente` solo sulle liste con `vista_sql`, e in
      meta' delle liste il nome del catalogo e' un nome di uscita che nel
      `WHERE` non esiste;
    - nessuna colonna accesa e un termine valido → **`FALSE`**: una ricerca
      che non ha dove cercare non trova niente (decisione di Tid del
      2026-09-23). Tornare tutta la lista direbbe all'operatore che ogni riga
      corrisponde al termine.

    Regola del 2 (2026-09-23): la stessa condizione era scritta a mano in otto
    repository di vendite, e le copie si erano gia' separate (Preventivi,
    Offerte e Contratti non trovavano codice BA e id fiscale). Presidio:
    `apps/core/tests/test_ricerca_full_seed` (la dichiarazione copre il seed)
    e `tests/db/test_ricerca_full_db` (la condizione parte sul DB vero).

    ⭐ `::text` su ogni espressione: il catalogo dice `string` anche dove la
    vista espone un intero (`vw_fatture_lista.numero`), e un `ILIKE` su un
    intero e' un errore di PostgreSQL. Su una colonna gia' testo non costa.
    """
    # ⚠️ PRIMA della soglia: controllato solo a termine valido, un alias
    #    sbagliato passerebbe ogni lista aperta senza ricerca e salterebbe al
    #    primo operatore che cerca.
    if not _NOME_COLONNA.match(alias):
        raise RuntimeError(f"add_ricerca_full_condition: alias non valido {alias!r}")
    # Il termine di soli spazi e' un termine vuoto: non vale una lettura.
    termine = (termine or "").strip()
    if not termine:
        return
    if len(termine) < soglia_ricerca(ricerca.lista_codice):
        return
    espressioni = ricerca.espressioni(alias)
    accese = set(colonne_ricerca_accese(ricerca.lista_codice))
    ignote = sorted(accese - espressioni.keys())
    if ignote:
        logger.warning(
            "ricerca_full.colonne_accese_non_dichiarate lista=%s colonne=%s",
            ricerca.lista_codice, ignote,
        )
    attive = [e for c, e in espressioni.items() if c in accese]
    if not attive:
        conditions.append("FALSE")
        return
    conditions.append(
        "(" + " OR ".join(f"({e})::text ILIKE %s" for e in attive) + ")"
    )
    params.extend([pattern_contiene(termine)] * len(attive))


def fetchone_scalar(cursor) -> Any:
    """Ritorna il primo valore della riga corrente (fetchone), riga garantita.

    Pattern per query `INSERT/UPDATE ... RETURNING <col>` e SELECT scalari dove
    il contesto garantisce esattamente una riga. L'`assert` e' un invariante (e
    type-narrowing per il checker): se la query non produce righe e' un bug di
    programmazione, non un input utente da validare.
    """
    row = cursor.fetchone()
    assert row is not None
    return row[0]


def call_jsonb_fn(fn_name: str, *args: Any) -> dict[str, Any]:
    """Chiama una funzione PostgreSQL che ritorna jsonb e la mappa a dict.

    Pattern condiviso per i wrapper "capability" dei detail API
    (Fase 1 refactor frontend vendite): preventivi/contratti/promo articoli
    chiamano `script.fn_*_<entita>(id)` e ricevono un blob JSONB con
    `available_actions`, `can_*`, `non_editable_fields`.

    Ritorna `{}` se la fn ritorna NULL (entita inesistente — il caller
    deve aver gia' verificato l'esistenza via get_<entita>).
    ⚠️ Il backend Django per psycopg 3 consegna il jsonb come TESTO fuori
    dall'ORM: il branch `isinstance(payload, str)` e' la decodifica di
    sempre, non un caso raro (lettura per posizione, fuori da
    `_colonne_e_decodifiche`).

    Esempio:
        capabilities = call_jsonb_fn(
            "script.fn_available_actions_preventivo", preventivo_id,
        )
    """
    placeholders = ", ".join(["%s"] * len(args))
    sql = f"SELECT {fn_name}({placeholders}) AS payload"
    with connection.cursor() as cursor:
        cursor.execute(sql, list(args))
        row = cursor.fetchone()
        if not row or row[0] is None:
            return {}
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload


def resolve_config_id_by_codice_interno(
    tabella: str,
    codice_interno: str,
    *,
    etichetta: str,
    not_found_message: str | None = None,
    function_name: str = "django_service",
    codice_errore: str = "E_CONFIG_MANCANTE",
    campo: str | None = None,
) -> int:
    """Risolve l'`id` di una riga config/lookup dal `codice_interno` IMMUTABILE.

    Match SEMPRE sulla colonna `codice_interno` (lockata da
    `script.trgfn_lock_columns`), MAI sul `codice` mutabile (etichetta a video):
    confrontare un literale di logica contro `codice` e' un bug latente (si
    rompe se l'utente rinomina il codice). Filtra `attivo = true`. Solleva
    `E_CONFIG_MANCANTE` se la riga non esiste o non e' attiva.

    Regola del 2: centralizza il pattern
    `SELECT id FROM <config> WHERE codice_interno = %s AND attivo = true`
    ripetuto in piu' repository/service (estratto da
    `pratiche_repository._resolve_stato`; vedi `analisi-hardcoded-codice.md`).

    `tabella` deve essere un identificatore schema-qualificato controllato dal
    codice (mai input utente): viene interpolato nella query.

    `not_found_message` permette al chiamante di preservare un messaggio
    diagnostico specifico (es. hint sul seed mancante); in assenza usa un
    default costruito da `etichetta`.

    ⛔ **Chi ha scelto il codice decide il codice d'errore.** Il default
    `E_CONFIG_MANCANTE` (TECNICO, 500) vale per un codice SCRITTO NEL CODICE:
    la riga che manca e' un seed mancante, e l'operatore non puo' rimediare.
    Quando il codice arriva dal CLIENT (`nuovo_stato`, `tipo_nota_codice`, ...)
    la riga che manca e' un valore sbagliato di chi chiama: il chiamante passa
    il suo codice di validazione (`codice_errore`, DATO_ERRATO → 400) e il
    `campo`. Fino al 2026-10-20 un `nuovo_stato` inventato era un 500.
    """
    sql = f"""
        SELECT id FROM {tabella}
        WHERE codice_interno = %s AND attivo = true
        LIMIT 1
    """  # noqa: S608 — `tabella` e' un identificatore controllato dal codice
    with connection.cursor() as cursor:
        cursor.execute(sql, [codice_interno])
        row = cursor.fetchone()
    ErrorManager.require(
        row is not None,
        code=codice_errore,
        message=(
            not_found_message
            or f"{etichetta} '{codice_interno}' non trovato in {tabella} "
            "(o non attivo)."
        ),
        context={"field": campo} if campo else None,
        function_name=function_name,
    )
    assert row is not None
    return int(row[0])


def richiedi_codice_a_vocabolario(
    tabella: str,
    colonna: str,
    valore: str | None,
    *,
    codice_errore: str,
    parametro: str,
    function_name: str = "django_service",
) -> str | None:
    """Il valore di un FILTRO esiste nel vocabolario che lo possiede, oppure 400.

    Per i filtri il cui vocabolario e' una TABELLA (`config.stati_doc_*`,
    `config.tipi_entita`, ...): `None` passa (filtro assente), un valore che la
    tabella non conosce e' `codice_errore` (il DATO_ERRATO del chiamante), col
    nome del `parametro` nel messaggio e nel context diagnostico. ⛔ Senza, un
    valore sbagliato finiva nel `WHERE` e la lista rispondeva vuota con un 200
    — indistinguibile da «non c'e' niente» (2026-10-20,
    brief-be-verifica-documentazione-api §3).

    ⛔ **Niente `field`** (decisione di Tid 2026-10-20, api.md §«Escono solo i
    nomi»): un filtro e' un parametro di QUERY, non un input del form in cui
    l'operatore si trova. Il valore esce da una select o da un chip, quindi un
    400 qui e' un client che sbaglia (bundle vecchio, URL a mano, client
    esterno), e `field` accenderebbe un input che non esiste.

    ⚠️ Esistenza e basta: nessun filtro `attivo`/`obsoleto_dal`. Filtrare su un
    codice DISMESSO e' una domanda legittima — i documenti vecchi lo portano
    ancora (decisione di Tid, 2026-10-20). E nessun id restituito: un filtro
    non ne ha bisogno, e `config.tipi_entita` un id non ce l'ha. Per risolvere
    un id da un codice c'e' `resolve_config_id_by_codice_interno`.

    `tabella` e `colonna` sono identificatori controllati dal codice (mai input
    utente): vengono interpolati nella query. Restituisce il valore.
    """
    if valore is None:
        return None
    sql = f"SELECT 1 FROM {tabella} WHERE {colonna} = %s LIMIT 1"  # noqa: S608 — identificatori controllati dal codice
    with connection.cursor() as cursor:
        cursor.execute(sql, [valore])
        trovato = cursor.fetchone() is not None
    ErrorManager.require(
        trovato,
        code=codice_errore,
        message=f"Valore '{valore}' non ammesso per '{parametro}'.",
        context={"parametro": parametro, parametro: valore},
        function_name=function_name,
    )
    return valore


def sql_order_direction(
    order_dir: str | None,
    *,
    default_desc: bool = False,
) -> str:
    """Clausola di direzione ORDER BY con **NULL ordinato come valore MINIMO**.

    Ritorna `'ASC NULLS FIRST'` oppure `'DESC NULLS LAST'`, da interpolare al
    posto della sola direzione: `ORDER BY {col} {direction}, <tiebreak>`.

    **Perche' i NULLS espliciti** (decisione Tid 2026-07-19): i default
    PostgreSQL sono l'opposto (ASC -> NULLS LAST, DESC -> NULLS FIRST), quindi
    un campo vuoto finiva **in cima** proprio ordinando dal piu' recente — il
    caso della lista DDT, dove `numero` e' NULL su TUTTE le bozze (lo assegna
    il trigger a EMESSO). Con questa regola il vuoto sta dove starebbe lo zero.

    Regola del 2 (ok Tid): unifica **29 call-site** in 6 varianti sintattiche
    della stessa espressione (`upper()`/`lower()`/`(order_dir or "")`), di cui
    3 avevano un `NULLS LAST` fisso incollato al template — semantica diversa
    ("il vuoto sempre in coda") che qui viene **uniformata**.

    `default_desc=True` per le liste che ordinano dal piu' recente quando il
    chiamante non specifica nulla.

    ⛔ **Una direzione INDICATA e non riconosciuta e' `ValueError`, non ASC**
    (decisione Tid 2026-09-26). Fino a quel giorno `giu`, `discendente` o
    `DESC NULLS LAST` diventavano ASC in silenzio: la lista rispondeva 200,
    ordinata al contrario di cio' che era stato chiesto, e nessuno lo vedeva.
    Il predicato e' `order_dir_ammessa`: assente (None, vuota, soli spazi) =
    il default; `asc`/`desc` con maiuscole e spazi qualsiasi = quella; il
    resto e' rifiutato.

    ⭐ Il messaggio e' il token `order_dir_invalid`, la convenzione dei
    parametri di query (`qp_int_optional` & C. in `payload_validators`): su un
    percorso `/api/` l'eccezione sale a `ApiExceptionMiddleware`, che la
    traduce in **400 `E_VALIDATION_INPUT`** — lo stesso 400 di `?page=abc`.
    Chi vuole il codice del proprio dominio valida prima, nel service
    (`list_helpers.validate_order_params`, `PayloadValidator.validate_order_by`).
    """
    if not order_dir_ammessa(order_dir):
        raise ValueError("order_dir_invalid")
    indicata = (order_dir or "").strip().lower()
    is_desc = (indicata or ("desc" if default_desc else "asc")) == "desc"
    return "DESC NULLS LAST" if is_desc else "ASC NULLS FIRST"


_ORDER_DIR_AMMESSE = frozenset({"asc", "desc"})


def order_dir_ammessa(order_dir: str | None) -> bool:
    """`True` se `order_dir` e' ASSENTE o e' una direzione riconosciuta.

    Assente = None, stringa vuota o soli spazi: prende il default di chi
    ordina. Riconosciuta = `asc`/`desc`, maiuscole e spazi ai lati ammessi.

    ⭐ **E' la sede UNICA della regola**, e ha due lettori che devono dire la
    stessa cosa: `sql_order_direction` (che rifiuta con `ValueError`) e
    `PayloadValidator.validate_order_by` (che rifiuta con il codice di
    dominio del service). Due copie dell'insieme `{asc, desc}` divergerebbero
    sulle maiuscole alla prima modifica, e allora il service lascerebbe
    passare cio' che il repository rifiuta — o viceversa.
    """
    indicata = (order_dir or "").strip().lower()
    return not indicata or indicata in _ORDER_DIR_AMMESSE


def sql_tiebreak_direction(direction: str) -> str:
    """Verso del **tiebreak**, allineato a quello della colonna primaria.

    Prende la clausola prodotta da `sql_order_direction` e ne estrae il solo
    verso (`'ASC'` / `'DESC'`), da interpolare sul tiebreak::

        direction = sql_order_direction(order_dir)
        tiebreak_dir = sql_tiebreak_direction(direction)
        ...
        ORDER BY {order_column} {direction}, cc.id {tiebreak_dir}

    **Perche'** (decisione Tid 2026-08-03): il tiebreak era inchiodato ad `ASC`
    in tutti i punti che costruiscono un ORDER BY. Ordinando i preventivi per
    data DESC, a parita' di data si vedeva prima il piu' VECCHIO — dentro il
    giorno l'elenco andava al contrario di come l'operatore lo aveva chiesto.
    Allineando il verso, «il piu' recente in cima» vale anche a parita' di
    data, e la stessa coerenza si estende a qualunque colonna (cliente,
    utility, stato...).

    ⚠️ **La paginazione deterministica non e' toccata**: dipende
    dall'UNIVOCITA' del tiebreak, non dal suo verso (frontend-standards,
    REGOLA CRITICA). `id` resta univoco in entrambe le direzioni.

    **Niente `NULLS` qui, ed e' il motivo per cui il tiebreak dev'essere `id`**
    (decisione Tid 2026-08-03): su una chiave tecnica non nullable non
    servono. Un tiebreak nullable — es. `numero`, NULL sulle bozze finche' il
    trigger non lo assegna — reintrodurrebbe in DESC i vuoti in cima, cioe'
    esattamente il difetto che `sql_order_direction` ha corretto.

    **Non si applica ai criteri GERARCHICI**, che non sono spareggi tecnici ma
    ordine logico e restano fissi: le righe di uno stesso reso vanno lette nel
    loro ordine naturale anche quando la lista e' ordinata al contrario.

    ⛔ **Una clausola che non comincia con `ASC` o `DESC` e' `RuntimeError`**
    (2026-09-26, stessa decisione di `sql_order_direction`): prima tutto cio'
    che non cominciava per `DESC` diventava ASC. Qui l'argomento non viene
    mai dall'utente — e' l'uscita del BB fratello o un letterale del codice —
    quindi un valore estraneo e' un errore di programmazione, e va detto.
    ⚠️ `RuntimeError` e non `ValueError`: `ErrorTranslator` traduce ogni
    `ValueError` in un 400 `E_VALIDATION_INPUT` loggato senza stack, cioe'
    «dato errato» a un client che non ha sbagliato niente. `RuntimeError`
    diventa `E_GENERICO`, 500 col traceback. `ValueError` resta alla sola
    direzione di `sql_order_direction`, che viene dall'utente.
    """
    verso = direction.strip().split(maxsplit=1)[0].upper() if direction.strip() else ""
    if verso not in ("ASC", "DESC"):
        raise RuntimeError(f"sql_tiebreak_direction: direzione non riconosciuta {direction!r}")
    return verso


def colonne_identita(*colonne: str) -> dict[str, str]:
    """Whitelist di ordinamento in cui il nome logico E' l'espressione SQL.

    `colonne_identita("codice", "descrizione")` -> `{"codice": "codice", ...}`.

    ⚠️ **Serve a DIRLO, non ad accorciare.** Alcune liste leggono una vista in
    cui la colonna si chiama gia' come il campo che il frontend manda: li' non
    c'e' nessuna traduzione da fare, e scrivere il dizionario a mano con le due
    meta' uguali sembra un errore di copia-incolla. Questa funzione lo rende una
    dichiarazione.

    Regola del 2 (2026-09-02): `indirizzi_repository` e `geo_repository` (6
    liste) avevano la stessa comprehension scritta in due forme diverse.

    ⭐ Le chiavi restano leggibili come insieme (`set(_ORDER_COLS)`), quindi i
    risolutori di whitelist del presidio seed non cambiano.
    """
    return {c: c for c in colonne}


# Le chiavi di ordinamento che per NOME sono date, per la convenzione del
# progetto: `data`, `data_*`, `*_at`, `valido_dal/al`, `validita_dal/al`, ogni
# `*_dal`/`*_al`, `competenza_mese`. La usa `sql_order_clause` per la regola
# di Tid del 2026-09-02 («le date partono DESC»).
_CHIAVE_DATA = re.compile(r"^(data|data_.+|.+_at|.+_dal|.+_al|competenza_mese)$")


def e_chiave_data(chiave: str) -> bool:
    """La chiave di ordinamento e' una data per nome (vedi `_CHIAVE_DATA`)."""
    return bool(_CHIAVE_DATA.match(chiave))


def colonna_ordinamento(order_by: str | None, colonne: Mapping[str, str]) -> str | None:
    """La COLONNA di una lista per la chiave `order_by` chiesta dal client.

    - assente (None, vuota, soli spazi) → `None`: l'ordine lo decide il
      default di chi ordina;
    - chiave della whitelist → la sua espressione SQL;
    - ogni altro valore → `ValueError("order_by_invalid")`, cioe' il 400
      `E_VALIDATION_INPUT` di `ApiExceptionMiddleware` (lo stesso di
      `order_dir_invalid`).

    ⛔ **Un `order_by` indicato e fuori whitelist e' un 400 in ogni lista**
    (decisione Tid 2026-10-20, brief-be-verifica-documentazione-api §A1). Fino a
    quel giorno meta' delle liste ripiegava in silenzio sul default — la lista
    rispondeva 200 ordinata in un altro modo, e nessuno lo vedeva — e l'altra
    meta' rispondeva 400 (o 500, col flag `rifiuta_fuori_whitelist`). E' la
    stessa regola dei filtri a vocabolario e della direzione.

    ⭐ Sede UNICA della risoluzione «chiave → colonna» (regola del 2): la
    usano `sql_order_clause`, `sql_order_direction_lista` e i repository che
    compongono l'`ORDER BY` a mano, dove il ripiego era scritto come
    `COLS.get(order_by, default)` una ventina di volte.

    ⚠️ Il default dichiarato dalla view (`parse_list_params(default_order=…)`)
    arriva qui come se il client l'avesse chiesto: dev'essere una chiave della
    whitelist, oppure `""` per lasciare il default al repository.
    """
    chiave = (order_by or "").strip()
    if not chiave:
        return None
    if chiave not in colonne:
        raise ValueError("order_by_invalid")
    return colonne[chiave]


def sql_order_direction_lista(
    order_by: str | None,
    order_dir: str | None,
    *,
    colonne: Mapping[str, str],
    default: str | None = None,
    default_desc: bool = False,
    colonne_desc: Collection[str] = (),
) -> str:
    """La DIREZIONE di una lista, risolta dalla chiave chiesta: la regola di
    `sql_order_clause`, per chi compone l'`ORDER BY` a mano.

    Ritorna cio' che ritorna `sql_order_direction` (`'ASC NULLS FIRST'` /
    `'DESC NULLS LAST'`); una direzione estranea e' `ValueError` su ogni ramo.

    Senza `order_dir`, il verso si decide cosi':

    - `order_by` assente → `default_desc` (il ramo di default della lista);
    - `order_by` che nomina la colonna di DEFAULT (per espressione o per
      chiave) → `default_desc`: la scelta della lista, che per una coda puo'
      essere crescente apposta;
    - ogni altra colonna → DESC se e' una data (`colonne_desc`, o per NOME con
      `e_chiave_data`), altrimenti ASC.

    ⛔ **Una chiave fuori `colonne` e' `ValueError` (400)**, da
    `colonna_ordinamento`: dal 2026-10-20 nessuna lista ripiega in silenzio sul
    default (decisione Tid, brief-be-verifica-documentazione-api §A1).

    ⭐ **Regola del 2 (ok Tid 2026-10-20).** La riga
    `sql_order_direction(order_dir, default_desc=e_chiave_data(order_by))` era
    stata ricopiata in 13 `ORDER BY` composti a mano (vendite, magazzino,
    amm-software, emittenti), e le copie divergevano gia' da `sql_order_clause`:
    guardavano la chiave chiesta e non la colonna risolta, e ignoravano la
    precedenza del default. `sql_order_clause` ora passa di qui.
    """
    colonna = colonna_ordinamento(order_by, colonne)
    if colonna is None:
        return sql_order_direction(order_dir, default_desc=default_desc)
    assert order_by is not None
    order_by = order_by.strip()
    # Il default si riconosce dall'espressione O dalla chiave: un `default`
    # scritto come chiave (`"data_scadenza"`) con una colonna qualificata
    # (`"v.data_scadenza"`) perderebbe in silenzio il verso della coda.
    if default is not None and default.strip() in (colonna.strip(), order_by):
        verso_desc = default_desc
    else:
        verso_desc = order_by in colonne_desc or e_chiave_data(order_by)
    return sql_order_direction(order_dir, default_desc=verso_desc)


def sql_order_clause(
    order_by: str | None,
    order_dir: str | None,
    *,
    colonne: Mapping[str, str],
    tiebreak: str,
    default: str | None = None,
    default_clause: str | None = None,
    default_desc: bool = False,
    colonne_desc: Collection[str] = (),
) -> str:
    """Il corpo di un `ORDER BY` di lista: colonna, direzione e spareggio.

    Ritorna la clausola SENZA la parola `ORDER BY`, da interpolare::

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS, default="t.data DESC"[...], tiebreak="t.id",
        )
        sql = f"... ORDER BY {ordinamento} LIMIT %s OFFSET %s"

    **Regola del 2 (ok Tid 2026-09-02)**: le tre righe
    `COLS.get(...)` + `sql_order_direction` + `sql_tiebreak_direction` erano
    scritte **46 volte** nel backend, in due varianti (`.get(k, COLS[DEF])` e
    `if not order_by or order_by not in COLS`). Qui vivono una volta sola.

    Argomenti:
      `colonne`  whitelist chiave-logica -> espressione SQL. ⛔ Le chiavi sono i
                 `campo_sorgente` FISICI del catalogo: il frontend manda quelli.
      `tiebreak` colonna univoca di spareggio, quasi sempre `<alias>.id`.
      `default`  **una COLONNA** usata quando `order_by` manca o e' fuori
                 whitelist: la direzione gliela mette il BB. E' SQL e non una
                 chiave perche' l'ordinamento di partenza di una lista spesso
                 non e' una colonna offerta all'operatore (`s.id`).
      `default_clause`  **una CLAUSOLA GIA' COMPLETA**, con le sue direzioni
                 dentro, usata verbatim. Alternativa esclusiva a `default`.
      `default_desc`   verso del ramo `default` quando nessuno chiede niente.
      `colonne_desc`   chiavi di `colonne` il cui verso NATURALE e' DESC.

    ⛔ **`default` e `default_clause` sono due parametri e non uno, e la prima
    stesura di questo BB ne aveva uno solo — sbagliando.** Un ordinamento di
    partenza a piu' criteri porta le direzioni dentro di se'
    (`COALESCE(valido_al,'infinity') DESC, valido_dal DESC`): trattarlo come una
    colonna gli appiccica una seconda direzione in coda e produce
    `... DESC DESC NULLS LAST`. ⭐ Li' e' andata bene — PostgreSQL rifiuta la
    query con un errore di sintassi, quindi il difetto si e' visto subito. Ma la
    distinzione resta nell'API perche' il prossimo chiamante non debba
    scoprirla allo stesso modo.

    ⭐ **`colonne_desc` e' la regola di Tid del 2026-09-02: «gli ordinamenti per
    DATA hanno sempre default DESC».** Una data si legge dalla piu' recente —
    chiedere «ordina per data» e ricevere il 2019 in cima e' il contrario di
    cio' che si e' chiesto. ⚠️ Vale solo quando `order_dir` NON e' indicato: una
    direzione esplicita vince sempre, altrimenti l'operatore non potrebbe
    invertire l'ordine di una colonna data.
    ⭐ **Dal 2026-10-20 le date si riconoscono anche dal NOME** (`e_chiave_data`,
    decisione di Tid): circa venti liste in sette app non dichiaravano le loro
    colonne data, e la regola per loro non valeva. `colonne_desc` resta per le
    date con un nome fuori convenzione. ⚠️ La colonna di DEFAULT, quando
    `order_by` la nomina (la riempie `parse_list_params`), segue `default_desc`
    — la scelta della lista, che per una coda puo' essere crescente apposta.

    ⛔ **Se la colonna risolta E' il tiebreak, lo spareggio non si scrive.**
    Senza questo, il ramo di default di una lista che ordina per `id` produceva
    `ORDER BY s.id ASC, s.id ASC` — la colonna e il suo stesso spareggio. Non
    sbaglia il risultato, ma e' una clausola che dice due volte la stessa cosa
    e nasconde alla lettura qual e' l'ordinamento vero.

    ⛔ **Un `order_by` INDICATO e fuori whitelist e' un 400, in ogni lista**
    (`colonna_ordinamento`, decisione Tid 2026-10-20, brief-be-verifica-
    documentazione-api §A1). Fino a quel giorno il flag
    `rifiuta_fuori_whitelist` sceglieva per lista fra «ripiega sul default» e
    «rifiuta» (con un 500): il ripiego era il contratto di molte liste, che
    rispondevano 200 ordinate in un altro modo da quello chiesto. Il flag e'
    ritirato con la scelta. Un `order_by` NON indicato (None o vuoto) prende
    il default, come sempre; la direzione la rifiuta `sql_order_direction`.
    """
    if (default is None) == (default_clause is None):
        raise RuntimeError(
            "sql_order_clause: si passa `default` (una colonna) OPPURE "
            "`default_clause` (una clausola completa), mai entrambi ne' nessuno"
        )
    # La direzione da UNA regola sola, la stessa degli `ORDER BY` composti a
    # mano: precedenza del default, date DESC (vedi `sql_order_direction_lista`).
    direzione = sql_order_direction_lista(
        order_by, order_dir, colonne=colonne, default=default,
        default_desc=default_desc, colonne_desc=colonne_desc,
    )
    risolta = colonna_ordinamento(order_by, colonne)
    if risolta is None:
        # ⚠️ La clausola completa NON prende direzione: ce l'ha gia' dentro, e
        #    aggiungerne una produrrebbe `DESC DESC`.
        if default_clause is not None:
            return f"{default_clause}, {tiebreak} {sql_tiebreak_direction(direzione)}"
        # Il controllo «uno dei due» qui sopra garantisce `default` non None
        # quando `default_clause` lo e'.
        assert default is not None
        colonna = default
    else:
        colonna = risolta
    # ⚠️ Confronto sul TESTO dell'espressione, che e' l'unica cosa che abbiamo:
    #    e' esatto sul caso che conta (il default che vale gia' il tiebreak) e
    #    al massimo scrive uno spareggio in piu' su una colonna che il tiebreak
    #    non e' davvero — cioe' sbaglia sempre dalla parte innocua.
    if colonna.strip() == tiebreak.strip():
        return f"{colonna} {direzione}"
    return f"{colonna} {direzione}, {tiebreak} {sql_tiebreak_direction(direzione)}"


def extract_paginated(cursor) -> tuple[list[dict[str, Any]], int]:
    """Estrae risultati paginati da query con COUNT(*) OVER() AS total_count.

    Restituisce (lista dict senza total_count, conteggio totale).
    Pre-computa mappa indici per evitare O(n*m) su cols.index().

    Promozione a BB core (regola del 2, 2026-07-18): nato in
    `anagrafiche/db/_helpers.py` (6 repository), lo stesso lavoro era
    riscritto inline in ~15 siti core/amm (email, dbops, lookup, search...).
    NB: a pagina oltre l'ultima (0 righe) il totale e' 0 — se il chiamante
    deve distinguere "lista vuota" da "pagina stantia" usi
    `fetch_paged_with_total` col fallback.
    """
    rows = cursor.fetchall()
    if not rows:
        return [], 0
    cols, decodifiche = _colonne_e_decodifiche(cursor)
    tc_idx = cols.index("total_count")
    total_count = rows[0][tc_idx]
    # La riga come in `rows_to_list` (jsonb decodificati), meno il totale.
    results = []
    for row in rows:
        riga = _riga_dict(cols, decodifiche, row)
        del riga["total_count"]
        results.append(riga)
    return results, total_count


def sql_lateral_primo_motivo(check_sql: str, alias: str) -> str:
    """Il frammento `LEFT JOIN LATERAL` che legge il PRIMO motivo di una
    `script.fn_check_*` — la terna `reason / reason_key / dettaglio` — come
    colonne di riga (linee-guida-sql §12.5, api.md §«Capability di riga»).

    Il chiamante lo innesta nel proprio `FROM` e proietta cio' che gli serve
    (`<alias>.reason AS <verbo>_blocco_reason`, `(<alias>.reason IS NULL) AS
    can_<verbo>`, …): il nome del verbo lo decide lui, il frammento no.

    ⚠️ `LEFT JOIN … ON TRUE` e non `CROSS JOIN`: la check risponde `[]` quando
    l'azione e' ammessa, e `jsonb_array_elements` su un array vuoto non produce
    righe — con un CROSS JOIN sparirebbero dalla lista proprio le righe su cui
    l'azione si puo' fare.
    ⚠️ L'ORDINE E' IL CONTRATTO: la madre solleva il PRIMO motivo con
    `fn_raise_primo_motivo_se_presente`, e il tooltip deve mostrare quello
    stesso — da qui `WITH ORDINALITY … ORDER BY ord LIMIT 1`.
    ⚠️ COSTO: la check gira PER RIGA di cio' su cui la si innesta. Dentro la
    lettura di una lista paginata, sotto la `COUNT(*) OVER ()`, e' per riga
    FILTRATA e non per riga di pagina: il motivo serve alle righe mostrate, e
    li' va innestata (dopo `LIMIT/OFFSET` — per esempio `_sql_con_elimina` di
    pagamenti). ⚠️ E una check SECURITY INVOKER che rilegge tabelle sotto RLS
    ricalcola il perimetro a OGNI chiamata: per una lista si chiama la forma
    che riceve la riga gia' letta (`fn_check_…_su_<testata>(alias)`), quando
    il DB la offre (linee-guida-sql §13.2). Chi la innesta su una lista lo
    misura con `EXPLAIN` sul DB provvisto (tests/db).

    ⛔ `check_sql` e `alias` sono SQL DEL CHIAMANTE — la chiamata alla check
    coi suoi argomenti (`script.fn_check_x(r.id)`) e l'alias del blocco — e
    vengono da costanti di modulo, MAI da input: finiscono interpolati.
    ⚠️ L'alias INTERNO della funzione e' `motivo`, non una lettera: `check_sql`
    nomina le colonne della riga esterna (`m.billing_account_id`, `r.id`) e
    PostgreSQL le risolve PRIMA di mettere in scope l'alias della funzione —
    un alias corto qui (`m`) avrebbe la stessa lettera di una tabella esterna
    (e' il caso del mapping BA degli emittenti) e leggerebbe giusto solo per
    ordine di parsing: chi legge lo crede sbagliato, e una forma che regge
    per caso e' fragile. Nessun chiamante deve aliasare `motivo`.

    Regola del 2 (2026-09-19, ok Tid — residuo Q-G del brief BE/FE incassi): la
    stessa LATERAL era scritta in QUATTRO repository nella stessa forma
    (`registri` ×2, `anagrafiche` ×1, `vendite` ×1, `pagamenti` ×1) e la
    validazione della distinta ne chiedeva la quinta.
    """
    return f"""
      LEFT JOIN LATERAL (
          SELECT motivo.value ->> 'reason'     AS reason,
                 motivo.value ->> 'reason_key' AS reason_key,
                 motivo.value -> 'dettaglio'   AS dettaglio
            FROM jsonb_array_elements({check_sql}) WITH ORDINALITY AS motivo(value, ord)
           ORDER BY motivo.ord
           LIMIT 1
      ) {alias} ON TRUE
"""  # noqa: S608 — check_sql/alias da costanti di modulo dei chiamanti, mai da input


def conta_con_perimetro(
    from_sql: str, conditions: list[str], params: list[Any],
) -> int:
    """Conteggio scalare su un perimetro DICHIARATO a pezzi (FROM + condizioni).

    Serve al caso «quante righe il filtro lascia FUORI dalla lista»: un numero
    che la lista non puo' produrre da se', perche' quelle righe il suo `WHERE`
    le ha gia' escluse. Il chiamante passa il PROPRIO frammento `FROM` (join
    compresi) e le proprie condizioni, cosi' il conteggio ha lo stesso
    perimetro delle righe consegnate.

    ⛔ Non e' un doppione di `fetch_paged_with_total`: quello risponde a
    «quante ne sto consegnando», questo a «quante ne sto nascondendo». Sono due
    domande e due valutazioni — `len(results)` non risponde a nessuna delle
    due, e un `COUNT(*) FILTER` sulla query di pagina non potrebbe vedere le
    righe che il `WHERE` ha tolto.

    ⚠️ `from_sql` e `conditions` sono SQL del chiamante: come ovunque nei
    repository, devono venire da frammenti costanti e whitelist, mai da input
    libero. I VALORI viaggiano in `params`.

    Regola del 2 (2026-09-04, archiviazione delle righe di coda): lo stesso
    conteggio serve alle due code — `dbops.coda_lavori` e
    `vendite.fatture_stampa_coda` — che vivono in due repository diversi.
    """
    where = " AND ".join(conditions)
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*)::int {from_sql} WHERE {where}",
            list(params),
        )
        return int(fetchone_scalar(cursor))


# Scopo: limite e offset di una pagina, riportati nei limiti: il limite fra 1 e
#        `tetto`, l'offset non negativo. Ritorna `(limite, offset)`.
# ⭐ Regola del 2 (2026-09-28): la coppia `safe_limit = max(1, min(int(limit),
#    200))` / `safe_offset = max(0, int(offset))` era scritta 41 volte, e il
#    tetto come numero in ognuna. `tetto` e' diverso da `MAX_LIMIT` solo per
#    l'export, che ha il suo.
def limiti_pagina(limit: Any, offset: Any, *, tetto: int = MAX_LIMIT) -> tuple[int, int]:
    return max(1, min(int(limit), tetto)), max(0, int(offset))


# `LIMIT %s OFFSET %s` in coda alla query: la forma che il ripiego sa rileggere.
_CODA_LIMIT_OFFSET = re.compile(r"LIMIT\s+%s\s+OFFSET\s+%s\s*;?\s*$", re.IGNORECASE)


def fetch_paged_with_total(
    data_sql: str,
    params: list[Any] | dict[str, Any],
    *,
    offset: int | None = None,
    fallback_count_sql: str | None = None,
    fallback_params: list[Any] | dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Esegue una query paginata in UNA valutazione (COUNT(*) OVER()).

    `data_sql` DEVE proiettare `COUNT(*) OVER () AS total_count` e portare
    LIMIT/OFFSET nei propri `params`. Ritorna (righe dict, totale).
    `params` posizionali (lista) o con nome (dict, `%(nome)s`): quello che
    accetta `cursor.execute`.

    Pagina oltre l'ultima: con `offset > 0` e 0 righe la window function non
    puo' dire il totale (non c'e' una riga che lo porti). Solo in quel caso
    (raro: una riga eliminata, una coda che si svuota sotto l'operatore) il
    totale si chiede di nuovo, in uno dei due modi:

    - `fallback_count_sql` + `fallback_params`, se il chiamante ne ha uno piu'
      leggero (stesso FROM/WHERE, senza le colonne calcolate);
    - altrimenti **la stessa query con `LIMIT 1 OFFSET 0`**: la prima riga
      porta la `COUNT(*) OVER ()` di tutto il risultato. Nessun FROM/WHERE da
      ricopiare, quindi nessuna seconda copia che diverga. Richiede che la
      query finisca con `LIMIT %s OFFSET %s` e che i due siano gli ultimi
      parametri posizionali; con i parametri con nome il conteggio va dato.

    ⛔ Fino al 2026-09-28 il ripiego era facoltativo e ~25 liste non lo
    avevano: oltre l'ultima pagina il totale usciva 0, e il frontend
    (`useListaStoreCore`, che ora arretra da solo) non sapeva dove tornare.
    L'offset serve per lo stesso motivo: senza, il ripiego non scatta mai.

    ⭐ **L'offset si ricava dalla query quando la query lo porta** (2026-10-04,
    §9.6 punto 4 del brief-db-liste-righe-documento, Tid): con parametri
    posizionali e la coda `LIMIT %s OFFSET %s` l'offset E' `params[-1]`, e
    passarlo anche a parte era un secondo valore della stesso numero, libero di
    divergere. Lo si passa (`offset=`) solo quando la query non lo dice da sé
    (parametri con nome). ⛔ Passato E ricavabile, deve coincidere: due valori
    diversi sono un errore del chiamante, e il ripiego scatterebbe (o no) sul
    numero sbagliato.

    Regola del 2 (2026-07-18): unifica il pattern COUNT-OVER inline dei
    repository con la variante fallback nata per le code resi.
    """
    offset = _offset_della_pagina(data_sql, params, offset)
    rilettura = None
    if fallback_count_sql is None:
        # ⛔ Si verifica SEMPRE, non solo quando serve: una query che non sa
        #    rileggersi deve rompersi al primo test, non al primo operatore
        #    rimasto su una pagina stantia.
        if not isinstance(params, list) or not _CODA_LIMIT_OFFSET.search(data_sql):
            raise ValueError(
                "fetch_paged_with_total: senza `fallback_count_sql` la query deve "
                "finire con `LIMIT %s OFFSET %s` e avere parametri posizionali"
            )
        rilettura = (data_sql, [*params[:-2], 1, 0])
    with connection.cursor() as cursor:
        cursor.execute(data_sql, params)
        results, total_count = extract_paginated(cursor)
        if not results and offset > 0:
            if rilettura is not None:
                cursor.execute(*rilettura)
                _, total_count = extract_paginated(cursor)
            else:
                # Senza rilettura c'e' sempre il conteggio dato (vedi sopra).
                assert fallback_count_sql is not None
                cursor.execute(fallback_count_sql, fallback_params or [])
                row = cursor.fetchone()
                total_count = row[0] if row else 0
    return results, total_count


# Scopo: l'offset della pagina per `fetch_paged_with_total`: dalla coda
#        `LIMIT %s OFFSET %s` dei parametri posizionali quando c'e', altrimenti
#        quello dichiarato. Vedi la docstring del BB per il perche'.
def _offset_della_pagina(
    data_sql: str, params: list[Any] | dict[str, Any], dichiarato: int | None,
) -> int:
    ricavabile = isinstance(params, list) and len(params) >= 2 and bool(
        _CODA_LIMIT_OFFSET.search(data_sql)
    )
    if not ricavabile:
        if dichiarato is None:
            raise ValueError(
                "fetch_paged_with_total: la query non porta l'offset nei parametri "
                "posizionali (`LIMIT %s OFFSET %s` in coda): va passato `offset=`"
            )
        return dichiarato
    assert isinstance(params, list)
    dalla_query = int(params[-1])
    if dichiarato is not None and int(dichiarato) != dalla_query:
        raise ValueError(
            f"fetch_paged_with_total: offset={dichiarato} diverso da quello della "
            f"query ({dalla_query}): uno dei due e' sbagliato"
        )
    return dalla_query


def fetch_con_sonda(
    data_sql: str, params: list[Any], *, limite: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Esegue un LOOKUP e dice se l'elenco e' COMPLETO — senza un secondo conto.

    `data_sql` deve finire con `LIMIT %s` e `params` NON deve portare il limite:
    lo aggiunge questa funzione, maggiorato di uno. Ritorna le prime `limite`
    righe piu' il flag `troncato`, che vale «ce n'erano altre».

    ⭐ SONDA `+1`, e non un `count(*)`: si chiede UNA riga in piu' del dovuto, si
    consegnano le `limite` e si dichiara se ce n'erano altre. Costa zero — nessuna
    seconda query, e nessun `COUNT(*) OVER ()` che obbligherebbe a materializzare
    l'intero insieme a ogni tasto premuto in un autocomplete — e risponde
    all'unica domanda che serve a video: **l'elenco e' completo?**

    ⛔ Non e' un doppione di `fetch_paged_with_total`, ed e' la ragione per cui
    sono due funzioni: quello serve una LISTA PAGINATA, che il totale vero ce
    l'ha e ne ha bisogno (il paginator deve sapere quante pagine sono). Un
    lookup non ha pagine: ha un tetto, e la sola cosa che deve dire e' se quel
    tetto ha tagliato qualcosa.

    🔴 PERCHE' STA QUI E NON NEL REPOSITORY CHE LA USA (2026-09-10, ok Tid). I
    tre pezzi — il `+1` nella query, il taglio a `limite`, il flag dedotto dal
    conteggio — sono UNA cosa sola: separati, si dimentica il taglio e la riga
    di sonda **trapela a chi legge**, oppure si dimentica il `+1` e il flag e'
    sempre falso. Nessuno dei due errori fallisce: il primo mostra una riga in
    piu', il secondo dice «elenco completo» su un elenco tagliato.

    ⚠️ Consumatore UNO (`CatalogoRepository.lookup_articoli`), e va detto: il
    gemello sulle unita' di misura e' stato tolto lo stesso giorno perche' non
    lo esponeva nessun endpoint. Resta un BB e non una riga nel repository per
    la ragione qui sopra — e perche' e' la sede dove il prossimo lookup che deve
    dichiarare il troncamento lo trovera' gia' fatto. Gli altri lookup ricchi
    (billing account, istanze utility, `dbops.fn_get_lookup_codici`) NON sono
    candidati: hanno gia' un `total_count` vero, che dice di piu'.

    ⚠️ Regge finche' i JOIN della query sono 1:1. Uno che moltiplicasse le righe
    le farebbe contare due volte: la sonda direbbe «troncato» su un elenco
    intero, e il taglio a `limite` butterebbe righe vere.
    """
    with connection.cursor() as cursor:
        cursor.execute(data_sql, [*params, limite + 1])
        righe = rows_to_list(cursor)
    return righe[:limite], len(righe) > limite


def query_paged_view(
    *,
    select_sql: str,
    order_by: str,
    params: list[Any],
    limit: int,
    offset: int,
    max_limit: int = MAX_LIMIT,
) -> tuple[list[tuple], int]:
    """Query paginata su vista/union costosa in UNA valutazione, con CLAMP.

    CTE materializzata + COUNT(*) OVER() + OFFSET clampato all'ultima pagina
    direttamente in SQL: il rientro da una pagina stantia non costa 2-3
    valutazioni della union (data vuota + count fallback + refetch FE) — il
    BE serve subito l'ultima pagina REALE e il service dichiara la pagina
    effettiva nell'envelope. Semantica diversa da `fetch_paged_with_total`
    (che serve la pagina RICHIESTA): usare il clamp solo dove il contratto
    API espone la pagina effettiva (famiglia cruscotti + usePagedDashFetch).

    `select_sql` = SELECT...FROM...WHERE gia' parametrizzato, SENZA
    ORDER/LIMIT; `order_by` = clausola ORDER BY completa su NOMI COLONNA DI
    OUTPUT della SELECT (whitelist a carico del chiamante, MAI input utente).
    Ritorna (rows, total_count): total_count e' SEMPRE l'ultima colonna.

    Promozione a BB core (regola del 2, 2026-07-18) da
    `VenditeRepository._query_paged_view` (estratto 2026-07-07, ok Tid).
    """
    safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)
    # MATERIALIZED esplicito: la CTE e' referenziata due volte (righe +
    # count del clamp) e deve essere valutata una volta sola.
    sql = f"""
        WITH righe AS MATERIALIZED (
            {select_sql}
        )
        SELECT r.*, COUNT(*) OVER () AS total_count
        FROM righe r
        {order_by}
        LIMIT %s
        OFFSET LEAST(
            %s,
            (SELECT GREATEST(COUNT(*) - 1, 0) / %s * %s FROM righe)
        )
    """  # noqa: S608
    with connection.cursor() as cursor:
        cursor.execute(
            sql, params + [safe_limit, safe_offset, safe_limit, safe_limit]
        )
        rows = cursor.fetchall()
    total_count = int(rows[0][-1]) if rows else 0
    return list(rows), total_count


def dynamic_update(table: str, pk: int, **kwargs: Any) -> bool:
    """UPDATE dinamico "kwargs espliciti": SET dai soli kwargs non-None.

    Delegatore di `sql_write_helpers.execute_dynamic_update(skip_none=True)`
    (unificazione 2026-07-13): None = "non toccare" — per AZZERARE campi
    nullable (PATCH whitelisted) usare il BB direttamente con skip_none=False.
    """
    from apps.core.db.sql_write_helpers import execute_dynamic_update

    return execute_dynamic_update(table, pk, kwargs, skip_none=True)
