-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Zero ERP — PRESIDIO sui riferimenti morti nelle funzioni
--
-- Brief: docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md §5
--
-- Pezzi del presidio (nessuno duplica la logica di un altro):
--   dbops.fn_check_funzioni_riferimenti_morti()   la misura      (20260804-62 … 20260914-02)
--   dbops.riferimenti_morti_esenzioni             il registro    (20260804-63)
--   dbops.vw_riferimenti_morti_da_sanare          i difetti aperti
--   dbops.vw_riferimenti_morti_rientrati          le voci di troppo (20260804-64)
--   scripts/sql/check_funzioni_riferimenti_morti.sql   lo strumento a mano
--   scripts/sql/guardrail_riferimenti_morti.sql        il gate della CI
--   questo file                                        il gate della suite
--
-- Indice test (9 asserzioni):
--   1. l'estensione plpgsql_check c'e' (senza, i test 2 e 3 fanno skip)
--   1-bis. plpgsql_check ha potuto controllare OGNI funzione (NON_MISURATO)
--   2. nessun difetto REALE/ORFANA fuori dal registro del debito
--   3. nessuna voce RIENTRATA nel registro (il debito deve calare)
--   4. ogni voce del registro ha un motivo scritto
--   5. nessun riferimento morto nei DATI di configurazione
--   6. il conteggio che legge il DIGEST concorda con la misura diretta
--   7. ⛔ un 42501 dentro una SECURITY DEFINER di un ALTRO proprietario non e'
--      mai REALE: e' FP_DEFINER_PRIVILEGIO (20260914-02) — skip dichiarato
--      dove questo ruolo non ne misura nessuno (proprietario, superuser, CI)
--   8. ⭐ l'esenzione «pgAgent» del registro c'e' SE E SOLO SE pgagent.pga_job
--      manca su questa macchina (90_end/20260914-03: un registro descrive una
--      macchina alla volta)
--   9. la vista delle voci rientrate legge la misura da
--      dbops.fn_check_funzioni_riferimenti_morti() (la 10 e la 11 la sostituiscono)
--  10. ⭐ una voce la cui funzione esce NON_MISURATO NON e' rientrata
--      (20261104-54, brief-db-revisione-dbops D7)
--  11. una voce coperta da un difetto non e' rientrata, una voce su una funzione
--      che la misura non vede piu' si'
--
-- ── ⚠️ I TEST 2 E 3 SONO IL PRESIDIO VERO DEL 20260914-02, E LO SONO DA OGNI
--   RUOLO. Il primo digest settimanale (14-09) ha dato «rientrati: 1» sulla
--   riga pgAgent: come zeroerp_app il 42501 usciva REALE e la riga serviva,
--   come titodb (fn_conta_presidio e' DEFINER) non usciva niente e la riga era
--   di troppo — la stessa riga, la stessa macchina. Con la classe nuova e la
--   convergenza del -03, il 2 e il 3 rispondono uguale da app e da
--   proprietario; senza la classe, tolta la riga, il 2 e' rosso come app.
-- ------------------------------------------------------------
-- ── PERCHE' ESISTE ──────────────────────────────────────────────────────
--   Il 2026-03-31 due funzioni morte furono **viste**, e lasciate li' con
--   un changeSet che diceva «Da verificare se la funzione va rimossa dal
--   DB». Cinque mesi dopo una delle due ha fatto fallire un migrate.
--   Una segnalazione in un commento non e' un presidio: e' un promemoria
--   che nessuno rilegge. Questo file e' la differenza fra le due cose.
--
--   ⚠️ Il caso `trgfn_preventivi_guard_annullamento` (`20260804-54`) dice
--   perche' serve la suite e non basta la buona volonta': quel guard e'
--   stato scritto e rotto lo **stesso giorno** in cui il controllo lo ha
--   trovato. Senza, sarebbe entrato in servizio parlando arabo esattamente
--   nel momento in cui doveva spiegare un rifiuto.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 1. L'estensione c'e'?
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check'),
  'estensione plpgsql_check presente (senza, il presidio non puo'' misurare)'
);

