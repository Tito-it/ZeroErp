# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura del REGISTRO DEI PROCESSI AUTOMATICI (`dbops.processi` e le sue
#        due tabelle satellite) e del ROSTER — chi lavora per conto di chi:
#        l'utente tecnico di un processo, per ogni emittente che quel processo
#        serve.
# Note: ⭐ Sta in `apps/core` e non in `apps/amm_software`, e non e' pedanteria
#        di layering: il roster serve al PRODUTTORE della fatturazione e al
#        worker della coda stampa, che vivono in `apps/vendite` — e `api.md`
#        vieta le chiamate laterali fra moduli allo stesso livello. Il pezzo
#        riusabile sta nell'anello interno; chi lo ESPONE (l'amministrazione)
#        ci costruisce sopra le proprie view.
#        ⚠️ Ne' `dbops.processi_identita` ne' `config.user_emittenti_fiscali`
#        hanno RLS: la lettura senza contesto operatore vede tutto, ed e' cio'
#        che serve a un produttore headless. ⛔ Il giorno in cui una delle due
#        l'avesse, questa lettura tornerebbe ZERO righe e il produttore
#        accoderebbe zero lavori chiudendo con «FATTO, 0» — un guasto che non
#        assomiglia a un errore ([[feedback_rls_conteggio_zero_non_e_un_dato]]).
#        Brief: work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypedDict

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)


# Scopo: una riga del roster — l'identita' con cui un processo lavora UN
#        emittente. E' la forma che `operator_identity_context` pretende
#        (auth_user_id + username + identita_id), piu' l'emittente.
class RigaRoster(TypedDict):
    auth_user_id: int
    username: str
    identita_id: int
    emittente_fiscale_id: int
    emittente_codice: str
    emittente_soggetto_ruolo_id: int | None


# Scopo: il CONTRATTO DI LIVENESS di un processo, come lo dichiara il catalogo
#        (`dbops.processi`, colonne entrate il 2026-09-11 — brief
#        `brief-db-quattro-processi-senza-presidio.md` §10.2, decisione D5).
#        `tolleranza_minuti`: «se sto bene, lascio un segno almeno ogni N
#        minuti» — `None` = nessun contratto, la liveness NON si presidia.
#        `segno_di_vita`: `GIORNALE` (l'ultimo run su `maintenance.job_run_log`)
#        oppure `SESSIONE` (una connessione viva in `pg_stat_activity` con
#        `application_name = codice`; a `SESSIONE` la tolleranza e' sempre NULL,
#        lo impone il CHECK `chk_processi_sessione_senza_tolleranza`).
class ContrattoLiveness(TypedDict):
    tolleranza_minuti: int | None
    segno_di_vita: str


# Whitelist ORDER BY della lista processi: chiave = nome esposto al frontend,
# valore = espressione SQL. ⛔ Si ordina la colonna che si VEDE.
# ⭐ Pubblica perche' la legge anche il service (`validate_order_params`): una
#    sola sede per «su cosa si puo' ordinare». Fino al 2026-11-09 il service ne
#    teneva una copia a mano (`_ORDER_AMMESSI`), senza presidio.
PROCESSI_SORT_COLUMNS: dict[str, str] = {
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "classe": "p.classe",
    "canale": "p.canale",
    "attivo": "p.attivo",
    "ultimo_run": "ur.ultimo_run",
}

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
_RICERCA_PROCESSI = RicercaFull("amm.processi", ("codice", "descrizione"))

