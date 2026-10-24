# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello TRASVERSALE fra il catalogo delle colonne
#        (`ui.lista_colonna.campo_sorgente`) e la riga che il backend consegna
#        davvero, per OGNI lista configurabile che non ha una vista.
#
#        PERCHE' ESISTE. Il presidio di questo legame vive a database: il
#        trigger `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` verifica
#        che ogni `campo_sorgente` sia un attributo della vista dichiarata in
#        `ui.lista_definizione.vista_sql`. Ma quel trigger, per costruzione,
#        **salta la lista che non ha una vista** — e non e' un caso di nicchia:
#        sono 39 liste su 54 (censimento del seed, 2026-09-01). Quelle righe le
#        compone un repository con join, LATERAL e filtri di scope: non esiste
#        un oggetto nel database contro cui validarle, e crearne uno finto
#        sposterebbe il problema di un posto dandogli l'aria di essere risolto
#        (la vista e la query potrebbero divergere, e il BE leggerebbe la
#        query). ⭐ Le due cose vere sono il CATALOGO e la PROIEZIONE del
#        repository: e' qui che si guardano.
#
#        ⚠️ IL DIFETTO CHE PRESIDIA E' SILENZIOSO — tre volte, e nessuna da'
#        errore:
#          · cella: `<ListaConfigurabile>` monta `:field="col.campo_sorgente"`,
#            la chiave non c'e' e la colonna esce VUOTA;
#          · export: `riga.get(campo_sorgente, "")` scrive la colonna vuota
#            CON la sua intestazione (`lista_export_service.py`);
#          · «Personalizza colonne»: la colonna resta accendibile, l'operatore
#            la accende, non vede niente e conclude che e' un permesso.
#
#        ⭐ SI ARMA DA SOLO. L'elenco delle liste da coprire NON e' scritto qui:
#        si legge dal seed (`vista_sql` nullo). Una lista nuova con lo stesso
#        difetto rende rosso `test_il_registro_copre_ogni_lista_senza_vista` il
#        giorno in cui viene seminata — nessuno deve ricordarsi di censirla.
#        Cio' che resta a mano e' solo COME si esercita la lista: una query
#        vuole i suoi argomenti, e non c'e' modo di dedurli.
#
#        ⭐ LE COLONNE LE DICHIARA IL CURSORE, non le righe: si legge
#        `cursor.description`, quindi la prova vale anche su una lista VUOTA —
#        che e' il caso in cui serve di piu', perche' una lista senza righe non
#        puo' smentire niente e un confronto sui dati sarebbe verde per
#        sottrazione. Per la stessa ragione il contesto operatore non serve: la
#        RLS toglie le RIGHE, non le colonne.
#
#        ⚠️ LA SEDE E' IL CSV, non la tabella: `80_data` si cambia dal CSV (il
#        mirror e' `runOnChange`), quindi il confronto si fa contro cio' che
#        sta in git.
#
#        ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI):
#        senza database non si sa quali colonne proietti una query. NON SCRIVE
#        NULLA — esegue le sole SELECT di lista, in transazione annullata.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_ogni_campo_sorgente_a_catalogo_arriva_nella_riga
   Per ogni lista senza vista: ogni `campo_sorgente` attivo del catalogo esiste
   fra le colonne che la lista proietta davvero.

1-bis. (stesso test) i `campi_da_python` dichiarati esistono davvero nella
   riga, quando una riga c'e': un'eccezione che invecchia diventa un permesso
   di passare rimasto acceso.

2. test_il_registro_copre_ogni_lista_senza_vista
   Il verso che arma il presidio: nessuna lista con `vista_sql` nullo puo'
   restare fuori da `_ESERCIZI` senza un'esenzione motivata. Senza questo,
   «tutte le liste» significherebbe «quelle del giorno in cui le ho censite».

3. test_nessun_esercizio_punta_a_una_lista_inesistente
   Il verso opposto: un codice rinominato a catalogo lascerebbe qui una riga
   morta, e la lista vera scoperta.

4. test_ogni_ordinamento_dichiarato_produce_sql_valido
   Ogni colonna della whitelist, in ENTRAMBI i versi, produce SQL che parte.
   E' la meta' che `test_liste_configurabili_seed` non copre: quello confronta
   due ELENCHI (seed e whitelist) e vale senza database; qui si guarda se la
   query PARTE. Sono difetti diversi: la' un nome che il frontend manda e il
   backend non riconosce (400), qui una colonna che il backend riconosce e
   l'SQL non ha (**500**).

1-ter. (dentro il test 1) le GEMELLE di un `formato` — la colonna in piu' che
   un formato pretende nella riga oltre al `campo_sorgente` (`natura_doc` →
   `natura_doc_codice_interno`, dal 2026-09-18) — contano come campi
   dichiarati: senza, il Tag renderebbe `—` su ogni riga e nessuno lo direbbe.

5. test_le_gemelle_di_formato_esistono_nella_vista
   Lo stesso per le liste CON vista, che il test 1 non esercita: il trigger DB
   valida il solo `campo_sorgente` contro la vista, non la gemella. Si chiede
   al catalogo PG se la vista la proietta.
