-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: generazione e applicazione fondi fattura
-- ------------------------------------------------------------
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): la sorgente nasce in
--   bozza e si porta avanti con dbops.fn_pgtap_porta_a_stato (prima nasceva
--   gia' DEFINITIVA).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): cliente, azienda e
--   registro li costruisce dbops.fn_pgtap_crea_mondo_cliente (+
--   script.fn_pgtap_registro_fattura) invece di pescare il primo billing
--   account, che su un database ricostruito non c'e'. Il contesto si apre
--   DOPO, sull'operatore del mondo.
-- rev 2026-10-24 (brief-modello-documento-vendita R-5): le due fatture le
--   scrive dbops.fn_pgtap_crea_fattura sul cliente del mondo, con minimo e
--   totale alla nascita; niente piu' INSERT a mano, snapshot in LATERAL e
--   porta_a_stato nel file.
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Tipo_fondo_fattura disponibile (F_F_ADD_ACC)
-- 3) Inserimento fattura sorgente (minimo)
-- 4) Generazione fondi source
-- 5) Inserimento fattura figlia
-- 6) Applicazione fondi fattura
-- 7) Source aggiornata e righe fondi presenti
-- 8) Sync contabili fondo fattura
-- 9) Reset fondi fattura (scenario standard): l'atto si CANCELLA
-- 10) Atto cancellato e righe fondi rimosse
-- 11) Righe contabili fondo rimosse
-- 11-bis) Il DELETE riapre la rigenerazione: il giro successivo rifa' l'atto
-- 12) Re-applicazione fondi
-- 13) Sync + chiusura contabile
-- 14a) Reset bloccato da contabile CHIUSA (denaro MAI registrato)
-- 15) Source ANNULLATA e warning log
-- 16) Source ANNULLATA su reset bloccato
-- 17) ⭐ Il reset bloccato dichiara il suo CODICE nel log (W_, 20260821-43)
-- 18) Ragione dell'annullamento SUL DATO (motivo), non solo nel log
-- 19) Warning log su reset bloccato
-- 20) Cleanup completato
-- 21) Assert finale cleanup
--
-- ⭐ IL CASO 14 E' SDOPPIATO (Tid, 2026-08-22). Qui resta la meta'
--   «contabilizzazione»: una distinta CHIUSA con dentro denaro che NON e' mai
--   stato registrato, dove il reset e' bloccato dalla chiusura. L'altra meta'
--   — «registrazione»: la riga diventa POSTATA, l'atto passa a ESEGUITO e il
--   reset non lo tocca — vive in db/pgtap/vendite/test-fondo-fattura-eseguito.sql,
--   perche' pretende un movimento contabile vero e un'altra catena di guard.
--   Due fatti diversi, due file: qui SOSPESA non e' piu' un rattoppo per
--   tenere il verde, e' la fixture giusta del caso che questo file racconta.
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
-- Il mondo (azienda, operatore, cliente) si costruisce PRIMA, e il contesto
-- si apre sul suo operatore.
CREATE TEMP TABLE tmp_mondo_ff AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('fondi_fattura');

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_ff)); END $ctx$;

SELECT plan(22);
-- ============================================================
-- 0) Riferimenti e costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_ff AS
SELECT 'pgtap_fondi_fattura'::text AS test_scope;
CREATE TEMP TABLE tmp_centro_fondo AS WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE -- c.attivo IS TRUE and
    c.is_fondo_fattura IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
      codice,
      codice_interno,
      descrizione,
      is_compensazione,
      is_fondo_fattura,
      attivo,
      meta
    )
  SELECT 'TEST_CENTRO_FONDO_' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
    'FONDO_TEST',
    'Centro fondo test pgtap',
    false,
    true,
    true,
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_ff
      )
    )
  WHERE NOT EXISTS (
      SELECT 1
      FROM existing
    )
  RETURNING id
)
SELECT id
FROM existing
UNION ALL
SELECT id
FROM ins;
-- I riferimenti del documento sono quelli del mondo: il registro e' quello
-- della sua azienda (lo crea se non c'e').
CREATE TEMP TABLE tmp_refs_ff AS
SELECT script.fn_pgtap_registro_fattura(m.emittente_soggetto_ruolo_id) AS registro_id,
  m.billing_account_id,
  m.utility_id,
  (
    SELECT id
    FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT id
    FROM config.valute
    ORDER BY id
    LIMIT 1
  ) AS valuta_id,
  m.emittente_soggetto_ruolo_id,
  (
    SELECT id
    FROM tmp_centro_fondo
    ORDER BY id
    LIMIT 1
  ) AS centro_fondo_id