-- ⚠️ La misura si materializza UNA VOLTA: compila ~500 funzioni, e le
--    trigger function una volta per ogni tabella agganciata. I test 2 e 3
--    sono due anti-join sullo stesso dato — passare dalle due viste
--    significherebbe pagarla due volte.
--    Se l'estensione manca la temp table resta vuota: i due test fanno
--    skip esplicito, che e' meglio di un verde che non ha misurato niente.
CREATE TEMP TABLE misura ON COMMIT DROP AS
SELECT *
  FROM dbops.fn_check_funzioni_riferimenti_morti()
 WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check');

-- ============================================================
-- 1-bis. 🔴 LO STRUMENTO HA MISURATO? — e va PRIMA dell'asserzione centrale
--
-- ⛔ Se `plpgsql_check` solleva invece di rispondere, il gestore EXCEPTION
--    della misura scrive `error:CHECK-KO:` e la funzione classifica quelle
--    righe come `NON_MISURATO` (changeSet 20260910-36). Di quelle funzioni
--    non si sa NIENTE: il test 2 direbbe «nessun riferimento morto» avendo
--    guardato la meta' delle cose, e il test 3 vedrebbe ogni voce del
--    registro come «rientrata».
-- ⚠️ Fino al 2026-09-10 quella forma cadeva nell'ELSE e usciva come REALE:
--    su dbdev sono state 779 righe su 780 funzioni, con un registro di DUE
--    voci — il test 2 falliva elencando 779 difetti che non esistevano.
--    Brief: brief-db-un-destinatario-per-i-presidi §9.3.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
        FROM (
          SELECT DISTINCT m.schema_nome || '.' || m.funzione || ' -> ' || m.esito AS riga
            FROM misura m
           WHERE m.classe = 'NON_MISURATO'
        ) x
    ), ''),
    '',
    'plpgsql_check ha potuto controllare OGNI funzione (nessuna NON_MISURATO)'
  )
END;

-- ============================================================
-- 2. Nessun difetto fuori registro — l'asserzione centrale
--
-- Il messaggio elenca i colpevoli invece di contarli: un test che dice
-- «ci sono 4 difetti» costringe a rilanciare lo strumento a mano per
-- sapere quali.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(x.riga, E'\n  ' ORDER BY x.riga)
        FROM (
          SELECT DISTINCT m.schema_nome || '.' || m.funzione || ' -> ' || m.esito AS riga
            FROM misura m
           WHERE m.classe IN ('REALE', 'ORFANA')
             AND NOT EXISTS (
                   SELECT 1 FROM dbops.riferimenti_morti_esenzioni e
                    WHERE e.schema_nome = m.schema_nome
                      AND e.funzione    = m.funzione
                      AND m.esito LIKE e.esito_like)
        ) x
    ), ''),
    '',
    'nessun riferimento morto fuori dal registro del debito'
  )
END;

-- ============================================================
-- 3. Il registro non contiene voci rientrate
--
-- ⚠️ E' cio' che rende il registro un DEBITO e non un elenco di eccezioni.
--    Se un difetto registrato non compare piu', la riga va TOLTA: senza
--    questo test il registro puo' solo crescere, e un registro che cresce
--    e basta e' il posto dove i problemi vanno a sparire.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(e.schema_nome || '.' || e.funzione, ', ' ORDER BY e.funzione)
        FROM dbops.riferimenti_morti_esenzioni e
       WHERE NOT EXISTS (
               SELECT 1 FROM misura m
                WHERE m.classe IN ('REALE', 'ORFANA')
                  AND m.schema_nome = e.schema_nome
                  AND m.funzione    = e.funzione
                  AND m.esito LIKE e.esito_like)
    ), ''),
    '',
    'nessuna voce rientrata nel registro (il difetto e'' risolto: togliere la riga)'
  )
END;

-- ============================================================
-- 4. Ogni voce del registro ha un motivo
--
-- Ridondante col CHECK chk_riferimenti_morti_esenzioni_motivo, e va bene:
-- il CHECK protegge la scrittura, questo protegge dal caso in cui qualcuno
-- droppi il CHECK per far passare una riga. Costa una query su una tabella
-- di poche righe.
-- ============================================================
SELECT is(
  (SELECT count(*) FROM dbops.riferimenti_morti_esenzioni
    WHERE motivo IS NULL OR length(btrim(motivo)) < 40)::int,
  0,
  'ogni voce del registro porta un motivo scritto (>= 40 caratteri)'
);