# ⛔ LA TUPLA DEI PRESIDI NON STA PIU' QUI (2026-09-10), ed e' il punto del
#    cantiere «un destinatario per i presidi». Erano dieci nomi scritti a mano,
#    e dal giorno in cui `dbops.presidi` esiste sarebbero stati la SECONDA sede
#    di un fatto che il database dichiara — quella che diverge alla prima vista
#    nuova, in silenzio. ⚠️ E le due gia' non coincidevano: cinque viste di
#    natura ZERO non le guardava nessuno, e una LAVORAZIONE stava fra gli
#    allarmi. Il lettore e' `apps.core.db.presidi_repository`.
# ⚠️ MIRROR DICHIARATO, non una seconda definizione. «Un processo vuole un
#    utente tecnico» e' una regola del DATABASE, scritta in TRE punti che
#    restano autoritativi: `script.fn_crea_utente_tecnico` (che rifiuta gli
#    altri), `dbops.vw_processi_dominio_senza_identita` e
#    `dbops.vw_emittenti_non_serviti` (che li escludono).
#    ⭐ Qui serve solo a rendere la colonna a video con TRE stati invece di due:
#    «non ne vuole» non e' «gliene manca uno», e mostrare un processo di coda
#    come carente insegnerebbe a ignorare l'avviso.
# ⛔ Se un giorno la regola cambia, cambia LA'; questa riga la segue, non la
#    decide. E' lo stesso patto di `_STATI_FLUSSO_TERMINALI` in `pratiche`.
# ⛔ E IL FRONTEND NON NE TIENE UNA COPIA (dal 2026-09-15). Fino a quel giorno
#    `ProcessoDrawer.vue` rifaceva il conto da se' con `['PGAGENT', 'COMMAND']`
#    — la lista leggeva `vuole_identita` dal backend, il drawer no — e nessun
#    test la guardava: sul drawer di `chiusura_scadenze_daily` diceva «non gli
#    serve un utente tecnico» mentre ne usa uno per azienda, e nascondeva
#    l'avviso delle aziende scoperte. ⇒ Il dettaglio proietta lo stesso
#    `vuole_identita` della lista (`_SQL_VUOLE_IDENTITA`) e il client lo legge.
_CLASSE_CON_IDENTITA = "DOMINIO"
# ⚠️ `CODA_AUTOMATICA` e' entrato il 2026-09-05 con la decisione R-E, e NON e'
#    un terzo caso: e' la correzione del modello. Un processo di coda accodato
#    da una MACCHINA vuole l'identita' come gli altri — chi lo sveglia non ha un
#    nome da prestargli. ⛔ `CODA` resta fuori, e li' la ragione regge: lo accoda
#    una persona, e l'identita' e' la sua.
#    ⭐ Letto dal verso autoritativo (`dbops.vw_processi_dominio_senza_identita`
#    e `vw_emittenti_non_serviti`, che elencano gli stessi tre canali), non
#    dedotto dal nome: fosse rimasto a due, `chiusura_scadenze_daily` sarebbe
#    apparso a video come «non ne vuole» proprio mentre ne usa una.
_CANALI_CON_IDENTITA = ("PGAGENT", "COMMAND", "CODA_AUTOMATICA")

# ⭐ L'ESPRESSIONE «questo processo vuole un utente tecnico», scritta UNA volta
#    per le due letture che la proiettano — la lista e il dettaglio. Alias `p`
#    della tabella `dbops.processi`, valori del mirror come PARAMETRI (mai
#    interpolati), nell'ordine che `_params_vuole_identita` restituisce.
# ⚠️ Due query con la stessa espressione ricopiata sono il modo in cui lista e
#    drawer arrivano a dire due cose diverse dello stesso processo: e' successo
#    col client (vedi sopra), e una seconda sede qui lo rifarebbe lato server.
_SQL_VUOLE_IDENTITA = "(p.classe = %s AND p.canale = ANY(%s))"


# ⭐ L'ESPRESSIONE «questo processo e' vivo», scritta UNA volta per il filtro
#    della lista e per le due letture che la proiettano (lista e dettaglio).
#    ⛔ «Vivo» NON e' `p.attivo` (D11, Q2 di brief-db-revisione-dbops, giro 9):
#    il ritiro ha una sede sola, `obsoleto_dal`, e un processo con la data
#    raggiunta e' ritirato anche con `attivo = true`. La regola si CHIEDE al
#    DB, al BB che leggono sveglia, roster e panorama, e non si ricalcola qui:
#    una data futura (ritiro programmato) e' ancora vivo, e «raggiunta» si
#    legge alla data operativa del DB, non a quella del server applicativo.
#    ⚠️ Fino al 2026-11-09 il filtro chiedeva il DB e la proiezione no: la
#    lista filtrava sul ritiro e il drawer mostrava `attivo`, cioe' due
#    risposte diverse alla stessa domanda sullo stesso processo.
_SQL_VIVO = "(NOT script.fn_e_obsoleto(p.obsoleto_dal))"


