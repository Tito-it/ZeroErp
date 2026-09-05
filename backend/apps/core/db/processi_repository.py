# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#        Brief: work-in-progress/piano-be-fe-processi-automatici-identita-e-perimetro.md
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, TypedDict

from django.db import connection

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
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


# Whitelist ORDER BY della lista processi: chiave = nome esposto al frontend,
# valore = espressione SQL. ⛔ Si ordina la colonna che si VEDE.
_ORDER_COLS_PROCESSI: dict[str, str] = {
    "codice": "p.codice",
    "descrizione": "p.descrizione",
    "classe": "p.classe",
    "canale": "p.canale",
    "attivo": "p.attivo",
    "ultimo_run": "ur.ultimo_run",
}

# ⭐ I PRESIDI del cantiere «nessun processo senza operatore», nell'ordine in
#    cui conviene leggerli. ⛔ Qui c'e' SOLO il nome: che natura abbia ciascuno
#    — «deve restare vuota» oppure «registro di debito che deve calare» — lo
#    dichiara il DATABASE nel commento della vista, e si legge da li'
#    (`obj_description`). Scriverlo anche qui sarebbe la seconda sede dello
#    stesso fatto, e la seconda sede e' quella che diverge.
# ⚠️ E il loro NUMERO non si scrive da nessuna parte, per la stessa ragione: e'
#    passato da sei a otto il 2026-09-05, e ogni commento che diceva «i sei
#    presidi» era gia' una riga da correggere.
PRESIDI_PROCESSI: tuple[str, ...] = (
    "vw_processi_che_bypassano",
    "vw_processi_dominio_senza_emittente",
    "vw_processi_dominio_senza_difesa",
    "vw_processi_dominio_senza_identita",
    "vw_emittenti_non_serviti",
    "vw_run_senza_attore",
    # ⭐ 2026-09-05, con la migrazione della chiusura scadenze sulla coda.
    #    `..._su_pgagent` verifica la regola presa quel giorno — nessun processo
    #    di DOMINIO su pgAgent — e `..._da_guardare` e' il prezzo di quella
    #    scelta: spostando il lavoro nella coda si sposta anche il SILENZIO, e
    #    un lavoro che nessuno prende ha lo stesso effetto di un job morto.
    #    ⛔ Va letto anche quando tutto sembra a posto: la sua riga piu'
    #    pericolosa e' «mai preso», che si legge solo se il worker e' spento.
    "vw_processi_dominio_su_pgagent",
    "vw_coda_lavori_da_guardare",
)

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