"""

from __future__ import annotations

import dataclasses
import unittest
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import connection, transaction

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.core.tests.test_liste_configurabili_seed import (
    _LISTE,
    _colonne_attive,
    _seed,
    campi_gemelli_per_formato,
    ORDINAMENTO_LOCALE,
)

# Mese di comodo per le liste il cui filtro di competenza e' OBBLIGATORIO.
# ⚠️ Che questo mese ESISTA o no nei dati e' indifferente, ed e' il punto: qui si
#    guardano le COLONNE, e una query che torna zero righe le dichiara comunque.
#    Se per caso trova righe tanto meglio (si legge anche la riga vera), ma il
#    presidio non deve MAI dipendere da cosa c'e' nel database di turno.
_MESE = date(2026, 1, 1)

# Id di comodo per le sotto-liste che filtrano su un padre (lotto, listino,
# commessa). Stessa ragione del mese: serve a far PARTIRE la query.
# ⚠️ POSITIVO e non `0`, ed e' un fatto del dominio: le funzioni DB delle liste
#    del lotto e della commessa rifiutano `p_lotto_id`/`p_commessa_id` <= 0 con
#    un errore parlante, quindi con lo zero la query non partiva affatto. Un id
#    che non esiste va benissimo: torna zero righe, e le colonne le dichiara
#    comunque il cursore.
_ID_FINTO = 999_999_999


# Scopo: come si esercita una lista, cioe' l'unica cosa che il censimento non
#        puo' dedurre da solo.
# Campi:
#   chiama            -> esegue la query di lista; riceve (order_by, order_dir),
#                        entrambi opzionali (None = default del metodo).
#   dove              -> modulo::metodo che ospita la SELECT, per il messaggio.
#   campi_da_python   -> chiavi che la riga acquista DOPO la SELECT (capability
#                        calcolate dal service). Vanno elencate con il motivo:
#                        e' un'eccezione dichiarata, non una scorciatoia.
@dataclass(frozen=True)
class Esercizio:
    chiama: Callable[[str | None, str | None], Any]
    dove: str
    campi_da_python: frozenset[str] = frozenset()


# Scopo: le liste ATTIVE che non hanno una vista, lette dal seed. E' il
#        censimento che arma il presidio: non si scrive, si legge.
def _liste_senza_vista() -> set[str]:
    return {
        riga["codice"]
        for riga in _seed("lista_definizione.csv")
        if riga["attivo"] == "t"
        and (riga["vista_sql"] or "").strip().upper() in ("", "NULL")
    }


# Scopo: i `campo_sorgente` che il catalogo dichiara per una lista, cioe' le
#        chiavi che il frontend chiedera' alla riga.
# ⛔ Fuori restano le stesse due categorie che salta il trigger DB: le colonne
#    di tipo `azione` (non hanno sorgente per disegno) e quelle con
#    `campo_sorgente` vuoto (colonna calcolata interamente dal frontend).
# ⭐ Dal 2026-09-18 anche le GEMELLE di un formato: `natura_doc` rende il Tag
#    con la descrizione (il `campo_sorgente`) E il `codice_interno`, che il
#    frontend legge da una colonna gemella della riga. Se la lista non la
#    proietta il Tag esce `—` su ogni riga — un difetto che si vede ma che
#    nessuno attribuirebbe alla causa. Il nome della gemella si legge dal
#    sorgente FE (`campi_gemelli_per_formato`), non si ricopia qui.
def _campi_dichiarati(codice: str) -> set[str]:
    campi = set()
    gemelle = campi_gemelli_per_formato()
    for riga in _colonne_attive(codice):
        if riga["tipo_colonna"] == "azione":
            continue
        campo = (riga["campo_sorgente"] or "").strip()
        if campo and campo.upper() != "NULL":
            campi.add(campo)
        campi.update(gemelle.get((riga["formato"] or "").strip(), ()))
    return campi


# Scopo: le liste CON vista e, per ciascuna, le gemelle che le sue colonne
#        attive pretendono — `{(codice, schema, vista): {gemelle}}`.
def _gemelle_delle_liste_con_vista() -> dict[tuple[str, str, str], set[str]]:
    gemelle = campi_gemelli_per_formato()
    esito: dict[tuple[str, str, str], set[str]] = {}
    for definizione in _seed("lista_definizione.csv"):
        vista = (definizione["vista_sql"] or "").strip()
        if definizione["attivo"] != "t" or not vista or vista.upper() == "NULL":
            continue
        attese: set[str] = set()
        for riga in _colonne_attive(definizione["codice"]):
            attese.update(gemelle.get((riga["formato"] or "").strip(), ()))
        if attese:
            esito[(definizione["codice"], definizione["schema_dati"], vista)] = attese
    return esito


# I nomi con cui i repository chiamano la lista dentro un dict di ritorno.
# ⚠️ Non sono uno standard: `items` (code), `rows` (commessa), `results`
#    (envelope paginato). Sono elencati perche' un dict puo' contenere PIU'
#    liste (righe + stati, per dire), e in quel caso «la prima che trovo»
#    dipenderebbe dall'ordine delle chiavi.
_CHIAVI_RIGHE = ("results", "items", "rows", "righe", "data")


# Scopo: le righe di una lista, qualunque forma abbia il ritorno del metodo
#        (tupla `(righe, total)`, tupla a tre, dict, lista nuda).
# ⛔ Se non le trova SOLLEVA, e non e' pedanteria: tornare `[]` significherebbe
#    «lista vuota», cioe' il presidio smetterebbe di guardare le chiavi della
#    riga — la meta' piu' forte della misura — senza che niente lo dica. E'
#    successo nella prima stesura del guard incassi, che spiava il punto
#    sbagliato e rispondeva «0 colonne» su tutte e quattro: anche una prova e'
#    un programma, e puo' avere il suo difetto.
def _righe(risultato: Any) -> list[Any]:
    if isinstance(risultato, list):
        return risultato
    if isinstance(risultato, dict):
        for chiave in _CHIAVI_RIGHE:
            valore = risultato.get(chiave)
            if isinstance(valore, list):
                return valore
        liste = [v for v in risultato.values() if isinstance(v, list)]
        if len(liste) == 1:
            return liste[0]
        raise AssertionError(
            "ritorno a dict senza una lista di righe riconoscibile "
            f"(chiavi: {sorted(risultato)}): aggiungere il nome a `_CHIAVI_RIGHE`"
        )
    if isinstance(risultato, tuple):
        liste = [e for e in risultato if isinstance(e, list)]
        if len(liste) == 1:
            return liste[0]
        raise AssertionError(
            f"tupla di ritorno con {len(liste)} liste: quale sono le righe?"
        )
    raise AssertionError(f"forma di ritorno non prevista: {type(risultato).__name__}")


# Scopo: le chiavi di una riga. Le liste consegnano dict oppure dataclass di
#        riga (`DistintaRow`, `LottoFattureRow`, ...): in entrambi i casi sono
#        quelle le chiavi che arrivano al frontend.
# ⚠️ `None` — e non l'insieme vuoto — quando la riga e' di un tipo che non
#    sappiamo leggere: sono due cose diverse. Vuoto vorrebbe dire «riga senza
#    chiavi», cioe' un difetto da segnalare; `None` vuol dire «non ho guardato»,
#    e il chiamante ripiega sulle colonne del cursore invece di inventarsi un
#    rosso.
def _chiavi_riga(riga: Any) -> set[str] | None:
    if isinstance(riga, dict):
        return set(riga)
    if dataclasses.is_dataclass(riga) and not isinstance(riga, type):
        return {campo.name for campo in dataclasses.fields(riga)}
    return None


# Scopo: whitelist di ordinamento di una lista, presa dal registro `_LISTE` di
#        `test_liste_configurabili_seed`.
# ⭐ RIUSO, non copia: quel registro e' gia' la mappa «lista -> dove vive la sua
#    whitelist», ed e' gia' presidiato. Riscriverla qui vorrebbe dire tenere
#    due verita' allineate a mano.
def _whitelist(codice: str) -> Iterable[str] | str | None:
    for registrata, risolvi in _LISTE:
        if registrata == codice:
            # ⭐ La sentinella non si CHIAMA: e' una dichiarazione, non un
            #    risolutore. Quelle liste non ordinano lato backend — l'ordine
            #    lo calcola il browser sulle righe gia' consegnate — quindi una
            #    whitelist non ce l'hanno e non devono averla.
            if risolvi == ORDINAMENTO_LOCALE:
                return ORDINAMENTO_LOCALE
            return sorted(risolvi())
    return None


# Scopo: istanzia un repository per percorso+classe. L'import e' PIGRO (dentro
#        la lambda dell'esercizio) per non legare l'import di questo modulo a
#        mezza applicazione: un presidio che si tira dietro tutto e' un presidio
#        che rompe la discovery degli altri.
def _r(percorso: str, classe: str) -> Any:
    import importlib

    return getattr(importlib.import_module(percorso), classe)()


# Scopo: la configurazione di una famiglia del documento interno di magazzino,
#        risolta a chiamata (import pigro come `_r`).
def _famiglia(codice: str) -> Any:
    import importlib

    return importlib.import_module("apps.magazzino.db.famiglie").FAMIGLIE[codice]


# Scopo: traduce l'ordinamento richiesto dal test negli argomenti del metodo.
#        Senza colonna richiesta lascia decidere il metodo (chiavi omesse), a
#        meno che la firma non pretenda l'ordinamento: in quel caso l'esercizio
#        passa un default esplicito.
def _ordine(
    ob: str | None,
    od: str | None,
    colonna: str | None = None,
    direzione: str = "asc",
    *,
    chiavi: tuple[str, str] = ("order_by", "order_dir"),
) -> dict[str, str]:
    scelta = ob or colonna
    if scelta is None:
        return {}
    return {chiavi[0]: scelta, chiavi[1]: od or direzione}


# Scopo: le colonne che una funzione DB DICHIARA di restituire, lette dal
#        catalogo di PostgreSQL (`pg_proc`, modi `t`/`o`).
# ⭐ E' contratto, non popolazione: la firma di una funzione e' progetto scritto,
#    come una `CHECK` o una FK. Serve alle due liste sotto, la cui funzione
#    RIFIUTA un padre che non esiste — senza un lotto o una commessa veri la
#    query non parte, e senza query non c'e' `cursor.description`.
def _colonne_out_funzione(qualificato: str) -> list[str]:
    schema, nome = qualificato.split(".", 1)
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT p.proargnames, p.proargmodes
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = %s AND p.proname = %s
             LIMIT 1
            """,
            [schema, nome],
        )
        riga = cur.fetchone()
    assert riga is not None, f"funzione {qualificato} assente dal database"
    nomi, modi = riga
    # ⚠️ `proargmodes` e' NULL quando la funzione ha solo argomenti IN: li' non
    #    c'e' nessuna colonna dichiarata, e restituire una lista vuota
    #    trasformerebbe il ripiego in un confronto contro il nulla.
    fuori = (
        [n for n, m in zip(nomi or [], modi, strict=True) if m in ("t", "o")]
        if modi
        else []
    )
    assert fuori, (
        f"{qualificato} non dichiara colonne in uscita: non e' una funzione di "
        "lista, o la firma e' cambiata"
    )
    return fuori


