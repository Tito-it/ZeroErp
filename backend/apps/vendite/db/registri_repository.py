# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dei REGISTRI DI NUMERAZIONE (`vendite.registri_fatturazione`)
#        — lista paginata per emittente, dettaglio coi contatori, create/update
#        e il verbo `attivo`. Brief: brief-be-fe-crud-registri-di-numerazione §10.
# ------------------------------------------------------------
#
# ⛔ SOTTODOMINIO SUO, NON `vendite_repository.py`. Quello e' il generico dello
#    schema; i registri hanno regole proprie (le due specie di registro, i sei
#    guard di disattivazione, il guard sulla forma del numero) ed e' la stessa
#    scelta gia' fatta per `resi_repository` e `ddt_repository`.
#
# ⛔ SU QUESTA TABELLA NON C'E' LA RLS (riverificato 2026-09-01). Lo scope
#    emittente e' interamente a carico del BACKEND: chi legge senza filtrare
#    vede i registri di tutti gli emittenti. Il filtro si applica QUI, su
#    `emittente_soggetto_ruolo_id` — la colonna soggetto-ruolo, NON la PK
#    dell'emittente fiscale (`feedback_emittente_pk_vs_soggetto_ruolo`).
#
# ⚠️ LA SEMANTICA DELLO SCOPE HA TRE VALORI, NON DUE, ed e' quella di
#    `PermissionResolver`: `None` = nessuna restrizione, `[]` = NESSUN accesso,
#    lista piena = quegli emittenti. ⛔ Trattare `None` come «vuoto» spegnerebbe
#    la pagina all'operatore senza restrizioni; trattare `[]` come «tutti»
#    aprirebbe l'intera tabella a chi non ha accesso a niente — e nessuno dei
#    due fallisce, entrambi mostrano una lista plausibile. Da qui il tipo
#    esplicito `list[int] | None` su OGNI metodo, e il ramo `[] -> vuoto`
#    scritto per primo.

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    sql_lateral_primo_motivo,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# `vendite.registri_numerazione` (e' quello che <ListaConfigurabile> invia come
# sortField), valore = espressione SQL qualificata.
# ⛔ Whitelist e non passaggio diretto: il valore arriva dal client e finisce
#    in un ORDER BY, che non e' parametrizzabile.
_ORDER_COLS: dict[str, str] = {
    "codice": "r.codice",
    "descrizione": "r.descrizione",
    "famiglia_documento": "r.famiglia_documento",
    "famiglia_descrizione": "fd.descrizione",
    "utility_codice": "u.codice",
    "prefisso": "r.prefisso",
    "suffisso": "r.suffisso",
    "lunghezza_numero": "r.lunghezza_numero",
    "serie_default": "r.serie_default",
    "attivo": "r.attivo",
    "data_insert": "r.data_insert",
}
_ORDER_DEFAULT = "codice"

