-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto del test NON sta sul percorso applicativo —
--   `fn_accoda_chiusura_scadenze` la chiama un job pgAgent, che gira come
--   superuser, e nessun endpoint la espone. In piu' il test 6 fa DDL (un
--   trigger di fault injection su dbops.coda_lavori) per costruire il
--   fallimento di UNA sola azienda.
--
-- Test: dbops.fn_accoda_chiusura_scadenze — pgAgent sveglia, non lavora
-- Brief: brief-db-processi-automatici-identita-e-perimetro §12.12 (DB-1)
--
-- Elenco test (plan 6):
--  1) il produttore accoda UN lavoro per ogni azienda del roster
--  2) ⛔ i lavori sono OPERATORE, non SISTEMA
--  3) ⚠️ lo scope porta l'emittente CONGELATO all'accodamento
--  4) ⭐ una seconda sveglia nello stesso giorno non raddoppia
--  5) ⚠️ e la chiave di idempotenza non contiene l'ora
--  6) ⭐ ISOLAMENTO: se un'azienda fallisce, le altre vengono accodate lo stesso
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ CHE COSA CAMBIA, e perche' merita dei test propri.
--   Prima il job notturno chiamava `dbops.fn_apply_chiusura_scadenze()` e
--   CHIUDEVA le scadenze — di tutti, dentro pgAgent, senza identita' e senza un
--   posto dove raccontare un fallimento. Adesso non chiude niente: accoda un
--   lavoro per azienda, ciascuno con l'identita' tecnica di quella azienda
--   nello scope, e il lavoro vero lo fa il drenatore dentro la RLS.
--
-- ⭐ IL TEST 6 E' IL GUADAGNO PRINCIPALE, non un dettaglio di robustezza.
--   Il giro unico di prima era tutto-o-niente: un errore su una tabella fermava
--   la chiusura per TUTTE le aziende, e non lo diceva a nessuno. Provarlo
--   richiede di far fallire UNA riga sola — e per questo il test inietta un
--   guasto invece di aspettarne uno.
--
-- ⚠️ IL TEST 3 E' LA CONDIZIONE PIU' SILENZIOSA DI TUTTE.
--   Il worker esegue minuti dopo. Senza `emittente_attivo_id` nello scope
--   girerebbe in modalita' globale: un lavoro chiesto «dentro A» toccherebbe
--   anche B, e nessun errore lo direbbe — le righe di B verrebbero chiuse
--   correttamente, solo da chi non doveva.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Il roster su cui si suona — si COSTRUISCE, non si eredita
-- ============================================================
-- ⛔ Fino al 2026-09-09 questo file suonava sul roster che TROVAVA. Su dbdev ci
--   sono due emittenti veri e otto coppie, quindi sembrava verificare; su un
--   database ricostruito dai changelog il roster e' VUOTO — emittenti e
--   soggetti sono `dati_macchina` — e succedeva la cosa peggiore:
--   ⚠️ i test 1..5 passavano LO STESSO, perche' «zero accodati» e' uguale a
--   «zero aziende a roster». Verdi per sottrazione, cioe' verdi smettendo di
--   verificare. Solo il 6 diventava rosso, ed e' l'unico che si era accorto di
--   niente.
--
-- ⭐ DUE coppie e non una: il test 6 fa fallire la PRIMA azienda e pretende che
--   le altre passino lo stesso. Con una sola azienda a roster «le altre» non
--   esistono, e l'asserzione diventerebbe `1/0` — vera per mancanza di
--   materia, che e' di nuovo il difetto di sopra.
DO $roster$
BEGIN
    PERFORM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');
    PERFORM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');
END
$roster$;

-- ⭐ La condizione si COSTRUISCE: «nessun lavoro di chiusura per oggi».
--   Su un database vivo il job orario (20261009-61) ha gia' chiuso la
--   giornata delle aziende vere, e fn_accoda_chiusura_scadenze (20261009-46)
--   le salta: il test vedrebbe meno accodati del roster senza che niente sia
--   rotto (dbdev, 2026-10-09: 2 su 4). Si liberano le chiavi di oggi, come fa
--   gia' il test 6 qui sotto; tutto si annulla col ROLLBACK.
UPDATE dbops.coda_lavori
   SET idempotency_key = idempotency_key || ':pgtap-prima'
 WHERE job_type = 'CHIUSURA_SCADENZE'
   AND idempotency_key LIKE 'CHIUSURA_SCADENZE:%:' || script.fn_data_operativa()::text;