FROM tmp_mondo_ff m;
SELECT ok(
    (
      SELECT registro_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND utility_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND valuta_id IS NOT NULL
        AND emittente_soggetto_ruolo_id IS NOT NULL
        AND centro_fondo_id IS NOT NULL
      FROM tmp_refs_ff
    ),
    'Riferimenti minimi presenti'
  );
-- ============================================================
-- 1) Tipo fondo fattura
-- ============================================================
CREATE TEMP TABLE tmp_tipo_fondo AS
SELECT t.id
FROM vendite.tipi_fondi_fattura t
WHERE t.attivo IS TRUE
  AND t.codice_interno = 'F_F_ADD_ACC'
ORDER BY t.id
LIMIT 1;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_tipo_fondo
    ),
    'Tipo_fondo_fattura F_F_ADD_ACC disponibile'
  );
-- ============================================================
-- 2) Fattura sorgente con minimo
-- ============================================================
-- ⭐ La sorgente la scrive il builder (rev 2026-10-24, R-5): stesso cliente
--    del mondo (terzo parametro), minimo e totale alla NASCITA, e fuori bozza
--    indirizzi, intestazione e matrice fino a DEFINITIVA. Il registro e'
--    quello dell'azienda, lo stesso di tmp_refs_ff; l'etichetta da' il
--    test_scope del file ('pgtap_' || etichetta), su cui gira il cleanup.
--    ⚠️ utility_id e stato servono da 20260815-07: la generazione FILTRA
--    sull'utility (il builder scrive quella del BA, la stessa di tmp_refs_ff)
--    e accetta solo sorgenti DEFINITIVA.
CREATE TEMP TABLE tmp_fattura_src AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_fattura', 'DEFINITIVA',
         (SELECT billing_account_id FROM tmp_refs_ff),
         false, false,
         p_minimo => true, p_totale_a_pagare => 100.00) f;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_src
    ),
    'Inserimento fattura sorgente (minimo)'
  );
-- ============================================================
-- 3) Generazione fondi source
-- ============================================================
SELECT is(
    vendite.fn_genera_fondi_fattura_source(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Generazione fondi source'
  );
-- ============================================================
-- 4) Fattura figlia
-- ============================================================
-- ⚠️ Stessa utility della sorgente: da 20260815-08 il fondo passa solo
--    fra fatture che condividono tutti e NOVE gli elementi della chiave
--    di generazione, e l'utility e' uno di quelli. La figlia resta in bozza.
CREATE TEMP TABLE tmp_fattura_dst AS
SELECT f.fattura_id AS id
  FROM dbops.fn_pgtap_crea_fattura(
         'fondi_fattura', 'DRAFT',
         (SELECT billing_account_id FROM tmp_refs_ff),
         false, false,
         p_minimo => false, p_totale_a_pagare => 200.00) f;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_dst
    ),
    'Inserimento fattura figlia'
  );
-- ============================================================
-- 5) Applicazione fondi
-- ============================================================
SELECT is(
    vendite.fn_applica_fondi_fattura(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_fattura_figlia_id => (
        SELECT id
        FROM tmp_fattura_dst
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Applicazione fondi fattura'
  );
-- ============================================================
-- 6) Verifica stato source e righe
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.stato = 'ASSEGNATO'
        AND s.fattura_figlia_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
    ),
    'Source aggiornata a ASSEGNATO'
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura ff
      WHERE ff.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND ff.riferimento_fattura_id = (
          SELECT id
          FROM tmp_fattura_src
        )
    ),
    'Righe fondi fattura presenti'
  );