# Colonne scrivibili, per verbo.
#
# ⛔ FUORI DA ENTRAMBE: `id`, `uid` e `emittente_soggetto_ruolo_id`.
#    L'emittente lo da' il contesto, non il form.
#
# ⭐ `reset_policy` E' IN CREATE E NON IN UPDATE, dal 2026-09-08.
#    ⚠️ Qui c'era scritto che era «inchiodata ad ANNUALE dal CHECK
#    `chk_registri_fatturazione_reset` (e' un FATTO, non un campo)», e quella
#    frase e' SCADUTA IL GIORNO STESSO IN CUI E' STATA SCRITTA: il changeSet
#    `20260901-06` ha allargato quel CHECK a ANNUALE **e** NESSUNA, e
#    `fn_get_next_progressivo` ramifica davvero (sotto NESSUNA il secchio del
#    contatore e' uno solo e vale 0). Restava un divieto APPLICATIVO motivato
#    con un vincolo che non esisteva piu' — cioe' un parametro acceso nel
#    database e irraggiungibile dall'applicazione, lo specchio esatto del
#    difetto che il cantiere esiste per togliere: cio' che il documento afferma
#    deve corrispondere a cio' che il database ammette.
#    ⛔ IN UPDATE NO — ma ⚠️ ATTENZIONE ALLA RAGIONE, perche' quella di questa
#    riga e' gia' cambiata una volta. Fino al 2026-09-08 qui c'era scritto che
#    cambiarla «sposta il secchio, il progressivo riparte da 1 e sbatte contro i
#    numeri gia' scritti». Era vero, e il team DB lo ha **riparato**: col
#    changeSet `20260908-10` un secchio appena nato non parte piu' da zero, ma
#    dal massimo di quelli con cui i suoi documenti possono collidere.
#    ⭐ Decisione di Tid (brief chiave-del-contatore §11.7): *si ripara il
#    MECCANISMO, non si vieta il cambio*. Il guasto non c'e' piu', quindi non e'
#    piu' lui a tenere la politica fuori dall'update.
#    ⇒ La ragione VERA, ed e' quella del §11.7: la politica si sceglie ALLA
#    NASCITA (BE-R1), che e' l'unico momento in cui non c'e' nessun secchio da
#    innescare. Il seme del `20260908-10` e' la RETE, non la strada principale.
#    ⛔ E NON e' «la stessa famiglia di guasti di `serie_default`»: quella frase
#    stava qui ed era sbagliata: la serie va nel verso innocuo (vedi sotto).
#
# ⭐ I TRE CAMPI DI FORMA SONO IN UPDATE, ed e' una decisione del 2026-09-01.
#    Il brief li teneva fuori come «ripiego prudente in attesa che il criterio
#    nasca dove sta il rifiuto», con la data di scadenza dentro: «il giorno che
#    il guard esiste si aprono». Il guard esiste — `trg_registri_fatturazione_
#    a10_guard_forma_numero_upd`, applicato il 2026-09-01 — e a rifiutare e' il
#    database sul registro che ha gia' consegnato un numero. Tenerli fuori
#    adesso sarebbe un divieto APPLICATIVO accanto a uno di DATABASE: il secondo
#    elenco parallelo che tutto il cantiere esiste per non avere.
#
# ⛔ `serie_default` RESTA FUORI dall'update — ⚠️ e la ragione che stava qui era
#    SBAGLIATA. Diceva «il guard non la copre, quindi sarebbe l'unico campo
#    senza presidio»: il BE l'aveva segnalata come lacuna, e il team DB ha
#    risposto che il fatto era esatto e la conclusione no (§11.9, 2026-09-08).
#    ⭐ NON MANCA UN PRESIDIO: NON SERVE. Cambiare la serie non crea due forme
#    sullo stesso numero come farebbe la forma del numero — apre una SEQUENZA
#    NUOVA, che riparte da 1 e non collide con niente, perche' la serie sta
#    nella chiave di unicita' del documento
#    (`uq_fatture_numero (registro_id, anno, COALESCE(serie,''), numero)`, e
#    uguale su DDT e ordini). E' l'asimmetria dell'invariante nel verso INNOCUO:
#    il documento porta l'asse.
#    ⛔ Congelarla con un trigger vieterebbe un'operazione LEGITTIMA — spostare
#    un sezionale su una serie nuova — ed e' il motivo per cui quel trigger non
#    e' stato scritto.
#    🔭 Resta quindi fuori dall'update come SCELTA DI PERIMETRO, non per
#    mancanza di un guard: aprirla e' una decisione disponibile, non un rischio
#    da evitare. (Su resi e commesse non si pone: il guard
#    `trg_..._guard_serie_ammessa_ins_upd` vieta del tutto di avere una serie.) Si LEGGE — la maschera la mostra in sola lettura,
#    perche' spiega da dove viene la serie dei numeri — ma non si scrive.
_CAMPI_CREATE: tuple[str, ...] = (
    "codice",
    "descrizione",
    "famiglia_documento",
    "utility_id",
    "serie_default",
    "politica_data_documento",
    "limite_emissione_giorni",
    "limite_emissione_giorno_mese",
    "prefisso",
    "suffisso",
    "lunghezza_numero",
    "reset_policy",
)
_CAMPI_UPDATE: tuple[str, ...] = (
    "codice",
    "descrizione",
    "politica_data_documento",
    "limite_emissione_giorni",
    "limite_emissione_giorno_mese",
    "prefisso",
    "suffisso",
    "lunghezza_numero",
)