-- ============================================================
-- La sveglia suona una volta
-- ============================================================
-- ⚠️ Il riepilogo si mette da parte: le asserzioni dopo lo leggono senza
--   richiamare la funzione — richiamarla sarebbe una seconda sveglia, cioe' un
--   altro esperimento.
DO $sveglia$
DECLARE
    v_out jsonb;
BEGIN
    PERFORM set_config('pgtap.roster',
        (SELECT count(*)::text FROM dbops.vw_processi_roster
          WHERE processo_codice = 'chiusura_scadenze_daily'), true);

    v_out := dbops.fn_accoda_chiusura_scadenze();
    PERFORM set_config('pgtap.giro1', v_out::text, true);

    -- La seconda sveglia dello stesso giorno: e' il test 4.
    v_out := dbops.fn_accoda_chiusura_scadenze();
    PERFORM set_config('pgtap.giro2', v_out::text, true);
END
$sveglia$;

-- ============================================================
-- 1. Un lavoro per azienda
-- ============================================================
-- ⛔ Non «almeno uno»: uno per azienda. Un produttore che accodasse un lavoro
--   solo — per l'azienda che capita prima — sarebbe verde su un database con
--   un emittente, e sbagliato su tutti gli altri.
SELECT is(
    (current_setting('pgtap.giro1')::jsonb ->> '_accodati'),
    current_setting('pgtap.roster'),
    '1. il produttore accoda un lavoro per ogni azienda del roster'
);

-- ============================================================
-- 2..3. Chi lavora, e dentro quale perimetro
-- ============================================================
-- ⛔ OPERATORE e non SISTEMA: lo pretende il guard di classe di
--   `fn_accoda_lavoro` per un processo di dominio, ed e' la ragione per cui
--   tutto questo cantiere esiste.
SELECT is_empty(
    $$SELECT c.id FROM dbops.coda_lavori c
       WHERE c.job_type = 'CHIUSURA_SCADENZE'
         AND c.idempotency_key LIKE 'CHIUSURA_SCADENZE:%:' || script.fn_data_operativa()::text
         AND c.run_as <> 'OPERATORE'$$,
    '2. nessun lavoro di chiusura scadenze e'' accodato come SISTEMA'
);

-- ⭐ Il confronto e' col ROSTER, non con una costante: cosi' il test dice
--   «ogni lavoro porta l'emittente della riga da cui e' nato», che e' la
--   proprieta' vera, e non «porta l'emittente 44», che sarebbe una fotografia.
SELECT is_empty(
    $$SELECT c.id
        FROM dbops.coda_lavori c
        JOIN dbops.vw_processi_roster r
          ON r.processo_codice = 'chiusura_scadenze_daily'
         AND c.idempotency_key = 'CHIUSURA_SCADENZE:' || r.emittente_codice
                                 || ':' || script.fn_data_operativa()::text
       WHERE c.job_type = 'CHIUSURA_SCADENZE'
         AND ( (c.scope->>'emittente_attivo_id')::bigint
                   IS DISTINCT FROM r.emittente_fiscale_id
            OR (c.scope->>'auth_user_id')::integer
                   IS DISTINCT FROM r.auth_user_id )$$,
    '3. ogni lavoro porta l''emittente e l''utente della riga di roster da cui nasce'
);

-- ============================================================
-- 4..5. ⭐ Due sveglie, un lavoro
-- ============================================================
-- Un riavvio del server, una schedulazione doppia, una mano sul job: la
-- seconda sveglia non deve produrre un secondo giro di chiusure.
SELECT is(
    (SELECT jsonb_agg(d->>'job_id' ORDER BY d->>'job_id')
       FROM jsonb_array_elements(current_setting('pgtap.giro2')::jsonb -> '_dettaglio') d),
    (SELECT jsonb_agg(d->>'job_id' ORDER BY d->>'job_id')
       FROM jsonb_array_elements(current_setting('pgtap.giro1')::jsonb -> '_dettaglio') d),
    '4. la seconda sveglia restituisce gli STESSI lavori: non raddoppia'
);

