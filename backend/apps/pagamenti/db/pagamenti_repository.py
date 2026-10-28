# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dello schema `pagamenti` — letture di lista e dettaglio,
#        scritture semplici, e chiamate alle funzioni madri del database.
# Note: ⛔ Un repository PER SCHEMA e non uno per entita': distinte e righe
#       stanno insieme finche' non nasce un sottodominio con orchestrazione
#       propria (convenzione di naming, AGENTS.md).
#
#       🔴 TUTTE le tabelle di `pagamenti` hanno la row security accesa (lotto
#       DB 6) e le policy pretendono `app.ruolo_applicativo = 'OPERATORE'` per
#       LEGGERE e per SCRIVERE. Un percorso che le tocchi senza quella GUC non
#       vede niente e non scrive niente: la impostano il middleware JWT (ciclo
#       web) e il contesto della coda lavori (worker).
#
#       ⛔ E per la stessa ragione questi metodi NON vanno chiamati da un canale
#       di sistema (ruolo BYPASSRLS): li' il perimetro non filtra e le liste
#       mostrerebbero il denaro di tutti gli emittenti. Il guard e' esplicito
#       nelle letture di lista, non affidato al ricordo.
# ------------------------------------------------------------

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any, cast

from django.db import connection

from apps.core.db._helpers import (
    colonna_ordinamento,
    RicercaFull,
    add_ricerca_full_condition,
    conta_con_perimetro,
    fetch_paged_with_total,
    sql_lateral_primo_motivo,
    sql_order_clause,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
    utente_di_sessione,
)
from apps.core.db.emittente_scope_helpers import (
    add_emittente_scope_condition_risolta,
    fetch_emittenti_scope_ids,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause
from apps.core.services.error_manager import ErrorManager
from apps.core.services.system_context import connection_role_bypasses_rls
from apps.pagamenti.types import (
    DistintaDettaglioRow,
    DistintaRow,
    RicevutaPosting,
    RicevutaTardiva,
    RigaCodaRow,
    RigaContabileRow,
    StatoCatalogoRow,
    StatoRigaCatalogoRow,
)

_FN = "pagamenti.pagamenti_repository"

# Codice usato dai soli guard strutturali di questo modulo (canale di sistema):
# non e' un errore che un operatore possa causare compilando qualcosa.
_E_CHIAMATA = "E_PAGAMENTI_CHIAMATA_NON_VALIDA"

# ✅ Il «fuori perimetro», gia' a catalogo (classe `NON_PERMESSO` -> **403**) e
# gia' col suo ripiego: non se ne inventa uno nuovo, che cadrebbe su
# `E_GENERICO` e quindi su un **500**.
_E_SCOPE_EMITTENTE = "E_SCOPE_EMITTENTE"


# ══════════════════════════════════════════════════════════════════
#  Frammenti SQL condivisi
# ══════════════════════════════════════════════════════════════════

# I totali derivati della distinta. ⚠️ Contano le righe ATTIVE, SCARTATA
# compresa: e' la stessa somma che il guard di validazione confronta con
# `importo_dichiarato` — se una riga scartata uscisse dal conto, il primo
# scarto romperebbe la quadratura di una distinta sana.
_TOTALI_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT
            count(*)::int                                          AS righe_totali,
            count(*) FILTER (WHERE rs.is_postabile)::int           AS righe_registrabili,
            COALESCE(sum(r.importo), 0)                            AS totale_righe,
            COALESCE(sum(r.importo) FILTER (WHERE rs.is_postabile), 0) AS totale_registrabile
          FROM pagamenti.vendite_contabili_righe r
          JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
         WHERE r.contabile_id = c.id
           AND r.attivo IS TRUE
    ) tot ON TRUE
"""

# Cosa si PUO' cercare in ogni lista; cosa si cerca lo dice il catalogo
# (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue §5.3). Le
# espressioni sono quelle che la `SELECT` proietta con quel nome: si cerca su
# cio' che si mostra. ⚠️ Le liste su vista (`v.*`) usano l'alias `v` del BB.
_RICERCA_DISTINTE = RicercaFull("pagamenti.distinte", {"codice": "c.codice"})
# ⭐ Le due liste di righe (coda e distinta) proiettano la STESSA `_RIGA_COLONNE`
#    sullo stesso `_RIGA_FROM`: sanno cercare le stesse colonne, e quali
#    cercano lo decide il catalogo di ciascuna. Due mappe scritte a mano
#    avrebbero due copie della stessa espressione, libere di separarsi.
_RICERCA_RIGA: dict[str, str] = {
    "riferimento_ente": "r.riferimento_ente",
    "billing_account_descrizione": "srd.ragione_sociale_completa",
    "billing_account_codice": "ba.codice",
    "fattura_numero": "f.numero",
    "fattura_numero_documento": "vendite.fn_numero_documento_fattura(f.numero, f.serie)",
}
_RICERCA_RIGHE_CODA = RicercaFull("pagamenti.righe", {
    **_RICERCA_RIGA,
    "contabile_codice": "c.codice",
})
_RICERCA_RIGHE_DISTINTA = RicercaFull("pagamenti.distinta_righe", _RICERCA_RIGA)
_RICERCA_RATE_FUORI_CAPIENZA = RicercaFull(
    "pagamenti.rate_fuori_capienza", ("fattura_numero", "numero_documento"),
)
_RICERCA_ECCEDENZE = RicercaFull("pagamenti.eccedenze", {
    "cliente_ragione_sociale": "srd.ragione_sociale_completa",
    "fattura_numero": "v.fattura_numero",
})
# ⭐ Le rate (passo 7 del brief, dopo il seed DB del 24-09): forma a TUPLA,
#    perche' tutte e quattro sono colonne della STESSA vista
#    (`vendite.vw_fatture_scadenze_lista`) e la lista la legge con DUE alias —
#    `v` la pagina, `p` il perimetro di `solo_aperte`. La tupla prende l'alias
#    dalla chiamata: una mappa lo cablerebbe, e il secondo ramo cercherebbe
#    sulla relazione sbagliata. ⭐ `numero_documento` c'e' per decisione di Tid
#    (23-09): si cerca ANCHE il documento, non solo il cliente.
_RICERCA_RATE = RicercaFull("pagamenti.rate", (
    "numero_documento",
    "ragione_sociale_completa",
    "ba_codice",
    "id_fiscale_univoco_cf_piva",
))

_DISTINTA_SELECT = """
    SELECT
        c.id,
        c.codice,
        c.centro_riscossione_id,
        cr.codice          AS centro_codice,
        cr.descrizione     AS centro_descrizione,
        c.ente_incasso_id,
        ei.codice          AS ente_codice,
        ei.descrizione     AS ente_descrizione,
        c.data_contabile,
        c.data_registrazione,
        c.stato_id,
        st.codice_interno  AS stato_codice,
        st.descrizione     AS stato_descrizione,
        st.is_final        AS stato_is_final,
        -- ⭐ «Registrabile» sta nel CATALOGO (D20-d, 2026-09-18): la bandiera
        --    che la madre del posting legge al posto del letterale `VALIDATA`.
        --    Il frontend la porta per spegnere «Registra» COL MOTIVO invece di
        --    lasciarlo finire in 409 — e non deduce niente dal nome dello stato.
        st.is_registrabile AS stato_is_registrabile,
        -- ⭐ «Le righe di questa distinta si lavorano ancora?» sta nel CATALOGO
        --    (D-1, brief-db-righe-distinta-annullata-fuori-dalle-code): CHIUSA e
        --    ANNULLATA sono entrambe `is_final` ma opposte per le righe. Il
        --    frontend spegne le azioni di riga da qui, e non ricalcola piu'
        --    «finale e non registrata» con `data_conferma` presa in prestito.
        st.righe_lavorabili AS stato_righe_lavorabili,
        -- ⭐ La riga «dove sono» del drawer (FE-9): la chiave i18n vive nel
        --    `meta` dello STATO, come negli otto domini che usano
        --    `DrawerActionsBar :info-key`. Il backend la TRASPORTA: un `CASE`
        --    sul codice qui sarebbe la stessa regola scritta due volte.
        --    ⚠️ NULL finche' il seed (brief §4 P-8) non e' applicato: il
        --    frontend non mostra niente, non una chiave grezza.
        st.meta ->> 'nessuna_azione_key' AS stato_info_key,
        c.origine,
        -- ⭐ LA DISTINTA SA DI CHI E' (D3, brief distinta-numerata-sul-registro,
        --    2026-09-17): l'emittente e' una COLONNA della riga, non piu' una
        --    catena per canale — e il codice `DIS-<SIGLA>-<ANNO>-<7 cifre>` lo
        --    porta dentro. Si espongono il soggetto-ruolo (la chiave che il DB
        --    usa), la PK con sigla e ragione sociale (cio' che il frontend
        --    conosce: `EmittenteFiscaleField` in edit legge
        --    `emittente_fiscale_id/_codice` + `emittente_ragione_sociale`, gli
        --    stessi nomi dei documenti di vendite), e i due assi del contatore.
        -- ⚠️ `registro_id` e `anno` sono NULL sul pregresso `VC_…` (numerato
        --    prima del trasloco): non e' un buco, e' un documento che non ha
        --    mai avuto un registro.
        c.emittente_soggetto_ruolo_id,
        ef.id              AS emittente_fiscale_id,
        ef.codice          AS emittente_fiscale_codice,
        sre.ragione_sociale_completa AS emittente_ragione_sociale,
        c.registro_id,
        c.anno,
        c.importo_dichiarato,
        c.data_conferma,
        c.user_conferma,
        -- ⭐ IL LEGAME DELLA CORREZIONE, letto nei DUE versi (Q-7, C-3): una
        --    distinta puo' essere la correzione di un'altra, oppure essere
        --    quella che e' stata corretta. ⛔ Sono due domande diverse e a
        --    video dicono due cose opposte: «questo documento rovescia quello»
        --    e «questo documento e' gia' stato rovesciato». Portarne una sola
        --    lascerebbe l'altra meta' invisibile.
        c.contabile_corretta_id,
        orig.codice        AS contabile_corretta_codice,
        corr.id            AS correzione_id,
        corr.codice        AS correzione_codice,
        lot.lotti_ids,
        c.meta,
        tot.righe_totali,
        tot.righe_registrabili,
        tot.totale_righe,
        tot.totale_registrabile,
        -- Lo scarto esiste solo se qualcuno ha dichiarato un totale: NULL non
        -- e' zero, e mostrare «scarto 0» dove nessuno ha dichiarato niente
        -- direbbe che la distinta quadra quando non c'e' niente da quadrare.
        CASE WHEN c.importo_dichiarato IS NULL THEN NULL
             ELSE tot.totale_righe - c.importo_dichiarato
        END AS scarto_dichiarato
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.centri_riscossione cr        ON cr.id = c.centro_riscossione_id
      LEFT JOIN pagamenti.enti_incasso ei         ON ei.id = c.ente_incasso_id
      LEFT JOIN pagamenti.vendite_contabili_stati st ON st.id = c.stato_id
      -- L'emittente della distinta: LEFT per simmetria con le sorelle, ma la
      -- colonna e' NOT NULL. `uq_emittenti_fiscali_ruolo` e' UNIQUE su
      -- `soggetto_ruolo_id`: il join non puo' duplicare la riga (e il totale).
      -- La ragione sociale viene dalla vista di dettaglio, la sede unica del
      -- nome di un soggetto-ruolo — come per il billing account delle righe.
      LEFT JOIN anagrafiche.emittenti_fiscali ef  ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio sre
             ON sre.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
      -- Il documento da cui questa correzione nasce.
      LEFT JOIN pagamenti.vendite_contabili orig     ON orig.id = c.contabile_corretta_id
      -- ⚠️ E la correzione di QUESTO documento, se c'e'. E' un LEFT JOIN
      --    diretto e non una LATERAL perche' non puo' duplicare la riga:
      --    `uq_vendite_contabili_correzione` e' un unico parziale su
      --    `contabile_corretta_id`, quindi la corrispondenza e' al piu' una.
      LEFT JOIN pagamenti.vendite_contabili corr     ON corr.contabile_corretta_id = c.id
      -- 🔴 I lotti si AGGREGANO, non si joinano. L'unico e' su
      -- `(lotto_id, contabile_id)` e NON sul solo `contabile_id`: una distinta
      -- puo' legittimamente appartenere a piu' lotti, e un LEFT JOIN diretto
      -- avrebbe DUPLICATO la riga nell'elenco — con il conteggio totale
      -- sbagliato di conseguenza, che e' il modo silenzioso di rompersi.
      LEFT JOIN LATERAL (
          SELECT array_agg(l.lotto_id ORDER BY l.lotto_id) AS lotti_ids
            FROM pagamenti.vendite_contabili_lotti l
           WHERE l.contabile_id = c.id
      ) lot ON TRUE
"""

_RIGA_COLONNE = """
        r.id,
        r.contabile_id,
        r.importo,
        r.riferimento_ente,
        r.data_pagamento,
        r.data_valuta,
        r.data_operazione,
        r.fattura_id,
        f.numero           AS fattura_numero,
        f.anno             AS fattura_anno,
        f.serie            AS fattura_serie,
        -- ⭐ IL DOCUMENTO, NON IL CONTATORE (D19-b, 2026-09-17): chi corregge
        --    un importo deve sapere su che cosa lo corregge. Il numero
        --    parlante si LEGGE dalla sede unica (`fn_numero_documento_fattura`,
        --    IMMUTABLE — si inlinea), mai composto qui: `fattura_numero` da
        --    solo e' ambiguo per costruzione (una fattura 1 e una nota di
        --    credito 1 nello stesso anno). NULL sulla non numerata: il ripiego
        --    lo sceglie chi rende.
        vendite.fn_numero_documento_fattura(f.numero, f.serie) AS fattura_numero_documento,
        f.data             AS fattura_data,
        f.totale_doc       AS fattura_totale_doc,
        reg.codice         AS fattura_registro_codice,
        -- La natura si SEGNALA, non si nasconde: una nota di credito su una
        -- riga di incasso e' il caso in cui il cliente ce la paga (D19-e).
        -- ⚠️ SENZA il prefisso `fattura_` (dal 2026-09-18): e' il nome con cui
        --    OGNI proiezione del progetto porta `config.nature_doc_fiscale`, ed
        --    e' la GEMELLA che il `formato = natura_doc` del catalogo liste
        --    legge dalla riga (`CellaConfigurabile.CAMPO_GEMELLO_NATURA_DOC`).
        --    Col prefisso la lista `pagamenti.distinta_righe` avrebbe reso `—`
        --    su ogni riga, senza errore.
        ndf.codice_interno AS natura_doc_codice_interno,
        ndf.descrizione    AS natura_doc_descrizione,
        r.billing_account_id,
        ba.codice          AS billing_account_codice,
        srd.ragione_sociale_completa AS billing_account_descrizione,
        r.scadenza_id,
        sc.numero_rata     AS scadenza_numero_rata,
        sc.data_scadenza   AS scadenza_data,
        sc.importo         AS scadenza_importo,
        r.forzata,
        r.motivo_forzatura,
        r.stato_id,
        rs.codice_interno  AS stato_codice,
        rs.descrizione     AS stato_descrizione,
        rs.is_postabile    AS stato_is_postabile,
        rs.richiede_abbinamento AS stato_richiede_abbinamento,
        r.motivo_sospeso,
        r.fondo_source_id,
        r.attivo,
        r.meta