-- ============================================================
-- 7) Sync contabili fondo fattura
-- ============================================================
SELECT is(
    (
      SELECT inserted_righe
      FROM vendite.fn_sync_contabili_fondo_fattura(
          p_fattura_figlia_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Sync contabili fondo fattura'
  );
-- ============================================================
-- 8) Reset fondi fattura (scenario standard)
-- ============================================================
-- ⭐ DAL 2026-08-21 IL RESET CANCELLA (S1-17, decisione D11): un atto non
--   eseguito e' una PROPOSTA, non un fatto, e il giro successivo ne fa uno
--   nuovo letto sul residuo DI ADESSO. Prima tornava a DISPONIBILE con
--   l'importo vecchio congelato.
--   ⚠️ La colonna di ritorno si chiama ora `deleted_source`: `updated_source`
--   avrebbe continuato a dire una cosa falsa.
SELECT is(
    (
      SELECT deleted_source
      FROM vendite.fn_reset_fondi_fattura(
          p_fattura_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Reset fondi fattura (atto cancellato)'
  );
-- ============================================================
-- 9) Verifica reset standard
-- ============================================================
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
    ),
    'Atto non eseguito CANCELLATO dal reset'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM vendite.fatture_fondi_fattura ff
      WHERE ff.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
    ),
    'Righe fondi fattura rimosse'
  );
SELECT ok(
    (
      SELECT count(*) = 0
      FROM pagamenti.vendite_contabili_righe cr
      WHERE cr.fattura_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND cr.attivo IS TRUE
        AND COALESCE(cr.meta->>'origine', '') = 'FONDO_FATTURA'
    ),
    'Righe contabili fondo rimosse'
  );
-- ============================================================
-- 9-bis) Il DELETE riapre la rigenerazione — ed e' voluto
-- ============================================================
-- ⭐ E' la seconda meta' di S1-17, quella che non si vede: e' la regola
--   dell'«atto unico» (fn_fondo_fattura_proponibile, passo 2) a impedire al
--   giro notturno di rifare un fondo, e quella guarda se un atto esiste IN
--   QUALUNQUE STATO. Finche' il reset lo lasciava ANNULLATO, la porta restava
--   chiusa per sempre; cancellandolo, il giro successivo lo rifa' leggendo il
--   residuo di ADESSO.
--   ⚠️ Senza questa asserzione il cambio sarebbe invisibile: il resto del file
--   riapplicherebbe un fondo che non esiste piu' e fallirebbe piu' avanti, con
--   un rosso che accusa la riapplicazione invece del reset.
SELECT is(
    vendite.fn_genera_fondi_fattura_source(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Cancellato l''atto, il giro successivo ne rigenera uno nuovo'
  );
-- ============================================================
-- 10) Re-applicazione + contabilizzazione movimento
-- ============================================================
SELECT is(
    vendite.fn_applica_fondi_fattura(
      p_billing_account_id => (
        SELECT billing_account_id
        FROM tmp_refs_ff
      ),
      p_utility_id => (
        SELECT utility_id
        FROM tmp_refs_ff
      ),
      p_tipo_doc_fiscale_id => (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_ff
      ),
      p_emittente_soggetto_ruolo_id => (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_ff
      ),
      p_valuta_id => (
        SELECT valuta_id
        FROM tmp_refs_ff
      ),
      p_fattura_figlia_id => (
        SELECT id
        FROM tmp_fattura_dst
      ),
      p_tipo_fondo_fattura_id => (
        SELECT id
        FROM tmp_tipo_fondo
      )
    ),
    1,
    'Re-applicazione fondi fattura'
  );