# Scopo: i parametri di `_SQL_VUOLE_IDENTITA`, nell'ordine dei segnaposto.
#        Lista NUOVA a ogni chiamata: chi la riceve la estende con i propri.
def _params_vuole_identita() -> list[Any]:
    return [_CLASSE_CON_IDENTITA, list(_CANALI_CON_IDENTITA)]


class ProcessiRepository:
    """Lettura del registro dei processi automatici e del loro roster."""

    # Scopo: Il ROSTER di un processo — un'identita' completa per ogni emittente
    #        che quel processo serve. E' la risposta a «per conto di chi devo
    #        girare, e quante volte».
    #
    # ⭐ La fonte e' il BADGE, non il lavoro: si iterano gli emittenti per cui
    #    esiste un utente tecnico, non quelli che «hanno qualcosa da fare». Un
    #    emittente senza badge non viene servito, e il presidio
    #    `dbops.vw_emittenti_non_serviti` lo dice — invece di lasciarlo scoprire
    #    a una fattura che non esce.
    # ⚠️ Si filtra su TUTTA la catena viva — legame attivo, identita' attiva,
    #    ruolo OPERATORE, utente Django attivo, emittente attivo: un solo anello
    #    spento e il lavoro girerebbe con un'identita' che
    #    `operator_identity_context` rifiuta a meta' strada
    #    (`E_CODA_IDENTITA_NON_ATTIVA`), cioe' dopo aver gia' accodato.
    #
    # ⭐ LE CINQUE CONDIZIONI NON SONO PIU' QUI, ed e' il punto di questo metodo.
    #    Stavano in una stringa SQL dentro Python finche' il roster serviva a un
    #    solo consumatore; dal 2026-09-05 lo legge anche il database — il job
    #    notturno che accoda la chiusura scadenze — e riscriverlo di la' avrebbe
    #    fatto due copie della stessa regola. ⛔ Due copie della stessa regola
    #    non restano uguali: si spegne un anello in una e l'altra continua a
    #    servire un'azienda che non andava piu' servita, senza dirlo.
    #    ⇒ La sede e' `dbops.vw_processi_roster`, e qui c'e' solo il filtro.
    # ⚠️ L'ORDER BY e' ripetuto qui anche se la vista ne ha uno: l'ordine di una
    #    vista non e' un contratto quando la si filtra da fuori, e i consumatori
    #    (produttore, drawer) leggono il roster in sequenza.
    def roster_processo(self, processo_codice: str) -> list[RigaRoster]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT auth_user_id,
                       username,
                       identita_id,
                       emittente_fiscale_id,
                       emittente_codice,
                       emittente_soggetto_ruolo_id
                  FROM dbops.vw_processi_roster
                 WHERE processo_codice = %s
                 ORDER BY emittente_codice, auth_user_id
                """,
                [processo_codice],
            )
            return rows_to_list(cursor)  # type: ignore[return-value]

    # Scopo: Gli emittenti ATTIVI che un processo di dominio headless dovrebbe
    #        servire e per cui NON esiste un utente tecnico. Lettura diretta del
    #        presidio `dbops.vw_emittenti_non_serviti`, ristretta a un processo.
    #
    # ⭐ Serve a un produttore per DIRLO invece di tacere: «ho accodato 2 lavori
    #    su 3 emittenti» e' un'informazione, «ho accodato 2 lavori» non lo e'.
    #    ⚠️ E' esattamente il buco silenzioso della D-9: senza il badge il lavoro
    #    non parte, la RLS non mostra niente, e nessuno se ne accorge.
    def emittenti_non_serviti(self, processo_codice: str) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT emittente_fiscale_id, emittente_codice
                  FROM dbops.vw_emittenti_non_serviti
                 WHERE processo_codice = %s
                 ORDER BY emittente_codice
                """,
                [processo_codice],
            )
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  Il registro: che processi esistono, e come stanno
    # ══════════════════════════════════════════════════════════

    # Scopo: L'elenco paginato dei processi automatici, con le colonne che
    #        rispondono alle domande che uno si fa guardandoli: ha un'identita'?
    #        quante aziende serve? quand'e' girato l'ultima volta, ed e' andato
    #        bene?
    #
    # ⚠️ Le decodifiche si fanno QUI, a JOIN, non nel frontend: una lista che
    #    chiede N volte «e questo codice cosa vuol dire?» e' N round-trip e una
    #    seconda copia del vocabolario.
    # ⚠️ Il totale arriva da `COUNT(*) OVER ()` nella stessa valutazione delle
    #    righe (`fetch_paged_with_total`): `len(results)` sarebbe un'eco.
    # ⭐ `ultimo_run` e `ultimo_esito` guardano il giornale PER CODICE processo,
    #    non per jobname: e' esattamente il legame che la FK ha reso solido.
    def list_processi(
        self,
        *,
        classe: str | None = None,
        canale: str | None = None,
        vivo: bool | None = None,
        search: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = ["TRUE"]
        params: list[Any] = []
        if classe:
            conditions.append("p.classe = %s")
            params.append(classe)
        if canale:
            conditions.append("p.canale = %s")
            params.append(canale)
        # «Vivo» e' `_SQL_VIVO`, la stessa espressione che la SELECT proietta.
        if vivo is not None:
            conditions.append(_SQL_VIVO if vivo else f"NOT {_SQL_VIVO}")
        # Soglia della ricerca: la dichiara il catalogo della lista
        # (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_PROCESSI, alias="p")

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=PROCESSI_SORT_COLUMNS,
            # ⚠️ `default_clause` e non `default`: l'ordine di partenza ha DUE
            #    criteri (prima il canale, poi il codice) e porta le direzioni
            #    dentro di se'. Trattarlo come una colonna gli appiccicherebbe
            #    una seconda direzione in coda.
            default_clause="p.canale ASC, p.codice ASC",
            tiebreak="p.id",
        )
        # ⚠️ I due parametri del mirror stanno in TESTA alla lista: compaiono
        #    nella SELECT, cioe' PRIMA delle condizioni del WHERE. L'ordine dei
        #    segnaposto e' posizionale, e sbagliarlo non da' errore di sintassi
        #    — da' un filtro applicato al valore sbagliato.
        where_params = params
        params = [*_params_vuole_identita(), *params]
        data_sql = f"""
            SELECT p.id,
                   p.codice,
                   p.descrizione,
                   p.classe,
                   p.canale,
                   p.attivo,
                   p.obsoleto_dal::text AS obsoleto_dal,
                   {_SQL_VIVO} AS vivo,
                   -- ⭐ Un processo di CODA non deve avere un utente tecnico:
                   --    gira con l'identita' di chi lo accoda. Dirlo qui evita
                   --    che a video sembri «manca qualcosa». Stessa espressione
                   --    del dettaglio (`_SQL_VUOLE_IDENTITA`), di proposito.
                   {_SQL_VUOLE_IDENTITA} AS vuole_identita,
                   (SELECT count(*) FROM dbops.processi_identita pi
                     WHERE pi.processo_id = p.id AND pi.attivo) AS identita_attive,
                   (SELECT count(*) FROM dbops.processi_bersagli b
                     WHERE b.processo_id = p.id) AS bersagli,
                   ur.ultimo_run,
                   ur.ultimo_ok,
                   ur.run_totali,
                   COUNT(*) OVER () AS total_count
              FROM dbops.processi p
              LEFT JOIN LATERAL (
                   SELECT max(j.started_at) AS ultimo_run,
                          -- Le corse VERE, come `total_runs` di
                          -- MaintenanceRepository.list_job_summary: una saltata
                          -- non e' un'esecuzione.
                          count(*) FILTER (WHERE NOT j.saltata) AS run_totali,
                          -- L'esito e' dell'ultima corsa VERA: una saltata (lock
                          -- occupato) e' segno di vita in `ultimo_run`, ma non ha
                          -- fatto il lavoro. Stessa regola di `ultimo_esito` in
                          -- dbops.vw_processi_programmazione (brief corsa-saltata D3).
                          (array_agg(j.ok ORDER BY j.started_at DESC, j.id DESC)
                               FILTER (WHERE NOT j.saltata))[1] AS ultimo_ok
                     FROM maintenance.job_run_log j
                    WHERE j.processo_codice = p.codice
              ) ur ON TRUE
             WHERE {' AND '.join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        return fetch_paged_with_total(
            data_sql, params + [limit, offset],
            # Stesso FROM/WHERE della pagina, senza il mirror della SELECT.
            fallback_count_sql=(
                f"SELECT COUNT(*) FROM dbops.processi p WHERE {' AND '.join(conditions)}"  # noqa: S608
            ),
            fallback_params=where_params,
            offset=offset,
        )

    # Scopo: I contratti di liveness dei processi chiesti, per codice. Chi non e'
    #        a catalogo NON compare nel dict — e' contratto: «non lo conosco» e
    #        «non ha tolleranza» sono due risposte diverse, e il chiamante decide
    #        cosa farne (il badge code ripiega, il battito del digest tace).
    #
    # ⭐ PERCHE' SI LEGGE QUI E NON DA `deploy/sveglie.json` (dov'era fino al
    #    2026-09-11). La tolleranza e' il CONTRATTO del processo — uguale su ogni
    #    installazione — mentre la cadenza e' COME il deploy lo onora, e resta nel
    #    JSON. E la ragione decisiva non e' di principio: il lettore che ne ha
    #    piu' bisogno sta nel database — `dbops.vw_processi_programmazione` dice
    #    `MUTO` sui COMMAND col contratto, e il guardiano pgAgent del digest legge
    #    solo il catalogo. Una sede sola resta una sede sola: il campo e' USCITO
    #    dal JSON, e `carica_sveglie` lo rifiuta se ricompare.
    # ⚠️ IL CONTRATTO HA LA GRANA DEL PROCESSO, il giornale quella della CORSIA
    #    (`<codice>:<corsia>`). Un processo con due corsie a cadenze diverse ha
    #    UNA tolleranza, la piu' larga: la morte della sola corsia stretta si
    #    legge dal battito per corsia («mai girata»), non da questo numero.
    #    Limite accettato da Tid il 2026-09-11 (brief §11.2); se un giorno serve
    #    la grana corsia, la sede e' una figlia a catalogo, non il JSON.
    # ⚠️ `dbops.processi` non ha RLS: la lettura vede tutto anche senza contesto
    #    operatore, ed e' cio' che serve al badge e al digest.
    def contratti_liveness(
        self, codici: Iterable[str],
    ) -> dict[str, ContrattoLiveness]:
        elenco = sorted({c for c in codici if c})
        if not elenco:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT codice, tolleranza_minuti, segno_di_vita
                  FROM dbops.processi
                 WHERE codice = ANY(%s)
                """,
                [elenco],
            )
            rows = cursor.fetchall()
        return {
            str(r[0]): ContrattoLiveness(
                tolleranza_minuti=int(r[1]) if r[1] is not None else None,
                segno_di_vita=str(r[2]),
            )
            for r in rows
        }

    # Scopo: La tolleranza di UN processo, o `None` se non ha contratto o non e'
    #        a catalogo. Comodita' sul metodo sopra per chi ne chiede uno solo.
    def tolleranza_minuti(self, processo_codice: str) -> int | None:
        contratto = self.contratti_liveness([processo_codice]).get(processo_codice)
        return contratto["tolleranza_minuti"] if contratto else None

    # Scopo: Il dettaglio di un processo: la sua riga, i BERSAGLI che dichiara di
    #        scrivere e con quale percorso raggiungono l'emittente, e le IDENTITA'
    #        con cui lavora. `None` se il codice non esiste.
    def get_processo(self, codice: str) -> dict[str, Any] | None:
        # ⭐ `vuole_identita` viaggia col dettaglio come con la lista, dalla
        #    STESSA espressione: e' il dato con cui il drawer decide se mostrare
        #    gli utenti tecnici e l'avviso delle aziende scoperte, e fino al
        #    2026-09-15 il client lo ricalcolava da se' — male.
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT p.id, p.codice, p.descrizione, p.classe, p.canale, p.attivo,
                       p.obsoleto_dal::text AS obsoleto_dal, p.meta,
                       {_SQL_VIVO} AS vivo,
                       {_SQL_VUOLE_IDENTITA} AS vuole_identita
                  FROM dbops.processi p
                 WHERE p.codice = %s
                """,  # noqa: S608 — frammento costante di modulo, valori in params
                [*_params_vuole_identita(), codice],
            )
            testa = row_to_dict(cursor)
        if testa is None:
            return None

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT b.schema_tabella, b.nome_tabella, b.emittente_via,
                       b.emittente_colonna, b.note
                  FROM dbops.processi_bersagli b
                 WHERE b.processo_id = %s
                 ORDER BY b.schema_tabella, b.nome_tabella
                """,
                [testa["id"]],
            )
            bersagli = rows_to_list(cursor)

        return {
            **testa,
            "bersagli": bersagli,
            "identita": self.roster_processo(codice),
        }

    # Scopo: L'ACCENSIONE di un processo su questa installazione, per chi
    #        DESCRIVE (il drawer) e per il predicato di «Esegui ora»:
    #          - `acceso`: lo stato effettivo, da
    #            `dbops.fn_processo_acceso_dichiarato` — NULL se non decidibile
    #            (ambiente non dichiarato) o senza sveglia (CODA, ritirato);
    #          - `spegnibile` e il default per i due ambienti, dal catalogo;
    #          - `ambiente`: `script.fn_ambiente_dichiarato()`, NULL se non
    #            dichiarato;
    #          - `scelta_a_mano`: la riga di `dbops.processi_accensione` (acceso,
    #            motivo, chi e quando) o None se vale il default;
    #          - `accendere_ammesso`: il gesto «accendi a mano» e' ammesso qui?
    #            True / False (non accendibile in PRODUZIONE) / None (ambiente
    #            non dichiarato). E' il predicato del guard
    #            (`dbops.fn_accensione_a_mano_ammessa_su_valori`, R-BE-5), letto
    #            con `acceso = true`: ⛔ non si ricalcola in Python
    #            (linee-guida-sql §12.1), il service ne fa la capability.
    #        `None` se il codice non esiste.
    # ⛔ La regola NON si ricalcola qui: `acceso` e' la risposta del DB. Il
    #    default e la scelta viaggiano per dire DA DOVE viene, non per decidere.
    # ⚠️ Lettori «che descrivono»: non sollevano su un'installazione non
    #    dichiarata (la pagina dei processi deve aprirsi proprio allora). Chi
    #    DECIDE e' `maintenance.fn_sveglia_accesa` (la sveglia systemd); il
    #    predicato di «Esegui ora» tratta il NULL come motivo, non come acceso.
    def accensione_processo(self, codice: str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT dbops.fn_processo_acceso_dichiarato(p.codice) AS acceso,
                       p.spegnibile,
                       p.acceso_in_sviluppo,
                       p.acceso_in_produzione,
                       amb.ambiente,
                       dbops.fn_accensione_a_mano_ammessa_su_valori(
                           true, p.accendibile_in_produzione, amb.ambiente
                       ) AS accendere_ammesso,
                       a.acceso       AS scelta_acceso,
                       a.motivo       AS scelta_motivo,
                       a.user_update  AS scelta_utente,
                       a.data_update  AS scelta_data
                  FROM dbops.processi p
                  -- ⚠️ L'ambiente si legge UNA volta: quello mostrato e quello
                  --    con cui si decide «Accendi» sono lo stesso valore.
                 CROSS JOIN LATERAL (SELECT script.fn_ambiente_dichiarato() AS ambiente) amb
                  LEFT JOIN dbops.processi_accensione a ON a.processo_id = p.id
                 WHERE p.codice = %s
                """,
                [codice],
            )
            riga = row_to_dict(cursor)
        if riga is None:
            return None
        scelta = None
        if riga["scelta_acceso"] is not None:
            scelta = {
                "acceso": riga["scelta_acceso"],
                "motivo": riga["scelta_motivo"],
                "utente": riga["scelta_utente"],
                "data": riga["scelta_data"],
            }
        return {
            "acceso": riga["acceso"],
            "spegnibile": riga["spegnibile"],
            "acceso_in_sviluppo": riga["acceso_in_sviluppo"],
            "acceso_in_produzione": riga["acceso_in_produzione"],
            "ambiente": riga["ambiente"],
            "scelta_a_mano": scelta,
            "accendere_ammesso": riga["accendere_ammesso"],
        }

    # Scopo: lo STATO EFFETTIVO del processo su questa installazione, e basta
    #        — la domanda di chi DECIDE se lanciarlo a mano (il rifiuto di
    #        «Esegui ora» e il ricontrollo dell'handler). True / False, o None se
    #        non decidibile (ambiente non dichiarato) o senza sveglia.
    #        `accensione_processo` resta la lettura di chi DESCRIVE (il drawer).
    # ⛔ Un processo che non c'e' NON e' None: sarebbe letto «ambiente non
    #    dichiarato» e manderebbe a cercare nel posto sbagliato. Solleva
    #    `LookupError`, e il chiamante lo traduce nel 404 di dominio.
    def acceso_processo(self, codice: str) -> bool | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT dbops.fn_processo_acceso_dichiarato(p.codice)"
                "  FROM dbops.processi p WHERE p.codice = %s",
                [codice],
            )
            row = cursor.fetchone()
        if row is None:
            raise LookupError(f"processo {codice!r} non e' in dbops.processi")
        return row[0]

    # Scopo: Il verbo della scelta a mano: accende (`True`), spegne (`False`)
    #        o toglie la scelta (`None`: torna il default per ambiente).
    #        Ritorna lo stato effettivo dopo il gesto (NULL se non decidibile).
    # ⛔ I limiti (processo senza sveglia, non spegnibile, motivo obbligatorio)
    #    li dice il guard della tabella: qui non si ripetono, si traducono.
    def imposta_accensione(
        self, codice: str, *, acceso: bool | None, motivo: str | None,
    ) -> bool | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT dbops.fn_imposta_accensione_processo(%s, %s, %s)",
                [codice, acceso, motivo],
            )
            row = cursor.fetchone()
        assert row is not None
        return row[0]

    # Scopo: Le ultime corse di un processo — la sua storia recente, per il tab
    #        «Ultimi run» del drawer.
    def list_run_processo(
        self, codice: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        data_sql = """
            SELECT j.id, j.jobname, j.stepname, j.origine,
                   j.started_at, j.ended_at, j.ok, j.message,
                   j.rows_affected, j.error_code, j.auth_user_id, j.saltata,
                   au.username AS auth_username,
                   COUNT(*) OVER () AS total_count
              FROM maintenance.job_run_log j
              LEFT JOIN auth_user au ON au.id = j.auth_user_id
             WHERE j.processo_codice = %s
             ORDER BY j.started_at DESC, j.id DESC
             LIMIT %s OFFSET %s
        """
        return fetch_paged_with_total(
            data_sql, [codice, limit, offset],
            fallback_count_sql=(
                "SELECT COUNT(*) FROM maintenance.job_run_log j WHERE j.processo_codice = %s"
            ),
            fallback_params=[codice],
            offset=offset,
        )