# ⛔ PREFISSO E SUFFISSO NON SI STRIPPANO (2026-09-26, migrazione ai BB core di
#    scrittura, che strippano ogni stringa). Sono PEZZI DEL NUMERO stampato:
#    `"FT "` + `"12"` e' una forma, `"FT"` + `"12"` e' un'altra — uno spazio
#    ai bordi e' contenuto, non rumore, e toglierlo in silenzio cambierebbe
#    la numerazione senza che l'operatore l'abbia chiesto. Le altre stringhe
#    (codice, descrizione, serie...) si strippano come ovunque.
_CAMPI_LETTERALI: tuple[str, ...] = ("prefisso", "suffisso")

# ⭐ I DUE VERBI, LETTI IN UNA QUERY SOLA (brief §9.2, misurato: 9,161 ms
#    sull'intera tabella). Non serve nessuna vista nuova e non si chiamano le
#    check riga per riga dal service.
# ⛔ DUE COLONNE, DUE NOMI: `rimozione_blocco_*` risponde a «posso spegnerlo?»,
#    `forma_blocco_*` a «posso cambiargli la forma del numero?». Su un registro
#    che ha numerato sono spenti ENTRAMBI, per motivi diversi — riusare una
#    colonna per l'altra domanda mostra la frase sbagliata senza che niente
#    fallisca (api.md §12.5.4).
# ⭐ Il frammento e' il BB `sql_lateral_primo_motivo` (core/db, 2026-09-19):
#    LEFT JOIN … ON TRUE (non CROSS: le righe ammesse non devono sparire) e
#    `ORDER BY ord LIMIT 1` (il PRIMO motivo, lo stesso che la madre solleva).
_LATERAL_BLOCCHI = (
    sql_lateral_primo_motivo("script.fn_check_registro_disattivabile(r.id)", "rimozione")
    + sql_lateral_primo_motivo("script.fn_check_registro_forma_modificabile(r.id)", "forma")
)

_PROIEZIONE = """
                   r.id,
                   r.uid,
                   r.codice,
                   r.descrizione,
                   r.famiglia_documento,
                   fd.descrizione                 AS famiglia_descrizione,
                   r.emittente_soggetto_ruolo_id,
                   r.utility_id,
                   u.codice                       AS utility_codice,
                   u.descrizione                  AS utility_descrizione,
                   r.serie_default,
                   r.reset_policy,
                   r.politica_data_documento,
                   r.limite_emissione_giorni,
                   r.limite_emissione_giorno_mese,
                   r.prefisso,
                   r.suffisso,
                   r.lunghezza_numero,
                   -- ⭐ L'anno entra nella STRINGA del numero (2026-09-08). Non
                   --    e' scrivibile da qui: lo decide un risolutore a INSERT
                   --    (`trg_..._set_anno_nel_numero_ins`) dal default della
                   --    famiglia. Si legge perche' cambia il numero che una
                   --    persona vede — senza, l'anteprima in maschera mostra
                   --    una stringa che il documento non avra' mai.
                   r.anno_nel_numero,
                   r.attivo,
                   r.data_insert,
                   r.data_update,
                   rimozione.reason               AS rimozione_blocco_reason,
                   rimozione.reason_key           AS rimozione_blocco_reason_key,
                   rimozione.dettaglio            AS rimozione_blocco_dettaglio,
                   (rimozione.reason IS NULL)     AS can_disattivare,
                   forma.reason                   AS forma_blocco_reason,
                   forma.reason_key               AS forma_blocco_reason_key,
                   forma.dettaglio                AS forma_blocco_dettaglio,
                   (forma.reason IS NULL)         AS can_cambiare_forma
"""

# ⭐ Display field via JOIN, non lookup client-side (`feedback_display_fields_backend`).
#    La famiglia porta la sua `descrizione` di catalogo perche' e' il RIPIEGO del
#    client su una famiglia che non ha ancora la sua chiave i18n: il vocabolario
#    di `vendite.famiglie_documento` e' APERTO, una famiglia nuova arriva con un
#    seed e non con un rilascio del frontend.
_FROM = """
              FROM vendite.registri_fatturazione r
              LEFT JOIN vendite.famiglie_documento fd ON fd.codice_interno = r.famiglia_documento
              LEFT JOIN config.utilities u            ON u.id     = r.utility_id
"""

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
_RICERCA = RicercaFull("vendite.registri_numerazione", ("codice", "descrizione", "prefisso"))