SELECT is(
    (
      SELECT inserted_righe
      FROM vendite.fn_sync_contabili_fondo_fattura(
          p_fattura_figlia_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    1,
    'Sync contabili fondo (secondo giro)'
  );
-- ⚠️ La distinta si sceglie UNA volta e si tiene: prima serviva alle righe da
--   sospendere, poi alla chiusura. Due sotto-select indipendenti potrebbero
--   pescare distinte diverse, e il test passerebbe a giorni alterni.
-- ⭐ Il legame riga -> atto si legge dalla COLONNA `fondo_source_id`
--   (changeSet 20260821-48, passo S1-14): prima era una stringa dentro il
--   meta, senza integrita' ne' indice, e la leggevano tre funzioni.
CREATE TEMP TABLE tmp_contabile_ff AS
SELECT cr.contabile_id
FROM pagamenti.vendite_contabili_righe cr
WHERE cr.fattura_id = (
    SELECT id
    FROM tmp_fattura_src
  )
  AND cr.fondo_source_id = (
    SELECT s.id
    FROM vendite.fatture_fondi_fattura_source s
    WHERE s.fattura_sorgente_id = (
        SELECT id
        FROM tmp_fattura_src
      )
      AND s.fattura_figlia_id = (
        SELECT id
        FROM tmp_fattura_dst
      )
    ORDER BY s.id DESC
    LIMIT 1
  )
ORDER BY cr.id DESC
LIMIT 1;

-- ⛔ DAL 2026-08-21 UNA DISTINTA NON SI CHIUDE CON RIGHE ANCORA PRONTE.
--   Il guard pagamenti.trgfn_vendite_contabili_guard_chiusura (changeSet
--   20260821-29) conta le righe attive il cui stato ha `is_postabile` — cioe'
--   `ABBINATA`, l'unico — e rifiuta la chiusura: sono denaro dichiarato che
--   sparirebbe da entrambi i conti.
--   La riga nata dal sync del fondo e' esattamente in quello stato, quindi la
--   fixture chiudeva la distinta in un modo che l'applicazione non puo' piu'
--   percorrere. Si prende una delle due uscite che il guard stesso indica:
--   sospendere (`SOSPESA`, `is_postabile = false`).
--
--   ⭐ E SOSPESA e' la fixture GIUSTA di questo caso, non un ripiego — deciso
--   sdoppiando il caso 14 (Tid, 2026-08-22). Qui si collauda la
--   CONTABILIZZAZIONE: una distinta chiusa con dentro denaro che NON e' mai
--   stato registrato, dove a bloccare il reset e' la chiusura.
--   `vendite.fn_reset_fondi_fattura` blocca sulla distinta CHIUSA e non guarda
--   lo stato della riga: sospesa, la riga resta agganciata, la distinta si
--   chiude, il reset e' bloccato — e l'atto passa ad ANNULLATO col motivo sul
--   dato.
--   ⇒ L'altra meta', la REGISTRAZIONE (riga POSTATA con il suo movimento, atto
--   che passa a ESEGUITO, reset che non lo tocca), sta in
--   db/pgtap/vendite/test-fondo-fattura-eseguito.sql: pretende un
--   vendite_movimenti vero e un'altra catena di guard, ed e' un fatto diverso
--   — non lo stesso caso scritto meglio.
UPDATE pagamenti.vendite_contabili_righe cr
SET stato_id = (
    SELECT s.id
    FROM pagamenti.vendite_contabili_righe_stati s
    WHERE s.codice_interno = 'SOSPESA'
    ORDER BY s.id
    LIMIT 1
  )
FROM pagamenti.vendite_contabili_righe_stati st
WHERE cr.contabile_id = (SELECT contabile_id FROM tmp_contabile_ff)
  AND st.id = cr.stato_id
  AND cr.attivo IS TRUE
  AND st.is_postabile IS TRUE;

UPDATE pagamenti.vendite_contabili c
SET stato_id = (
    SELECT s.id
    FROM pagamenti.vendite_contabili_stati s
    WHERE s.codice_interno = 'CHIUSA'
    ORDER BY s.id
    LIMIT 1
  )
WHERE c.id = (SELECT contabile_id FROM tmp_contabile_ff);
-- ============================================================
-- 11) Reset bloccato dalla distinta CHIUSA (caso 14a)
-- ============================================================
-- ⚠️ Zero CANCELLATI, non zero aggiornati: il reset cancella gli atti che puo'
--   toccare, e questo non lo puo' toccare. La distinta e' chiusa, quindi il
--   minimo non e' piu' ripristinabile e l'atto passa ad ANNULLATO.
SELECT is(
    (
      SELECT deleted_source
      FROM vendite.fn_reset_fondi_fattura(
          p_fattura_id => (
            SELECT id
            FROM tmp_fattura_dst
          )
        )
    ),
    0,
    'Reset bloccato dalla distinta contabile CHIUSA'
  );
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.fattura_figlia_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND s.stato = 'ANNULLATO'
    ),
    'Source ANNULLATA su reset bloccato'
  );