-- ============================================================
-- 5. Riferimenti morti nei DATI di configurazione
--
-- ⚠️ plpgsql_check compila i CORPI: una tabella nominata come stringa in
--    una tabella di configurazione gli e' invisibile — nel corpo che la
--    consuma compare solo come parametro. Il 2026-08-04 questa misura ha
--    trovato config.sistema_codici 'lotti_attivita', che puntava a
--    vendite.attivita_fatturabili_lotti droppata cinque mesi prima: stessa
--    morte delle funzioni, ma nessuno dei due giri del controllo sulle
--    funzioni poteva vederla. (Rimossa da 20260804-50.)
-- ============================================================
SELECT is(
  COALESCE((
    SELECT string_agg(sc.codice_interno || ' -> ' || sc.schema_tabella || '.' || sc.nome_tabella,
                      ', ' ORDER BY sc.codice_interno)
      FROM config.sistema_codici sc
     WHERE sc.nome_tabella IS NOT NULL
       AND to_regclass(sc.schema_tabella || '.' || sc.nome_tabella) IS NULL
  ), ''),
  '',
  'nessuna riga di config.sistema_codici punta a una tabella inesistente'
);

-- ============================================================
-- 6. 🔴 IL CONTEGGIO CHE LEGGE IL DIGEST — quello che il test 1-bis NON vede
--
-- ⛔ Il digest dei presidi non legge questa vista: chiede
--    `dbops.fn_conta_presidio`, che e' SECURITY DEFINER con
--    `search_path = pg_catalog, pg_temp`. Fino al 2026-09-12 la scansione
--    ereditava quel path, e li' non si risolvevano NE' `plpgsql_check_function`
--    (sta in `public`) NE' i riferimenti a `unaccent`, `dblink` e `geometry`
--    dentro le funzioni che compila: ogni funzione usciva `NON_MISURATO`.
--    Misurato quel giorno: il digest riferiva **784** «riferimenti morti»
--    mentre questa stessa vista, letta diretta, rispondeva **0**.
--
-- ⭐ Il test 1-bis non poteva prenderlo, e non per una svista: misura la
--    scansione DIRETTA, cioe' il percorso SANO. Per due giorni e' stato verde
--    su un difetto vivo.
--    *Un presidio che misura il percorso sano non presidia quello in servizio.*
--
-- ⇒ Qui si confrontano i DUE percorsi. Non e' circolare — i due lati girano in
--    contesti di risoluzione diversi, ed e' proprio la differenza fra i due che
--    il difetto produceva.
-- ⚠️ E non pinna un numero: se comparira' un riferimento morto vero, i due lati
--    saliranno INSIEME e questo test restera' verde. A dirlo e' il test 2, che
--    e' il suo mestiere. Qui si asserisce che i due percorsi CONCORDANO.
--
-- ⚠️ Il `DROP TABLE IF EXISTS tmp_raw` non e' pulizia: e' obbligatorio. La
--    scansione lavora su una temp table, e quella creata qui sopra appartiene
--    al ruolo del TEST; `fn_conta_presidio` gira come PROPRIETARIO e il suo
--    `DELETE FROM tmp_raw` prenderebbe `42501 permesso negato` — cioe' un
--    ERRORE, che ferma il file e lascia tutti i test SENZA girare.
-- ⚠️ Costa una seconda scansione completa (~4s): e' il prezzo per misurare il
--    percorso che il digest usa davvero, e non un suo somigliante.
-- ============================================================
-- ⚠️ Il verbo in un'istruzione SUA, prima dell'asserzione: dentro la `SELECT`
--    non si droppa niente, e il `DELETE` della DEFINER arriverebbe comunque su
--    una temp table che non e' sua.
DROP TABLE IF EXISTS tmp_raw;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  ELSE is(
    dbops.fn_conta_presidio('dbops.vw_riferimenti_morti_da_sanare'),
    (SELECT count(*)
       FROM misura m
      WHERE m.classe IN ('REALE', 'ORFANA', 'NON_MISURATO')
        AND NOT EXISTS (
              SELECT 1 FROM dbops.riferimenti_morti_esenzioni e
               WHERE e.schema_nome = m.schema_nome
                 AND e.funzione    = m.funzione
                 AND m.esito LIKE e.esito_like)),
    'il conteggio che legge il digest (fn_conta_presidio) concorda con la misura diretta'
  )