class RegistriRepository:
    """Accesso DB ai registri di numerazione."""

    # =================================================================
    # Lettura
    # =================================================================

    # Scopo: lista paginata dei registri, filtrata sugli emittenti che
    #        l'operatore puo' vedere.
    # ⛔ `emittenti_sr_ids` NON e' opzionale e NON ha un default che significhi
    #    «tutti»: senza RLS un default permissivo sarebbe una fuga di dati che
    #    non fallisce mai. Una lista vuota deve dare zero righe, non tutte.
    def list_registri(
        self,
        emittenti_sr_ids: list[int] | None,
        *,
        emittente_soggetto_ruolo_id: int | None = None,
        famiglia_documento: str | None = None,
        attivo: bool | None = None,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = _ORDER_DEFAULT,
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        if emittenti_sr_ids is not None and not emittenti_sr_ids:
            return [], 0
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS[_ORDER_DEFAULT],
            tiebreak="r.id",
        )
        conditions: list[str] = [
            "(%s::bigint[] IS NULL OR r.emittente_soggetto_ruolo_id = ANY(%s))",
            "(%s::bigint IS NULL OR r.emittente_soggetto_ruolo_id = %s)",
            "(%s::text IS NULL OR r.famiglia_documento = %s)",
            "(%s::boolean IS NULL OR r.attivo = %s)",
        ]
        params: list[Any] = [
            emittenti_sr_ids, emittenti_sr_ids,
            emittente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
            famiglia_documento, famiglia_documento,
            attivo, attivo,
        ]
        # Soglia della ricerca: la dichiara il catalogo della lista
        # (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA, alias="r")
        sql = f"""
            SELECT {_PROIEZIONE},
                   COUNT(*) OVER () AS total_count
            {_FROM}
            {_LATERAL_BLOCCHI}
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        righe, totale = fetch_paged_with_total(sql, params, offset=offset)
        return righe, totale

    # Scopo: il dettaglio di un registro, con lo scope applicato.
    #        Torna None se non esiste O se e' fuori perimetro — che al chiamante
    #        sono la stessa cosa e devono restarlo: distinguere «non c'e'» da
    #        «non e' tuo» racconta l'esistenza di un registro altrui.
    def get_registro(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
    ) -> dict[str, Any] | None:
        if emittenti_sr_ids is not None and not emittenti_sr_ids:
            return None
        sql = f"""
            SELECT {_PROIEZIONE}
            {_FROM}
            {_LATERAL_BLOCCHI}
             WHERE r.id = %s
               AND (%s::bigint[] IS NULL OR r.emittente_soggetto_ruolo_id = ANY(%s))
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [registro_id, emittenti_sr_ids, emittenti_sr_ids])
            riga = row_to_dict(cursor)
        if riga is None:
            return None
        return riga

    # Scopo: i CONTATORI del registro, in SOLA LETTURA (brief §BE-4).
    # ⛔ Non esiste — e non deve nascere — nessun metodo di scrittura su questa
    #    tabella. Cambiare `last_numero` a mano significa riassegnare un numero
    #    gia' uscito, cioe' produrre due documenti con lo stesso numero sullo
    #    stesso sezionale: il difetto che l'intero cantiere del trasloco esiste
    #    per rendere impossibile. Se un giorno servira', sara' un verbo di
    #    dominio con la sua ragione e il suo audit, non un campo in un form.
    def list_progressivi(self, registro_id: int) -> list[dict[str, Any]]:
        # ⛔ NIENTE `mese`, ED E' UNA CORREZIONE. La doc auto-generata di
        #    `registri_fatturazione_progressivi` elenca ancora la colonna, il
        #    suo CHECK e la sua presenza in `uq_regprog_key` — ma sul database
        #    vivo (verificato 2026-09-01) NON ESISTE PIU': il team DB l'ha
        #    tolta, come il §8.1 Q1 del brief annunciava («dormiente e senza
        #    nessun documento che la porti, si toglie»), e l'auto-gen non e'
        #    stata rigenerata. La chiave del contatore e' oggi
        #    `(registro_id, anno, serie)`.
        # ⚠️ Il difetto NON si vede nei test: un mock del cursore accetta
        #    qualunque SQL. Si e' visto alla prima chiamata vera.
        sql = """
            SELECT p.anno, p.serie, p.last_numero, p.ultima_data, p.attivo
              FROM vendite.registri_fatturazione_progressivi p
             WHERE p.registro_id = %s
             -- `serie` e' NOT NULL (default ''), quindi niente NULLS FIRST/LAST.
             ORDER BY p.anno DESC, p.serie
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [registro_id])
            return rows_to_list(cursor)

    # =================================================================
    # Scrittura
    # =================================================================

    # Scopo: crea un registro per l'emittente dato e ne ritorna l'id.
    # ⚠️ L'emittente NON viene dal payload: lo passa il chiamante dal contesto
    #    (il tab e' dentro il drawer di UN emittente). Un emittente scelto nel
    #    form sarebbe un secondo modo di sbagliare perimetro.
    def create_registro(
        self,
        emittente_soggetto_ruolo_id: int,
        dati: dict[str, Any],
    ) -> int:
        # ⭐ BB core `execute_dynamic_insert` (2026-09-26): la whitelist e'
        #    RIGIDA — una chiave fuori `_CAMPI_CREATE` e' `RuntimeError`, non
        #    piu' uno scarto silenzioso. Il 400 educato lo da' il service
        #    (`_verifica_chiavi`), che il contratto lo controlla prima.
        # ⚠️ L'emittente si scrive PER ULTIMO nel dict: e' quello del
        #    contesto, e nessuna chiave del payload lo puo' sovrascrivere.
        riga = execute_dynamic_insert(
            "vendite.registri_fatturazione",
            {**dati, "emittente_soggetto_ruolo_id": emittente_soggetto_ruolo_id},
            allowed=("emittente_soggetto_ruolo_id", *_CAMPI_CREATE),
            letterali=_CAMPI_LETTERALI,
        )
        return riga["id"]

    # Scopo: aggiorna le colonne ammesse. Ritorna il numero di righe toccate,
    #        cosi' il service distingue «non esiste / fuori perimetro» da «fatto».
    # ⚠️ Un update senza colonne ammesse NON diventa un UPDATE vuoto: sarebbe
    #    SQL non valido, e per di piu' toccherebbe `data_update` per niente.
    def update_registro(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
        dati: dict[str, Any],
    ) -> int:
        if not dati or (emittenti_sr_ids is not None and not emittenti_sr_ids):
            return 0
        # ⭐ BB core `sql_set_clause` (2026-09-26): il WHERE resta qui perche'
        #    porta lo SCOPE emittente, che `execute_dynamic_update` (WHERE id e
        #    basta) non sa scrivere. Whitelist RIGIDA: una chiave fuori
        #    `_CAMPI_UPDATE` e' `RuntimeError` — il service l'ha gia' rifiutata
        #    con un 400 (`_verifica_chiavi`).
        set_sql, params = sql_set_clause(
            dati, allowed=_CAMPI_UPDATE, letterali=_CAMPI_LETTERALI,
        )
        sql = f"""
            UPDATE vendite.registri_fatturazione
               SET {set_sql}
             WHERE id = %s
               AND (%s::bigint[] IS NULL OR emittente_soggetto_ruolo_id = ANY(%s))
        """  # noqa: S608 — set_sql dal BB sql_set_clause (colonne in whitelist _CAMPI_UPDATE, valori come parametri)
        params += [registro_id, emittenti_sr_ids, emittenti_sr_ids]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: accende o spegne il registro — un verbo suo, non un PATCH generico.
    # ⛔ Lo spegnimento e' presidiato da SEI trigger di disattivazione, cinque
    #    dei quali sull'ESISTENZA dei figli e non sulle righe attive: qui non si
    #    ricontrolla niente, si lascia rifiutare il database e si traduce il
    #    codice. Un controllo applicativo sarebbe il settimo elenco.
    def set_attivo(
        self,
        registro_id: int,
        emittenti_sr_ids: list[int] | None,
        attivo: bool,
    ) -> int:
        if emittenti_sr_ids is not None and not emittenti_sr_ids:
            return 0
        sql = """
            UPDATE vendite.registri_fatturazione
               SET attivo = %s
             WHERE id = %s
               AND (%s::bigint[] IS NULL OR emittente_soggetto_ruolo_id = ANY(%s))
               AND attivo IS DISTINCT FROM %s
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [attivo, registro_id, emittenti_sr_ids, emittenti_sr_ids, attivo],
            )
            return cursor.rowcount