-- ⭐ Il ramo bloccato scrive anche il suo CODICE nel diario della fattura
--    (changeSet 20260821-43, cantiere brief-db-liste-drawer-lotto L1/P-6).
--    Qui non c'e' nessun errore catturato: la condizione — la contabile e'
--    chiusa — la vede questa funzione, quindi il codice e' DICHIARATO, ed e'
--    un `W_` perche' non si solleva: il resto del reset va avanti.
--    ⚠️ `cause` vive nello stesso meta e non e' la stessa cosa: quello e' il
--    vocabolario locale del ramo, `error_code` e' il codice di catalogo che le
--    liste del drawer lotto mostrano.
SELECT is(
    (
      SELECT fl.meta->>'error_code'
      FROM vendite.fatture_log fl
      WHERE fl.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND fl.meta->>'cause' = 'CONTABILE_CHIUSA'
      ORDER BY fl.id DESC
      LIMIT 1
    ),
    'W_FONDO_MINIMO_NON_RIPRISTINABILE',
    'Il reset bloccato dichiara il suo codice nel log'
  );
-- ⚠️ Questa asserzione dichiara una copertura che altrimenti resterebbe
--    INCIDENTALE: `chk_fondi_source_motivo_obbligatorio` fa gia' fallire il
--    reset se il motivo manca, quindi il verde del test precedente e' gia' una
--    prova — ma e' una prova che nessuno ha scritto, e un verde per sottrazione
--    non si distingue da un verde per merito quando il vincolo cambia.
SELECT ok(
    (
      SELECT count(*) = 1
      FROM vendite.fatture_fondi_fattura_source s
      WHERE s.fattura_sorgente_id = (
          SELECT id
          FROM tmp_fattura_src
        )
        AND s.stato = 'ANNULLATO'
        AND s.motivo IS NOT NULL
        AND btrim(s.motivo) <> ''
    ),
    'Annullamento automatico: la ragione e'' sul dato (motivo), non solo in fatture_log'
  );
SELECT ok(
    (
      SELECT count(*) >= 1
      FROM vendite.fatture_log l
      WHERE l.fattura_id = (
          SELECT id
          FROM tmp_fattura_dst
        )
        AND l.status = 'W'
        AND l.messaggio ILIKE 'Minimo non ripristinabile:%'
    ),
    'Warning log inserito su reset bloccato'
  );
-- ============================================================
-- Cleanup
-- ============================================================
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

UPDATE vendite.fatture
SET storicizza = false
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
DELETE FROM vendite.fatture_log
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_dst
  );
DELETE FROM pagamenti.vendite_movimenti
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  )
  AND COALESCE(meta->>'origine', '') = 'FONDO_FATTURA';
-- ⚠️ Dal 2026-09-14 (D17) il DELETE di una riga contabile passa dal guard del
--    contenuto della distinta: sotto una CHIUSA o una GENERATA e' rifiutato.
--    Questo cleanup e' un passaggio tecnico e lo dichiara con la stessa GUC
--    che usa la madre del giro dei fondi (fn_cancella_fondo_fattura); il
--    ROLLBACK farebbe comunque il lavoro.
SELECT set_config('zeroerp.allow_contabile_riga_delete_override', 'on', true);
DELETE FROM pagamenti.vendite_contabili_righe
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  )
  AND COALESCE(meta->>'origine', '') = 'FONDO_FATTURA';
DELETE FROM vendite.fatture_fondi_fattura
WHERE fattura_id IN (
    SELECT id
    FROM tmp_fattura_dst
  )
  OR riferimento_fattura_id IN (
    SELECT id
    FROM tmp_fattura_src
  );
DELETE FROM vendite.fatture_fondi_fattura_source
WHERE fattura_sorgente_id IN (
    SELECT id
    FROM tmp_fattura_src
  );
DELETE FROM vendite.fatture
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
DELETE FROM vendite.tipi_fondi_fattura
WHERE meta->>'test_scope' = (
    SELECT test_scope
    FROM tmp_costanti_ff
  );
/*  
 DELETE FROM pagamenti.centri_riscossione
 WHERE meta->>'test_scope' = (
 SELECT test_scope
 FROM tmp_costanti_ff
 );  */
SELECT ok(true, 'Cleanup completato');
SELECT *
FROM finish();
ROLLBACK;