# Quante righe di esempio si consegnano per presidio: il pannello serve a dire
# CHE c'e' qualcosa e a farsi un'idea, non a essere una lista paginata.
_RIGHE_PRESIDIO = 20


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
        attivo: bool | None = None,
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
        if attivo is not None:
            conditions.append("p.attivo = %s")
            params.append(attivo)
        if search:
            conditions.append("(p.codice ILIKE %s OR p.descrizione ILIKE %s)")
            params.extend([f"%{search}%"] * 2)

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_PROCESSI,
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
        params = [_CLASSE_CON_IDENTITA, list(_CANALI_CON_IDENTITA), *params]
        data_sql = f"""
            SELECT p.id,
                   p.codice,
                   p.descrizione,
                   p.classe,
                   p.canale,
                   p.attivo,
                   p.obsoleto_dal::text AS obsoleto_dal,
                   -- ⭐ Un processo di CODA non deve avere un utente tecnico:
                   --    gira con l'identita' di chi lo accoda. Dirlo qui evita
                   --    che a video sembri «manca qualcosa».
                   -- ⚠️ Mirror della regola del DB (vedi `_CLASSE_CON_IDENTITA`):
                   --    i valori arrivano come PARAMETRI, non interpolati.
                   (p.classe = %s AND p.canale = ANY(%s)) AS vuole_identita,
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
                          count(*)          AS run_totali,
                          (array_agg(j.ok ORDER BY j.started_at DESC))[1] AS ultimo_ok
                     FROM maintenance.job_run_log j
                    WHERE j.processo_codice = p.codice
              ) ur ON TRUE
             WHERE {' AND '.join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        return fetch_paged_with_total(data_sql, params + [limit, offset])

    # Scopo: Il dettaglio di un processo: la sua riga, i BERSAGLI che dichiara di
    #        scrivere e con quale percorso raggiungono l'emittente, e le IDENTITA'
    #        con cui lavora. `None` se il codice non esiste.
    def get_processo(self, codice: str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione, classe, canale, attivo,
                       obsoleto_dal::text AS obsoleto_dal, meta
                  FROM dbops.processi
                 WHERE codice = %s
                """,
                [codice],
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

    # Scopo: Le ultime corse di un processo — la sua storia recente, per il tab
    #        «Ultimi run» del drawer.
    def list_run_processo(
        self, codice: str, *, limit: int = DEFAULT_LIMIT, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        data_sql = """
            SELECT j.id, j.jobname, j.stepname, j.origine,
                   j.started_at, j.ended_at, j.ok, j.message,
                   j.rows_affected, j.error_code, j.auth_user_id,
                   au.username AS auth_username,
                   COUNT(*) OVER () AS total_count
              FROM maintenance.job_run_log j
              LEFT JOIN auth_user au ON au.id = j.auth_user_id
             WHERE j.processo_codice = %s
             ORDER BY j.started_at DESC, j.id DESC
             LIMIT %s OFFSET %s
        """
        return fetch_paged_with_total(data_sql, [codice, limit, offset])

    # ══════════════════════════════════════════════════════════
    #  I presidi: le viste che devono restare vuote
    # ══════════════════════════════════════════════════════════

    # Scopo: Lo stato dei presidi in un round-trip: per ognuno il conteggio,
    #        le prime righe e — ⭐ letta dal DATABASE, non riscritta qui — la
    #        DESCRIZIONE che dice che natura ha quel presidio.
    #
    # ⭐ La descrizione arriva da `obj_description`, cioe' dal commento che il
    #    team DB ha scritto sulla vista: e' li' che sta «DEVE restare VUOTA»
    #    contro «e' un registro di DEBITO, deve CALARE». Il frontend rende quel
    #    testo invece di avere una tabella di eccezioni in casa.
    # ⚠️ Finche' la richiesta DB-2 non e' fatta, una delle sei NON e' mai vuota
    #    per costruzione (la riga dichiarata di `config.email_outbox`). ⛔ Non si
    #    compensa nascondendola qui: sarebbe scrivere nel frontend un elenco di
    #    righe attese, cioe' la cosa che DB-2 chiede di mettere nel dato.
    # ⚠️ `count(*)` PRIMA delle righe e senza filtro: e' il numero che dice
    #    quanto sta fuori dalle prime venti.
    def stato_presidi(self, righe_per_presidio: int = _RIGHE_PRESIDIO) -> list[dict[str, Any]]:
        esito: list[dict[str, Any]] = []
        for vista in PRESIDI_PROCESSI:
            # ⛔ Il nome viene da una tupla COSTANTE del modulo, mai
            #    dall'esterno: qui e' interpolato nell'SQL.
            qualificata = f"dbops.{vista}"
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT obj_description(%s::regclass, 'pg_class')", [qualificata],
                )
                riga = cursor.fetchone()
                descrizione = riga[0] if riga else None

                cursor.execute(f"SELECT count(*) FROM {qualificata}")  # noqa: S608
                conteggio = int(cursor.fetchone()[0])

                cursor.execute(
                    f"SELECT * FROM {qualificata} LIMIT %s",  # noqa: S608
                    [righe_per_presidio],
                )
                righe = rows_to_list(cursor)

            esito.append({
                "vista": vista,
                "descrizione": descrizione,
                "conteggio": conteggio,
                "righe": righe,
                "troncato": conteggio > len(righe),
            })
        return esito