END;

-- ============================================================
-- 7. ⛔ Un 42501 in una DEFINER altrui non e' mai REALE
--
-- Il corpo di una SECURITY DEFINER gira coi privilegi del PROPRIETARIO:
-- «il chiamante puo' risolvere il riferimento?» non dice niente della
-- funzione. Questo ruolo (l'app) prende un 42501 su fn_get_pgagent_job_stato
-- perche' non vede pgagent.*; fino al 20260914-02 usciva REALE.
-- ⚠️ Il caso si PRESENTA solo dove chi misura non e' proprietario e c'e' uno
--   schema che non vede: come proprietario, come superuser (CI) o dove ogni
--   schema e' visibile, non c'e' nessun 42501 da classificare — e allora si
--   DICHIARA, non si finge di aver verificato.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'plpgsql_check')
    THEN skip('plpgsql_check assente: misura non eseguibile', 1)
  WHEN NOT EXISTS (SELECT 1 FROM misura m WHERE m.esito ~ '^error:42501:')
    THEN skip('nessun 42501 misurato da ' || current_user || ': il caso non si presenta da questo ruolo', 1)
  ELSE is(
    COALESCE((
      SELECT string_agg(m.classe || ' ' || m.schema_nome || '.' || m.funzione, ', ' ORDER BY m.funzione)
        FROM misura m
       WHERE m.esito ~ '^error:42501:'
         AND m.classe <> 'FP_DEFINER_PRIVILEGIO'
         AND EXISTS (
               SELECT 1
                 FROM pg_proc p
                 JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = m.schema_nome
                  AND p.proname = m.funzione
                  AND pg_get_function_identity_arguments(p.oid) = m.argomenti
                  AND p.prosecdef
                  AND NOT pg_has_role(current_user, p.proowner, 'MEMBER'))
    ), ''),
    '',
    'ogni 42501 dentro una SECURITY DEFINER di un altro proprietario e'' FP_DEFINER_PRIVILEGIO, mai REALE'
  )
END;