"""

# ⭐ IL VERBO «ELIMINA» E IL SUO MOTIVO (D17, linee-guida-sql §12.5): la terna
#    `reason / reason_key / dettaglio` + il flag, letti dalla STESSA check che
#    il guard chiama per rifiutare. Cosi' il cestino spento in lista e il 409
#    del database non «coincidono oggi»: non possono divergere. ⛔ Il nome dice
#    QUALE verbo: su una riga ce ne sono altri (abbina, sospendi), e un
#    `blocco_reason` generico li confonderebbe al primo che si aggiunge.
# ⚠️ NON stanno in `_RIGA_COLONNE`: le aggiunge `_sql_con_elimina` SOPRA la
#    lettura, dopo la pagina (vedi sotto).
_ELIMINA_COLONNE = """
        elimina.reason             AS elimina_blocco_reason,
        elimina.reason_key         AS elimina_blocco_reason_key,
        elimina.dettaglio          AS elimina_blocco_dettaglio,
        (elimina.reason IS NULL)   AS can_eliminare
"""

# ⭐ La LATERAL del PRIMO motivo e' il BB `sql_lateral_primo_motivo` (core/db,
#    2026-09-19): LEFT JOIN … ON TRUE (le righe eliminabili non devono sparire)
#    e `ORDER BY ord LIMIT 1` (lo stesso motivo che il guard solleva).
# ⭐ Rev 2026-10-21: la check si chiama sulla TESTATA, non sull'id della riga.
#    `fn_check_riga_contabile_eliminabile(id)` e' SECURITY INVOKER e rilegge
#    riga e testata sotto RLS: chiamata per riga, ogni chiamata ricalcolava il
#    perimetro (EXPLAIN del 2026-10-21: ~114 buffer a riga, il costo maggiore
#    della coda). La meta' `_su_distinta` giudica la testata RICEVUTA e non
#    legge niente sotto perimetro: la testata la legge questa istruzione, sotto
#    la sua policy, col perimetro una volta (linee-guida-sql §13.2). Il 404
#    no-leak resta della firma per id (guard) e, qui, della RLS sulla riga.
# ⚠️ `testata` e' una LATERAL che espone la SOLA riga intera `c`, non le sue
#    colonne: la clausola d'ordine si riapplica qui sopra coi nomi della
#    proiezione, e una `c.codice`/`c.id` in scope li renderebbe ambigui.
#    LEFT e non INNER: una testata che non si legge non fa sparire la riga in
#    silenzio — la check solleva E_PAGAMENTI_CHIAMATA_NON_VALIDA.
_LATERAL_ELIMINA = f"""
      LEFT JOIN LATERAL (
          SELECT c FROM pagamenti.vendite_contabili c WHERE c.id = p.contabile_id
      ) testata ON TRUE
      {sql_lateral_primo_motivo(
          "script.fn_check_riga_contabile_eliminabile_su_distinta(testata.c)", "elimina"
      )}
"""  # noqa: S608 — frammenti costanti del modulo, nessun input


# Scopo: Aggiunge il blocco «elimina» a una lettura di righe GIA' fatta: la
#        check gira sulle righe che escono, non su quelle che la lettura ha
#        scorso per arrivarci.
# ⭐ E' la ragione per cui sta SOPRA e non dentro `_RIGA_FROM`: nelle liste
#    paginate `_lista_paginata` la applica alla PAGINA (dopo `LIMIT/OFFSET`),
#    quindi la check gira per riga mostrata e non per riga filtrata sotto la
#    `COUNT(*) OVER ()`. Una sede sola per le quattro letture (dettaglio,
#    anteprima, righe della distinta, coda).
# ⚠️ `order_clause`: l'ordine di una sottoquery non sopravvive alle join di
#    sopra, quindi chi ha un ordine lo RIPASSA qui (gli stessi nomi della
#    proiezione).
def _sql_con_elimina(sql: str, order_clause: str = "") -> str:
    return f"""
        SELECT p.*, {_ELIMINA_COLONNE}
          FROM ({sql}) p
          {_LATERAL_ELIMINA}
        {order_clause}
    """  # noqa: S608 — sql e order_clause da costanti del modulo / whitelist, valori come parametri


_RIGA_FROM = """
      FROM pagamenti.vendite_contabili_righe r
      LEFT JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
      LEFT JOIN vendite.fatture f            ON f.id = r.fattura_id
      -- Registro e natura del documento: LEFT come tutto il resto — una riga
      -- senza fattura (DA_ABBINARE) e una fattura in bozza senza registro
      -- devono comparire, non sparire.
      LEFT JOIN vendite.registri_fatturazione reg ON reg.id = f.registro_id
      LEFT JOIN config.nature_doc_fiscale ndf     ON ndf.id = f.natura_doc_id
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = r.billing_account_id
      -- Il nome del cliente non sta sul billing account: la vista di dettaglio
      -- e' la sede unica della ragione sociale (persone fisiche e giuridiche
      -- si compongono in modo diverso, e ricomporla qui sarebbe una copia).
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
             ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
      LEFT JOIN vendite.fatture_scadenze sc  ON sc.id = r.scadenza_id
"""

# La riga «nuda», per il dettaglio e per le righe di UNA distinta. Senza il
# blocco «elimina»: lo aggiunge `_sql_con_elimina` sopra.
_RIGA_SELECT = f"SELECT {_RIGA_COLONNE} {_RIGA_FROM}"

# Il perimetro MINIMO «riga + suo stato», per i conteggi che non hanno bisogno
# dei display field ne' della LATERAL (`conta_con_perimetro`): contare quante
# righe SCARTATA la lista nasconde non deve pagare la check di eliminabilita'
# su ognuna. ⚠️ Le condizioni che ci si applicano sono le stesse della lista
# (`r.contabile_id`, `r.attivo`, `rs.codice_interno`), quindi il perimetro
# coincide — e' la regola del BB.
_RIGA_STATO_FROM = """
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
"""

# Le righe ATTIVE di una distinta — il perimetro che `list_righe` (l'insieme
# intero, per l'anteprima di registrazione) e `list_righe_distinta` (la pagina
# della lista 69) devono condividere: scritto due volte, il giorno in cui uno
# dei due cambia l'anteprima dice quali righe restano indietro su un insieme
# diverso da quello che la lista mostra, senza che niente fallisca.
# ⚠️ Solo le righe ATTIVE, e senza un interruttore per vederle tutte: una riga
#    disattivata non e' un dato da mostrare con un filtro, e un parametro che
#    nessuno passa e' superficie che invecchia.
_RIGHE_DISTINTA_ATTIVE_SQL = f"""
    {_RIGA_SELECT}
    WHERE r.contabile_id = %s
      AND r.attivo IS TRUE
"""

# 🔴 La riga della CODA porta anche la sua distinta, e non e' un di piu': una
# riga cross-distinta senza il documento da cui viene non si lavora — chi la
# guarda deve poterci tornare. ⚠️ Ed e' anche la colonna su cui il contratto
# dichiara di saper ordinare: senza, `order_by=distinta` sarebbe un 500.
# ⭐ E porta i FATTI della testata che decidono il verbo (BE-4, D20-b): lo
#    stato in cui la distinta si trova e se e' REGISTRATA (`data_conferma`
#    scritta dal posting). Dalla coda «Sospese» una riga sotto una distinta
#    registrata si «abbina e registra» (la tardiva), sotto una aperta si
#    abbina e basta: il frontend sceglie il verbo da un fatto, non ricalcola
#    una regola.
# ⭐ E porta la bandiera del CATALOGO `righe_lavorabili` (D-1, brief-db-righe-
#    distinta-annullata-fuori-dalle-code §6): e' la risposta a «si lavora?»,
#    la stessa che il guard legge per congelare. ⚠️ Sulla coda vale sempre
#    true per costruzione (`list_righe_coda` filtra su di lei), ma la
#    proiezione e' la RIGA della coda, non la coda: chi la legge non deve
#    sapere da quale filtro e' passata.
_RIGA_CODA_SELECT = f"""
    SELECT {_RIGA_COLONNE},
        c.codice          AS contabile_codice,
        c.data_contabile  AS contabile_data,
        c.origine         AS contabile_origine,
        cst.codice_interno AS contabile_stato_codice_interno,
        cst.is_final       AS contabile_is_final,
        cst.righe_lavorabili AS contabile_righe_lavorabili,
        (c.data_conferma IS NOT NULL) AS contabile_registrata
    {_RIGA_FROM}
      JOIN pagamenti.vendite_contabili c ON c.id = r.contabile_id
      LEFT JOIN pagamenti.vendite_contabili_stati cst ON cst.id = c.stato_id
"""

# L'INSERT della riga, coi fatti E la destinazione (D16). A costante di modulo
# perche' il presidio sul DB provvisto lo pianifica con `EXPLAIN` senza
# scrivere niente: un nome di colonna sbagliato qui e' un 500 sul primo
# incasso digitato, non un test rosso.
_RIGA_INSERT = """
    INSERT INTO pagamenti.vendite_contabili_righe (
        contabile_id, importo, stato_id, riferimento_ente,
        data_pagamento, data_valuta, data_operazione,
        motivo_sospeso, meta,
        fattura_id, billing_account_id, scadenza_id,
        forzata, motivo_forzatura
    )
    SELECT
        %s, %s, st.id, %s,
        %s, %s, %s,
        %s, %s::jsonb,
        %s, %s, %s,
        %s, %s
      FROM pagamenti.vendite_contabili_righe_stati st
     WHERE st.codice_interno = %s
       AND st.attivo IS TRUE
    RETURNING id
"""

# Scopo: Il predicato «questo stato si propone ancora» — attivo e non
#        RITIRATO (`obsoleto_dal`) — per le due tabelle di stato del dominio.
# ⚠️ `alias` e' un identificatore scelto dal codice (mai da input): finisce
#    interpolato nell'SQL. Vuoto = colonne non qualificate.
# ⭐ Era scritto sei volte fra i cataloghi e le matrici: uno stato ritirato
#    che restava proponibile in UNA delle sei copie non avrebbe dato errore —
#    avrebbe offerto un pulsante che il guard rifiuta.
def _sql_stato_vivo(alias: str = "") -> str:
    p = f"{alias}." if alias else ""
    return (
        f"{p}attivo IS TRUE"
        f" AND ({p}obsoleto_dal IS NULL OR {p}obsoleto_dal > (SELECT script.fn_data_operativa()))"
    )


# L'eliminazione (D17): `attivo = false`, solo su una riga ancora attiva.
_RIGA_DISATTIVA = """
    UPDATE pagamenti.vendite_contabili_righe
       SET attivo = false
     WHERE id = %s
       AND attivo IS TRUE
"""

# ⭐ IL VERBO «VALIDA» E IL SUO MOTIVO (D20-a, BE-1 — linee-guida-sql §12.5):
#    la terna del primo motivo di `script.fn_check_contabile_validabile` — la
#    STESSA check che `trgfn_vendite_contabili_guard_validazione` chiama per
#    rifiutare l'ingresso in VALIDATA — piu' il flag `can_validare`. Cosi' il
#    pulsante «Porta a VALIDATA» spento nel drawer e il 409 del database non
#    «coincidono oggi»: non possono divergere.
# ⚠️ DUE ARGOMENTI, e il secondo non e' un di piu' (brief §4-bis): il guard
#    gira BEFORE ROW e legge `NEW.importo_dichiarato`, che non e' ancora in
#    tabella; qui si passa `c.importo_dichiarato`, cioe' il dichiarato che la
#    distinta HA. Chi chiama passa quello che vede — e' la forma della check.
# ⚠️ SOLO SUL DETTAGLIO, non sulla lista: la check legge righe e stati della
#    distinta, e sull'elenco girerebbe per ogni riga filtrata per un campo che
#    la lista non mostra.
# ⚠️ E' scritta contro l'alias `q` della sottoquery del dettaglio, non contro
#    `c`: la LATERAL si innesta FUORI dalla proiezione condivisa
#    (`_DISTINTA_SELECT`), che resta la stessa della lista.
_LATERAL_VALIDAZIONE = sql_lateral_primo_motivo(
    "script.fn_check_contabile_validabile(q.id, q.importo_dichiarato)", "valida"
)

# ⭐ LE RIGHE PER STATO (BE-1): quante righe attive e per che importo, stato
#    per stato — la fotografia che il dialog di validazione mostra e da cui la
#    quadratura legge «di cui non nostre». Un array jsonb ORDINATO dal catalogo
#    (`ordine`), vuoto — non NULL — su una distinta senza righe.
# ⚠️ Le righe ATTIVE, SCARTATA compresa: e' lo stesso perimetro di
#    `_TOTALI_LATERAL` e della quadratura.
_RIGHE_PER_STATO_LATERAL = """
      LEFT JOIN LATERAL (
          SELECT COALESCE(jsonb_agg(
                     jsonb_build_object(
                         'stato_codice_interno', g.stato_codice_interno,
                         'stato_descrizione', g.stato_descrizione,
                         'righe',             g.righe,
                         'importo',           g.importo)
                     ORDER BY g.ordine NULLS LAST, g.stato_id), '[]'::jsonb) AS righe_per_stato
            FROM (
                SELECT rs.id AS stato_id, rs.codice_interno AS stato_codice_interno,
                       rs.descrizione AS stato_descrizione, rs.ordine,
                       count(*)::int AS righe, COALESCE(sum(r.importo), 0) AS importo
                  FROM pagamenti.vendite_contabili_righe r
                  JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
                 WHERE r.contabile_id = q.id
                   AND r.attivo IS TRUE
                 GROUP BY rs.id, rs.codice_interno, rs.descrizione, rs.ordine
            ) g
      ) rps ON TRUE
"""

# La chiamata alla madre della registrazione TARDIVA (D20-b, P-5), a costante
# di modulo come `_RIGA_INSERT`: il presidio sul DB provvisto la pianifica con
# `EXPLAIN`, cosi' un parametro rinominato e' un test rosso e non un 500 sul
# primo «Abbina e registra».
_POSTA_RIGA_TARDIVA = """
    SELECT movimento_id, riga_id, importo, esito
      FROM pagamenti.fn_posta_riga_tardiva(
           p_riga_id            := %s,
           p_fattura_id         := %s,
           p_billing_account_id := %s,
           p_scadenza_id        := %s,
           p_forzata            := %s,
           p_motivo_forzatura   := %s
      )