# Scopo: esercita una lista che filtra su un padre OBBLIGATORIO ed ESISTENTE.
#        Con un padre vero si esegue la query di lista (la prova piena); dove il
#        database non ne ha nemmeno uno si ripiega sulle colonne dichiarate
#        dalla funzione.
# ⚠️ Il ripiego e' piu' debole e va saputo: prova il contratto della funzione,
#    non l'eventuale rimappatura Python a valle. E' comunque piu' forte del
#    silenzio, ed e' l'unica sede disponibile su un database appena ricostruito.
def _lista_con_padre(
    *, sql_padre: str, con_padre: Callable[[int], Any], funzione: str
) -> Any:
    with connection.cursor() as cur:
        cur.execute(sql_padre)
        riga = cur.fetchone()
    if riga is not None:
        return con_padre(riga[0])
    return [dict.fromkeys(_colonne_out_funzione(funzione))]


# ══════════════════════════════════════════════════════════════════════
# IL REGISTRO — una riga per lista senza vista.
#
# ⭐ Non e' un censimento: il censimento lo fa il seed. Questa e' solo la
#    ISTRUZIONE PER ESEGUIRE la query, che nessuno puo' dedurre al posto nostro.
#    Chi aggiunge una lista senza vista viene mandato qui da un test rosso.
# ⚠️ Gli argomenti sono NEUTRI e finti (mese di comodo, id 0): servono a far
#    partire la query, non a trovare righe. Le colonne le dichiara il cursore.
# ══════════════════════════════════════════════════════════════════════
_ESERCIZI: dict[str, Esercizio] = {
    # ---------- anagrafiche ----------
    "anagrafiche.soggetti": Esercizio(
        dove="anagrafiche/db/soggetti_repository.py::list_soggetti",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.soggetti_repository", "SoggettiRepository"
        ).list_soggetti(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "anagrafiche.emittenti_fiscali": Esercizio(
        dove="anagrafiche/db/emittenti_fiscali_repository.py::list_emittenti_fiscali",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.emittenti_fiscali_repository",
            "EmittentiFiscaliRepository",
        ).list_emittenti_fiscali(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "anagrafiche.emittente_billing_account": Esercizio(
        dove="anagrafiche/db/emittenti_fiscali_repository.py::list_by_emittente",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.emittenti_fiscali_repository",
            "EmittentiFiscaliBillingAccountRepository",
        ).list_by_emittente(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "anagrafiche.operatori": Esercizio(
        dove="amm_software/db/amm_software_repository.py::list_operatori",
        chiama=lambda ob, od: _r(
            "apps.amm_software.db.amm_software_repository", "AmmSoftwareRepository"
        ).list_operatori(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # I reparti (2026-09-27): la SELECT sta in una CTE per ordinare i conteggi.
    "amm.reparti": Esercizio(
        dove="amm_software/db/amm_software_repository.py::list_reparti",
        chiama=lambda ob, od: _r(
            "apps.amm_software.db.amm_software_repository", "AmmSoftwareRepository"
        ).list_reparti(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "anagrafiche.categorie_clienti_listini": Esercizio(
        dove="anagrafiche/db/categorie_clienti_listini_repository.py::list_matrice",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.categorie_clienti_listini_repository",
            "CategorieClientiListiniRepository",
        ).list_matrice(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # ---------- config ----------
    "config.utilities_tipi_ruolo": Esercizio(
        dove="config/db/utilities_tipi_ruolo_repository.py::list_matrice",
        chiama=lambda ob, od: _r(
            "apps.config.db.utilities_tipi_ruolo_repository",
            "UtilitiesTipiRuoloRepository",
        ).list_matrice(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "config.tipi_ruolo_tipi_indirizzo": Esercizio(
        dove="config/db/tipi_ruolo_tipi_indirizzo_repository.py::list_matrice",
        chiama=lambda ob, od: _r(
            "apps.config.db.tipi_ruolo_tipi_indirizzo_repository",
            "TipiRuoloTipiIndirizzoRepository",
        ).list_matrice(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "config.email_account": Esercizio(
        dove="core/db/email_repository.py::list_accounts",
        chiama=lambda ob, od: _r(
            "apps.core.db.email_repository", "EmailRepository"
        ).list_accounts(attivo_only=False, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "config.email_template": Esercizio(
        dove="core/db/email_repository.py::list_templates",
        chiama=lambda ob, od: _r(
            "apps.core.db.email_repository", "EmailRepository"
        ).list_templates(attivo_only=False, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "config.email_log": Esercizio(
        dove="core/db/email_repository.py::list_logs",
        chiama=lambda ob, od: _r(
            "apps.core.db.email_repository", "EmailRepository"
        ).list_logs(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # ---------- catalogo ----------
    "catalogo.unita_misura": Esercizio(
        dove="catalogo/db/catalogo_repository.py::list_unita_misura",
        chiama=lambda ob, od: _r(
            "apps.catalogo.db.catalogo_repository", "CatalogoRepository"
        ).list_unita_misura(
            attivo=None, search=None, limit=1, offset=0, **_ordine(ob, od, "codice")
        ),
    ),
    "catalogo.conversioni_uom": Esercizio(
        dove="catalogo/db/catalogo_repository.py::list_conversioni",
        chiama=lambda ob, od: _r(
            "apps.catalogo.db.catalogo_repository", "CatalogoRepository"
        ).list_conversioni(attivo=None, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # ---------- documenti ----------
    "documenti.template_documenti": Esercizio(
        dove="documenti/db/documenti_repository.py::list_templates",
        chiama=lambda ob, od: _r(
            "apps.documenti.db.documenti_repository", "DocumentiRepository"
        ).list_templates(
            attivo=None,
            tipo_documento_output_id=None,
            sorgente_tipo_id=None,
            emittente_fiscale_id=None,
            search=None,
            emittente_ids_scope=None,
            limit=1,
            offset=0,
            **_ordine(ob, od, "codice"),
        ),
    ),
    "documenti.template_asset": Esercizio(
        dove="documenti/db/documenti_repository.py::list_asset",
        chiama=lambda ob, od: _r(
            "apps.documenti.db.documenti_repository", "DocumentiRepository"
        ).list_asset(
            attivo=None,
            asset_tipo_id=None,
            emittente_fiscale_id=None,
            search=None,
            emittente_ids_scope=None,
            limit=1,
            offset=0,
            **_ordine(ob, od, "codice"),
        ),
    ),
    # I documenti generati di una sorgente e le versioni di un template
    # (2026-09-27, liste 84 e 88): sorgente e template finti, nessuna riga —
    # le colonne le dichiara il cursore. «Originale» e' `has_file_principale`
    # (EXISTS sui file del documento).
    "documenti.documenti_sorgente": Esercizio(
        dove="documenti/db/documenti_repository.py::list_documenti_per_sorgente",
        chiama=lambda ob, od: _r(
            "apps.documenti.db.documenti_repository", "DocumentiRepository"
        ).list_documenti_per_sorgente(
            sorgente_tipo_id=_ID_FINTO,
            sorgente_uid="00000000-0000-0000-0000-000000000000",
            sorgente_riga=None,
            emittente_ids_scope=None,
            limit=1,
            offset=0,
            **_ordine(ob, od),
        ),
    ),
    "documenti.template_versioni": Esercizio(
        dove="documenti/db/documenti_repository.py::list_versioni",
        chiama=lambda ob, od: _r(
            "apps.documenti.db.documenti_repository", "DocumentiRepository"
        ).list_versioni(
            _ID_FINTO, attivo=None, stato=None, limit=1, offset=0, **_ordine(ob, od),
        ),
    ),
    # ---------- pratiche ----------
    "pratiche.pratiche": Esercizio(
        dove="pratiche/db/pratiche_repository.py::list_pratiche",
        chiama=lambda ob, od: _r(
            "apps.pratiche.db.pratiche_repository", "PraticheRepository"
        ).list_pratiche(
            emittente_fiscale_id=_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    # ---------- core / tracciamento ----------
    "storico.audit_log": Esercizio(
        dove="amm_software/db/amm_software_repository.py::list_audit_log",
        # ⛔ NON e' `core/db/dbops_repository.py::list_audit_logs`, che pure
        #    dichiara `lista_codice = "storico.audit_log"` su `ApiAuditLog`:
        #    quello legge `dbops.audit_log` (le ESECUZIONI di funzione) e le sue
        #    colonne non hanno niente a che vedere col catalogo di questa lista.
        #    La lista che il frontend monta chiama `/amm-software/audit-log/`,
        #    cioe' lo storico delle MODIFICHE per tabella. Due cose diverse con
        #    lo stesso nome — ed e' la prima cosa che ha trovato questo presidio.
        chiama=lambda ob, od: _r(
            "apps.amm_software.db.amm_software_repository", "AmmSoftwareRepository"
        ).list_audit_log(limit=1, offset=0, **_ordine(ob, od)),
        # ⛔ TRE NOMI CHE LA SELECT NON HA, e non e' un difetto: la riga li
        #    acquista in Python. `list_audit_log` proietta `valid_from`,
        #    `user_insert` e `code`, e li RIBATTEZZA `timestamp`,
        #    `user_modifica` e `tabella` mentre compone il dict — `tabella` e'
        #    l'alias di retrocompatibilita' di `code` per i consumer vecchi.
        # 🔴 PERCHE' L'ESENZIONE ARRIVA SOLO ORA. Fino al 2026-09-02 questa
        #    lista non arrivava nemmeno a essere guardata: la query esplodeva
        #    (`storico.risorse_umane_auth_user` inesistente su un database
        #    RICOSTRUITO) e il test dava ERRORE, non fallimento. Spento il
        #    rosso, la query parte — e in CI torna ZERO righe, perche' le
        #    storico di un database appena costruito sono vuote. Senza righe il
        #    presidio ripiega sulle colonne del CURSORE, dove i tre nomi
        #    Python non ci sono. ⇒ Il difetto era latente e nascosto dietro un
        #    errore piu' rumoroso.
        # ⭐ L'esenzione resta ONESTA: il test 1-bis pretende che questi tre
        #    nomi esistano DAVVERO nella riga, quando una riga c'e' — e sullo
        #    sviluppo c'e'. Un `campi_da_python` invecchiato diventa rosso.
        campi_da_python=frozenset({"timestamp", "user_modifica", "tabella"}),
    ),
    "dbops.coda_lavori": Esercizio(
        dove="core/services/coda_lavori/repository.py::elenca",
        # ⚠️ Qui l'ordinamento si chiama `sort_by`/`sort_dir`, non
        #    `order_by`/`order_dir`: e' il punto in cui un nome viene TRADOTTO,
        #    e i punti che traducono sono quelli che si rompono.
        chiama=lambda ob, od: _r(
            "apps.core.services.coda_lavori.repository", "CodaLavoriRepository"
        ).elenca(
            limit=1,
            offset=0,
            **_ordine(ob, od, chiavi=("sort_by", "sort_dir")),
        ),
    ),
    # ⚠️ Il registro dei processi automatici sta fra le liste di TRACCIAMENTO
    #    anche se il suo codice comincia per `amm.`: il dato e' `dbops`, e il
    #    repository e' in `core` perche' il roster serve anche a `vendite` (una
    #    chiamata laterale fra domini non si fa). Il prefisso dice DOVE si
    #    guarda la lista, non di chi e' il dato.
    "amm.processi": Esercizio(
        dove="core/db/processi_repository.py::list_processi",
        chiama=lambda ob, od: _r(
            "apps.core.db.processi_repository", "ProcessiRepository"
        ).list_processi(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # Le sessioni attive (2026-09-27): utente 0, nessuna riga — le colonne le
    # dichiara il cursore. `escludi_jti=None` = nessuna sessione da togliere.
    "core.sessioni_attive": Esercizio(
        dove="core/db/session_audit_repository.py::list_sessioni_attive_paginata",
        chiama=lambda ob, od: _r(
            "apps.core.db.session_audit_repository", "SessionAuditRepository"
        ).list_sessioni_attive_paginata(0, escludi_jti=None, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # I flussi di una pratica (2026-09-27, lista 85): pratica 0, nessuna riga —
    # le colonne le dichiara il cursore. Stessa proiezione del dettaglio flusso
    # (`_FLUSSO_SELECT`), l'esito esce come `esito_descrizione`.
    "pratiche.flussi": Esercizio(
        dove="pratiche/db/pratiche_repository.py::list_flussi_pagina",
        chiama=lambda ob, od: _r(
            "apps.pratiche.db.pratiche_repository", "PraticheRepository"
        ).list_flussi_pagina(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # L'utilizzo di una riga della matrice utility/ruoli (2026-09-27, lista
    # 86): riga di matrice finta, nessun emittente — basta il cursore.
    "config.utilities_tipi_ruolo_usage": Esercizio(
        dove="config/db/utilities_tipi_ruolo_repository.py::list_emittenti_usage",
        chiama=lambda ob, od: _r(
            "apps.config.db.utilities_tipi_ruolo_repository",
            "UtilitiesTipiRuoloRepository",
        ).list_emittenti_usage(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # La consultazione di `dbops.error_log` (pezzo E dell'osservabilita',
    # 2026-09-19): il catalogo dei messaggi arriva per JOIN nella stessa SELECT.
    "dbops.error_log": Esercizio(
        dove="core/db/dbops_repository.py::list_error_logs",
        chiama=lambda ob, od: _r(
            "apps.core.db.dbops_repository", "DbopsRepository"
        ).list_error_logs(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # ---------- vendite ----------
    # Il giornale trasversale degli eventi (pezzo G): terzo lettore della vista
    # cucita. ⚠️ `entita_display` (codice del lotto, «serie/numero» del
    # documento) si risolve in Python sulla pagina, con una query a parte:
    # e' una chiave della riga, non una colonna della SELECT del giornale.
    "vendite.giornale": Esercizio(
        dove="vendite/db/vendite_repository.py::list_giornale_trasversale",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_giornale_trasversale(
            gravita=["ERROR", "WARN", "INFO"], limit=1, offset=0,
            **_ordine(ob, od, chiavi=("sort_by", "sort_dir")),
        ),
        campi_da_python=frozenset({"entita_display"}),
    ),
    "vendite.lotti": Esercizio(
        dove="vendite/db/vendite_repository.py::list_lotti",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_lotti(
            competenza_mese=None,
            utility_id=None,
            stato_lotto=None,
            area_geografica_id=None,
            tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=None,
            limit=1,
            offset=0,
            **_ordine(ob, od),
        ),
    ),
    "vendite.listini": Esercizio(
        dove="vendite/db/listini_repository.py::list_listini",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.listini_repository", "ListiniRepository"
        ).list_listini(
            utility_id=None,
            tipologia_id=None,
            attivo=None,
            search=None,
            limit=1,
            offset=0,
            **_ordine(ob, od, "codice"),
        ),
    ),
    "vendite.listini_righe": Esercizio(
        dove="vendite/db/listini_repository.py::list_righe",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.listini_repository", "ListiniRepository"
        ).list_righe(
            _ID_FINTO, _ID_FINTO, attivo=None, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    "vendite.promo_articoli": Esercizio(
        dove="vendite/db/promo_articoli_repository.py::list_promo",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.promo_articoli_repository", "PromoArticoliRepository"
        ).list_promo(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "vendite.registri_numerazione": Esercizio(
        dove="vendite/db/registri_repository.py::list_registri",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.registri_repository", "RegistriRepository"
        ).list_registri(None, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # I due tab «Revisioni» (2026-09-27, liste 89 e 90): documento finto,
    # nessuna riga — la radice/il numero escono NULL e le colonne le dichiara
    # il cursore (`v.*` delle due viste di lista).
    "vendite.preventivo_revisioni": Esercizio(
        dove="vendite/db/preventivi_repository.py::list_revisioni",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.preventivi_repository", "PreventiviRepository"
        ).list_revisioni(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "vendite.offerta_revisioni": Esercizio(
        dove="vendite/db/offerte_repository.py::list_revisioni",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.offerte_repository", "OfferteRepository"
        ).list_revisioni(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # Le righe di un contratto (2026-09-30, brief-db-liste-righe-documento
    # lotto D): la sorgente e' `fn_contratto_righe_preview`, che su un contratto
    # che non esiste risponde zero righe ma dichiara le sue colonne.
    "vendite.contratto_righe": Esercizio(
        dove="vendite/db/_righe_repo_mixin.py::list_righe_pagina (ContrattoRigheListaRepository)",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.contratti_repository", "ContrattoRigheListaRepository"
        ).list_righe_pagina(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    # Le righe di un'offerta (2026-10-05, brief-db-righe-esclusione-solo-non-si-
    # vende §8.1): gemella della 103, sorgente `fn_offerta_righe_preview`.
    "vendite.offerta_righe": Esercizio(
        dove="core/db/righe_lista_mixin.py::list_righe_pagina (OffertaRigheListaRepository)",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.offerte_repository", "OffertaRigheListaRepository"
        ).list_righe_pagina(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "vendite.commesse_attivita": Esercizio(
        dove="vendite/db/commesse_repository.py::list_commessa_attivita",
        # ⚠️ `fn_list_commessa_attivita` rifiuta una commessa inesistente: qui
        #    serve un padre VERO, e senza nemmeno uno si legge la firma della
        #    funzione (vedi `_lista_con_padre`).
        chiama=lambda ob, od: _lista_con_padre(
            sql_padre="SELECT id FROM vendite.commesse LIMIT 1",
            funzione="vendite.fn_list_commessa_attivita",
            con_padre=lambda pid: _r(
                "apps.vendite.db.commesse_repository", "CommesseRepository"
            ).list_commessa_attivita(pid, limit=1, offset=0, **_ordine(ob, od)),
        ),
    ),
    "vendite.approvazioni_prezzo": Esercizio(
        dove="pratiche/db/pratiche_repository.py::list_pratiche",
        # ⭐ La coda approvazioni NON ha una query propria: attraversa
        #    `cerca_pratiche`, e il service aggiunge a ogni riga le capability
        #    calcolate in Python (`approvazioni_prezzo_service._capabilities_
        #    per_pratica`). Quelle chiavi non stanno in nessun SELECT, e vanno
        #    dichiarate qui: e' un'eccezione motivata, non una scorciatoia.
        campi_da_python=frozenset(
            {"can_approve", "can_reject", "reason", "sorgente"}
        ),
        chiama=lambda ob, od: _r(
            "apps.pratiche.db.pratiche_repository", "PraticheRepository"
        ).list_pratiche(
            emittente_fiscale_id=_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    "vendite.fatture_stampa_coda": Esercizio(
        dove="vendite/db/pipeline_repository.py::elenca_coda_stampa",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.pipeline_repository", "VenditePipelineRepository"
        ).elenca_coda_stampa(
            limit=1, offset=0, **_ordine(ob, od, chiavi=("sort_by", "sort_dir"))
        ),
    ),
    "vendite.fondi_fattura_da_decidere": Esercizio(
        dove="vendite/db/vendite_repository.py::list_fondi_fattura_da_decidere",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_fondi_fattura_da_decidere(limit=1, offset=0, **_ordine(ob, od)),
    ),
    "vendite.lotto_fatture": Esercizio(
        dove="vendite/db/vendite_repository.py::list_lotto_fatture",
        # ⭐ `errore_codice` non e' una colonna del SELECT: nasce in Python dal
        #    `meta` dell'errore (`errore_meta.get("error_code")`), accanto a
        #    `errore_messaggio` che invece e' un alias SQL. Le due gemelle hanno
        #    origine diversa, e solo una delle due il cursore la vede.
        campi_da_python=frozenset({"errore_codice"}),
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_lotto_fatture(
            lotto_id=_ID_FINTO,
            stato_esecuzione=None,
            limit=1,
            offset=0,
            **_ordine(ob, od),
        ),
    ),
    # ⭐ La scheda «Presi in carico» (brief-db-esito-gruppo-lotto): i documenti
    #    che il lotto ha preso, compresi quelli che una fattura non sono mai
    #    diventati. ⚠️ Nessun `campi_da_python`: qui il cursore vede TUTTO —
    #    l'identita' del gruppo la porta la SELECT (aggregata dalla vista di
    #    competenza), non il mapping.
    "vendite.lotto_gruppi": Esercizio(
        dove="vendite/db/vendite_repository.py::list_lotto_gruppi",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_lotto_gruppi(
            lotto_id=_ID_FINTO,
            limit=1,
            offset=0,
            **_ordine(ob, od, chiavi=("sort_by", "sort_dir")),
        ),
    ),
    "vendite.lotto_task_runs": Esercizio(
        dove="vendite/db/pipeline_repository.py::list_lotto_task_runs",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.pipeline_repository", "VenditePipelineRepository"
        ).list_lotto_task_runs(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "vendite.lotto_segnalazioni": Esercizio(
        dove="vendite/db/pipeline_repository.py::list_lotto_segnalazioni",
        # ⚠️ Come sopra: `fn_list_lotto_segnalazioni` pretende un lotto che
        #    esiste. ⭐ La gemella `lotto_task_runs` no, ed e' il motivo per cui
        #    quella si esercita per intero e questa a volte no: due funzioni
        #    sorelle, due severita' diverse sullo stesso parametro.
        chiama=lambda ob, od: _lista_con_padre(
            sql_padre="SELECT id FROM vendite.fatturazione_lotti LIMIT 1",
            funzione="vendite.fn_list_lotto_segnalazioni",
            con_padre=lambda pid: _r(
                "apps.vendite.db.pipeline_repository", "VenditePipelineRepository"
            ).list_lotto_segnalazioni(
                lotto_id=pid, limit=1, offset=0, **_ordine(ob, od)
            ),
        ),
    ),
    # ---------- vendite: le sei liste delle dashboard ----------
    "vendite.dash_aperto_documenti": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_aperto_documenti",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_aperto_documenti(
            area=None, fase=None, ritardo_giorni=None, limit=1, offset=0,
            **_ordine(ob, od),
        ),
    ),
    "vendite.dash_backlog_documenti": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_backlog_documenti",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_backlog_documenti(
            classe=None, area=None, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    "vendite.dash_competenza_errori": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_competenza_errori",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_competenza_errori(
            competenza_mese=_MESE, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    "vendite.dash_competenza_gruppi": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_competenza_gruppi",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_competenza_gruppi(
            competenza_mese=_MESE, stadio=None, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    "vendite.dash_competenza_commesse": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_competenza_commesse",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_competenza_commesse(
            competenza_mese=_MESE,
            stadio=None,
            solo_ritardo=False,
            limit=1,
            offset=0,
            **_ordine(ob, od),
        ),
    ),
    "vendite.dash_competenza_residui": Esercizio(
        dove="vendite/db/vendite_repository.py::list_dash_competenza_residui",
        chiama=lambda ob, od: _r(
            "apps.vendite.db.vendite_repository", "VenditeRepository"
        ).list_dash_competenza_residui(
            competenza_mese=_MESE, limit=1, offset=0, **_ordine(ob, od)
        ),
    ),
    # ---------- ui: i quattro cataloghi delle liste ----------
    # ⭐ Sono il CRUD delle liste configurabili, seminate il 2026-09-02. Non
    #    paginano e non ordinano lato backend (`:paginata="false"`), ma la
    #    domanda di questo presidio vale identica: il catalogo dichiara dei
    #    `campo_sorgente`, e se la riga non li porta la cella esce VUOTA.
    # ⚠️ Le tre figlie prendono l'id della lista PADRE: un id che non esiste
    #    torna zero righe, e le colonne le dichiara comunque il cursore.
    "ui.lista_definizione": Esercizio(
        dove="ui/db/ui_admin_repository.py::list_definizioni_admin",
        chiama=lambda ob, od: _r(
            "apps.ui.db.ui_admin_repository", "UiAdminRepository"
        ).list_definizioni_admin(),
    ),
    "ui.lista_colonna": Esercizio(
        dove="ui/db/ui_admin_repository.py::list_colonne_by_lista_admin",
        chiama=lambda ob, od: _r(
            "apps.ui.db.ui_admin_repository", "UiAdminRepository"
        ).list_colonne_by_lista_admin(_ID_FINTO),
    ),
    "ui.lista_preset": Esercizio(
        dove="ui/db/ui_admin_repository.py::list_preset_by_lista",
        chiama=lambda ob, od: _r(
            "apps.ui.db.ui_admin_repository", "UiAdminRepository"
        ).list_preset_by_lista(_ID_FINTO),
    ),
    "ui.lista_colonna_permesso": Esercizio(
        dove="ui/db/ui_admin_repository.py::list_permessi_by_lista",
        chiama=lambda ob, od: _r(
            "apps.ui.db.ui_admin_repository", "UiAdminRepository"
        ).list_permessi_by_lista(_ID_FINTO),
    ),
    # ---------- pagamenti (cantiere incassi) ----------
    "pagamenti.distinte": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_distinte",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_distinte(
            limit=1, offset=0, **_ordine(ob, od, "data_contabile", "DESC")
        ),
    ),
    "pagamenti.righe": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_righe_coda",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_righe_coda(
            stati=("DA_ABBINARE",),
            limit=1,
            offset=0,
            **_ordine(ob, od, "data_pagamento", "DESC"),
        ),
    ),
    # Le righe di UNA distinta (lista 69, 2026-09-18). ⚠️ `_ID_FINTO`: la
    # distinta non esiste, la query torna zero righe e le colonne le dichiara
    # il cursore — e' il caso in cui il presidio serve di piu'.
    "pagamenti.distinta_righe": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_righe_distinta",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_righe_distinta(
            _ID_FINTO, limit=1, offset=0, **_ordine(ob, od, None),
        ),
    ),
    "pagamenti.rate_fuori_capienza": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_rate_fuori_capienza",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_rate_fuori_capienza(
            limit=1, offset=0, **_ordine(ob, od, "data_scadenza", "DESC")
        ),
    ),
    # ⭐ I tre saldi arrivano da una SECONDA query (il nucleo `fn_get_saldi_rate`
    #    sugli id della pagina) e su una pagina vuota non c'e' nessuna riga su
    #    cui appoggiarli: qui si passa `solo_aperte=True`, dove i saldi escono
    #    dalla STESSA query e le colonne le dichiara il cursore anche a zero
    #    righe. L'altro ramo lo prova `test_rate_lista_db` sul caso costruito.
    "pagamenti.rate": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_rate_paginata",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_rate_paginata(
            auth_user_id=None, solo_aperte=True, limit=1, offset=0,
            **_ordine(ob, od, None),
        ),
    ),
    "pagamenti.eccedenze": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_eccedenze",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_eccedenze(
            limit=1, offset=0, **_ordine(ob, od, "eccedenza_cliente", "DESC")
        ),
    ),
    # ── Lotto 2 (2026-09-02). ⭐ Il presidio si e' armato da solo su tutte e
    #    quattro il giorno del seed: nessuno le ha censite a mano, le ha
    #    pretese `test_il_registro_copre_ogni_lista_senza_vista` leggendo il
    #    CSV. Resta a mano solo COME si esercita ciascuna — una query vuole i
    #    suoi argomenti, e quelli non si deducono.
    "pagamenti.canali_incasso": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_enti_incasso",
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_enti_incasso(
            limit=1, offset=0, **_ordine(ob, od, "codice", "asc")
        ),
    ),
    "pagamenti.sistemazioni_fattura": Esercizio(
        dove="pagamenti/db/pagamenti_repository.py::list_sistemazioni_fattura",
        # ⚠️ `fattura_id=1` puo' non esistere: la prova legge
        #    `cursor.description`, quindi vale anche a zero righe — che e' il
        #    caso in cui serve di piu', perche' una lista vuota non mostra a
        #    nessuno che una colonna e' sparita.
        chiama=lambda ob, od: _r(
            "apps.pagamenti.db.pagamenti_repository", "PagamentiRepository"
        ).list_sistemazioni_fattura(1, limit=1, offset=0, **_ordine(ob, od)),
    ),
    "anagrafiche.soggetto_titoli_iva": Esercizio(
        dove="anagrafiche/db/titoli_iva_repository.py::list_titoli_soggetto",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.titoli_iva_repository", "TitoliIvaRepository"
        ).list_titoli_soggetto(
            "00000000-0000-0000-0000-000000000000", **_ordine(ob, od)
        ),
    ),
    # ---------- lotto 3 (2026-09-02): le due liste dentro `TitoloIvaDrawer` ----------
    # ⭐ Anche queste arrivano PRIMA della loro schermata (Gruppo B, drawer non
    #    ancora convertito), e il presidio le pretende lo stesso: si arma dal
    #    seed. La query esiste gia', quindi un `campo_sorgente` sbagliato esiste
    #    gia' anche lui.
    "anagrafiche.titolo_iva_ambiti": Esercizio(
        dove="anagrafiche/db/titoli_iva_repository.py::list_ambiti",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.titoli_iva_repository", "TitoliIvaRepository"
        ).list_ambiti(_ID_FINTO),
    ),
    "anagrafiche.titolo_iva_movimenti": Esercizio(
        dove="anagrafiche/db/titoli_iva_repository.py::list_movimenti",
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.titoli_iva_repository", "TitoliIvaRepository"
        ).list_movimenti(_ID_FINTO, **_ordine(ob, od)),
    ),
    "anagrafiche.titoli_iva_sfondati": Esercizio(
        dove="anagrafiche/db/titoli_iva_repository.py::list_titoli_sfondati",
        # ⚠️ Ritorna `(righe, totale)`: al presidio interessa la proiezione, che
        #    legge dal cursore — la tupla non lo disturba.
        chiama=lambda ob, od: _r(
            "apps.anagrafiche.db.titoli_iva_repository", "TitoliIvaRepository"
        ).list_titoli_sfondati(limit=1, offset=0, **_ordine(ob, od)),
    ),
    # ── Magazzino, Lotto 2 (2026-09-18). ⭐ Inventari e rettifiche sono UNA
    #    implementazione parametrica sulla famiglia (Q-1): l'esercizio passa la
    #    famiglia, e la proiezione — `descrizione` NULL sulla rettifica,
    #    `qta_contata`/`qta_sistema` contro `qta_delta`/`motivo` sulle righe —
    #    e' quella che ogni famiglia dichiara a catalogo.
    "magazzino.inventari": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_documenti",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_documenti(
            _famiglia("inventari"), auth_user_id=None, limit=1, offset=0,
            **_ordine(ob, od, None),
        ),
    ),
    "magazzino.rettifiche": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_documenti",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_documenti(
            _famiglia("rettifiche"), auth_user_id=None, limit=1, offset=0,
            **_ordine(ob, od, None),
        ),
    ),
    "magazzino.inventario_righe": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_righe",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_righe(
            _famiglia("inventari"), _ID_FINTO, limit=1, offset=0, **_ordine(ob, od, None),
        ),
    ),
    "magazzino.rettifica_righe": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_righe",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_righe(
            _famiglia("rettifiche"), _ID_FINTO, limit=1, offset=0, **_ordine(ob, od, None),
        ),
    ),
    "magazzino.inventario_piano": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_piano",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_piano(_ID_FINTO, limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    "magazzino.disponibilita": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_disponibilita",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_disponibilita(auth_user_id=None, limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    "magazzino.disponibilita_articoli": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_disponibilita_articoli",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_disponibilita_articoli(limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    "magazzino.movimenti": Esercizio(
        dove="magazzino/db/magazzino_repository.py::list_movimenti",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.magazzino_repository", "MagazzinoRepository"
        ).list_movimenti(auth_user_id=None, limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    # ── Le tre anagrafiche di magazzino (2026-09-21, piano anagrafiche-fuori-
    #    dal-pannello-config). I lotti si leggono per articolo: un uuid finto
    #    esercita la query (zero righe, proiezione intera).
    "magazzino.magazzini": Esercizio(
        dove="magazzino/db/anagrafiche_magazzino_repository.py::list_magazzini",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.anagrafiche_magazzino_repository", "AnagraficheMagazzinoRepository"
        ).list_magazzini(auth_user_id=None, limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    "magazzino.ubicazioni": Esercizio(
        dove="magazzino/db/anagrafiche_magazzino_repository.py::list_ubicazioni",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.anagrafiche_magazzino_repository", "AnagraficheMagazzinoRepository"
        ).list_ubicazioni(magazzino_id=_ID_FINTO, limit=1, offset=0, **_ordine(ob, od, None)),
    ),
    "magazzino.lotti": Esercizio(
        dove="magazzino/db/anagrafiche_magazzino_repository.py::list_lotti",
        chiama=lambda ob, od: _r(
            "apps.magazzino.db.anagrafiche_magazzino_repository", "AnagraficheMagazzinoRepository"
        ).list_lotti(articolo_id="00000000-0000-0000-0000-000000000000", limit=1, offset=0, **_ordine(ob, od, None)),
    ),
}


# ⛔ Liste senza vista che NON possono essere esercitate da qui, con la ragione.
#    ⚠️ Deve restare VUOTO o cortissimo: una lista che finisce qui per far
#       passare il test e' un buco, non un'esenzione.
_ESENZIONI: dict[str, str] = {}


class ListaProiezioneCampoSorgenteTests(unittest.TestCase):
    """Il legame catalogo <-> proiezione, per le liste che il DB non presidia."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: esegue la query di una lista e raccoglie DUE cose: le colonne che
    #        ogni SELECT della chiamata dichiara (`cursor.description`) e le
    #        chiavi della prima riga, quando una riga c'e'.
    # ⚠️ Le colonne si prendono dall'UNIONE delle SELECT della chiamata, non
    #    dalla singola query di pagina: alcune liste compongono la riga con piu'
    #    di un giro (conteggio + pagina). E' il verso prudente — un nome che non
    #    esiste in NESSUNA delle due e' comunque un difetto, ed e' quello che
    #    qui si cerca.
    # ⭐ La riga, quando c'e', e' la prova PIU' forte: e' il contratto vero,
    #    dopo l'eventuale mappatura Python. Su un database vuoto non c'e', e il
    #    presidio ripiega sulle colonne del cursore — che restano dichiarate
    #    anche a zero righe. Nessuno dei due modi e' verde per sottrazione.
    def _proiezione(
        self, esercizio: Esercizio, ob: str | None = None, od: str | None = None
    ) -> tuple[set[str], set[str] | None]:
        colonne: set[str] = set()

        def spia(execute, sql, params, many, context):
            esito = execute(sql, params, many, context)
            descrizione = getattr(context.get("cursor"), "description", None)
            if descrizione:
                colonne.update(c[0] for c in descrizione)
            return esito

        # ⛔ UN SAVEPOINT PER LISTA, e non e' pulizia formale: la prima stesura
        #    teneva una sola transazione per tutto il ciclo, e la PRIMA query che
        #    falliva la lasciava interrotta — da li' in poi PostgreSQL rifiutava
        #    ogni comando, e 39 liste diventavano 300 errori tutti uguali che
        #    nascondevano l'unico difetto vero. Un presidio che si rompe al primo
        #    rosso non dice quanti rossi ci sono.
        with transaction.atomic():
            with connection.execute_wrapper(spia):
                risultato = esercizio.chiama(ob, od)
            transaction.set_rollback(True)

        righe = _righe(risultato)
        # `None` = nessuna riga da guardare, ed e' diverso da «riga senza
        # chiavi»: sul primo si ripiega sulle colonne del cursore, sul secondo
        # ci sarebbe un difetto da dire.
        chiavi = _chiavi_riga(righe[0]) if righe else None
        if chiavi is not None:
            colonne |= chiavi
        return colonne, chiavi

    # 1. Il cancello vero: ogni colonna promessa dal catalogo esiste davvero.
    def test_ogni_campo_sorgente_a_catalogo_arriva_nella_riga(self) -> None:
        mancanti: dict[str, dict[str, Any]] = {}
        fantasmi: dict[str, list[str]] = {}
        provate = 0
        for codice, esercizio in sorted(_ESERCIZI.items()):
            # Contato PRIMA delle verifiche: un fallimento dentro il `subTest`
            # salta il resto del blocco, e un contatore incrementato in fondo
            # farebbe fallire anche il conteggio — due rossi per un difetto
            # solo, e il secondo parla di un'altra cosa.
            provate += 1
            with self.subTest(lista=codice):
                dichiarati = _campi_dichiarati(codice)
                self.assertTrue(
                    dichiarati,
                    f"la lista '{codice}' non dichiara nessun campo_sorgente "
                    "a catalogo: il confronto sarebbe verde a vuoto",
                )
                colonne, chiavi_riga = self._proiezione(esercizio)
                assenti = sorted(
                    dichiarati - colonne - set(esercizio.campi_da_python)
                )
                if assenti:
                    mancanti[codice] = {
                        "colonne": assenti,
                        "query": esercizio.dove,
                    }
                # 1-bis. L'eccezione dichiarata deve restare VERA. Con una riga
                # sotto gli occhi si puo' verificare, e un `campi_da_python` che
                # non esiste piu' e' un permesso di passare rimasto acceso.
                if chiavi_riga is not None and esercizio.campi_da_python:
                    spariti = sorted(set(esercizio.campi_da_python) - chiavi_riga)
                    if spariti:
                        fantasmi[codice] = spariti
        self.assertEqual(provate, len(_ESERCIZI))
        self.assertEqual(
            mancanti,
            {},
            "campo_sorgente a catalogo che la lista NON proietta: a video "
            "sarebbe una colonna VUOTA e un export con l'intestazione e niente "
            "sotto, non un errore",
        )
        self.assertEqual(
            fantasmi,
            {},
            "`campi_da_python` dichiarati in `_ESERCIZI` che la riga vera NON "
            "ha: l'eccezione e' invecchiata e sta coprendo una colonna assente",
        )

    # 2. ⭐ Il verso che ARMA il presidio: il censimento e' il seed, non questo
    #    file. Una lista nuova senza vista trova subito la sua riga rossa.
    def test_il_registro_copre_ogni_lista_senza_vista(self) -> None:
        censite = _liste_senza_vista()
        self.assertGreater(
            len(censite), 1, "censimento delle liste senza vista rotto"
        )
        scoperte = sorted(censite - set(_ESERCIZI) - set(_ESENZIONI))
        self.assertEqual(
            scoperte,
            [],
            "liste con `vista_sql` nullo fuori dal registro: il trigger DB non "
            "le guarda (nessuna vista contro cui validare) e qui non le guarda "
            "nessuno. Aggiungere una riga a `_ESERCIZI` con la chiamata che "
            "esegue la loro query.",
        )

    # 3. Il verso opposto: una riga morta qui nasconde una lista scoperta la'.
    def test_nessun_esercizio_punta_a_una_lista_inesistente(self) -> None:
        codici = {riga["codice"] for riga in _seed("lista_definizione.csv")}
        orfani = sorted(set(_ESERCIZI) - codici)
        self.assertEqual(orfani, [], "esercizi su liste assenti dal catalogo")
        con_vista = sorted(set(_ESERCIZI) - _liste_senza_vista())
        self.assertEqual(
            con_vista,
            [],
            "liste che ORA hanno una vista: le presidia il trigger DB, e la "
            "riga qui va tolta (o il presidio guarda la cosa sbagliata)",
        )

    # 5. Le gemelle di formato sulle liste CON vista: il trigger DB valida il
    #    `campo_sorgente` contro la vista, la gemella no — e il test 1 quelle
    #    liste non le esercita (le presidia il trigger). Si chiede al catalogo.
    # ⚠️ Se nessuna lista con vista dichiara un formato con gemella, il test lo
    #    DICE con uno skip: un giro su zero liste non e' un verde.
    def test_le_gemelle_di_formato_esistono_nella_vista(self) -> None:
        attese = _gemelle_delle_liste_con_vista()
        if not attese:
            self.skipTest("nessuna lista con vista dichiara un formato con gemella")
        mancanti: dict[str, list[str]] = {}
        with transaction.atomic():
            with connection.cursor() as cur:
                for (codice, schema, vista), gemelle in sorted(attese.items()):
                    cur.execute(
                        """
                        SELECT column_name FROM information_schema.columns
                         WHERE table_schema = %s AND table_name = %s
                        """,
                        [schema, vista],
                    )
                    colonne = {r[0] for r in cur.fetchall()}
                    self.assertTrue(
                        colonne, f"la vista {schema}.{vista} della lista '{codice}' non esiste",
                    )
                    assenti = sorted(gemelle - colonne)
                    if assenti:
                        mancanti[codice] = assenti
            transaction.set_rollback(True)
        self.assertEqual(
            mancanti, {},
            "gemella di formato che la VISTA non proietta: il Tag renderebbe "
            "`—` su ogni riga, senza errore",
        )

    # 4. Ogni ordinamento dichiarato produce SQL valido — per intero, non a
    #    campione. Una colonna che il backend riconosce e l'SQL non ha e' un
    #    500 sul click di un'intestazione.
    def test_ogni_ordinamento_dichiarato_produce_sql_valido(self) -> None:
        provate = 0
        senza_whitelist: list[str] = []
        locali: list[str] = []
        for codice, esercizio in sorted(_ESERCIZI.items()):
            whitelist = _whitelist(codice)
            # ⭐ Ordinamento LOCALE: non c'e' niente da provare, e non e' un
            #    buco — e' una proprieta' della lista, dichiarata a registro.
            #    Sta in un ramo suo perche' «non ha whitelist» e «non ordina
            #    lato backend» sono due cose diverse, e confonderle
            #    trasformerebbe una scelta in un debito (o viceversa).
            if whitelist == ORDINAMENTO_LOCALE:
                locali.append(codice)
                continue
            if not whitelist:
                # ⛔ Non un `continue` silenzioso: una lista che sparisce da
                #    `_LISTE` uscirebbe da questo ciclo senza dirlo, e il test
                #    resterebbe verde avendo smesso di provarla.
                senza_whitelist.append(codice)
                continue
            for colonna in whitelist:
                # ⚠️ ENTRAMBI i versi: la direzione finisce nella stessa
                #    clausola SQL della colonna (e con lei la posizione dei
                #    NULL), e un ripiego malformato si vedrebbe su un verso
                #    solo.
                for verso in ("ASC", "DESC"):
                    with self.subTest(lista=codice, colonna=colonna, verso=verso):
                        self._proiezione(esercizio, colonna, verso)
                        provate += 1
        self.assertEqual(
            senza_whitelist,
            [],
            "liste senza vista che non hanno una whitelist di ordinamento a "
            "registro (`_LISTE` di `test_liste_configurabili_seed`): i loro "
            "ordinamenti non li prova nessuno",
        )
        self.assertGreater(
            provate, 0, "nessun ordinamento provato: il raccordo con `_LISTE` e' rotto"
        )
        # Le liste a ordinamento locale ci sono, e restano contate: se un giorno
        # sparissero tutte, il ramo sopra sarebbe morto senza che nessuno lo
        # dica.
        self.assertLessEqual(len(locali), len(_ESERCIZI))