-- ============================================================
-- 8. ⭐ L'esenzione «pgAgent» segue la macchina
--
-- Il 20260906-16 ha scritto la regola («un registro di debito descrive lo
-- stato di UNA macchina alla volta»); il 90_end/20260914-03 la esegue a ogni
-- migrate: la riga c'e' dove pgagent.pga_job manca (in CI: 42P01 per chiunque)
-- e non c'e' dove esiste (dev: nessun occhio trova piu' quel difetto).
-- ⚠️ La presenza si legge dal CATALOGO, non con to_regclass: quella solleva
--   42501 a chi non ha USAGE sullo schema — e questo test gira come app.
-- ============================================================
SELECT is(
  (SELECT count(*)
     FROM dbops.riferimenti_morti_esenzioni e
    WHERE e.schema_nome = 'dbops'
      AND e.funzione    = 'fn_get_pgagent_job_stato'
      AND e.esito_like  = '%:RETURN QUERY:%pgagent%'),
  CASE WHEN EXISTS (SELECT 1
                      FROM pg_class c
                      JOIN pg_namespace n ON n.oid = c.relnamespace
                     WHERE n.nspname = 'pgagent' AND c.relname = 'pga_job' AND c.relkind = 'r')
       THEN 0::bigint ELSE 1::bigint END,
  'l''esenzione pgAgent del registro c''e'' se e solo se pgagent.pga_job manca su questa macchina'
);

-- ============================================================
-- 9-11. La vista delle voci rientrate, su una misura COSTRUITA
--
-- ⛔ Il caso vero (plpgsql_check che solleva invece di rispondere) non si
--   costruisce in un test: provati il 2026-11-04 un errore di sintassi, un
--   1/0, una IMMUTABLE che solleva al planning, un record non assegnato, una
--   polimorfica, un event trigger, trigger su vista, partizionata e con
--   transition table — plpgsql_check li RIFERISCE tutti, nessuno lo fa
--   sollevare. Solleva per l'ambiente (estensione irraggiungibile, lock): non
--   per una funzione.
-- ⭐ Allora si prova la vista VIVA su una misura costruita: il suo testo
--   (pg_get_viewdef) con la chiamata alla misura sostituita da una funzione in
--   pg_temp con le stesse colonne. Non e' una copia della logica: e' la vista,
--   con un'altra sorgente. La 9 prova che la sostituzione avviene.
-- ============================================================
CREATE FUNCTION pg_temp.fn_pgtap_misura_finta()
RETURNS TABLE(classe text, schema_nome text, funzione text, argomenti text, esito text)
LANGUAGE sql AS $f$
  VALUES ('NON_MISURATO', 'pgtap_rm', 'fn_non_misurata', '', 'error:CHECK-KO:lo strumento ha sollevato'),
         ('REALE',        'pgtap_rm', 'fn_coperta',      '', 'error:42P01:1:istruzione SQL:tabella_sparita_pgtap')
$f$;

INSERT INTO dbops.riferimenti_morti_esenzioni (id, schema_nome, funzione, esito_like, motivo)
VALUES (990001, 'pgtap_rm', 'fn_non_misurata', '%tabella_sparita_pgtap%',
        'pgTAP: voce su una funzione che lo strumento non ha potuto misurare'),
       (990002, 'pgtap_rm', 'fn_coperta',      '%tabella_sparita_pgtap%',
        'pgTAP: voce su una funzione col difetto ancora presente nella misura'),
       (990003, 'pgtap_rm', 'fn_guarita',      '%tabella_sparita_pgtap%',
        'pgTAP: voce su una funzione che la misura non vede piu, da togliere');

-- ⚠️ Il testo si legge con search_path = pg_catalog: pg_get_viewdef qualifica
--   i nomi RISPETTO al search_path di chi chiama, e l'app ha dbops nel suo
--   (rosso visto da Tid, 2026-11-04: la sostituzione non trovava il nome).
-- ⛔ Se la sostituzione non avviene, la 10 e la 11 NON eseguono la vista con la
--   misura vera: e' una compilazione di centinaia di funzioni, e dopo la 6
--   (conteggio DEFINER) cade su tmp_raw, che e' del proprietario. Diventano
--   rosse con una riga sentinella.
SET LOCAL search_path = pg_catalog;
CREATE TEMP TABLE _rientrati_testo ON COMMIT DROP AS
SELECT v.orig,
       CASE WHEN strpos(v.sost, 'dbops.fn_check_funzioni_riferimenti_morti()') = 0
             AND strpos(v.sost, 'pg_temp.fn_pgtap_misura_finta()') > 0
            THEN v.sost
            ELSE $q$SELECT 990001 AS id, 'sostituzione mancata'::text AS funzione$q$
       END AS finta
  FROM (SELECT d AS orig,
               replace(d, 'dbops.fn_check_funzioni_riferimenti_morti()',
                          'pg_temp.fn_pgtap_misura_finta()') AS sost
          FROM pg_get_viewdef('dbops.vw_riferimenti_morti_rientrati'::regclass) AS d) v;
RESET search_path;

SELECT ok(
  (SELECT strpos(orig, 'dbops.fn_check_funzioni_riferimenti_morti()') > 0
          AND strpos(finta, 'pg_temp.fn_pgtap_misura_finta()') > 0
     FROM _rientrati_testo),
  'la vista delle voci rientrate legge la misura da fn_check_funzioni_riferimenti_morti: la sostituzione avviene'
);

SELECT is_empty(
  format($q$SELECT funzione FROM (%s) v WHERE v.id = 990001$q$,
         rtrim((SELECT finta FROM _rientrati_testo), '; ')),
  'una voce la cui funzione esce NON_MISURATO non e'' rientrata: di quella funzione non si sa niente'
);

SELECT results_eq(
  format($q$SELECT funzione FROM (%s) v WHERE v.id IN (990002, 990003) ORDER BY 1$q$,
         rtrim((SELECT finta FROM _rientrati_testo), '; ')),
  $$VALUES ('fn_guarita'::text)$$,
  'una voce coperta da un difetto non e'' rientrata; una su una funzione che la misura non vede piu'' si'''
);

SELECT * FROM finish();

ROLLBACK;