"""

# 🔴 LE CHIAVI SONO IL `campo_sorgente` DEL SEED, NON IL `codice` LOGICO — e la
# differenza non e' di stile. `<ListaConfigurabile>` monta le Column con
# `:field="col.campo_sorgente"`, quindi al click sull'intestazione PrimeVue
# manda **il nome fisico**: una whitelist chiavata sul codice logico risponde
# **400 su una colonna che il catalogo dichiara ordinabile**. E' il difetto gia'
# pagato su `vendite.lotti` il 2026-07-31, presidiato da
# `apps/core/tests/test_liste_configurabili_seed.py`
# (`test_whitelist_chiavata_sul_campo_sorgente`).
# ⚠️ Dove il codice logico e il campo fisico divergono, anche il VALORE segue il
# campo mostrato (`stato_descrizione`, non `stato_codice`): una colonna che
# mostra una cosa e ordina per un'altra sembra semplicemente non ordinata —
# codice e descrizione non hanno lo stesso ordine alfabetico.
# ⛔ Mai input utente dentro l'ORDER BY: la whitelist e' chiusa.

# Colonne ordinabili della lista distinte.
DISTINTE_SORT_COLUMNS: dict[str, str] = {
    "data_contabile": "data_contabile",
    "codice": "codice",
    "stato_descrizione": "stato_descrizione",
    "origine": "origine",
    "centro_descrizione": "centro_descrizione",
    "totale_righe": "totale_righe",
}

# Colonne ordinabili della coda del riconciliatore (righe cross-distinta).
RIGHE_SORT_COLUMNS: dict[str, str] = {
    "data_pagamento": "data_pagamento",
    "importo": "importo",
    "stato_descrizione": "stato_descrizione",
    "contabile_codice": "contabile_codice",
}

# Colonne ordinabili delle righe di UNA distinta (lista
# `pagamenti.distinta_righe`, id 69 — 2026-09-18, decisione di Tid: le righe
# del foglio sono una lista a tutti gli effetti, con paginazione, personalizza
# ed export, come gli atti di sistemazione dal 02/09). Le chiavi sono i
# `campo_sorgente` FISICI del seed, i valori gli alias della proiezione
# `_RIGA_COLONNE` (la clausola si applica FUORI, sul risultato di
# `_lista_paginata`).
# ⭐ `fattura_numero_documento` ordina per la COPPIA `(fattura_numero,
#    fattura_serie)` — il costruttore del numero parlante — e non per il testo
#    «numero - serie»: ordinando il testo «10 - A» verrebbe prima di «9 - A»
#    (stessa ragione di `RATE_SORT_COLUMNS`).
# ⭐ `id` e' ordinabile perche' e' l'ordine di DIGITAZIONE, cioe' l'ordine di
#    apertura della lista (vedi `list_righe_distinta`): senza, l'operatore non
#    potrebbe tornarci dopo aver cliccato un'altra intestazione.
DISTINTA_RIGHE_SORT_COLUMNS: dict[str, str] = {
    "id": "id",
    "data_pagamento": "data_pagamento",
    "data_valuta": "data_valuta",
    "data_operazione": "data_operazione",
    "riferimento_ente": "riferimento_ente",
    "importo": "importo",
    "billing_account_descrizione": "billing_account_descrizione",
    "billing_account_codice": "billing_account_codice",
    "fattura_numero_documento": "(fattura_numero, fattura_serie)",
    "scadenza_numero_rata": "scadenza_numero_rata",
    "scadenza_data": "scadenza_data",
    "stato_descrizione": "stato_descrizione",
}

# Le colonne DATA della lista 69: verso DESC al primo click senza `order_dir`
# (regola di Tid del 2026-09-02, come `RATE_SORT_COLONNE_DATA`).
DISTINTA_RIGHE_SORT_COLONNE_DATA: frozenset[str] = frozenset(
    {"data_pagamento", "data_valuta", "data_operazione", "scadenza_data"}
)

# Colonne ordinabili dell'elenco delle rate fuori capienza.
# ⭐ `numero_documento` (P-1-bis, 2026-09-17): la vista porta il numero
#    parlante e la colonna 766 lo mostra; si ordina per la coppia
#    `(fattura_numero, serie)` come sulla lista rate, non per il testo.
RATE_FUORI_CAPIENZA_SORT_COLUMNS: dict[str, str] = {
    "data_scadenza": "data_scadenza",
    "motivo": "motivo",
    "residuo": "residuo",
    "importo_rata": "importo_rata",
    "fattura_numero": "fattura_numero",
    "numero_documento": "(fattura_numero, serie)",
}

# Colonne ordinabili dell'elenco delle RATE (lista `pagamenti.rate`, id 68 —
# D19-c, 2026-09-17): le chiavi sono i `campo_sorgente` FISICI del seed
# (`ordinabile = t`), i valori le espressioni sulla vista
# `vendite.vw_fatture_scadenze_lista` (alias della sottoquery, non `v.`: la
# clausola si applica FUORI, sul risultato paginato).
# ⭐ `numero_documento` si ordina per la COPPIA `(numero, serie)` — il
#    costruttore di riga — e non per il testo «numero - serie»: ordinando il
#    testo, «10 - A» verrebbe prima di «9 - A». E' la ragione scritta nel brief
#    DB (§4-bis.9). ⚠️ Provato con EXPLAIN sul DB vero il 2026-09-17:
#    `Sort Key: (ROW(f.numero, f.serie)) DESC NULLS LAST`, sintassi accettata
#    da PostgreSQL 18.
# ⛔ I tre saldi (`residuo`, `in_lavorazione`, `incassato`) NON ci sono, ed e'
#    il seed a dichiararli `ordinabile = f`: non stanno nella vista — arrivano
#    dal nucleo `fn_get_saldi_rate` DOPO la pagina — e una whitelist che li
#    nominasse produrrebbe un 500 sul primo click.
#    ⭐ `stato_descrizione` e `ba_codice` ordinano perche' lo pretende il NUCLEO
#    (regola di dominio di Tid, 2026-07-31, presidiata da
#    `gen_seed_lista.py --verifica-ordinamento`): stato e billing account
#    ordinano sempre, quando la lista ce li ha. Il brief DB le dava
#    `ordinabile = f`; la regola vince.
RATE_SORT_COLUMNS: dict[str, str] = {
    "numero_documento": "(numero, serie)",
    "data": "data",
    "ragione_sociale_completa": "ragione_sociale_completa",
    "ba_codice": "ba_codice",
    "numero_rata": "numero_rata",
    "data_scadenza": "data_scadenza",
    "importo": "importo",
    "totale_doc": "totale_doc",
    "stato_descrizione": "stato_descrizione",
}

# Le colonne DATA della lista 68, per il verso DESC quando il chiamante non ne
# indica uno (regola di Tid del 2026-09-02). ⚠️ NON e' il default della lista:
# senza `order_by` la lista si apre `data_scadenza ASC` — e' una CODA, la rata
# piu' vecchia e' quella che un pagamento piu' probabilmente salda (stessa
# ragione dei residui di competenza). Il primo click dell'operatore
# sull'intestazione resta DESC per la regola generale, e lo decide il catalogo
# (`tipo_dato = date`) nel frontend.
RATE_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data", "data_scadenza"})

# Colonne ordinabili dell'elenco delle eccedenze da sistemare.
# ⭐ Il default e' per CLIENTE, non per documento: la decisione si prende
#    guardando il cliente (D15-b) — compensare significa mettere insieme due
#    documenti suoi.
ECCEDENZE_SORT_COLUMNS: dict[str, str] = {
    "cliente_ragione_sociale": "cliente_ragione_sociale",
    "eccedenza_cliente": "eccedenza_cliente",
    "eccedenza": "eccedenza",
    "fattura_data": "fattura_data",
    "fattura_numero": "fattura_numero",
}

# ⭐ La utility di un conto: si legge nei DUE punti in cui si sceglie un conto —
# l'elenco dei conti agganciabili e il canale che ne ha gia' uno — perche' un
# elenco che non la dice fa scegliere il conto del gas al posto di quello
# dell'energia, e chi sbaglia se ne accorge dopo (BE-11).
# ⛔ NON e' una colonna di `enti_incasso`: la utility e' un fatto del CONTO, e
#    dichiararla anche sul canale sarebbe una seconda sede.
# ⚠️ Non si passa da `anagrafiche.vw_istanze_utilities_dettaglio` benche' la
#    porti: quella vista descrive l'istanza col suo INDIRIZZO — sei join, due
#    dei quali su viste di indirizzo che PostgreSQL non pota. Misurato con
#    EXPLAIN il 2026-08-27 sull'elenco dei conti: **928.86 contro 6.10**, per
#    decodificare una parola. La catena diretta e' anche la forma gia' in uso
#    in `BillingAccountRepository.search_lookup`.
# ⚠️ La descrizione e' NULL in DUE casi legittimi, e sono diversi: il conto non
#    ha istanza (`istanza_utility_id` e' nullable: e' il conto generico del
#    ruolo, cfr. `uq_src_bancari_..._no_istanza`), oppure l'istanza non ha PDP.
#    ⛔ A video NULL non e' un buco: e' «nessuna utility», e va reso come tale.
# ⚠️ Chi lo innesta usa una f-string: una graffa LETTERALE nell'SQL (un
#    `'{}'::jsonb`) andrebbe raddoppiata. Il difetto sarebbe rumoroso — errore
#    all'import, l'applicazione non parte — non silenzioso.
_UTILITY_DEL_CONTO_JOIN = """
      LEFT JOIN anagrafiche.istanze_utilities iu ON iu.id = src.istanza_utility_id
      LEFT JOIN anagrafiche.pdp p ON p.id = iu.pdp_id
      LEFT JOIN config.utilities u ON u.id = p.utility_id
"""

_ENTE_INCASSO_SELECT = f"""
    SELECT
        e.id, e.codice, e.codice_interno, e.descrizione, e.tipo, e.attivo,
        e.centro_riscossione_id,
        cr.codice          AS centro_codice,
        cr.descrizione     AS centro_descrizione,
        e.soggetto_ruolo_id,
        srp.ragione_sociale_completa AS soggetto_ragione_sociale,
        e.bank_branch_id,
        bb.name       AS bank_branch_nome,
        bb.bank_code  AS bank_branch_bank_code,
        e.soggetto_ruolo_conto_bancario_id,
        cb.iban            AS conto_iban,
        src.uso            AS conto_uso,
        src.soggetto_ruolo_id AS conto_soggetto_ruolo_id,
        src.istanza_utility_id AS conto_istanza_utility_id,
        u.descrizione      AS conto_utility_descrizione,
        e.formato_flusso, e.regole_match, e.meta
      FROM pagamenti.enti_incasso e
      LEFT JOIN pagamenti.centri_riscossione cr ON cr.id = e.centro_riscossione_id
      LEFT JOIN anagrafiche.soggetti_ruoli_conti_bancari src
             ON src.id = e.soggetto_ruolo_conto_bancario_id
      LEFT JOIN anagrafiche.conti_bancari cb ON cb.id = src.conto_bancario_id
      -- ⭐ Filiale e soggetto PSP IN CHIARO, e non e' cosmesi: il drawer li
      --    mostra su un canale gia' configurato, e senza il nome resterebbe un
      --    campo vuoto accanto a un id valorizzato — cioe' direbbe «non c'e'
      --    filiale» di un canale BANCA, dove la filiale e' obbligatoria.
      LEFT JOIN anagrafiche.bank_branches bb ON bb.id = e.bank_branch_id
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srp
             ON srp.soggetto_ruolo_id = e.soggetto_ruolo_id
      {_UTILITY_DEL_CONTO_JOIN}
