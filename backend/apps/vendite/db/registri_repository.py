# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from apps.core.db._helpers import (
    sql_order_clause,
    extract_paginated,
    jsonb_out,
    row_to_dict,
    rows_to_list,
)

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
# ⛔ FUORI DA ENTRAMBE: `id`, `uid`, `reset_policy` e `emittente_soggetto_ruolo_id`.
#    `reset_policy` e' inchiodata ad ANNUALE dal CHECK `chk_registri_fatturazione_reset`
#    (e' un FATTO, non un campo); l'emittente lo da' il contesto, non il form.
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
# ⛔ `serie_default` RESTA FUORI dall'update, e non e' una svista. Il guard non
#    la copre (brief §8.1 Q1: entra nella chiave del contatore, e il mirror CSV
#    la riscrive a ogni migrate), quindi un campo editabile su di lei sarebbe
#    l'unico senza presidio. Si LEGGE — la maschera la mostra in sola lettura,
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

# ⭐ I DUE VERBI, LETTI IN UNA QUERY SOLA (brief §9.2, misurato: 9,161 ms
#    sull'intera tabella). Non serve nessuna vista nuova e non si chiamano le
#    check riga per riga dal service.
# ⛔ DUE COLONNE, DUE NOMI: `rimozione_blocco_*` risponde a «posso spegnerlo?»,
#    `forma_blocco_*` a «posso cambiargli la forma del numero?». Su un registro
#    che ha numerato sono spenti ENTRAMBI, per motivi diversi — riusare una
#    colonna per l'altra domanda mostra la frase sbagliata senza che niente
#    fallisca (api.md §12.5.4).
# ⚠️ `LEFT JOIN LATERAL ... ON TRUE` e non `CROSS JOIN`: la check risponde `[]`
#    quando l'azione e' ammessa, e `jsonb_array_elements` su un array vuoto non
#    produce righe. Con un CROSS JOIN quelle righe uscirebbero dalla LISTA —
#    cioe' sparirebbero proprio i registri senza problemi.
# ⚠️ L'ORDINE E' IL CONTRATTO: la madre solleva il PRIMO motivo, e il tooltip
#    deve mostrare quello stesso. Da qui `ORDER BY ord LIMIT 1`.
_LATERAL_BLOCCHI = """
              LEFT JOIN LATERAL (
                  SELECT m.value ->> 'reason'     AS reason,
                         m.value ->> 'reason_key' AS reason_key,
                         m.value -> 'dettaglio'   AS dettaglio
                    FROM jsonb_array_elements(
                             script.fn_check_registro_disattivabile(r.id)
                         ) WITH ORDINALITY AS m(value, ord)
                   ORDER BY m.ord
                   LIMIT 1
              ) rimozione ON TRUE
              LEFT JOIN LATERAL (
                  SELECT m.value ->> 'reason'     AS reason,
                         m.value ->> 'reason_key' AS reason_key,
                         m.value -> 'dettaglio'   AS dettaglio
                    FROM jsonb_array_elements(
                             script.fn_check_registro_forma_modificabile(r.id)
                         ) WITH ORDINALITY AS m(value, ord)
                   ORDER BY m.ord
                   LIMIT 1
              ) forma ON TRUE
"""

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

# Colonne jsonb da decodificare: fuori dall'ORM psycopg 3 consegna i jsonb come
# `str`, e un oggetto servito come stringa arriva al client come testo — che nel
# template non fallisce, si limita a non avere le sue chiavi. E' proprio il
# `dettaglio` da cui il frontend prende i parametri della frase.
_COLONNE_JSONB = ("rimozione_blocco_dettaglio", "forma_blocco_dettaglio")


def _decodifica_jsonb(righe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for riga in righe:
        for col in _COLONNE_JSONB:
            if col in riga:
                riga[col] = jsonb_out(riga[col])
    return righe


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
        limit: int = 25,
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
        pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT {_PROIEZIONE},
                   COUNT(*) OVER () AS total_count
            {_FROM}
            {_LATERAL_BLOCCHI}
             WHERE (%s::bigint[] IS NULL OR r.emittente_soggetto_ruolo_id = ANY(%s))
               AND (%s::bigint IS NULL OR r.emittente_soggetto_ruolo_id = %s)
               AND (%s::text IS NULL OR r.famiglia_documento = %s)
               AND (%s::boolean IS NULL OR r.attivo = %s)
               AND (%s::text IS NULL OR (
                       r.codice ILIKE %s
                    OR r.descrizione ILIKE %s
                    OR r.prefisso ILIKE %s
                   ))
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params: list[Any] = [
            emittenti_sr_ids, emittenti_sr_ids,
            emittente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
            famiglia_documento, famiglia_documento,
            attivo, attivo,
            pattern, pattern, pattern, pattern,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            righe, totale = extract_paginated(cursor)
        return _decodifica_jsonb(righe), totale

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
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [registro_id, emittenti_sr_ids, emittenti_sr_ids])
            riga = row_to_dict(cursor)
        if riga is None:
            return None
        return _decodifica_jsonb([riga])[0]

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
        colonne = [c for c in _CAMPI_CREATE if c in dati]
        campi = ["emittente_soggetto_ruolo_id", *colonne]
        segnaposti = ", ".join(["%s"] * len(campi))
        sql = f"""
            INSERT INTO vendite.registri_fatturazione ({", ".join(campi)})
            VALUES ({segnaposti})
            RETURNING id
        """  # noqa: S608
        params = [emittente_soggetto_ruolo_id, *[dati[c] for c in colonne]]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()[0]

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
        colonne = [c for c in _CAMPI_UPDATE if c in dati]
        if not colonne or (emittenti_sr_ids is not None and not emittenti_sr_ids):
            return 0
        set_sql = ", ".join(f"{c} = %s" for c in colonne)
        sql = f"""
            UPDATE vendite.registri_fatturazione
               SET {set_sql}
             WHERE id = %s
               AND (%s::bigint[] IS NULL OR emittente_soggetto_ruolo_id = ANY(%s))
        """  # noqa: S608
        params = [
            *[dati[c] for c in colonne],
            registro_id, emittenti_sr_ids, emittenti_sr_ids,
        ]
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
