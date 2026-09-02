# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
    fetchone_scalar,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
)

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

_TITOLO_JOINS = """
              FROM anagrafiche.soggetti_titoli_iva t
              JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
              JOIN config.iva iva ON iva.id = t.iva_id
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t.emittente_fiscale_id
              JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id"""

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


class TitoliIvaRepository:
    """Accesso DB per titoli IVA del soggetto, ambiti e registro movimenti."""

    # =================================================================
    # Titoli
    # =================================================================

    # Scopo: Titoli IVA di un soggetto, ordinati dal piu' recente.
    # ⚠️ `valido_al` NULL = «senza scadenza», e va in cima: e' il titolo vivo.
    #    `COALESCE(..., 'infinity')` e' la forma del progetto per le date di
    #    validita' (`feedback_ordinamento_validita_infinity`).
    # Scopo: Conta i titoli di un soggetto con lo STESSO perimetro di
    #        `list_titoli_soggetto`, senza passare dalle righe.
    # ⛔ Query separata, non `len()` sul risultato: serve al frontend come
    #    ASSERZIONE che le righe consegnate siano tutte (guard
    #    `troncamentoSospetto` di `<ListaConfigurabile>` con `paginata: false`).
    #    Un conteggio derivato dalle righe e' un'eco, non un presidio.
    # ⭐ Il FROM e' `_TITOLO_JOINS` per intero, e non e' pigrizia: quei JOIN sono
    #    INNER, quindi POSSONO togliere righe. Un `count(*)` sulla sola
    #    `soggetti_titoli_iva` conterebbe anche i titoli che i join scartano,
    #    direbbe piu' di quanto la lista consegna, e accenderebbe il guard su un
    #    troncamento che non c'e'. Indipendente dalle RIGHE, non dal PERIMETRO.
    def count_titoli_soggetto(self, soggetto_id: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT count(*)
                {_TITOLO_JOINS}
                 WHERE t.soggetto_id = %s::uuid
                """,
                [soggetto_id],
            )
            return int(fetchone_scalar(cursor))

    def list_titoli_soggetto(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {_TITOLO_COLS}
              {_TITOLO_JOINS}
             WHERE t.soggetto_id = %s::uuid
             ORDER BY COALESCE(t.valido_al, 'infinity'::date) DESC,
                      t.valido_dal DESC, t.id DESC
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Un titolo per id. Ritorna None se non esiste O se e' fuori dal
    #        perimetro emittente dell'operatore — la RLS non distingue i due
    #        casi, ed e' voluto: dire «esiste ma non e' tuo» sarebbe gia' un dato.
    def get_titolo(self, titolo_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {_TITOLO_COLS}
              {_TITOLO_JOINS}
             WHERE t.id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [titolo_id])
            return row_to_dict(cursor)

    # Scopo: Crea un titolo. Le colonne assenti dal payload prendono il default
    #        DB; i guard di coerenza (plafond <-> tipo, ambito <-> righe) sono
    #        trigger e scattano qui.
    def create_titolo(
        self, *, soggetto_id: str, emittente_fiscale_id: int, data: dict[str, Any],
    ) -> int:
        cols = ["soggetto_id", "emittente_fiscale_id"]
        placeholders = ["%s::uuid", "%s"]
        vals: list[Any] = [soggetto_id, emittente_fiscale_id]
        for col in _TITOLO_UPDATE_COLS:
            if col in data:
                cols.append(col)
                placeholders.append("%s")
                vals.append(data[col])
        sql = f"""
            INSERT INTO anagrafiche.soggetti_titoli_iva ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Aggiorna un titolo. Solo le colonne whitelisted; niente da
    #        aggiornare -> False, e il service decide se e' un errore.
    def update_titolo(self, titolo_id: int, data: dict[str, Any]) -> bool:
        set_parts: list[str] = []
        vals: list[Any] = []
        for col in _TITOLO_UPDATE_COLS:
            if col in data:
                set_parts.append(f"{col} = %s")
                vals.append(data[col])
        if not set_parts:
            return False
        vals.append(titolo_id)
        sql = f"""
            UPDATE anagrafiche.soggetti_titoli_iva
               SET {", ".join(set_parts)}
             WHERE id = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount > 0

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
        colonna = _ORDER_COLS_SFONDATI.get(
            order_by or "", _ORDER_COLS_SFONDATI[SFONDATI_ORDER_DEFAULT],
        )
        # ⭐ `default_desc=True`: senza indicazioni si ordina dalla PIU' GRAVE.
        #    Su un presidio l'ordine non e' una preferenza — e' cio' che mette in
        #    cima la cosa da guardare per prima.
        direzione = sql_order_direction(order_dir, default_desc=True)
        # ⛔ Il tiebreak segue la direzione PRIMARIA, non un `DESC` inchiodato
        #    (decisione Tid 2026-08-03): a parita' di eccedenza l'elenco andrebbe
        #    al contrario di come e' stato chiesto. E il tiebreak su `t.id` e'
        #    obbligatorio: due titoli con la stessa eccedenza non sono un caso di
        #    scuola (il plafond e' lo stesso per tipo), e senza di esso a offset
        #    alti PostgreSQL puo' restituire righe gia' viste.
        verso_tiebreak = sql_tiebreak_direction(direzione)
        data_sql = f"""
            SELECT {_TITOLO_COLS},
                   sog.ragione_sociale_completa    AS soggetto_ragione_sociale,
                   sog.id_fiscale_univoco_cf_piva  AS soggetto_id_fiscale,
                   (t.imponibile_utilizzato - t.plafond) AS eccedenza,
                   COUNT(*) OVER ()                AS total_count
             {_SFONDATI_FROM_WHERE}
             ORDER BY {colonna} {direzione}, t.id {verso_tiebreak}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        return fetch_paged_with_total(
            data_sql,
            [limit, offset],
            fallback_count_sql=f"SELECT count(*) {_SFONDATI_FROM_WHERE}",  # noqa: S608
            offset=offset,
        )

    # =================================================================
    # Ambiti (D12: la condizione di applicabilita', non un'etichetta)
    # =================================================================

    # Scopo: Righe di ambito di un titolo, con le descrizioni degli oggetti.
    def list_ambiti(self, titolo_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {_AMBITO_COLS}
              FROM anagrafiche.soggetti_titoli_iva_ambiti a
              LEFT JOIN catalogo.articoli art ON art.id = a.articolo_id
              LEFT JOIN vendite.articoli_gruppi gv ON gv.id = a.gruppo_voce_id
              LEFT JOIN vendite.articoli_tipologie tv ON tv.id = a.tipo_voce_id
             WHERE a.titolo_iva_id = %s
             ORDER BY a.livello, a.id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [titolo_id])
            return rows_to_list(cursor)

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
    def list_movimenti(self, titolo_id: int) -> list[dict[str, Any]]:
        # ⭐ SI LEGGE LA VISTA, non piu' la tabella (T3-b, 2026-08-31). La vista
        #    porta tre cose che la tabella non ha e che il frontend non puo'
        #    ricostruire: il legame dell'annullo nei DUE versi (`is_annullo` /
        #    `is_annullato`), e il MOTIVO per cui l'annullo e' bloccato.
        # ⛔ E il motivo lo produce `script.fn_check_annullo_movimento_titolo_iva`,
        #    cioe' la STESSA funzione che la madre interroga per rifiutare: il
        #    pulsante spento e il rifiuto non possono divergere.
        # ⚠️ `security_invoker=on`: la vista si legge con la connessione
        #    dell'utente, mai da un canale di sistema.
        sql = f"""
            SELECT {_MOVIMENTO_COLS}
              FROM anagrafiche.vw_stiva_movimenti_dettaglio m
             WHERE m.titolo_iva_id = %s
             ORDER BY m.data_movimento DESC, m.id DESC
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [titolo_id])
            return rows_to_list(cursor)

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
    #    `fn_consuma_plafond_titolo_iva`, che e' anche l'unica a prendere il lock
    #    di D15-bis. Un endpoint che accettasse FATTURA consumerebbe plafond
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
