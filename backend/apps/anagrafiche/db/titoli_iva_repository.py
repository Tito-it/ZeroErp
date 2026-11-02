# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per i TITOLI IVA del soggetto (I7 / D10 di
#        brief-db-be-iva-risolutore-e-regime-cliente): la sede del documento che
#        SOSTITUISCE l'aliquota ordinaria di una riga.
#        Copre le tre tabelle della famiglia:
#          - anagrafiche.soggetti_titoli_iva            il titolo
#          - anagrafiche.soggetti_titoli_iva_ambiti     dove si applica (D12)
#          - anagrafiche.soggetti_titoli_iva_movimenti  il registro di D5
#
# 🔴 PROPRIETARIO il soggetto, DESTINATARIO l'emittente, due colonne sulla stessa
#    riga (D10-bis): lo stesso esportatore abituale che compra da due societa'
#    emittenti presenta DUE dichiarazioni, ognuna col suo plafond. Senza la
#    seconda colonna i due plafond si consumerebbero da un contatore solo — un
#    errore silenzioso su precisamente il numero che l'Agenzia delle Entrate
#    verifica.
#
# ⚠️ LA RLS FA GIA' IL PERIMETRO EMITTENTE, e qui NON si ri-filtra in Python:
#    le tre tabelle hanno una policy su `script.fn_scope_ef_whitelist(user,
#    emittente_fiscale_id)`. Aggiungere un secondo filtro applicativo darebbe due
#    verita' sullo stesso perimetro, e la piu' debole vincerebbe in silenzio il
#    giorno che divergono.
#    📌 Ne discende una regola per i test: un conteggio senza contesto operatore
#    torna ZERO e sembra un dato (`feedback_rls_conteggio_zero_non_e_un_dato`).
#
# ⚠️ `imponibile_utilizzato` SI LEGGE, non si ricalcola: e' il trigger
#    `trgfn_soggetti_titoli_iva_movimenti_accumulatore` a tenerlo pari alla somma
#    del registro dopo ogni scrittura (D5). Ri-sommare le righe qui creerebbe una
#    seconda verita' sullo stesso numero — esattamente il difetto che D5 esiste
#    per evitare.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection


from apps.core.db._helpers import (
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update

# Display field via JOIN (`feedback_display_fields_backend`): il frontend riceve
# le descrizioni gia' risolte e non fa lookup client-side.
_TITOLO_COLS = """
                   t.id,
                   t.soggetto_id,
                   t.emittente_fiscale_id,
                   ef.codice                       AS emittente_codice,
                   s_ef.ragione_sociale_completa   AS emittente_ragione_sociale,
                   t.tipo_titolo_iva_id,
                   tt.codice_interno               AS tipo_codice_interno,
                   tt.descrizione                  AS tipo_descrizione,
                   tt.ha_plafond                   AS tipo_ha_plafond,
                   t.iva_id,
                   iva.codice                      AS iva_codice,
                   iva.descrizione                 AS iva_descrizione,
                   t.ambito,
                   t.valido_dal,
                   t.valido_al,
                   t.protocollo,
                   t.data_ricezione,
                   t.riferimento,
                   t.plafond,
                   t.imponibile_utilizzato,
                   -- Residuo = tetto - imponibile gia' applicato (Q4, precisata
                   -- da Tid il 2026-08-29). NULL sui tipi senza tetto: li' il
                   -- residuo non significa niente, e uno zero sembrerebbe un
                   -- plafond esaurito.
                   CASE WHEN t.plafond IS NOT NULL
                        THEN t.plafond - t.imponibile_utilizzato
                   END                             AS residuo,
                   t.attivo,
                   t.note,
                   -- Quante righe di ambito ha il titolo. ⭐ Sta QUI e non in una
                   -- query per titolo: il service deve dire «RISTRETTO senza
                   -- righe» (Q2) su OGNI riga della lista, e chiederlo a giro
                   -- sarebbe un N+1 che cresce con l'anagrafica.
                   (SELECT count(*)
                      FROM anagrafiche.soggetti_titoli_iva_ambiti a
                     WHERE a.titolo_iva_id = t.id)  AS ambiti_count"""

# ⛔ Whitelist di ordinamento della lista sfondati, CHIAVATA SUL
#    `campo_sorgente` e non sul codice logico: `<ListaConfigurabile>` monta le
#    Column con `:field="col.campo_sorgente"`, quindi `event.sortField` porta il
#    nome FISICO. Chiavarla sui codici logici romperebbe proprio le colonne dove
#    i due divergono — difetto trovato su `vendite.lotti` il 2026-07-31.
# ⚠️ `eccedenza` non e' una colonna di tabella: e' l'espressione che da' senso a
#    questa lista, esposta come alias e ordinabile come le altre.
_ORDER_COLS_SFONDATI: dict[str, str] = {
    "soggetto_ragione_sociale": "sog.ragione_sociale_completa",
    "soggetto_id_fiscale": "sog.id_fiscale_univoco_cf_piva",
    "tipo_descrizione": "tt.descrizione",
    "emittente_ragione_sociale": "s_ef.ragione_sociale_completa",
    "plafond": "t.plafond",
    "imponibile_utilizzato": "t.imponibile_utilizzato",
    "eccedenza": "(t.imponibile_utilizzato - t.plafond)",
}

# Colonne ordinabili del REGISTRO MOVIMENTI di un titolo (lista 65).
# ⛔ Chiavata sui `campo_sorgente` FISICI — stessa regola delle due gemelle qui
#    sopra. Le quattro chiavi sono esattamente le colonne che il seed dichiara
#    `ordinabile = t` (righe 706/707/708/710): una in piu' sarebbe una capacita'
#    che l'operatore non puo' raggiungere, una in meno una freccia che non fa
#    quello che promette.
# ⚠️ `documento` NON c'e' ed e' giusto: a catalogo non ha `campo_sorgente` —
#    la cella la compone il frontend da `fattura_id` — quindi non esiste una
#    colonna SQL per cui ordinare.
_ORDER_COLS_MOVIMENTI: dict[str, str] = {
    "data_movimento": "m.data_movimento",
    "tipo_movimento": "m.tipo_movimento",
    "imponibile": "m.imponibile",
    "motivo": "m.motivo",
}

# ⭐ Le colonne DATA della lista 65: il BB `sql_order_clause` le ordina DESC
#    quando il chiamante non indica un verso — «gli ordinamenti per data hanno
#    sempre default DESC» (Tid, 2026-09-02).
# ⚠️ Accanto alla whitelist e non altrove: e' un sottoinsieme delle sue chiavi,
#    e a distanza le due si separerebbero senza che niente lo dica.
_ORDER_COLONNE_DATA_MOVIMENTI: frozenset[str] = frozenset({"data_movimento"})

_TITOLO_JOINS = """
              FROM anagrafiche.soggetti_titoli_iva t
              JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
              JOIN config.iva iva ON iva.id = t.iva_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t.emittente_fiscale_id
              JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id"""

# FROM + WHERE dei titoli di UN soggetto, condiviso fra la pagina e il conteggio
# di ripiego. ⛔ Una copia sola: due predicati scritti due volte divergono, e il
# giorno che divergono il totale racconta una popolazione diversa da quella
# mostrata — senza che niente fallisca.
_TITOLI_SOGGETTO_FROM_WHERE = f"""
              {_TITOLO_JOINS}
             WHERE t.soggetto_id = %s::uuid"""

# Colonne ordinabili dei TITOLI DI UN SOGGETTO (lista 62).
# ⛔ Chiavata sui `campo_sorgente` FISICI — vedi la nota gemella su
#    `_ORDER_COLS_SFONDATI`. Prima di questa modifica il metodo IGNORAVA
#    `order_by`: la freccia si girava sopra righe immobili, senza un 400 a dirlo.
# ⚠️ `residuo` NON e' una colonna della tabella: e' un `CASE WHEN plafond IS NOT
#    NULL THEN plafond - imponibile_utilizzato END` calcolato dalla SELECT, che
#    vale **NULL** sui tipi senza tetto. Si ordina per l'ALIAS di output —
#    PostgreSQL lo ammette in `ORDER BY` — e non per una sottrazione riscritta a
#    mano: quella darebbe un numero anche dove il residuo non significa niente, e
#    l'elenco si ordinerebbe **diversamente da come si legge**.
_ORDER_COLS_TITOLI_SOGGETTO: dict[str, str] = {
    "tipo_descrizione": "tt.descrizione",
    "emittente_ragione_sociale": "s_ef.ragione_sociale_completa",
    "iva_codice": "iva.codice",
    "residuo": "residuo",
}

# Ordinamento di DEFAULT della lista di presidio: la piu' grave per prima.
# ⭐ E' una costante e non una stringa scritta due volte: la view la passa come
#    `default_order` e il repository la usa come fallback del lookup. Con due
#    letterali, rinominare la chiave avrebbe lasciato la view a chiedere una
#    colonna che la whitelist non conosce piu'.
SFONDATI_ORDER_DEFAULT = "eccedenza"

# Perimetro della lista di presidio, in UN posto solo: lo condividono la pagina
# e il conteggio, che altrimenti potrebbero divergere in silenzio.
# ⚠️ FROM **e** WHERE insieme, non solo il WHERE: i join sono INNER e possono
#    togliere righe, quindi anche loro fanno parte del perimetro. Estrarne meta'
#    lascia l'altra meta' libera di divergere — ed e' esattamente cio' che il
#    conteggio non deve poter fare rispetto alla pagina.
_SFONDATI_FROM_WHERE = f"""
              {_TITOLO_JOINS}
              JOIN anagrafiche.soggetti sog ON sog.id = t.soggetto_id
             WHERE tt.ha_plafond IS TRUE
               AND t.plafond IS NOT NULL
               AND t.imponibile_utilizzato > t.plafond"""


# Colonne scrivibili del titolo.
# ⛔ `emittente_fiscale_id` NON c'e', ed e' la decisione Q5: spostarlo
#    sposterebbe sotto un altro fornitore anche il plafond gia' consumato, perche'
#    i movimenti sono attaccati al TITOLO, non all'emittente. Chi ha sbagliato
#    destinatario disattiva e ne registra un altro — che e' anche la traccia
#    giusta.
# ⛔ `imponibile_utilizzato` NON c'e' e non ci sara': lo scrive il trigger
#    dell'accumulatore. E' la colonna che D5 ha voluto memorizzata E non
#    scrivibile a mano.
_TITOLO_UPDATE_COLS: tuple[str, ...] = (
    "tipo_titolo_iva_id",
    "iva_id",
    "ambito",
    "valido_dal",
    "valido_al",
    "protocollo",
    "data_ricezione",
    "riferimento",
    "plafond",
    "attivo",
    "note",
)
# In create si scrivono anche le due chiavi del padre (immutabili dopo, Q5).
_TITOLO_CREATE_COLS: frozenset[str] = frozenset(
    ("soggetto_id", "emittente_fiscale_id", *_TITOLO_UPDATE_COLS)
)

_AMBITO_COLS = """
                   a.id,
                   a.titolo_iva_id,
                   a.livello,
                   a.articolo_id,
                   art.descrizione                 AS articolo_descrizione,
                   art.codice                      AS articolo_codice,
                   a.gruppo_voce_id,
                   gv.descrizione                  AS gruppo_voce_descrizione,
                   a.tipo_voce_id,
                   tv.descrizione                  AS tipo_voce_descrizione,
                   a.note"""

# FROM + WHERE degli ambiti di UN titolo, condiviso fra la pagina e il conteggio
# di ripiego. ⛔ Una copia sola: due predicati scritti due volte divergono, e il
# giorno che divergono il totale racconta una popolazione diversa da quella
# mostrata — su una lista non paginata, dove il totale E' la promessa che le
# righe siano tutte, e' il difetto peggiore possibile.
# ⚠️ I JOIN sono LEFT e quindi non tolgono righe: qui il perimetro lo fa la sola
#    `WHERE`. Restano nel frammento condiviso lo stesso, perche' il giorno che
#    uno diventasse INNER il conteggio deve seguirlo da se'.
_AMBITI_FROM_WHERE = """
              FROM anagrafiche.soggetti_titoli_iva_ambiti a
              LEFT JOIN catalogo.articoli art ON art.id = a.articolo_id
              LEFT JOIN vendite.articoli_gruppi gv ON gv.id = a.gruppo_voce_id
              LEFT JOIN vendite.articoli_tipologie tv ON tv.id = a.tipo_voce_id
             WHERE a.titolo_iva_id = %s"""

_MOVIMENTO_COLS = """
                   m.id,
                   m.titolo_iva_id,
                   m.tipo_movimento,
                   m.imponibile,
                   m.data_movimento,
                   m.fattura_id,
                   m.fattura_riga_id,
                   m.motivo,
                   m.annulla_movimento_id,
                   m.annullato_da_movimento_id,
                   m.is_annullo,
                   m.is_annullato,
                   m.annullo_blocco_codice,
                   m.annullo_blocco_reason_key,
                   m.data_insert,
                   m.user_insert"""

# FROM + WHERE del registro di UN titolo, condiviso fra la pagina e il conteggio
# di ripiego. ⭐ Si legge la VISTA e non la tabella (T3-b): e' li' che vivono il
# legame dell'annullo nei due versi e il motivo del blocco.
_MOVIMENTI_FROM_WHERE = """
              FROM anagrafiche.vw_stiva_movimenti_dettaglio m
             WHERE m.titolo_iva_id = %s"""


class TitoliIvaRepository:
    """Accesso DB per titoli IVA del soggetto, ambiti e registro movimenti."""

    # =================================================================
    # Tipi di titolo ammessi per il soggetto (lookup)
    # =================================================================

    # Scopo: I tipi di titolo IVA attivi che la natura del soggetto ammette,
    #        con `ha_plafond` (il drawer mostra il tetto solo dove esiste).
    # ⭐ Il filtro e' il PREDICATO DEL GUARD, `anagrafiche.fn_titolo_iva_ammesso`
    #    (brief-db-dati-fiscali-e-societari-del-soggetto, parte D): nessuna riga
    #    di matrice = nessun tipo ammesso, soggetto senza natura = nessun tipo.
    #    E' una comodita' del form: la regola resta in
    #    `trgfn_soggetti_titoli_iva_guard_tipo_soggetto`.
    # ⚠️ Un soggetto inesistente torna la lista vuota, non un 404: e' un lookup.
    def list_tipi_ammessi_soggetto(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT tt.id, tt.codice, tt.codice_interno, tt.descrizione,
                   tt.attivo, tt.ha_plafond
              FROM config.tipi_titolo_iva tt
              JOIN anagrafiche.soggetti s ON s.id = %s::uuid
             WHERE tt.attivo
               AND anagrafiche.fn_titolo_iva_ammesso(tt.id, s.tipo_soggetto_dettaglio_id)
             ORDER BY tt.ordine, tt.descrizione, tt.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # =================================================================
    # Titoli
    # =================================================================

    # Scopo: UNA pagina dei titoli IVA di un soggetto PIU' il totale, in una
    #        valutazione sola (`COUNT(*) OVER()` via `fetch_paged_with_total`).
    #
    # ⭐ Era una `list_` piu' una `count_` separata (2026-09-02), ed e' stata
    #    unificata al primo consumatore che ha chiesto le pagine: due
    #    valutazioni dello stesso predicato possono NON concordare se una riga
    #    entra fra l'una e l'altra, e il totale racconterebbe una popolazione
    #    diversa da quella mostrata. Stessa forma di `list_titoli_sfondati`.
    #
    # ⚠️ `limit=None` = «tutte le righe», e serve al SECONDO consumatore:
    #    `soggetti_service` incorpora i titoli nel dettaglio del soggetto e non
    #    impagina. Il totale torna lo stesso — con `limit` assente coincide col
    #    numero di righe, ma resta la stessa query e la stessa promessa.
    #
    # ⚠️ `fallback_count_sql` serve al rientro su una pagina STANTIA: con
    #    `offset > 0` e zero righe la window function non ha nulla su cui
    #    contare, e senza fallback la schermata direbbe «nessun titolo» a chi e'
    #    solo rimasto su una pagina che si e' accorciata sotto di lui.
    def list_titoli_soggetto(
        self,
        soggetto_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        # ⭐ Senza `order_by` resta l'ordinamento STORICO — validita' piu' lunga
        #    per prima, con `COALESCE(valido_al,'infinity')` che porta in cima i
        #    titoli senza scadenza (`feedback_ordinamento_validita_infinity`).
        #    ⚠️ Va preservato perche' questo metodo ha un SECONDO consumatore:
        #    `soggetti_service` lo incorpora nel dettaglio di un soggetto e non
        #    passa nessun ordinamento. Cambiargli il default sotto i piedi
        #    riordinerebbe una sezione che nessuno sta toccando.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_TITOLI_SOGGETTO,
            # ⚠️ `default_clause` e non `default`: questo ordinamento di
            #    partenza ha DUE criteri e porta le direzioni dentro di se'.
            #    Passarlo come colonna gli farebbe appiccicare una seconda
            #    direzione in coda (`DESC DESC`), che PostgreSQL rifiuta.
            default_clause=(
                "COALESCE(t.valido_al, 'infinity'::date) DESC, t.valido_dal DESC"
            ),
            tiebreak="t.id",
            default_desc=True,
        )
        # ⛔ LIMIT/OFFSET si aggiungono solo se il chiamante impagina: una
        #    `LIMIT NULL` sarebbe legale in PostgreSQL ma legherebbe il ripiego
        #    a un parametro in piu' senza che serva a nessuno.
        paginazione = "" if limit is None else "\n             LIMIT %s OFFSET %s"
        params: list[Any] = [soggetto_id]
        if limit is not None:
            params += [limit, offset]
        data_sql = f"""
            SELECT {_TITOLO_COLS},
                   COUNT(*) OVER () AS total_count
             {_TITOLI_SOGGETTO_FROM_WHERE}
             ORDER BY {ordinamento}{paginazione}
        """
        return fetch_paged_with_total(
            data_sql,
            params,
            fallback_count_sql=(
                f"SELECT count(*) {_TITOLI_SOGGETTO_FROM_WHERE}"
            ),
            fallback_params=[soggetto_id],
            offset=offset,
        )

    # Scopo: Un titolo per id. Ritorna None se non esiste O se e' fuori dal
    #        perimetro emittente dell'operatore — la RLS non distingue i due
    #        casi, ed e' voluto: dire «esiste ma non e' tuo» sarebbe gia' un dato.
    def get_titolo(self, titolo_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_TITOLO_COLS}
              {_TITOLO_JOINS}
             WHERE t.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [titolo_id])
            return row_to_dict(cursor)

    # Scopo: Crea un titolo. Le colonne assenti dal payload prendono il default
    #        DB; i guard di coerenza (plafond <-> tipo, ambito <-> righe) sono
    #        trigger e scattano qui.
    #        BB `execute_dynamic_insert` (2026-09-26): whitelist RIGIDA
    #        (`_TITOLO_UPDATE_COLS` + le due chiavi del padre) — prima una
    #        chiave fuori lista era scartata in silenzio; le chiavi le valida
    #        il service. None scrive NULL, come prima.
    def create_titolo(
        self, *, soggetto_id: str, emittente_fiscale_id: int, data: dict[str, Any],
    ) -> int:
        riga = execute_dynamic_insert(
            "anagrafiche.soggetti_titoli_iva",
            {"soggetto_id": soggetto_id, "emittente_fiscale_id": emittente_fiscale_id, **data},
            allowed=_TITOLO_CREATE_COLS,
            casts={"soggetto_id": "uuid"},
        )
        return int(riga["id"])

    # Scopo: Aggiorna un titolo. Solo le colonne whitelisted; niente da
    #        aggiornare -> False, e il service decide se e' un errore.
    #        BB `execute_dynamic_update` (2026-09-26), whitelist RIGIDA.
    def update_titolo(self, titolo_id: int, data: dict[str, Any]) -> bool:
        return execute_dynamic_update(
            "anagrafiche.soggetti_titoli_iva", titolo_id, data,
            allowed=_TITOLO_UPDATE_COLS,
        )

    # Scopo: Elimina un titolo. Le righe di ambito seguono (ON DELETE CASCADE);
    #        i movimenti NO, e il service deve aver gia' rifiutato il caso (Q6).
    def delete_titolo(self, titolo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM anagrafiche.soggetti_titoli_iva WHERE id = %s",
                [titolo_id],
            )
            return cursor.rowcount > 0

    # Scopo: Quanti movimenti ha un titolo. Serve al guard di Q6: un registro e'
    #        la traccia di cio' che e' stato consumato, e un DELETE se la porta
    #        via.
    def count_movimenti(self, titolo_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                  FROM anagrafiche.soggetti_titoli_iva_movimenti
                 WHERE titolo_iva_id = %s
                """,
                [titolo_id],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Titoli con il plafond sfondato (Q4), su tutti i soggetti.
    #        Perimetro: SOLO i tipi che un tetto ce l'hanno — sugli altri il
    #        residuo non significa niente.
    # ⚠️ Il filtro e' su `tt.ha_plafond`, non su `t.plafond IS NOT NULL`: sono la
    #    stessa cosa solo finche' il guard di coerenza regge, e appoggiarsi
    #    all'effetto invece che alla causa e' il modo in cui una lista di presidio
    #    smette di presidiare senza che nessuno se ne accorga.
    # Scopo: UNA pagina dei titoli sfondati PIU' il totale, in una valutazione
    #        sola (`COUNT(*) OVER()` via `fetch_paged_with_total`).
    #
    # ⭐ Non due query. Il building block esiste da luglio e fa esattamente
    #    questo: una prima stesura di questo metodo aveva una `list_` e una
    #    `count_` separate — un gemello scritto a mano dello stesso pattern.
    #    ⚠️ E non era solo ridondante: due valutazioni dello stesso predicato
    #    possono **non concordare** se una riga entra fra l'una e l'altra, e il
    #    totale racconterebbe una popolazione diversa da quella mostrata.
    #
    # ⚠️ `fallback_count_sql` serve al rientro su una pagina STANTIA: con
    #    `offset > 0` e zero righe la window function non ha nulla su cui
    #    contare, e senza fallback la schermata direbbe «nessun caso» a chi e'
    #    solo rimasto su una pagina che si e' accorciata sotto di lui. Su una
    #    lista di presidio dire «zero» quando i casi ci sono e' il difetto che
    #    questa schermata esiste per evitare.
    def list_titoli_sfondati(
        self,
        *,
        limit: int,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        # ⭐ `default_desc=True`: senza indicazioni si ordina dalla PIU' GRAVE.
        #    Su un presidio l'ordine non e' una preferenza — e' cio' che mette in
        #    cima la cosa da guardare per prima.
        # ⛔ Il tiebreak segue la direzione PRIMARIA, non un `DESC` inchiodato
        #    (decisione Tid 2026-08-03): a parita' di eccedenza l'elenco andrebbe
        #    al contrario di come e' stato chiesto. E il tiebreak su `t.id` e'
        #    obbligatorio: due titoli con la stessa eccedenza non sono un caso di
        #    scuola (il plafond e' lo stesso per tipo), e senza di esso a offset
        #    alti PostgreSQL puo' restituire righe gia' viste. Entrambe le cose
        #    le fa ora il BB.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_SFONDATI,
            default=_ORDER_COLS_SFONDATI[SFONDATI_ORDER_DEFAULT],
            tiebreak="t.id",
            default_desc=True,
        )
        data_sql = f"""
            SELECT {_TITOLO_COLS},
                   sog.ragione_sociale_completa    AS soggetto_ragione_sociale,
                   sog.id_fiscale_univoco_cf_piva  AS soggetto_id_fiscale,
                   (t.imponibile_utilizzato - t.plafond) AS eccedenza,
                   COUNT(*) OVER ()                AS total_count
             {_SFONDATI_FROM_WHERE}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """
        return fetch_paged_with_total(
            data_sql,
            [limit, offset],
            fallback_count_sql=f"SELECT count(*) {_SFONDATI_FROM_WHERE}",
            offset=offset,
        )

    # =================================================================
    # Ambiti (D12: la condizione di applicabilita', non un'etichetta)
    # =================================================================

    # Scopo: Righe di ambito di un titolo PIU' il totale, con le descrizioni
    #        degli oggetti.
    #
    # ⛔ Il totale non e' decorazione: la lista si monta `:paginata="false"`
    #    (lista 64, nessuna colonna `ordinabile` a catalogo), e in quella
    #    modalita' `total` e' l'ASSERZIONE che le righe consegnate siano TUTTE
    #    — il building block rifiuta di disegnare la tabella se non coincide.
    #    Derivarlo da `len(results)` lo renderebbe un'eco: `rows.length ===
    #    rows.length` e' vero sempre, anche mentre tronca.
    # ⚠️ `limit=None` = tutte le righe, ed e' il caso del SECONDO consumatore:
    #    `get_titolo` incorpora gli ambiti nel dettaglio e non impagina.
    def list_ambiti(
        self, titolo_id: int, *, limit: int | None = None, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        paginazione = "" if limit is None else "\n             LIMIT %s OFFSET %s"
        params: list[Any] = [titolo_id]
        if limit is not None:
            params += [limit, offset]
        data_sql = f"""
            SELECT {_AMBITO_COLS},
                   COUNT(*) OVER () AS total_count
             {_AMBITI_FROM_WHERE}
             ORDER BY a.livello, a.id{paginazione}
        """
        return fetch_paged_with_total(
            data_sql,
            params,
            fallback_count_sql=(
                f"SELECT count(*) {_AMBITI_FROM_WHERE}"
            ),
            fallback_params=[titolo_id],
            offset=offset,
        )

    # Scopo: Aggiunge una riga di ambito. Il CHECK di livello pretende che sia
    #        valorizzata la colonna del livello dichiarato e NULL le altre due:
    #        il service normalizza prima, qui si scrive.
    def create_ambito(self, titolo_id: int, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO anagrafiche.soggetti_titoli_iva_ambiti
                   (titolo_iva_id, livello, articolo_id, gruppo_voce_id,
                    tipo_voce_id, note)
            VALUES (%s, %s, %s::uuid, %s, %s, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                titolo_id,
                data["livello"],
                data.get("articolo_id"),
                data.get("gruppo_voce_id"),
                data.get("tipo_voce_id"),
                data.get("note"),
            ])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Toglie una riga di ambito.
    def delete_ambito(self, titolo_id: int, ambito_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM anagrafiche.soggetti_titoli_iva_ambiti
                 WHERE id = %s AND titolo_iva_id = %s
                """,
                [ambito_id, titolo_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # Registro movimenti (D5)
    # =================================================================

    # Scopo: Il registro di un titolo, dal piu' recente.
    # ⭐ PAGINATA dal 2026-09-02 (lista 65, `pagina_dimensione = 25` a
    #    catalogo): un registro append-only cresce a ogni fattura, e una query
    #    senza LIMIT che un giorno torna diecimila righe fa cadere la maschera
    #    proprio sul titolo piu' usato.
    # ⚠️ `limit=None` = tutte, ed e' il caso dei DUE altri consumatori:
    #    `get_titolo` incorpora il registro nel dettaglio, e `annulla_movimento`
    #    lo indicizza per id per verificare che il movimento sia di questo
    #    titolo. Impaginare sotto di loro nasconderebbe righe a un controllo di
    #    appartenenza — che e' il modo in cui un guard smette di guardare.
    def list_movimenti(
        self,
        titolo_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        # ⭐ SI LEGGE LA VISTA, non piu' la tabella (T3-b, 2026-08-31). La vista
        #    porta tre cose che la tabella non ha e che il frontend non puo'
        #    ricostruire: il legame dell'annullo nei DUE versi (`is_annullo` /
        #    `is_annullato`), e il MOTIVO per cui l'annullo e' bloccato.
        # ⛔ E il motivo lo produce `script.fn_check_annullo_movimento_titolo_iva`,
        #    cioe' la STESSA funzione che la madre interroga per rifiutare: il
        #    pulsante spento e il rifiuto non possono divergere.
        # ⚠️ `security_invoker=on`: la vista si legge con la connessione
        #    dell'utente, mai da un canale di sistema.
        # ⭐ Senza `order_by` resta l'ordinamento STORICO — il movimento piu'
        #    recente per primo, che e' come si legge un registro.
        #    ⚠️ Va preservato perche' questo metodo ha un SECONDO consumatore:
        #    `get_titolo` lo incorpora nel dettaglio e non passa nessun
        #    ordinamento. Cambiargli il default sotto i piedi riordinerebbe una
        #    sezione che nessuno sta toccando.
        # ⚠️ Tiebreak `m.id` allineato alla direzione primaria: due movimenti con
        #    la stessa data non sono un caso di scuola — un annullo nasce quasi
        #    sempre nella giornata di cio' che annulla.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_MOVIMENTI,
            default="m.data_movimento",
            tiebreak="m.id",
            default_desc=True,
            colonne_desc=_ORDER_COLONNE_DATA_MOVIMENTI,
        )
        paginazione = "" if limit is None else "\n             LIMIT %s OFFSET %s"
        params: list[Any] = [titolo_id]
        if limit is not None:
            params += [limit, offset]
        data_sql = f"""
            SELECT {_MOVIMENTO_COLS},
                   COUNT(*) OVER () AS total_count
             {_MOVIMENTI_FROM_WHERE}
             ORDER BY {ordinamento}{paginazione}
        """
        return fetch_paged_with_total(
            data_sql,
            params,
            fallback_count_sql=(
                f"SELECT count(*) {_MOVIMENTI_FROM_WHERE}"
            ),
            fallback_params=[titolo_id],
            offset=offset,
        )

    # Scopo: Annulla un movimento del registro scrivendo il CONTRO-MOVIMENTO.
    # ⛔ NON e' un UPDATE e non e' un flag, ed e' la decisione `Q7` di Tid:
    #    «deve rimanere traccia, no delete». L'annullo e' una seconda riga
    #    `FORZATURA` di segno opposto che punta a quella annullata — cosi' il
    #    registro resta append-only (il punto di `D5`), l'accumulatore non si
    #    tocca (fa `SUM` su tutto e il contro-movimento lo riporta da solo al
    #    valore giusto), e la DATA dell'annullo resta un'informazione.
    # ⭐ Delega alla madre `fn_annulla_movimento_titolo_iva`: e' lei a
    #    interrogare la check e a sollevare il codice del PRIMO motivo. Qui non
    #    si ricopia nessuna precondizione — ricopiarle vorrebbe dire farle
    #    divergere dal rifiuto vero.
    def annulla_movimento(self, movimento_id: int, *, motivo: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_annulla_movimento_titolo_iva(%s, %s)",
                [movimento_id, motivo],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Registra una FORZATURA manuale.
    # ⛔ SOLO forzature, ed e' la decisione Q3: gli altri due tipi (FATTURA,
    #    NOTA_CREDITO) li scrive la pipeline con I4, passando da
    #    `fn_consuma_plafond_titolo_iva_righe`, che e' anche l'unica a prendere
    #    il lock di D15-bis. Un endpoint che accettasse FATTURA consumerebbe plafond
    #    SENZA una fattura.
    # ⚠️ `fattura_id`/`fattura_riga_id` restano NULL: lo impone
    #    `chk_stiva_movimenti_documento`, ed e' cio' che rende una forzatura
    #    riconoscibile come tale nel registro.
    def create_forzatura(
        self, titolo_id: int, *, imponibile: Any, data_movimento: Any, motivo: str,
    ) -> int:
        sql = """
            INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
                   (titolo_iva_id, tipo_movimento, imponibile, data_movimento, motivo)
            VALUES (%s, 'FORZATURA', %s, %s, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [titolo_id, imponibile, data_movimento, motivo])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])
