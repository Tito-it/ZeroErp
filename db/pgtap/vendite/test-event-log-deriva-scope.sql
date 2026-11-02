-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — vendite.trgfn_event_log_deriva_scope (+ dbops.trgfn_cleanup_at_alla_nascita)
--   ⏱️ 2026-09-18 (Passo D): la scadenza non la scrive piu' deriva_scope ma il
--   BB generico dbops.trgfn_cleanup_at_alla_nascita (trigger _m50_, 20260918-31),
--   che legge il TTL da dbops.fn_cleanup_at_params; vendite.fn_event_log_ttl_days
--   e' ritirata. Il test 4 pinna lo stesso identico risultato di prima.
--   La riga di `vendite.event_log` si compila da sola: perimetro, identita' e
--   scadenza li scrive il database, non il chiamante.
--   Brief: brief-db-event-log-scope-e-riga-parlante.md §3.2
--
-- ⭐ LA REGOLA CHE QUESTO FILE PRESIDIA (D-12):
--     Il diario rifiuta una riga SOLO quando non riesce a dire di chi e'.
--     Tutto il resto lo registra.
--   Il test 7 e' quello che vale davvero, ed e' controintuitivo: si presidia
--   l'ASSENZA di un lucchetto, cioe' una cosa che nessuno vedrebbe mancare.
--
-- Indice test (1..7):
--   1. il perimetro e' quello dell'entita' citata
--   2. il chiamante NON puo' imporre un perimetro suo: il trigger sovrascrive
--   3. `auth_user_id` e' l'utente della sessione — «chi», come numero
--   4. `cleanup_at` = `event_time` + il TTL letto da dbops.automation_rules_tbl
--   5. entity_type fuori vocabolario -> rifiutato, e la frase NOMINA il tipo
--   6. entita' inesistente           -> rifiutato, con una frase DIVERSA
--   7. ⭐ nessun lucchetto `require_attivo` su event_log — il diario non puo'
--      smettere di scrivere perche' un padre e' stato disattivato
--
-- ⚠️ 5 e 6 usano `throws_like` e non `throws_ok('P0001')`: qui il punto NON e'
--   «e' un errore di dominio» ma QUALE dei due, e `P0001` non distingue. Sono
--   due codici apposta, perche' il rimedio e' diverso — e un test che li
--   confondesse lascerebbe passare proprio la regressione che conta.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture — una scelta sola, proiettata da temp table
-- ============================================================
CREATE TEMP TABLE _rif AS
SELECT
    script.fn_pgtap_emittente_sr_operatore()                        AS sr_atteso,
    current_setting('app.current_user_id', true)::bigint            AS uid_atteso,
    (dbops.fn_cleanup_at_params('vendite', 'event_log') ->> 'ttl_days')::integer AS ttl_days,
    (SELECT c.id
       FROM vendite.commesse c
      WHERE c.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
      ORDER BY c.id
      LIMIT 1)                                                      AS commessa_id;

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la snapshot di
--   statement legge PRIMA delle scritture.
-- ⚠️ INSERT diretto e non fn_log_event, apposta: serve passare un
--   `emittente_soggetto_ruolo_id` FINTO per il test 2, e la funzione non
--   espone quel parametro (ed e' il punto).
CREATE TEMP TABLE _ev AS
WITH ins AS (
    INSERT INTO vendite.event_log
        (entity_type, entity_id, event_code, emittente_soggetto_ruolo_id, auth_user_id)
    SELECT 'COMMESSA', r.commessa_id, 'PGTAP_DERIVA',
           -9,      -- perimetro finto: il trigger deve sovrascriverlo
           -1       -- identita' finta: idem
      FROM _rif r
     WHERE r.commessa_id IS NOT NULL
    RETURNING id, emittente_soggetto_ruolo_id, auth_user_id, event_time, cleanup_at
)
SELECT * FROM ins;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) Il perimetro e' quello dell'entita'.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('nessuna commessa dell''emittente dell''operatore', 1)
    ELSE is(
        (SELECT emittente_soggetto_ruolo_id FROM _ev),
        (SELECT sr_atteso FROM _rif),
        'il perimetro e'' quello della commessa citata dall''evento'
    )
END;

-- 2) ⭐ E il chiamante non puo' imporne un altro: il -9 e' sparito.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE isnt(
        (SELECT emittente_soggetto_ruolo_id FROM _ev),
        -9::bigint,
        'il perimetro passato dal chiamante viene SOVRASCRITTO: e'' un fatto del DB'
    )
END;

-- 3) «Chi», come numero.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT auth_user_id FROM _ev),
        (SELECT uid_atteso FROM _rif),
        'auth_user_id e'' l''utente della sessione, non quello passato dal chiamante'
    )
END;

-- 4) La scadenza: event_time + TTL, e il TTL viene dalla regola, non da una
--    costante nel trigger. ⚠️ Confronto sul valore atteso RICALCOLATO dalla
--    stessa sorgente: se domani la regola cambia, il test segue senza
--    diventare una seconda sede del numero.
SELECT CASE
    WHEN (SELECT commessa_id FROM _rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    WHEN (SELECT ttl_days FROM _rif) IS NULL
      THEN skip('nessuna regola CLEANUP_AT per vendite.event_log: cleanup_at resta NULL', 1)
    ELSE is(
        (SELECT e.cleanup_at FROM _ev e),
        (SELECT e.event_time + make_interval(days => r.ttl_days) FROM _ev e, _rif r),
        'cleanup_at = event_time + il TTL di dbops.automation_rules_tbl'
    )
END;

-- 5) Tipo fuori vocabolario: la frase nomina il TIPO PASSATO.
--    ⚠️ Il pattern non attraversa il segnaposto: si aggancia alla coda fissa.
SELECT throws_like(
    'SELECT vendite.fn_log_event(''PIPPO'', 1, ''PGTAP_IGNOTO'')',
    '%non sa dove collocare%',
    'entity_type fuori vocabolario: rifiutato, e la frase nomina il tipo passato'
);

-- 6) Entita' inesistente: frase DIVERSA, perche' il rimedio e' diverso.
SELECT throws_like(
    'SELECT vendite.fn_log_event(''COMMESSA'', 999999999, ''PGTAP_ORFANO'')',
    '%non si lega a nessun emittente%',
    'entita'' inesistente: rifiutato con un messaggio distinto dal tipo ignoto'
);

-- 7) ⭐ Il presidio dell'ASSENZA (D-12).
--    Se un domani una FK verso una tabella con `attivo` entrasse su event_log,
--    `dbops.fn_run_automations_attivo` genererebbe da sola un lucchetto
--    `require_attivo`, e il diario smetterebbe di scrivere per un emittente
--    cessato — cioe' proprio quando serve. E' una regressione che nessuno
--    vedrebbe arrivare: non la introduce una persona, la introduce
--    un'automazione, alle 21:00.
--    ⚠️ Asserzione STRUTTURALE e non comportamentale, ed e' dichiarato: il caso
--    funzionale non e' raggiungibile perche' disattivare un emittente con
--    documenti collegati e' gia' vietato da un altro guard (misurato:
--    «Non si puo' disattivare anagrafiche.emittenti_fiscali ... ci sono ancora
--    righe collegate in vendite.contratti»).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite'
        AND c.relname = 'event_log'
        AND NOT t.tgisinternal
        AND t.tgname LIKE '%require_attivo%'),
    0,
    'nessun lucchetto require_attivo su event_log: il diario non smette di scrivere'
);

SELECT * FROM finish();
ROLLBACK;