"""  # noqa: S608 — _UTILITY_DEL_CONTO_JOIN costante di modulo

# Le colonne aggiornabili di un canale. ⛔ `codice_interno` NON c'e': e' la
# chiave stabile con cui il resto del sistema lo nomina, e cambiarla romperebbe
# i riferimenti senza che niente lo dica.
_COLONNE_ENTE_INCASSO_AGGIORNABILI = frozenset(
    {"codice", "descrizione", "tipo", "attivo", "centro_riscossione_id",
     "soggetto_ruolo_id", "bank_branch_id", "soggetto_ruolo_conto_bancario_id",
     "formato_flusso", "regole_match", "meta"}
)
# Le colonne con cui un canale NASCE. Oggi coincidono con le aggiornabili (anche
# `codice_interno` resta fuori: il service non lo compila), ma e' una domanda
# diversa e ha un nome suo — il giorno in cui divergono, divergono qui.
# 🔴 Prima di questa costante l'INSERT componeva le colonne da `list(campi)`
#    SENZA whitelist nel repository: l'«ultimo cancello» valeva per l'UPDATE e
#    non per l'INSERT.
_COLONNE_ENTE_INCASSO_INSERIBILI = _COLONNE_ENTE_INCASSO_AGGIORNABILI

# Colonne ordinabili degli ATTI DI SISTEMAZIONE di una fattura (lista 61).
# ⛔ Chiavata sui `campo_sorgente` FISICI, non sui codici logici: il frontend
#    monta le Column con `:field="col.campo_sorgente"` e manda QUELLO in
#    `order_by`. Chiavarla sui codici logici e' il difetto di `vendite.lotti`
#    (2026-07-31), e qui sarebbe stato peggio: prima di questa modifica il
#    metodo aveva `ORDER BY s.id` inchiodato e **ignorava** `order_by` in
#    silenzio — la freccia si girava sopra righe immobili, senza nemmeno un 400
#    a dirlo.
# `FROM` + `WHERE` degli ATTI DI SISTEMAZIONE di una fattura, in una sede sola.
# ⛔ Lo condividono la query di PAGINA e il conteggio di RIPIEGO: sono due
#    domande sullo stesso insieme, e scritte due volte diventano due insiemi al
#    primo filtro che se ne aggiunge a una sola delle due.
_SISTEMAZIONI_FROM_WHERE = """
              FROM pagamenti.sistemazioni s
             WHERE s.fattura_origine_id = %s"""

SISTEMAZIONI_SORT_COLUMNS: dict[str, str] = {
    "destinazione": "s.destinazione",
    "importo": "s.importo",
    "stato": "s.stato",
    "motivo": "s.motivo",
    "data_esecuzione": "s.data_esecuzione",
}

# ⭐ Le colonne DATA della lista 61. Il BB `sql_order_clause` le ordina DESC
#    quando il chiamante non indica un verso: «gli ordinamenti per data hanno
#    sempre default DESC» (Tid, 2026-09-02). Una data si legge dalla piu'
#    recente, e chiedere «ordina per data» ricevendo il caso piu' vecchio in
#    cima e' il contrario di cio' che si e' chiesto.
# ⚠️ Vive ACCANTO alla whitelist e non altrove: e' un sottoinsieme delle sue
#    chiavi, e a distanza le due si separerebbero senza che niente lo dica.
SISTEMAZIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_esecuzione"})

# Colonne ordinabili dell'elenco dei canali di incasso.
# ⭐ CHIAVATA SUI `campo_sorgente` FISICI dal 2026-09-02, ed e' il giorno che il
#    commento precedente aveva previsto: *«il giorno in cui la schermata dei
#    canali si monta sul BB, `centro` va riscritta come `centro_descrizione` — o
#    l'intestazione rispondera' 400 al click»*. La lista e' seedata
#    (`pagamenti.canali_incasso`, id 60) con `campo_sorgente = centro_descrizione`,
#    quindi quel giorno e' arrivato.
# ⭐ E SI ORDINA PER LA DESCRIZIONE, non per il codice (decisione di Tid,
#    2026-09-02). Il valore era `centro_codice`: l'intestazione mostra
#    `centro_descrizione` e ordinava per un campo che a video non c'e'. Se
#    codice e descrizione non sono correlati l'ordine sembra arbitrario — e un
#    ordinamento che non corrisponde a cio' che si legge e' un difetto che
#    l'operatore vede e nessun test prende.
#    ⇒ **Si ordina la colonna che si vede.**
ENTI_INCASSO_SORT_COLUMNS: dict[str, str] = {
    "codice": "codice",
    "descrizione": "descrizione",
    "tipo": "tipo",
    "centro_descrizione": "centro_descrizione",
}

# Colonne jsonb scritte da questo repository (`jsonb=` dei BB di scrittura). In
# lettura le decodifica il lettore comune (`rows_to_list`, dal tipo della
# colonna, 2026-10-28): fino ad allora le decodificava `_shape` da questo
# elenco, ed era la sua ragione d'essere — i difetti qui sotto ne sono la
# storia.
# ⚠️ `elimina_blocco_dettaglio` e' l'oggetto coi NOMI dei parametri della frase
#    i18n del cestino spento: servito come stringa non fallisce — il frontend
#    si limita a non trovarci le chiavi, e la frase esce coi segnaposto dentro.
# ⚠️ Idem per `validazione_blocco_dettaglio` e `righe_per_stato` (il dettaglio
#    della distinta): il primo riempie la frase del «Porta a VALIDATA» spento,
#    il secondo e' l'array che il dialog di validazione elenca.
# ⚠️ `regole_match` (jsonb NOT NULL di `enti_incasso`) mancava fino al
#    2026-09-26, e il difetto era muto: il dettaglio del canale la serviva come
#    STRINGA (il driver restituisce jsonb come testo e `_shape` non la
#    decodificava) mentre il contratto in ingresso la vuole oggetto; e l'UPDATE
#    la scriveva senza `::jsonb`, mentre l'INSERT la castava con un'eccezione
#    scritta a mano accanto a questa lista — due regole per la stessa colonna.
_JSONB_COLS = (
    "meta", "elimina_blocco_dettaglio", "validazione_blocco_dettaglio", "righe_per_stato",
    "regole_match",
)

# 🔴 Le colonne che questo repository accetta di aggiornare, e non e' una
# ripetizione della whitelist del service: quella dice che cosa il CONTRATTO
# API espone, questa e' l'ultimo cancello prima che un nome finisca dentro una
# stringa SQL. Il giorno in cui qualcuno chiamasse questi metodi con delle
# chiavi che arrivano da un payload, la differenza fra le due sarebbe una
# SQL injection.
_COLONNE_DISTINTA_AGGIORNABILI = frozenset(
    {"data_contabile", "data_registrazione", "ente_incasso_id",
     "importo_dichiarato", "meta"}
)
_COLONNE_RIGA_AGGIORNABILI = frozenset(
    {"importo", "riferimento_ente", "data_pagamento", "data_valuta",
     "data_operazione", "fattura_id", "billing_account_id", "scadenza_id",
     "forzata", "motivo_forzatura", "motivo_sospeso", "meta"}
)


class PagamentiRepository:
    """Accesso dati dello schema `pagamenti`."""

    # ══════════════════════════════════════════════════════════════
    #  Guard strutturale
    # ══════════════════════════════════════════════════════════════

    # Scopo: Impedisce che una lettura di perimetro giri su un ruolo BYPASSRLS.
    # Contesto: le policy di `pagamenti` sono l'unico cancello di queste liste.
    #        Su un ruolo che le scavalca la lista non fallirebbe: mostrerebbe
    #        il denaro di TUTTI gli emittenti, che e' molto peggio di un errore.
    @staticmethod
    def _guard_canale_sistema(metodo: str) -> None:
        ErrorManager.require(
            not connection_role_bypasses_rls(),
            code=_E_CHIAMATA,
            message="Operazione non disponibile dal canale di sistema.",
            detail=(
                "Le tabelle di pagamenti sono protette da RLS: lette da un "
                "ruolo BYPASSRLS perderebbero il perimetro emittente. Usare "
                "la connessione dell'utente della richiesta."
            ),
            function_name=f"{_FN}.{metodo}",
        )

    # Scopo: Esegue una lista paginata: pagina + totale in una valutazione, e
    #        il conteggio di ripiego per la pagina stantia.
    # Nota: era scritto tre volte (distinte, coda, rate fuori capienza) — e tre
    #       copie della stessa paginazione divergono alla prima correzione.
    # ⚠️ `order_clause` si compone dalla WHITELIST del chiamante e MAI da input
    #    utente: qui dentro finisce in una stringa SQL.
    # ⭐ `dopo_pagina`: cio' che si calcola sulle righe MOSTRATE e non su quelle
    #    filtrate — oggi il blocco «elimina» delle righe (`_sql_con_elimina`).
    #    Riceve la query della pagina (gia' con `total_count` e `LIMIT/OFFSET`)
    #    e la clausola d'ordine da ripassare sopra. Il conteggio di ripiego non
    #    lo paga: conta le righe, non le giudica.
    @staticmethod
    def _lista_paginata(
        *,
        select_sql: str,
        params: list[Any],
        order_clause: str,
        limit: int,
        offset: int,
        dopo_pagina: Callable[[str, str], str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        data_sql = f"""
            SELECT *, COUNT(*) OVER () AS total_count FROM (
                {select_sql}
            ) q
            {order_clause}
            LIMIT %s OFFSET %s
        """  # noqa: S608 — select_sql da costanti del modulo, order_clause da sql_order_clause su whitelist, valori come parametri
        if dopo_pagina is not None:
            data_sql = dopo_pagina(data_sql, order_clause)
        # ⚠️ Il conteggio di ripiego serve SOLO a pagina oltre l'ultima: li' la
        # window function non ha righe su cui calcolare il totale e
        # risponderebbe zero. Senza, a chi e' rimasto su una pagina stantia di
        # una lista che si e' accorciata sotto di lui diremmo «nessun
        # risultato» — una cosa falsa, con l'aria di un dato.
        count_sql = f"SELECT COUNT(*) FROM ({select_sql}) q"  # noqa: S608 — select_sql da costanti del modulo e frammenti letterali, valori come parametri
        return fetch_paged_with_total(
            data_sql,
            [*params, limit, offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=offset,
        )

    # ══════════════════════════════════════════════════════════════
    #  Cataloghi di stato
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il vocabolario degli stati della distinta, coi suoi flag.
    # Nota: `obsoleto_dal` filtra i valori RITIRATI — che restano leggibili
    #       sui documenti vecchi ma non si propongono piu' a nessuno.
    # ⭐ `is_registrabile` (D20-d): e' la bandiera con cui il frontend riconosce
    #    lo stato «pronta da registrare» — quello in cui si entra VALIDANDO —
    #    senza confrontare il nome dello stato con un letterale.
    def list_stati_distinta(self) -> list[StatoCatalogoRow]:
        sql = f"""
            SELECT id, codice, codice_interno, descrizione, is_final, ordine,
                   is_registrabile
              FROM pagamenti.vendite_contabili_stati
             WHERE {_sql_stato_vivo()}
             ORDER BY ordine NULLS LAST, id
        """  # noqa: S608 — _sql_stato_vivo(): frammento letterale
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # Scopo: Il vocabolario degli stati della riga, coi due flag che governano
    #        l'interfaccia — `is_postabile` (occupa spazio, si puo' registrare)
    #        e `richiede_abbinamento` (pretende fattura e cliente).
    def list_stati_riga(self) -> list[StatoRigaCatalogoRow]:
        sql = f"""
            SELECT id, codice, codice_interno, descrizione, is_final, ordine,
                   is_postabile, richiede_abbinamento
              FROM pagamenti.vendite_contabili_righe_stati
             WHERE {_sql_stato_vivo()}
             ORDER BY ordine NULLS LAST, id
        """  # noqa: S608 — _sql_stato_vivo(): frammento letterale
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Distinte — lettura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Elenco paginato delle distinte contabili con i display field in
    #        JOIN e i totali derivati.
    # Perimetro: la RLS della testata, che dal 2026-09-17 (D3 del brief
    #        distinta-numerata-sul-registro) passa dalla COLONNA
    #        `emittente_soggetto_ruolo_id` — la forma di
    #        `rls_fatturazione_lotti_ef_whitelist`. Nessun filtro applicativo
    #        aggiuntivo. ⚠️ Fino a quel giorno questa riga diceva «le policy
    #        passano dal canale e dalla fattura, non da una colonna emittente»,
    #        ed era vero: una distinta senza canale era «di tutti». Non lo e'
    #        piu': e' del suo emittente, come il lotto da cui nasce.
    def list_distinte(
        self,
        *,
        stato_codice: str | None = None,
        origine: str | None = None,
        centro_riscossione_id: int | None = None,
        ente_incasso_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        search: str | None = None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DistintaRow], int]:
        self._guard_canale_sistema("list_distinte")

        conditions: list[str] = []
        params: list[Any] = []
        if stato_codice is not None:
            conditions.append("st.codice_interno = %s")
            params.append(stato_codice)
        if origine is not None:
            conditions.append("c.origine = %s")
            params.append(origine)
        if centro_riscossione_id is not None:
            conditions.append("c.centro_riscossione_id = %s")
            params.append(centro_riscossione_id)
        if ente_incasso_id is not None:
            conditions.append("c.ente_incasso_id = %s")
            params.append(ente_incasso_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_DISTINTE)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # ⚠️ La direzione la compone l'helper condiviso, e porta con se' la
        # posizione dei NULL: i vuoti vanno dove starebbe lo zero (in coda
        # scendendo, in testa salendo). ⛔ Non si incolla un `NULLS LAST` fisso:
        # sarebbe sintatticamente doppio, e su una lista che si ordina dal piu'
        # recente porterebbe i campi vuoti in cima.
        # Tiebreak nella STESSA direzione della colonna primaria: due distinte
        # dello stesso giorno non devono cambiare posto fra una pagina e l'altra.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DISTINTE_SORT_COLUMNS,
            default="data_contabile",
            tiebreak="id",
            default_desc=True,
        )

        rows, total = self._lista_paginata(
            select_sql=f"{_DISTINTA_SELECT}{_TOTALI_LATERAL}{where_clause}",
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )
        return [cast(DistintaRow, row) for row in rows], total

    # Scopo: Dettaglio di una distinta (testata + display + totali derivati).
    # Risultato: None se non esiste — o se il perimetro non la lascia vedere,
    #        e i due casi sono volutamente indistinguibili al chiamante.
    # ⭐ Porta anche cio' che SOLO il dettaglio ha (BE-1, D20-a): la terna del
    #    verbo «valida» + `can_validare` dalla check del database, e le righe
    #    per stato. Sono innestate FUORI dalla proiezione condivisa con la
    #    lista, sull'alias `q`: la lista non le paga.
    # ⚠️ La terna si legge SEMPRE qui; e' il SERVICE a lasciarla a `null` quando
    #    lo stato corrente non ammette VALIDATA fra le uscite (la matrice la
    #    legge gia' lui): un motivo su un verbo che non si propone e' rumore.
    def get_distinta(self, contabile_id: int) -> DistintaDettaglioRow | None:
        self._guard_canale_sistema("get_distinta")
        sql = f"""
            SELECT q.*,
                   valida.reason              AS validazione_blocco_reason,
                   valida.reason_key          AS validazione_blocco_reason_key,
                   valida.dettaglio           AS validazione_blocco_dettaglio,
                   (valida.reason IS NULL)    AS can_validare,
                   rps.righe_per_stato
              FROM (
                {_DISTINTA_SELECT}
                {_TOTALI_LATERAL}
                WHERE c.id = %s
              ) q
              {_LATERAL_VALIDAZIONE}
              {_RIGHE_PER_STATO_LATERAL}
        """  # noqa: S608 — _DISTINTA_SELECT e LATERAL costanti di modulo, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return cast(DistintaDettaglioRow, rows[0]) if rows else None

    # ══════════════════════════════════════════════════════════════
    #  Distinte — scrittura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Apre (o ritrova) la distinta manuale dell'operatore.
    # ⭐ E' un GET **or** CREATE, e la chiave di riuso comprende CHI STA
    #    LAVORANDO oltre alla giornata e al canale: due operatori non si
    #    contendono la stessa distinta, e il lock che sarebbe servito a
    #    governarla non si costruisce.
    # ⛔ L'operatore NON si passa: lo mette la funzione dall'identita' della
    #    connessione. Passarlo dal backend sarebbe una seconda verita'.
    # ⛔ E l'EMITTENTE NON SI RISOLVE QUI (D4 del brief distinta-numerata-sul-
    #    registro, 2026-09-17): `p_emittente_fiscale_id` (PK) e' cio' che il
    #    chiamante SA — la scelta di un form — e viaggia com'e', `NULL`
    #    compreso. I quattro livelli (dato → canale → operatore in sessione →
    #    rifiuto `E_CONTABILE_EMITTENTE_OBBLIGATORIO`) vivono in
    #    `pagamenti.fn_get_emittente_distinta`, e sono la CHIAVE DI RIUSO della
    #    madre prima ancora dell'INSERT: un secondo risolutore in Python
    #    sarebbe la seconda sede della stessa regola, e la manuale smetterebbe
    #    di essere il lotto di lavoro dell'operatore.
    # ⚠️ Il valore di ritorno e' il solo `id`: «creata» e «riaperta» non si
    #    distinguono dalla chiamata — si leggono dal dettaglio (ha righe o no).
    def get_or_create_distinta(
        self,
        *,
        centro_riscossione_id: int,
        data_contabile: date,
        data_registrazione: date | None = None,
        ente_incasso_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        codice_stato_interno: str = "BOZZA",
        origine: str = "MANUALE",
        meta: str = "{}",
    ) -> int:
        sql = """
            SELECT pagamenti.fn_get_or_create_vendite_contabile(
                p_centro_riscossione_id := %s,
                p_data_contabile        := %s,
                p_data_registrazione    := COALESCE(%s, (SELECT script.fn_data_operativa())),
                p_ente_incasso_id       := %s,
                p_emittente_fiscale_id  := %s,
                p_codice_stato_interno  := %s,
                p_meta                  := %s::jsonb,
                p_origine               := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(centro_riscossione_id),
                    data_contabile,
                    data_registrazione,
                    ente_incasso_id,
                    emittente_fiscale_id,
                    codice_stato_interno,
                    meta,
                    origine,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Verifica che OGNI nome di colonna di una scrittura sia nella
    #        whitelist del suo oggetto — UPDATE e INSERT, stesso cancello.
    # ⚠️ Il BB fa lo stesso controllo (ValueError); questo resta davanti per
    #    parlare col codice del modulo (`_E_CHIAMATA`), come ha sempre fatto.
    @staticmethod
    def _verifica_colonne(
        campi: dict[str, Any], consentite: frozenset[str], metodo: str
    ) -> None:
        fuori = sorted(c for c in campi if c not in consentite)
        ErrorManager.require(
            not fuori,
            code=_E_CHIAMATA,
            message="Scrittura non ammessa su queste colonne.",
            detail=f"Colonne non ammesse: {', '.join(fuori)}",
            function_name=f"{_FN}.{metodo}",
        )

    # Scopo: Compone la clausola SET di un UPDATE parziale, verificando che
    #        OGNI nome di colonna sia nella whitelist del suo oggetto.
    # ⛔ Nessun nome arriva mai in SQL senza passare di qui.
    # ⭐ La composizione e' il BB `sql_set_clause` (2026-09-26): le colonne di
    #    `_JSONB_COLS` escono `::jsonb` col valore gia' serializzato dal service.
    @classmethod
    def _set_clause(
        cls, campi: dict[str, Any], consentite: frozenset[str], metodo: str
    ) -> tuple[str, list[Any]]:
        cls._verifica_colonne(campi, consentite, metodo)
        return sql_set_clause(campi, allowed=consentite, jsonb=_JSONB_COLS)

    # Scopo: Aggiorna i campi che una persona compila sulla testata.
    # ⛔ Lo stato NON passa di qui: cambiarlo e' un'azione, e la matrice delle
    #    transizioni ha un guard suo che va fatto parlare.
    # Risultato: numero di righe toccate (0 = distinta inesistente o fuori
    #        perimetro, e il service lo traduce in 404).
    def update_distinta(self, contabile_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_DISTINTA_AGGIORNABILI, "update_distinta"
        )
        params.append(int(contabile_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili
               SET {set_clause}
             WHERE id = %s
        """  # noqa: S608 — SET da _set_clause su whitelist _COLONNE_DISTINTA_AGGIORNABILI, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato della distinta risolvendo il codice a catalogo.
    # ⚠️ Un UPDATE solo: la transizione la giudicano i guard del database
    #    (matrice, quadratura col dichiarato, riapertura solo se MANUALE,
    #    chiusura con righe ancora pronte). Il backend non li replica.
    def set_stato_distinta(self, contabile_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili c
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_stati st
             WHERE c.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), codice_stato_interno])
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  Righe
    # ══════════════════════════════════════════════════════════════

    # Scopo: TUTTE le righe attive di una distinta, in ordine di digitazione.
    # ⚠️ Dal 2026-09-18 NON e' piu' cio' che il drawer mostra: la lista a video
    #    e' `list_righe_distinta` (paginata). Questa lettura serve a chi ha
    #    bisogno dell'INSIEME intero — l'anteprima di registrazione, che deve
    #    dire quali righe restano indietro e non puo' farlo su una pagina.
    def list_righe(self, contabile_id: int) -> list[RigaContabileRow]:
        self._guard_canale_sistema("list_righe")
        sql = _sql_con_elimina(_RIGHE_DISTINTA_ATTIVE_SQL, "ORDER BY id")
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return [cast(RigaContabileRow, row) for row in rows]

    # Scopo: Le righe attive di una distinta come LISTA — pagina + totale in
    #        una valutazione, ordinamento dalla whitelist.
    # ⭐ 2026-09-18 (decisione di Tid): le righe del foglio hanno paginazione,
    #    ricarica, «Personalizza colonne» ed export come ogni altra lista
    #    configurabile. La ragione per cui non le avevano — «le righe di una
    #    distinta sono limitate per costruzione» — era una previsione sui DATI,
    #    e una previsione sui dati non decide la forma di una lista (regola
    #    zero; stessa strada degli atti di sistemazione dal 02/09).
    # ⭐ Default `id DESC`: l'ULTIMA riga digitata sta in cima. E' la scelta di
    #    Tid del 02/09 sugli atti di sistemazione, per la stessa ragione: da
    #    quando la lista impagina, una riga appena scritta in ordine crescente
    #    finirebbe nell'ULTIMA pagina, e chi l'ha appena digitata non la
    #    vedrebbe. ⚠️ `default_desc` governa solo il ramo senza `order_by`: chi
    #    clicca «Id riga» ottiene il verso che chiede.
    # ⚠️ L'export non chiede «tutto»: chiede `EXPORT_MAX_ROWS + 1` righe, ed e'
    #    il `+1` a far scattare il guard del tetto PRIMA di serializzare
    #    (`build_export_response`), come su ogni altra lista.
    # ⭐ `escludi_stato_codice` (BE-2, D20-c): lo stato che la lista NASCONDE di
    #    default — le SCARTATA, «non e' nostra», fuori dal lavoro ma dentro la
    #    distinta e dentro la quadratura. Il codice lo nomina il service
    #    (`STATO_RIGA_SCARTATA`), qui e' un filtro. `None` = tutte le attive.
    def list_righe_distinta(
        self,
        contabile_id: int,
        *,
        escludi_stato_codice: str | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[RigaContabileRow], int]:
        self._guard_canale_sistema("list_righe_distinta")
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DISTINTA_RIGHE_SORT_COLUMNS,
            default="id",
            tiebreak="id",
            default_desc=True,
            colonne_desc=DISTINTA_RIGHE_SORT_COLONNE_DATA,
        )
        # `_RIGHE_DISTINTA_ATTIVE_SQL` finisce col suo `WHERE`: le condizioni
        # in piu' vi si attaccano in `AND`.
        conditions: list[str] = []
        params: list[Any] = [int(contabile_id)]
        if escludi_stato_codice is not None:
            # ⚠️ `IS DISTINCT FROM` e non `<>`: `rs` e' in LEFT JOIN, e una riga
            #    con uno stato che non risolve a catalogo (NULL) deve restare
            #    a video, non sparire come se fosse scartata.
            conditions.append("rs.codice_interno IS DISTINCT FROM %s")
            params.append(escludi_stato_codice)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_RIGHE_DISTINTA)
        select_sql = " AND ".join([_RIGHE_DISTINTA_ATTIVE_SQL, *conditions])
        rows, total = self._lista_paginata(
            select_sql=select_sql,
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
            dopo_pagina=_sql_con_elimina,
        )
        return [cast(RigaContabileRow, row) for row in rows], total

    # Scopo: QUANTE righe attive di una distinta stanno in uno stato — il numero
    #        accanto a «Mostra scartate (N)» (BE-2, la forma di
    #        `archiviate_count`/`annullati_count`).
    # ⛔ Non e' derivabile dalla lista: quelle righe il suo `WHERE` le ha gia'
    #    escluse. E' il caso per cui esiste il BB `conta_con_perimetro`, sul
    #    perimetro minimo «riga + stato» — le condizioni sono le stesse della
    #    lista, senza pagare display field e LATERAL per un numero.
    def count_righe_in_stato(self, contabile_id: int, stato_codice: str) -> int:
        self._guard_canale_sistema("count_righe_in_stato")
        return conta_con_perimetro(
            _RIGA_STATO_FROM,
            ["r.contabile_id = %s", "r.attivo IS TRUE", "rs.codice_interno = %s"],
            [int(contabile_id), stato_codice],
        )

    # Scopo: Dettaglio di una singola riga contabile ATTIVA.
    # ⚠️ Il filtro su `attivo` e' un cancello, non un dettaglio (D17): questa
    #    lettura e' il `_riga_o_404` di ogni verbo — PATCH, stato, abbina,
    #    elimina. Senza, una riga eliminata (che nessuna lista mostra) restava
    #    modificabile e abbinabile dall'API, in silenzio. Prima del 14/09 non
    #    c'era modo di produrne una dall'app; adesso c'e'.
    def get_riga(self, riga_id: int) -> RigaContabileRow | None:
        self._guard_canale_sistema("get_riga")
        sql = _sql_con_elimina(f"""
            {_RIGA_SELECT}
            WHERE r.id = %s
              AND r.attivo IS TRUE
        """)
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id)])
            rows = rows_to_list(cursor)
        return cast(RigaContabileRow, rows[0]) if rows else None

    # Scopo: Crea una riga sotto una distinta — coi fatti E la destinazione.
    # ⚠️ Lo stato si risolve dal catalogo per codice: gli id sono smallint
    #    seminati e non si scrivono a mano da nessuna parte (mai id cablati).
    # ⭐ D16: fattura, cliente, rata e forzatura entrano nello STESSO INSERT dei
    #    fatti. ⛔ Fino al 14/09 questi parametri erano stati TOLTI come «seconda
    #    porta per scrivere l'abbinamento aggirando il verbo»: la ragione decade
    #    perche' la nascita abbinata E' il verbo, e i guard che lo governano
    #    (dati richiesti dallo stato, coerenza rata/fattura, capienza, scope
    #    emittente) sono `BEFORE INSERT OR UPDATE` — sull'INSERT parlano uguale.
    #    Lo STATO lo sceglie il service in base alla destinazione; qui non si
    #    decide niente.
    def create_riga(
        self,
        *,
        contabile_id: int,
        importo: Decimal,
        codice_stato_interno: str,
        riferimento_ente: str | None = None,
        data_pagamento: date | None = None,
        data_valuta: date | None = None,
        data_operazione: date | None = None,
        motivo_sospeso: str | None = None,
        meta: str = "{}",
        fattura_id: int | None = None,
        billing_account_id: int | None = None,
        scadenza_id: int | None = None,
        forzata: bool = False,
        motivo_forzatura: str | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                _RIGA_INSERT,
                [
                    int(contabile_id), importo, riferimento_ente,
                    data_pagamento, data_valuta, data_operazione,
                    motivo_sospeso, meta,
                    fattura_id, billing_account_id, scadenza_id,
                    bool(forzata), motivo_forzatura,
                    codice_stato_interno,
                ],
            )
            row = cursor.fetchone()
        # Nessuna riga di ritorno = il codice di stato non esiste a catalogo:
        # non e' un dato dell'operatore, e il service lo traduce come tale.
        ErrorManager.require(
            row is not None,
            code="E_CONTABILE_STATO_NON_CONFIGURATO",
            message="Stato riga contabile non configurato.",
            detail=f"codice_interno={codice_stato_interno} assente o non attivo.",
            function_name=f"{_FN}.create_riga",
        )
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna i FATTI di una riga (importo, date, riferimento) e le
    #        decisioni che non sono un'azione di dominio.
    def update_riga(self, riga_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_RIGA_AGGIORNABILI, "update_riga"
        )
        params.append(int(riga_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili_righe
               SET {set_clause}
             WHERE id = %s
        """  # noqa: S608 — SET da _set_clause su whitelist _COLONNE_RIGA_AGGIORNABILI, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato di una riga risolvendo il codice a catalogo.
    # ⚠️ Come per la testata: un UPDATE solo, e i guard del database dicono se
    #    la transizione e' ammessa e se i dati che quello stato pretende ci
    #    sono (fattura e cliente su ABBINATA, per esempio).
    def set_stato_riga(self, riga_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id), codice_stato_interno])
            return cursor.rowcount

    # Scopo: Imputa una riga a una fattura (e, quando c'e', a una rata).
    # ⭐ UN SOLO `UPDATE`: i dati dell'abbinamento e lo stato viaggiano insieme,
    #    perche' sono lo stesso gesto — «questa riga e' di questo documento».
    #    Separarli lascerebbe per un istante una riga abbinata a meta', che i
    #    guard rifiuterebbero comunque, ma con un messaggio sull'ordine delle
    #    scritture invece che sul merito.
    # ⚠️ `forzata` e' il SECONDO TEMPO della capienza (D14-d): il primo
    #    tentativo arriva senza, il guard rifiuta con la ragione e i numeri, e
    #    la conferma dell'operatore torna qui come `forzata = true` — che resta
    #    SCRITTA sulla riga, ed e' cio' che l'elenco a valle legge.
    def abbina_riga(
        self,
        *,
        riga_id: int,
        fattura_id: int,
        billing_account_id: int,
        scadenza_id: int | None,
        forzata: bool,
        motivo_forzatura: str | None,
        codice_stato_interno: str,
    ) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET fattura_id         = %s,
                   billing_account_id = %s,
                   scadenza_id        = %s,
                   forzata            = %s,
                   motivo_forzatura   = %s,
                   stato_id           = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(fattura_id), int(billing_account_id), scadenza_id,
                    bool(forzata), motivo_forzatura,
                    int(riga_id), codice_stato_interno,
                ],
            )
            return cursor.rowcount

    # Scopo: Elimina una riga — `attivo = false` (D17).
    # ⭐ E' la porta che il modello aveva gia' aperto: tutti i lettori (saldi,
    #    posting, quadratura, viste, e qui `list_righe`) filtrano `attivo`.
    #    Resta la traccia di chi ha tolto cosa (`user_update`/`data_update`).
    # ⛔ Nessun predicato qui: chi puo' e chi no lo dice
    #    `trgfn_vendite_contabili_righe_guard_contenuto`, leggendo la stessa
    #    check che alimenta `elimina_blocco_*` in lista.
    # ⚠️ `AND attivo IS TRUE`: su una riga gia' eliminata non si scrive niente
    #    (zero righe, e il service lo traduce in «non trovata»), e il guard non
    #    viene nemmeno svegliato per un `false -> false`.
    def disattiva_riga(self, riga_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(_RIGA_DISATTIVA, [int(riga_id)])
            return cursor.rowcount

    # Scopo: Le due matrici di transizione — testata e riga — come coppie di
    #        codici `(stato_da, stato_a)`, in una lettura sola.
    # ⭐ Sono catalogo (BE-5): il frontend costruisce le voci «Porta a …» da
    #    qui, ristrette dal service a cio' che una PERSONA puo' chiedere. Prima
    #    offriva il vocabolario intero meno lo stato corrente, e su una riga
    #    `ABBINATA` proponeva `SCARTATA`, che il guard rifiuta.
    # ⚠️ Gli stati RITIRATI (`obsoleto_dal`) escono da entrambi i lati: una
    #    transizione verso uno stato che non si propone piu' non e' un'uscita.
    # ⚠️ `UNION ALL` con una colonna discriminante e non due query: una
    #    lettura, e le due mappe non possono descrivere due istanti diversi.
    def list_transizioni(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        sql = f"""
            SELECT 'distinta' AS macchina, sd.codice_interno AS stato_da, sa.codice_interno AS stato_a
              FROM pagamenti.transizioni_stati_contabile t
              JOIN pagamenti.vendite_contabili_stati sd ON sd.id = t.stato_da_id
              JOIN pagamenti.vendite_contabili_stati sa ON sa.id = t.stato_a_id
             WHERE t.attivo IS TRUE
               AND {_sql_stato_vivo("sd")}
               AND {_sql_stato_vivo("sa")}
            UNION ALL
            SELECT 'riga', sd.codice_interno, sa.codice_interno
              FROM pagamenti.transizioni_stati_contabile_riga t
              JOIN pagamenti.vendite_contabili_righe_stati sd ON sd.id = t.stato_da_id
              JOIN pagamenti.vendite_contabili_righe_stati sa ON sa.id = t.stato_a_id
             WHERE t.attivo IS TRUE
               AND {_sql_stato_vivo("sd")}
               AND {_sql_stato_vivo("sa")}
             ORDER BY 1, 2, 3
        """  # noqa: S608 — _sql_stato_vivo() con alias letterali
        distinta: list[tuple[str, str]] = []
        riga: list[tuple[str, str]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql)
            for macchina, stato_da, stato_a in cursor.fetchall():
                (distinta if macchina == "distinta" else riga).append((stato_da, stato_a))
        return distinta, riga

    # ══════════════════════════════════════════════════════════════
    #  I saldi — le tre letture, e nient'altro le chiama
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il saldo di una RATA: residuo, in lavorazione, incassato.
    # ⭐ Tre numeri e non uno: «quanto manca», «quanto e' gia' digitato ma non
    #    registrato» e «quanto e' entrato davvero in banca» sono tre domande
    #    diverse, e la terza esclude i centri interni (fondi, compensazioni).
    # ⚠️ `escludi_riga_id` serve a chiedere lo spazio PRIMA DI SE': e' cosi' che
    #    si verifica se una riga ci sta, senza contarsi addosso.
    def get_saldo_rata(
        self, scadenza_id: int, *, escludi_riga_id: int | None = None
    ) -> dict[str, Any] | None:
        # Le tre funzioni di saldo sono SECURITY INVOKER: la row security del
        # chiamante si applica da sola, e su un ruolo che la scavalca
        # risponderebbero i numeri di TUTTI gli emittenti.
        self._guard_canale_sistema("get_saldo_rata")
        sql = """
            SELECT saldo, in_lavorazione, incassato, has_movimenti
              FROM pagamenti.fn_get_saldo_rata(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(scadenza_id), escludi_riga_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Il saldo di un DOCUMENTO: residuo e denaro in lavorazione.
    # ⭐ UNA query per due funzioni, e non e' solo un round-trip risparmiato su
    #    un pannello che si apre a ogni fattura: due `SELECT` separate leggono
    #    DUE ISTANTI diversi. Se una registrazione atterra fra l'una e l'altra,
    #    il pannello mostra un residuo di prima accanto a un «in lavorazione»
    #    di dopo — due numeri veri che insieme raccontano una cosa falsa.
    # ⭐ TRE numeri, dal 2026-08-29: la richiesta DB-10 e' atterrata il 25/08 e
    #    `fn_get_saldo_fattura` risponde `saldo, in_lavorazione, incassato,
    #    has_movimenti` — la stessa forma e lo stesso ordine della sorella della
    #    rata. Fino a ieri qui se ne leggevano DUE e l'`incassato` si buttava
    #    via: la richiesta che questo cantiere aveva fatto era stata esaudita e
    #    nessuno era passato a raccoglierla.
    # ⛔ E `in_lavorazione` si prende da `f`, non da `fn_get_saldo_fattura_contabili`:
    #    il numero e' lo stesso — la funzione delega proprio a quella — ma
    #    leggerlo dalla seconda gli darebbe DUE sorgenti con lo stesso nome, che
    #    e' cio' che il vincolo «una sede sola per i saldi» vieta.
    # ⭐ UNA funzione sola, e non e' un'ottimizzazione. Fino al 2026-08-29 qui
    #    c'era un `CROSS JOIN` con `fn_get_saldo_fattura_contabili` per prendere
    #    `has_righe_postabili`: quella colonna **non la legge nessuno** — ne'
    #    service, ne' view, ne' frontend — quindi il join faceva girare una
    #    seconda volta, a ogni apertura del drawer fattura, una funzione che
    #    `fn_get_saldo_fattura` chiama gia' al suo interno.
    #    ⚠️ E non era gratis: `fn_get_saldo_fattura` NON e' dichiarata STABLE (il
    #    suo ramo d'errore scrive nel registro), quindi due valutazioni sono due
    #    letture indipendenti — la trappola gia' pagata sul guard del fondo, dove
    #    una funzione VOLATILE letta due volte poteva accettare meta' condizione
    #    e rifiutare l'altra.
    #    📮 Se un giorno servira' `has_righe_postabili`, la sede giusta e'
    #    aggiungerlo a `fn_get_saldo_fattura` — che quella funzione la interroga
    #    gia' — non rimettere il join qui.
    # ⭐ `escludi_riga_id` dal 2026-09-18 (P-6 del brief D19): la stessa
    #    domanda della rata — «quanto c'era PRIMA di me» — con lo stesso nome
    #    di parametro, cosi' il pannello dice la stessa cosa ai due livelli.
    #    ⚠️ Semantica identica alla rata, ed e' una scelta del DB dichiarata nel
    #    changeSet: la riga esclusa esce dal DICHIARATO e, se e' gia'
    #    registrata, anche col suo MOVIMENTO — come nel nucleo `fn_get_saldi_rate`.
    def get_saldo_documento(
        self, fattura_id: int, *, escludi_riga_id: int | None = None
    ) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_saldo_documento")
        sql = """
            SELECT f.saldo, f.in_lavorazione, f.incassato, f.has_movimenti
              FROM pagamenti.fn_get_saldo_fattura(%s, %s) f
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id), escludi_riga_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Le rate di un documento, con il loro saldo accanto.
    # ⭐ Sta in `pagamenti` e non in `vendite` benche' le rate siano di vendite:
    #    la domanda e' «quanto resta su questa rata», e a saperla rispondere e'
    #    questo schema. ⚠️ E `vendite` non potrebbe chiederglielo: le chiamate
    #    laterali fra moduli di pari livello non sono ammesse (api.md).
    def list_rate_con_saldo(self, fattura_id: int) -> list[dict[str, Any]]:
        self._guard_canale_sistema("list_rate_con_saldo")
        # ⭐ `fattura_id` viaggia con la rata (2026-09-17, D19-c): il form della
        #    riga tiene «una rata resta scelta solo se e' del documento scelto»,
        #    e per dirlo la rata deve sapere di chi e' — la stessa chiave che
        #    porta la riga della lista rate (`vw_fatture_scadenze_lista`), cosi'
        #    le due sorgenti hanno la stessa forma.
        sql = """
            SELECT
                sc.id                AS scadenza_id,
                sc.fattura_id,
                sc.numero_rata,
                sc.data_scadenza,
                sc.importo,
                s.saldo              AS residuo,
                s.in_lavorazione,
                s.incassato,
                s.has_movimenti
              FROM vendite.fatture_scadenze sc
              CROSS JOIN LATERAL pagamenti.fn_get_saldo_rata(sc.id) s
             WHERE sc.fattura_id = %s
             ORDER BY sc.numero_rata NULLS LAST, sc.data_scadenza NULLS LAST, sc.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # Scopo: I saldi di UN INSIEME di rate in una chiamata — la «porta 3» del
    #        nucleo `pagamenti.fn_get_saldi_rate` (brief DB distinta-ricerca-rate,
    #        §4-bis.4): `{scadenza_id: {residuo, in_lavorazione, incassato,
    #        has_movimenti}}`.
    # ⛔ UNA chiamata con l'ARRAY, non una `LATERAL` per riga: provato dal team
    #    DB con EXPLAIN (§4-bis.9), `ARRAY[sc.id]` in `LATERAL` non piega il
    #    filtro dentro gli aggregati e diventa una scansione dei movimenti PER
    #    RATA. Con l'array costante della pagina il nucleo si inlinea e va a
    #    indice sui due parziali. ⚠️ E l'array e' OBBLIGATORIO: `NULL` non vuol
    #    dire «tutte» — per lo scadenzario c'e' `vw_saldi_rate`.
    # ⚠️ Il nucleo e' `security_invoker`: una rata fuori perimetro e' ZERO righe,
    #    non un errore — il chiamante confronta il numero delle risposte con
    #    quello delle domande. Una rata SENZA movimenti torna lo stesso (LEFT nel
    #    nucleo), con `has_movimenti = false`.
    # ⭐ Le chiavi escono col NOME della base dei saldi (`residuo`, non `saldo`):
    #    e' il vocabolario di `saldi_service.CAMPI_SALDO`, e chi consuma la
    #    riga della lista legge lo stesso nome del pannello.
    def get_saldi_rate(self, scadenza_ids: list[int]) -> dict[int, dict[str, Any]]:
        self._guard_canale_sistema("get_saldi_rate")
        if not scadenza_ids:
            return {}
        sql = """
            SELECT scadenza_id,
                   saldo AS residuo,
                   in_lavorazione,
                   incassato,
                   has_movimenti
              FROM pagamenti.fn_get_saldi_rate(%s::bigint[])
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [[int(i) for i in scadenza_ids]])
            righe = rows_to_list(cursor)
        return {int(r.pop("scadenza_id")): r for r in righe}

    # Scopo: L'ELENCO PAGINATO DELLE RATE (lista `pagamenti.rate`, id 68 — D19-c,
    #        2026-09-17): una riga per rata di `vendite.vw_fatture_scadenze_lista`
    #        col documento, il cliente e i tre saldi dalla base unica.
    # ⭐ PAGINA PRIMA, SALDO DOPO (brief DB §8): la query pagina la VISTA
    #    (`COUNT(*) OVER ()` nella stessa valutazione) e i saldi si chiedono al
    #    nucleo in una SECONDA query, sugli id della pagina. ⛔ Non nella stessa
    #    query del `COUNT(*) OVER ()`: girerebbe sul perimetro intero e non
    #    sulla pagina — il costo gia' letto sul piano della coda righe (EXPLAIN
    #    del 14/09 per la `LATERAL` dei motivi).
    # ⚠️ L'ECCEZIONE E' `solo_aperte`, e non puo' essere altrimenti: «aperta» =
    #    `saldo <> 0` (Q-B, Tid 2026-09-17) e' un predicato sul SALDO, quindi sta
    #    nel `WHERE` — e un `WHERE` non puo' aspettare la pagina. Li' il nucleo
    #    si chiama sul PERIMETRO (l'array delle rate che passano i filtri,
    #    `ARRAY(SELECT …)`) e i saldi escono dalla stessa query: e' il costo
    #    onesto che il brief DB ha accettato per quel filtro (§4.3 «col filtro
    #    solo aperte, di ogni rata del perimetro, perche' il filtro sta nel
    #    WHERE»). ⚠️ Sullo scadenzario intero (nessun criterio) e' il costo di
    #    `vw_saldi_rate`; sul perimetro di un cliente regge.
    # ⛔ `fattura_numero` e' un confronto ESATTO, non un `ILIKE`: nel lookup 101
    #    porta anche 1010 e 2101, ed e' giusto la'; qui chi digita un numero
    #    nel filtro vuole QUEL documento (brief §8). ⚠️ `search` e' un'ALTRA
    #    cosa, e dal 2026-09-24 cerca ANCHE il documento (decisione di Tid,
    #    brief-be-ricerca-full-liste-residue §7): e' la ricerca libera, che
    #    cade sulle colonne che il catalogo accende (`_RICERCA_RATE` ∩
    #    `ui.fn_lista_colonne_ricerca_full`), e li' «101» porta anche la 1010
    #    — come in ogni ricerca libera. Il filtro esatto resta com'e'.
    # ⚠️ Lo scope emittente applicativo si SOMMA alla RLS (api.md §Enforcement
    #    RLS), come sulla lista fatture da cui il lookup legge: `v.emittente_fiscale_id`
    #    e' la PK dell'emittente, convenzione `pk`.
    # ⛔ `solo_numerate` (Tid, rilievo in-app 2026-09-18): la rata di un documento
    #    NON numerato — una bozza, `numero IS NULL` — non e' un credito su cui
    #    registrare un incasso, e il picker la mostrava accanto alle altre. Il
    #    predicato sta in `_condizioni`, quindi vale anche sul PERIMETRO di
    #    `solo_aperte`: i due insiemi non possono divergere. ⏳ La regola di Tid
    #    e' piu' stretta — «solo le definitive, inviate a SDI» — ed e' un
    #    predicato di dominio che va in una sede sola a DB, non un secondo
    #    booleano qui (piano D19 §8).
    # ⭐ IL DEFAULT E' `True` DAL 2026-09-23 (decisione di Tid), e il cambio non
    #    e' cosmetico: e' un PERIMETRO di dominio, non un filtro dell'operatore.
    #    Fino a quel giorno il default era `False` e la regola viveva nel
    #    FRONTEND, che la mandava a ogni chiamata — cioe' una regola di dominio
    #    scritta nella presentazione, e vera solo per il client che si ricordava
    #    di dirla. ⚠️ Si vedeva da un sintomo piccolo: il picker contava «1
    #    filtro attivo» su un filtro che l'operatore non poteva toccare.
    #    ⇒ Chi vuole ANCHE le bozze lo chiede esplicitamente (`False`), e resta
    #    una domanda legittima: la via d'uscita non e' stata tolta, e' stata
    #    messa dalla parte giusta.
    def list_rate_paginata(
        self,
        *,
        auth_user_id: int | None,
        billing_account_id: int | None = None,
        fattura_numero: int | None = None,
        serie: str | None = None,
        anno: int | None = None,
        search: str | None = None,
        solo_aperte: bool = False,
        solo_numerate: bool = True,
        data_scadenza_da: date | None = None,
        data_scadenza_a: date | None = None,
        natura_doc_codice: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_rate_paginata")

        # Il perimetro emittente si risolve UNA volta: con `solo_aperte` la
        # stessa condizione entra due volte (pagina e perimetro del nucleo), e
        # risolverla per ogni entrata sarebbe una query in piu' per niente.
        scope_ids = (
            fetch_emittenti_scope_ids(auth_user_id, convention="pk")
            if auth_user_id is not None else None
        )

        # Scopo: le condizioni della lista su un ALIAS dato — la stessa funzione
        #        per la pagina (`v`) e per il perimetro del nucleo (`p`), cosi'
        #        i due insiemi non possono divergere.
        def _condizioni(alias: str) -> tuple[list[str], list[Any]]:
            conditions: list[str] = []
            params: list[Any] = []
            if billing_account_id is not None:
                conditions.append(f"{alias}.billing_account_id = %s")
                params.append(billing_account_id)
            if fattura_numero is not None:
                conditions.append(f"{alias}.numero = %s")
                params.append(fattura_numero)
            if serie is not None:
                conditions.append(f"{alias}.serie = %s")
                params.append(serie)
            if anno is not None:
                conditions.append(f"{alias}.anno = %s")
                params.append(anno)
            # ⭐ Il BB DENTRO la funzione dell'alias, non fuori: pagina e
            #    perimetro ricevono la stessa condizione sulla loro relazione,
            #    e i due insiemi non possono divergere (brief §5.1). ⚠️ Con
            #    `solo_aperte` il catalogo si legge due volte nella stessa
            #    richiesta: e' il prezzo della sede unica, e una query leggera.
            add_ricerca_full_condition(conditions, params, search, _RICERCA_RATE, alias=alias)
            if data_scadenza_da is not None:
                conditions.append(f"{alias}.data_scadenza >= %s")
                params.append(data_scadenza_da)
            if data_scadenza_a is not None:
                conditions.append(f"{alias}.data_scadenza <= %s")
                params.append(data_scadenza_a)
            if natura_doc_codice is not None:
                conditions.append(f"{alias}.natura_doc_codice_interno = %s")
                params.append(natura_doc_codice)
            # Il numero e' NULL finche' il documento non e' DEFINITIVA: e' il
            # solo fatto della vista che dice «numerato», e la vista lo porta
            # apposta accanto a `numero_documento` (P-2).
            if solo_numerate:
                conditions.append(f"{alias}.numero IS NOT NULL")
            add_emittente_scope_condition_risolta(
                conditions, params,
                scope_ids=scope_ids,
                column=f"{alias}.emittente_fiscale_id",
            )
            return conditions, params

        conditions, params = _condizioni("v")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # ⚠️ `default_desc=False` e' la scelta, non l'omissione: e' una coda
        #    (vedi `RATE_SORT_COLONNE_DATA`). Il tiebreak `scadenza_id` e' la
        #    chiave della vista — la PK della rata.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RATE_SORT_COLUMNS,
            default="data_scadenza",
            tiebreak="scadenza_id",
            colonne_desc=RATE_SORT_COLONNE_DATA,
        )

        if solo_aperte:
            # Il perimetro e' la STESSA `FROM`+`WHERE` della pagina: l'array del
            # nucleo e la lista che lo legge devono parlare dello stesso insieme.
            cond_p, params_p = _condizioni("p")
            where_p = ("WHERE " + " AND ".join(cond_p)) if cond_p else ""
            perimetro_sql = (
                f"SELECT p.scadenza_id FROM vendite.vw_fatture_scadenze_lista p {where_p}"  # noqa: S608 — where_p da frammenti letterali di _condizioni con alias letterale, valori come parametri
            )
            select_sql = f"""
                SELECT v.*,
                       s.saldo AS residuo,
                       s.in_lavorazione,
                       s.incassato,
                       s.has_movimenti
                  FROM vendite.vw_fatture_scadenze_lista v
                  JOIN pagamenti.fn_get_saldi_rate(ARRAY({perimetro_sql})::bigint[]) s
                    ON s.scadenza_id = v.scadenza_id
                 {where}{" AND" if where else " WHERE"} s.saldo <> 0
            """  # noqa: S608
            return self._lista_paginata(
                select_sql=select_sql,
                # Prima i parametri del perimetro (l'`ARRAY(...)` sta nella
                # `FROM`), poi quelli del `WHERE` della pagina: l'ordine e'
                # quello in cui psycopg incontra i `%s`.
                params=[*params_p, *params],
                order_clause=f"ORDER BY {ordinamento}",
                limit=limit,
                offset=offset,
            )

        rows, total = self._lista_paginata(
            select_sql=f"SELECT v.* FROM vendite.vw_fatture_scadenze_lista v {where}",  # noqa: S608
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )
        saldi = self.get_saldi_rate([int(r["scadenza_id"]) for r in rows])
        # Il nucleo risponde per OGNI rata visibile (LEFT sulle senza
        # movimenti): una rata della pagina senza saldo e' un contratto rotto,
        # non un dato da riempire con dei NULL — e va detto, non nascosto.
        mancanti = [int(r["scadenza_id"]) for r in rows if int(r["scadenza_id"]) not in saldi]
        ErrorManager.require(
            not mancanti,
            code=_E_CHIAMATA,
            message="Il saldo di una rata della pagina non e' stato restituito.",
            detail=f"pagamenti.fn_get_saldi_rate senza riga per scadenza_id={mancanti}",
            function_name=f"{_FN}.list_rate_paginata",
        )
        for r in rows:
            r.update(saldi[int(r["scadenza_id"])])
        return rows, total

    # ══════════════════════════════════════════════════════════════
    #  Le due code di lavoro
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di TUTTE le distinte in uno degli stati chiesti — la coda
    #        del riconciliatore.
    # ⭐ Un endpoint solo per due code: «da abbinare» e «sospese» sono due
    #    mestieri diversi (D12-f) e due voci di menu, ma la stessa lista con un
    #    filtro diverso gia' impostato. Due definizioni a catalogo per due
    #    schermate identiche sarebbero due cose da tenere allineate.
    def list_righe_coda(
        self,
        *,
        stati: tuple[str, ...],
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        search: str | None = None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[RigaCodaRow], int]:
        self._guard_canale_sistema("list_righe_coda")

        # ⭐ La coda e' una lista di LAVORO: cio' che non si lavora non ci sta.
        #    Una riga DA_ABBINARE sotto una distinta ANNULLATA restava qui per
        #    sempre, con ogni azione spenta (brief-db-righe-distinta-annullata-
        #    fuori-dalle-code §1). La condizione e' la bandiera del catalogo,
        #    non `NOT is_final`: sotto una CHIUSA le sospese si lavorano ancora
        #    (la tardiva, D20-b). ⚠️ `IS TRUE`: con la LEFT JOIN, uno stato non
        #    letto non si dice «lavorabile» (fail-closed, come il default).
        conditions = [
            "r.attivo IS TRUE",
            "rs.codice_interno = ANY(%s)",
            "cst.righe_lavorabili IS TRUE",
        ]
        params: list[Any] = [list(stati)]
        if billing_account_id is not None:
            conditions.append("r.billing_account_id = %s")
            params.append(billing_account_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_RIGHE_CODA)

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RIGHE_SORT_COLUMNS,
            default="data_pagamento",
            tiebreak="id",
            default_desc=True,
        )

        rows, total = self._lista_paginata(
            select_sql=f'{_RIGA_CODA_SELECT} WHERE {" AND ".join(conditions)}',
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
            dopo_pagina=_sql_con_elimina,
        )
        return [cast(RigaCodaRow, row) for row in rows], total

    # Scopo: L'elenco delle rate uscite dalla banda di capienza.
    # ⭐ Senza questo elenco la forzatura sarebbe «un modo per nascondere, non
    #    per registrare»: e' la ragione per cui la vista sta nello stesso lotto
    #    del guard che permette di forzare.
    # ⚠️ `motivo` ha due valori e vanno mostrati entrambi: `SOVRA_INCASSATA` e
    #    `MOVIMENTO_CONTRARIO` — un rimborso dove non era entrato niente e' il
    #    caso che ha fatto cadere l'asimmetria di D1-bis.
    def list_rate_fuori_capienza(
        self,
        *,
        motivo: str | None = None,
        billing_account_id: int | None = None,
        search: str | None = None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_rate_fuori_capienza")

        conditions: list[str] = []
        params: list[Any] = []
        if motivo is not None:
            conditions.append("v.motivo = %s")
            params.append(motivo)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_RATE_FUORI_CAPIENZA)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RATE_FUORI_CAPIENZA_SORT_COLUMNS,
            default="data_scadenza",
            tiebreak="scadenza_id",
            default_desc=True,
        )

        return self._lista_paginata(
            select_sql=(
                f"SELECT v.* FROM pagamenti.vw_rate_fuori_capienza v {where_clause}"  # noqa: S608 — WHERE da frammenti letterali + colonne _RICERCA_RATE_FUORI_CAPIENZA, valori come parametri
            ),
            params=params,
            order_clause=(
                f"ORDER BY {ordinamento}"
            ),
            limit=limit,
            offset=offset,
        )

    # ══════════════════════════════════════════════════════════════
    #  I canali di incasso — da dove arrivano i soldi
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco dei canali, coi display field di chi li guarda.
    # ⭐ Il **conto** e' in JOIN e non e' un dettaglio: e' da li' che il
    #    database ricava di chi sono i soldi arrivati prima della fattura, ed e'
    #    la colonna che rende leggibile una riga di configurazione altrimenti
    #    fatta di id.
    def list_enti_incasso(
        self,
        *,
        tipo: str | None = None,
        centro_riscossione_id: int | None = None,
        attivo: bool | None = None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_enti_incasso")

        conditions: list[str] = []
        params: list[Any] = []
        if tipo is not None:
            conditions.append("e.tipo = %s")
            params.append(tipo)
        if centro_riscossione_id is not None:
            conditions.append("e.centro_riscossione_id = %s")
            params.append(centro_riscossione_id)
        if attivo is not None:
            conditions.append("e.attivo = %s")
            params.append(attivo)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ENTI_INCASSO_SORT_COLUMNS,
            default="codice",
            tiebreak="id",
        )

        select_sql = f"""
            {_ENTE_INCASSO_SELECT}
            {where_clause}
        """
        return self._lista_paginata(
            select_sql=select_sql,
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )

    # Scopo: Il dettaglio di un canale.
    def get_ente_incasso(self, ente_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_ente_incasso")
        sql = f"{_ENTE_INCASSO_SELECT} WHERE e.id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ente_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: L'emittente indicato e' dentro il perimetro di chi sta chiedendo?
    # 🔴 Serve perche' `anagrafiche.soggetti_ruoli_conti_bancari` ha la row
    #    security SPENTA di proposito: la' il perimetro non lo mette il
    #    database, quindi se non lo mette il backend non lo mette nessuno.
    #    ⛔ Misurato il 2026-08-28 (E-4): senza questa domanda un operatore
    #    dell'emittente A leggeva l'IBAN di incasso dell'emittente B passando il
    #    suo `soggetto_ruolo_id` — e senza nessun errore.
    # ⛔ SENZA UTENTE NON SI PASSA, e non e' pignoleria: la canonica
    #    `fn_check_user_emittente_scope` risponde **true** quando
    #    `p_auth_user_id` e' NULL (regola 1, «job batch»). Delegarle la domanda
    #    su un percorso senza GUC aprirebbe il perimetro invece di chiuderlo:
    #    qui «non so chi sei» vale **no**.
    def emittente_nel_perimetro(self, emittente_soggetto_ruolo_id: int) -> bool:
        self._guard_canale_sistema("emittente_nel_perimetro")
        # L'utente per cui la connessione agisce, dalla GUC delle policy RLS
        # (BB `utente_di_sessione`: il nome della GUC e il suo tranello stanno
        # li'). Senza utente non c'e' perimetro: si rifiuta.
        auth_user_id = utente_di_sessione()
        if auth_user_id is None:
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(script.fn_scope_ef_whitelist_via_sr(%s, %s), false)",
                [auth_user_id, int(emittente_soggetto_ruolo_id)],
            )
            return bool(cursor.fetchone()[0])

    # Scopo: I conti che un emittente puo' agganciare a un canale.
    # 🔴 **Solo quelli con `uso = 'INCASSO'`**, ed e' la richiesta BE-8: il
    #    database rifiuta gli altri con un errore parlante, ma un elenco che li
    #    propone fa sbagliare — e chi sbaglia se ne accorge dopo aver compilato
    #    tutto il resto.
    # ⚠️ Il livello e' quello del RUOLO (`soggetti_ruoli_conti_bancari`) e non
    #    del soggetto: e' li' che vive l'unicita' «un conto INCASSO -> un solo
    #    soggetto», che e' la garanzia da cui il perimetro degli incassi dipende.
    #    Un conto censito solo a livello soggetto NON e' agganciabile, e non e'
    #    una svista del modello: e' quella garanzia.
    def list_conti_incasso(self, soggetto_ruolo_id: int) -> list[dict[str, Any]]:
        self._guard_canale_sistema("list_conti_incasso")
        # 🔴 IL PERIMETRO, e sta QUI e non nel service: e' lo stesso posto e la
        #    stessa ragione di `_guard_canale_sistema` — il repository e'
        #    l'ultimo cancello prima della stringa SQL, e un controllo un piano
        #    piu' su lo salta il secondo chiamante che nascera'.
        # ⚠️ Si RIFIUTA, non si risponde vuoto: un elenco vuoto direbbe «questo
        #    emittente non ha conti di incasso», che e' un'altra frase — e
        #    falsa. E' la trappola del conteggio fail-closed.
        ErrorManager.require(
            self.emittente_nel_perimetro(soggetto_ruolo_id),
            code=_E_SCOPE_EMITTENTE,
            message="Questo emittente non e' nel tuo perimetro.",
            detail=f"soggetto_ruolo_id={soggetto_ruolo_id}",
            context={"field": "soggetto_ruolo_id"},
            function_name=f"{_FN}.list_conti_incasso",
        )
        sql = f"""
            SELECT src.id            AS soggetto_ruolo_conto_bancario_id,
                   src.soggetto_ruolo_id,
                   src.predefinito,
                   src.intestazione_dichiarata,
                   cb.id             AS conto_bancario_id,
                   cb.iban,
                   cb.bic_swift,
                   cb.intestatario_predefinito,
                   -- ⭐ La utility del conto: qui e' la tendina in cui si SCEGLIE,
                   --    quindi e' il punto in cui non dirla fa sbagliare (BE-11).
                   src.istanza_utility_id AS conto_istanza_utility_id,
                   u.descrizione     AS conto_utility_descrizione
              FROM anagrafiche.soggetti_ruoli_conti_bancari src
              JOIN anagrafiche.conti_bancari cb ON cb.id = src.conto_bancario_id
              {_UTILITY_DEL_CONTO_JOIN}
             WHERE src.soggetto_ruolo_id = %s
               AND src.uso = 'INCASSO'
               AND src.bloccato IS NOT TRUE
               -- Le date di validita' ordinano e filtrano sempre: un conto
               -- scaduto non si propone. `COALESCE(valido_al, 'infinity')`
               -- perche' scadenza vuota = validita' infinita.
               AND (src.valido_dal IS NULL OR src.valido_dal <= (SELECT script.fn_data_operativa()))
               AND COALESCE(src.valido_al, 'infinity'::date) >= (SELECT script.fn_data_operativa())
             ORDER BY src.predefinito DESC, cb.iban
        """  # noqa: S608 — _UTILITY_DEL_CONTO_JOIN costante di modulo, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(soggetto_ruolo_id)])
            return rows_to_list(cursor)

    # Scopo: Crea un canale di incasso.
    # ⚠️ Nessuna funzione madre: e' un `INSERT` su una tabella di
    #    configurazione, e i quattro guard (tipo/filiale, conto di incasso,
    #    coerenza PSP, scope emittente) parlano da soli.
    # ⭐ Stesso cancello dell'UPDATE (`_verifica_colonne`) e stessa regola
    #    jsonb (`_JSONB_COLS`), via il BB `execute_dynamic_insert`.
    def create_ente_incasso(self, campi: dict[str, Any]) -> int:
        self._verifica_colonne(
            campi, _COLONNE_ENTE_INCASSO_INSERIBILI, "create_ente_incasso"
        )
        riga = execute_dynamic_insert(
            "pagamenti.enti_incasso",
            campi,
            allowed=_COLONNE_ENTE_INCASSO_INSERIBILI,
            jsonb=_JSONB_COLS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna un canale di incasso.
    def update_ente_incasso(self, ente_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_ENTE_INCASSO_AGGIORNABILI, "update_ente_incasso"
        )
        params.append(int(ente_id))
        sql = f"""
            UPDATE pagamenti.enti_incasso
               SET {set_clause}
             WHERE id = %s
        """  # noqa: S608 — SET da _set_clause su whitelist _COLONNE_ENTE_INCASSO_AGGIORNABILI, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  Le sistemazioni — il denaro di troppo
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco dei documenti su cui e' entrato piu' del dovuto.
    # ⭐ La vista porta GIA' il raggruppamento per cliente in finestra
    #    (`eccedenza_cliente`, `documenti_cliente`): qui non si somma niente —
    #    rifarlo in Python sarebbe una seconda aritmetica da tenere allineata.
    # ⚠️ Il nome del cliente NON e' nella vista: si aggiunge in JOIN, perche' un
    #    elenco che si guarda per cliente e mostra un id non si guarda.
    def list_eccedenze(
        self,
        *,
        chi_e_in_credito: str | None = None,
        billing_account_id: int | None = None,
        search: str | None = None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_eccedenze")

        conditions: list[str] = []
        params: list[Any] = []
        if chi_e_in_credito is not None:
            conditions.append("v.chi_e_in_credito = %s")
            params.append(chi_e_in_credito)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ECCEDENZE)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sort_col = colonna_ordinamento(order_by, ECCEDENZE_SORT_COLUMNS) or "eccedenza_cliente"
        direction = sql_order_direction(order_dir, default_desc=True)
        tiebreak = sql_tiebreak_direction(direction)

        select_sql = f"""
            SELECT v.*,
                   srd.ragione_sociale_completa AS cliente_ragione_sociale
              FROM pagamenti.vw_eccedenze_da_sistemare v
              LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                     ON srd.soggetto_ruolo_id = v.cliente_soggetto_ruolo_id
              {where_clause}
        """  # noqa: S608 — WHERE da frammenti letterali + colonne _RICERCA_ECCEDENZE, valori come parametri
        return self._lista_paginata(
            select_sql=select_sql,
            params=params,
            # ⚠️ Tiebreak sul CLIENTE prima che sul documento: ordinando per
            # eccedenza di cliente, i documenti dello stesso cliente devono
            # restare insieme — altrimenti l'elenco «per cliente» li sparpaglia.
            order_clause=(
                f"ORDER BY {sort_col} {direction}, "
                f"cliente_soggetto_ruolo_id {tiebreak}, fattura_id {tiebreak}"
            ),
            limit=limit,
            offset=offset,
        )

    # Scopo: Cliente ed emittente di una fattura, DERIVATI e non dichiarati.
    # 🔴 Il guard sui dati li verifica con un codice TECNICO apposta: «l'emittente
    #    e il cliente non li sceglie una persona in un modulo, li DERIVA chi
    #    costruisce l'atto». Prenderli dal payload significherebbe far arrivare
    #    al database una dichiarazione che il database sa gia' — e che, se
    #    sbagliata, il suo autore non puo' correggere.
    # ⚠️ Lettura sotto RLS: una fattura fuori perimetro non risponde, e il
    #    chiamante lo traduce in «non trovata».
    def get_riferimenti_fattura(self, fattura_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_riferimenti_fattura")
        sql = """
            SELECT f.id                       AS fattura_id,
                   f.emittente_soggetto_ruolo_id,
                   f.billing_account_id,
                   ba.soggetto_ruolo_id       AS cliente_soggetto_ruolo_id
              FROM vendite.fatture f
              JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Di quale documento e' una rata — la sola cosa che il verbo
    #        «righe da rate» (D19-d) deve risolvere prima di chiamare la nascita
    #        della riga, che vuole la fattura.
    # ⚠️ Sotto RLS: una rata fuori perimetro e' `None`, indistinguibile da una
    #    inesistente — ed e' voluto, come per ogni lettura per id del dominio.
    def get_fattura_id_di_rata(self, scadenza_id: int) -> int | None:
        self._guard_canale_sistema("get_fattura_id_di_rata")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT fattura_id FROM vendite.fatture_scadenze WHERE id = %s",
                [int(scadenza_id)],
            )
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Registra l'atto di sistemazione.
    # ⭐ Un `INSERT`, non una funzione madre: una scrittura sola non ha bisogno
    #    di una madre, e inventarne una avrebbe aggiunto un oggetto che non
    #    garantisce niente in piu'.
    # ⚠️ Nasce in `BOZZA` (default di colonna): registrare una decisione non e'
    #    ancora eseguirla — il denaro si muove alla conferma.
    def create_sistemazione(
        self,
        *,
        destinazione: str,
        importo: Decimal,
        fattura_origine_id: int,
        cliente_soggetto_ruolo_id: int,
        emittente_soggetto_ruolo_id: int,
        fattura_destinazione_id: int | None = None,
        motivo: str | None = None,
        meta: str = "{}",
    ) -> int:
        sql = """
            INSERT INTO pagamenti.sistemazioni (
                destinazione, importo, fattura_origine_id, fattura_destinazione_id,
                cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id, motivo, meta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    destinazione, importo, int(fattura_origine_id),
                    fattura_destinazione_id, int(cliente_soggetto_ruolo_id),
                    int(emittente_soggetto_ruolo_id), motivo, meta,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Un atto di sistemazione, con i display field di chi lo legge.
    def get_sistemazione(self, sistemazione_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_sistemazione")
        sql = """
            SELECT s.id, s.destinazione, s.stato, s.importo, s.motivo,
                   s.fattura_origine_id, fo.numero AS fattura_origine_numero,
                   fo.anno AS fattura_origine_anno, fo.serie AS fattura_origine_serie,
                   s.fattura_destinazione_id, fd.numero AS fattura_destinazione_numero,
                   fd.anno AS fattura_destinazione_anno,
                   fd.serie AS fattura_destinazione_serie,
                   s.cliente_soggetto_ruolo_id,
                   srd.ragione_sociale_completa AS cliente_ragione_sociale,
                   s.emittente_soggetto_ruolo_id,
                   s.contabile_id, s.fondo_source_id,
                   s.data_esecuzione, s.user_esecuzione,
                   s.data_insert, s.user_insert, s.meta
              FROM pagamenti.sistemazioni s
              LEFT JOIN vendite.fatture fo ON fo.id = s.fattura_origine_id
              LEFT JOIN vendite.fatture fd ON fd.id = s.fattura_destinazione_id
              LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                     ON srd.soggetto_ruolo_id = s.cliente_soggetto_ruolo_id
             WHERE s.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Gli atti registrati su un documento.
    # ⭐ Sono PIU' DI UNO per natura: si puo' rimborsare una parte e riportare il
    #    resto, e l'elenco delle eccedenze conta apposta le bozze e le confermate
    #    separatamente.
    # ⭐ PAGINATA dal 2026-09-02 (decisione di Tid). Prima consegnava TUTTI gli
    #    atti in un colpo e il totale veniva da una query separata
    #    (`count_sistemazioni_fattura`, ora sparita): due valutazioni dello
    #    stesso predicato possono non concordare, una sola non puo'.
    # ⚠️ `limit=None` NON e' un ripiego per pigrizia: e' il modo in cui un
    #    chiamante dichiara di volere il dataset intero (l'export). Il totale
    #    resta quello vero perche' lo dice `COUNT(*) OVER ()`, che non guarda
    #    la finestra.
    def list_sistemazioni_fattura(
        self,
        fattura_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_sistemazioni_fattura")
        # ⭐ `default_desc=True` — decisione di Tid del 2026-09-02: **l'ultimo
        #    atto deciso sta in cima**. Prima era `s.id ASC`, e finche' la lista
        #    non impaginava non si vedeva; da quando impagina, un atto appena
        #    registrato finiva nell'ULTIMA pagina e chi l'aveva appena creato non
        #    lo vedeva. ⚠️ E' anche il verso del registro gemello qui accanto
        #    (`list_movimenti`, «il piu' recente per primo, che e' come si legge
        #    un registro»): due elenchi della stessa cosa non devono leggersi al
        #    contrario l'uno dell'altro.
        # ⛔ Il tiebreak `s.id` NON e' estetica da quando la lista impagina:
        #    senza, a offset diversi PostgreSQL puo' consegnare due volte la
        #    stessa riga e mai un'altra. Lo scrive il BB, allineato alla
        #    direzione primaria — e lo OMETTE quando la colonna e' gia' `s.id`.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=SISTEMAZIONI_SORT_COLUMNS,
            default="s.id",
            tiebreak="s.id",
            default_desc=True,
            colonne_desc=SISTEMAZIONI_SORT_COLONNE_DATA,
        )
        # ⛔ LIMIT/OFFSET solo se il chiamante impagina: una `LIMIT NULL` sarebbe
        #    legale in PostgreSQL ma legherebbe la query a un parametro in piu'
        #    senza che serva a nessuno.
        paginazione = "" if limit is None else "\n             LIMIT %s OFFSET %s"
        params: list[Any] = [int(fattura_id)]
        if limit is not None:
            params += [limit, offset]
        data_sql = f"""
            SELECT s.id, s.destinazione, s.stato, s.importo, s.motivo,
                   s.fattura_destinazione_id, s.contabile_id, s.fondo_source_id,
                   s.data_esecuzione, s.user_esecuzione, s.data_insert,
                   COUNT(*) OVER () AS total_count
             {_SISTEMAZIONI_FROM_WHERE}
             ORDER BY {ordinamento}{paginazione}
        """
        return fetch_paged_with_total(
            data_sql,
            params,
            # ⛔ Il conteggio di ripiego riusa lo STESSO `FROM`/`WHERE` della
            #    pagina, e non e' cerimonia: due predicati scritti a mano
            #    divergono, e il giorno in cui divergono il totale parla di un
            #    insieme diverso da quello che si sta guardando.
            fallback_count_sql=(
                f"SELECT count(*) {_SISTEMAZIONI_FROM_WHERE}"
            ),
            fallback_params=[int(fattura_id)],
            offset=offset,
        )

    # Scopo: Esegue l'atto — la decisione diventa un fatto.
    # ⭐ UNA SOLA `SELECT` sulla funzione madre: sceglie la strada (fondo,
    #    distinta negativa, distinta di compensazione) e ci mette sopra il
    #    denaro. ⛔ Nessuna delle tre macchine e' nuova, e nessuna la orchestra
    #    il backend.
    # ⚠️ `ente_incasso_id` si chiede QUI e non alla registrazione: «da quale
    #    conto esce il bonifico» e' una decisione del momento in cui si paga.
    def conferma_sistemazione(
        self, sistemazione_id: int, *, ente_incasso_id: int | None = None
    ) -> dict[str, Any] | None:
        sql = """
            SELECT contabile_id, fondo_source_id, esito
              FROM pagamenti.fn_conferma_sistemazione(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id), ente_incasso_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Scarta l'atto, lasciandolo a registro con la sua ragione.
    # ⚠️ Il motivo si FONDE con quello gia' scritto: se l'atto ne aveva uno e la
    #    chiamata arriva vuota, resta quello che c'era.
    def annulla_sistemazione(
        self, sistemazione_id: int, *, motivo: str | None = None
    ) -> str | None:
        sql = "SELECT pagamenti.fn_annulla_sistemazione(%s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id), motivo])
            row = cursor.fetchone()
        return row[0] if row else None

    # ══════════════════════════════════════════════════════════════
    #  La madre del posting
    # ══════════════════════════════════════════════════════════════

    # Scopo: Registra la distinta — trasforma in movimenti contabili le righe
    #        pronte a diventarlo, e chiude la distinta.
    # ⭐ UNA SOLA `SELECT`, quindi atomica per costruzione: l'atomicita' e'
    #    DENTRO la funzione. ⛔ Nessun `transaction.atomic()` attorno a piu'
    #    statement, nessun ciclo che posta le righe una a una.
    # ⚠️ `righe_attese` e `totale_atteso` sono la DICHIARAZIONE di chi conferma
    #    (quante righe pronte aveva davanti e per che totale): sono facoltativi
    #    ma LEGATI — o tutti e due o nessuno. Mezza dichiarazione non si puo'
    #    verificare, e accettarla significherebbe registrare senza controllo
    #    credendo di averlo fatto.
    # ⭐ Non solleva su «niente da registrare»: risponde `NULLA_DA_POSTARE` ed
    #    e' un esito, non un errore. Il backend lo passa senza interpretarlo.
    def posta_contabile(
        self,
        *,
        contabile_id: int,
        righe_attese: int | None = None,
        totale_atteso: Decimal | None = None,
    ) -> RicevutaPosting:
        sql = """
            SELECT movimenti_creati, righe_postate, righe_saltate,
                   totale_postato, esito
              FROM pagamenti.fn_posta_contabile(
                   p_contabile_id  := %s,
                   p_righe_attese  := %s,
                   p_totale_atteso := %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), righe_attese, totale_atteso])
            rows = rows_to_list(cursor)
        # La funzione ritorna sempre una riga: se non ci fosse, il contratto
        # sarebbe cambiato sotto e tacere sarebbe la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La registrazione non ha prodotto nessuna ricevuta.",
            detail="pagamenti.fn_posta_contabile non ha restituito righe.",
            function_name=f"{_FN}.posta_contabile",
        )
        return rows[0]  # type: ignore[return-value]

    # Scopo: La registrazione TARDIVA di una riga (D20-b, P-5): una `SOSPESA`
    #        sotto una distinta gia' registrata si abbina E si registra nello
    #        stesso gesto — movimento scritto, riga a `POSTATA`, distinta che
    #        resta `CHIUSA`.
    # ⭐ UNA SOLA `SELECT` sulla madre, come per il posting: i tre statement
    #    (riga → ABBINATA coi guard dell'abbinamento, movimento, riga → POSTATA)
    #    e la porta della quarta mossa (GUC transazionale) stanno DENTRO la
    #    funzione. ⛔ Nessun `abbina_riga` + `set_stato_riga` da qui: sotto una
    #    CHIUSA il secondo verrebbe rifiutato, e il primo resterebbe scritto.
    # ⚠️ `forzata` e' il SECONDO TEMPO della capienza, intatto: il primo
    #    tentativo arriva senza, il guard della rata rifiuta con
    #    `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` (`confirm_and_retry`), e la
    #    conferma torna qui come `forzata = true`.
    # ⛔ Nessun `NULLA_DA_POSTARE`: una tardiva su una riga che non si puo'
    #    registrare e' un RIFIUTO della madre (`E_RIGA_CONTABILE_TARDIVA_*`),
    #    non un esito — chi preme ha identificato quel denaro.
    def posta_riga_tardiva(
        self,
        *,
        riga_id: int,
        fattura_id: int,
        billing_account_id: int,
        scadenza_id: int | None,
        forzata: bool,
        motivo_forzatura: str | None,
    ) -> RicevutaTardiva:
        self._guard_canale_sistema("posta_riga_tardiva")
        with connection.cursor() as cursor:
            cursor.execute(
                _POSTA_RIGA_TARDIVA,
                [
                    int(riga_id), int(fattura_id), int(billing_account_id),
                    scadenza_id, bool(forzata), motivo_forzatura,
                ],
            )
            rows = rows_to_list(cursor)
        # La madre risponde SEMPRE una riga, o solleva: senza righe il contratto
        # e' cambiato sotto, e tacere su un gesto che ha scritto un movimento e'
        # la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La registrazione tardiva non ha prodotto nessuna ricevuta.",
            detail="pagamenti.fn_posta_riga_tardiva non ha restituito righe.",
            function_name=f"{_FN}.posta_riga_tardiva",
        )
        return rows[0]  # type: ignore[return-value]

    # Scopo: La CORREZIONE GUIDATA (Q-7) — apre una distinta nuova con le righe
    #        di segno opposto gia' dentro.
    # ⭐ UNA SOLA `SELECT` sulla madre, come le altre tre: la distinta e le sue N
    #    righe nascono atomiche per costruzione. ⛔ Nessun ciclo nel service —
    #    produrrebbe una distinta a meta' se qualcosa si rompe a meta' elenco,
    #    cioe' esattamente il documento che nessuno sa piu' leggere.
    # ⛔ E non e' uno «storno»: `STORNATA` e' stata ritirata dal catalogo il
    #    21/08, e rimetterne la parola riaprirebbe una porta che il lotto 2 ha
    #    chiuso. Si chiama correzione.
    # ⭐ Non solleva su «niente da correggere»: risponde `NULLA_DA_CORREGGERE`
    #    con `contabile_id` a NULL, ed e' un ESITO — il backend lo passa senza
    #    interpretarlo, come gia' fa con `NULLA_DA_POSTARE`.
    def crea_distinta_correzione(
        self,
        *,
        contabile_id: int,
        data_contabile: date | None = None,
        motivo: str | None = None,
    ) -> dict[str, Any]:
        self._guard_canale_sistema("crea_distinta_correzione")
        sql = """
            SELECT contabile_id, righe_create, righe_saltate, esito
              FROM pagamenti.fn_crea_distinta_correzione(
                       %s, COALESCE(%s::date, (SELECT script.fn_data_operativa())), %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), data_contabile, motivo])
            rows = rows_to_list(cursor)
        # La funzione risponde SEMPRE una riga, anche sul nulla da correggere.
        # Se non lo facesse, il contratto sarebbe cambiato sotto — e tacere su
        # un gesto che ha creato un documento e' la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La correzione non ha prodotto nessun esito.",
            detail="pagamenti.fn_crea_distinta_correzione non ha restituito righe.",
            function_name=f"{_FN}.crea_distinta_correzione",
        )
        return rows[0]