-- ⛔ Se la chiave portasse l'ora, due sveglie nello stesso giorno sarebbero due
--   intenzioni diverse — e il test 4 sarebbe verde solo finche' le due
--   chiamate cadono nello stesso secondo.
SELECT is_empty(
    $$SELECT c.id FROM dbops.coda_lavori c
        JOIN dbops.vw_processi_roster r
          ON r.processo_codice = 'chiusura_scadenze_daily'
         AND c.scope->>'emittente_attivo_id' = r.emittente_fiscale_id::text
       WHERE c.job_type = 'CHIUSURA_SCADENZE'
         AND c.data_insert >= script.fn_inizio_giorno_operativo(script.fn_data_operativa())
         -- le chiavi che questo file rinomina apposta (:pgtap-prima, :pgtap-ieri)
         AND c.idempotency_key NOT LIKE '%:pgtap-%'
         AND c.idempotency_key <> 'CHIUSURA_SCADENZE:' || r.emittente_codice
                                   || ':' || script.fn_data_operativa()::text$$,
    '5. la chiave di idempotenza e'' (tipo, azienda, GIORNO), senza l''ora'
);

-- ============================================================
-- 6. ⭐ L'isolamento per azienda
-- ============================================================
-- ⚠️ Il guasto si INIETTA: aspettare che una tabella si rompa da sola non e'
--   un test. Il trigger fa fallire l'accodamento della PRIMA azienda del
--   roster e lascia passare le altre — che e' esattamente la situazione che il
--   giro unico di prima non sapeva reggere.
-- ⛔ E si misura su un GIORNO diverso: le chiavi di oggi sono gia' occupate dai
--   giri 1 e 2, e l'idempotenza le farebbe tornare senza mai arrivare
--   all'INSERT — il guasto non scatterebbe e il test sarebbe verde per il
--   motivo sbagliato.
DO $isola$
DECLARE
    v_primo text;
    v_out   jsonb;
BEGIN
    SELECT r.emittente_codice INTO v_primo
      FROM dbops.vw_processi_roster r
     WHERE r.processo_codice = 'chiusura_scadenze_daily'
     ORDER BY r.emittente_codice
     LIMIT 1;

    EXECUTE format($ddl$
        CREATE OR REPLACE FUNCTION dbops.trgfn_pgtap_rompi_una_azienda()
         RETURNS trigger LANGUAGE plpgsql AS $f$
        BEGIN
            IF NEW.payload->>'emittente_codice' = %L THEN
                RAISE EXCEPTION 'pgtap: guasto iniettato su %%', NEW.payload->>'emittente_codice';
            END IF;
            RETURN NEW;
        END $f$;
    $ddl$, v_primo);

    CREATE TRIGGER trg_pgtap_rompi_una_azienda
        BEFORE INSERT ON dbops.coda_lavori
        FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_pgtap_rompi_una_azienda();

    -- Domani: chiavi libere, quindi si arriva davvero all'INSERT.
    UPDATE dbops.coda_lavori
       SET idempotency_key = idempotency_key || ':pgtap-ieri'
     WHERE job_type = 'CHIUSURA_SCADENZE'
       AND idempotency_key LIKE 'CHIUSURA_SCADENZE:%:' || script.fn_data_operativa()::text;

    v_out := dbops.fn_accoda_chiusura_scadenze();
    PERFORM set_config('pgtap.giro3', v_out::text, true);

    DROP TRIGGER trg_pgtap_rompi_una_azienda ON dbops.coda_lavori;
END
$isola$;

-- ⭐ Un fallito e tutti gli altri accodati: il giro unico di prima si sarebbe
--   fermato al primo errore, per tutte le aziende insieme.
SELECT is(
    (current_setting('pgtap.giro3')::jsonb ->> '_falliti') || '/' ||
    (current_setting('pgtap.giro3')::jsonb ->> '_accodati'),
    '1/' || (current_setting('pgtap.roster')::int - 1)::text,
    '6. una azienda fallisce, le altre vengono accodate lo stesso'
);

SELECT * FROM finish();

ROLLBACK;
