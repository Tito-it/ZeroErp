-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 4 (P-1) del cantiere «perimetro emittente»: un singolo albero di
-- billing account non puo' attraversare due emittenti fiscali.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §3.5, §11.2, §11.3
--
-- Elenco test (plan 8):
--   0) PRECONDIZIONI: due emittenti distinti + fixture creata
--   1) albero omogeneo                                  -> PASSA
--   2) * MOVIMENTO 1: padre di un altro emittente       -> E_ALBERO_EMITTENTE_MISTO
--   3) * MOVIMENTO 2: si cambia l'emittente del FIGLIO  -> E_ALBERO_EMITTENTE_MISTO
--   4) * MOVIMENTO 2: si cambia l'emittente del PADRE   -> E_ALBERO_EMITTENTE_MISTO
--        (il verso «verso i figli», quello che si dimentica)
--   5) * MOVIMENTO 3: si CANCELLA il mapping del figlio -> E_ALBERO_EMITTENTE_MISTO
--   8-9) * i DUE CANALI strutturati: CONSTRAINT = codice, COLUMN = campo (R-2)
--        (ricade sul gestore globale, che e' un altro emittente)
--   6) due alberi SEPARATI dello stesso soggetto        -> PASSA (§3.1, legittimo)
--   7) il guard non e' cieco: vede un figlio FUORI dal perimetro di chi scrive
--  10) * MOVIMENTO 4: si sposta il GESTORE GLOBALE, coppia MISTA -> rifiutato
--  11)   MOVIMENTO 4: si sposta il GESTORE GLOBALE, coppia OMOGENEA -> PASSA
--
-- ⭐ IL MOVIMENTO 4 NON RICHIEDE UN TEST NON TRANSAZIONALE — 2026-08-18.
--   L'intestazione diceva il contrario: «spostarlo richiede DELETE+INSERT della
--   riga default, e il constraint differito pretende il COMMIT che un file
--   pgTAP non fa mai». La premessa era sbagliata, e per due ragioni misurate:
--     a) «spostare il gestore globale» non obbliga a cambiare QUALE riga e'
--        default. Basta cambiare l'EMITTENTE della riga default — un solo
--        UPDATE, il default resta esattamente uno, il constraint differito non
--        ha mai niente da ridire. E' anche il modo naturale di dirlo: «da oggi
--        il gestore globale e' l'altro»;
--     b) anche volendo la coppia DELETE+INSERT, non servirebbe un COMMIT:
--        trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt e' un CONSTRAINT
--        TRIGGER deferrable, quindi si differisce per la coppia e si forza con
--        `SET CONSTRAINTS ... IMMEDIATE` dentro la transazione.
--   ⚠️ E il prezzo evitato non e' teorico: in tutta la suite non esiste un solo
--     file non transazionale, e la memoria del progetto dice perche' — un test
--     che non chiude in ROLLBACK contamina le corse successive.
--
-- ⚠️ NOTE DI FIXTURE (ereditate da test-billing-account-guard-cf-confrontabile-v1):
--   a) i test agiscono via UPDATE, non via INSERT del figlio: ogni istanza deve
--      nascere con il suo satellite, o scatta il constraint differito
--      trg_istanze_utilities_z90_require_utility_dichiarata_ins;
--   b) per questo `SET CONSTRAINTS ALL IMMEDIATE` sta DOPO la fixture;
--   c) i BA nascono mappati sull'emittente dell'operatore di contesto (lo fa
--      trg_billing_account_z90_link_ef_ins): per spostarli sull'altro emittente
--      si aggiorna la riga di emittenti_fiscali_billing_account MENTRE non sono
--      ancora legati fra loro — altrimenti sarebbe il guard stesso a fermarci.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
-- L'emittente dell'operatore di contesto (quello su cui i BA nascono) e un
-- SECONDO emittente attivo, diverso: senza il secondo non c'e' albero misto da
-- costruire, e il file lo dichiara nella precondizione invece di fingere.
CREATE TEMP TABLE _t_ef ON COMMIT DROP AS
SELECT (script.fn_get_emittenti_scope_sr_ids(
          NULLIF(current_setting('app.current_user_id', true), '')::integer))[1] AS ef_mio,
       (SELECT ef.soggetto_ruolo_id
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.attivo
           AND ef.soggetto_ruolo_id <> (script.fn_get_emittenti_scope_sr_ids(
                 NULLIF(current_setting('app.current_user_id', true), '')::integer))[1]
         ORDER BY ef.soggetto_ruolo_id
         LIMIT 1) AS ef_altro;

-- ⭐ Il SUPER ADMIN. Le asserzioni 2-7 girano nel SUO contesto, e non e' una
--   comodita': dopo aver spostato un BA sull'altro emittente, l'operatore non
--   lo VEDE piu' (RLS su billing_account), quindi
--   - il tentativo di agganciarlo cade prima su E_PARENT_NON_RAGGIUNGIBILE
--     (il guard di coerenza, che e' BEFORE e arriva per primo), e
--   - ogni UPDATE successivo su quel BA tocca ZERO righe, in silenzio.
--   E' esattamente §11.1: l'albero misto e' costruibile SOLO da chi vede
--   entrambi i rami. Provarlo da operatore misura un'altra cosa.
CREATE TEMP TABLE _t_sa ON COMMIT DROP AS
SELECT (SELECT idg.auth_user_id
          FROM anagrafiche.identita_digitali idg
         WHERE idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
           AND idg.attivo
           AND script.fn_is_super_admin(idg.auth_user_id)
         ORDER BY idg.auth_user_id
         LIMIT 1) AS auth_user_id;

-- Un soggetto raggiungibile, con i riferimenti per creare BA.
CREATE TEMP TABLE _t_ref ON COMMIT DROP AS
SELECT s.id                    AS soggetto_id,
       ba.soggetto_ruolo_id    AS soggetto_ruolo_id,
       ba.utility_id           AS utility_id,
       ba.categoria_cliente_id AS categoria_cliente_id
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
  JOIN anagrafiche.soggetti s          ON s.id  = iu.soggetto_id
 WHERE ba.utility_id IS NOT NULL
 ORDER BY ba.id
 LIMIT 1;

-- Quattro coppie istanza+BA sullo stesso soggetto, tutte senza parent.
CREATE TEMP TABLE _t_ba (etichetta text, ba_id bigint) ON COMMIT DROP;

DO $fx$
DECLARE
    r    record;
    v_iu bigint;
    v_ba bigint;
    e    text;
BEGIN
    SELECT * INTO r FROM _t_ref;
    FOREACH e IN ARRAY ARRAY['padre','figlio','padre2','figlio2'] LOOP
        INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
        VALUES (r.soggetto_id, true, 'TST-P1-IU-' || upper(e)) RETURNING id INTO v_iu;
        INSERT INTO anagrafiche.billing_account
               (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
        VALUES (v_iu, r.soggetto_ruolo_id, r.utility_id, r.categoria_cliente_id, CURRENT_DATE)
        RETURNING id INTO v_ba;
        INSERT INTO _t_ba VALUES (e, v_ba);
    END LOOP;
END
$fx$;

-- ⚠️ Qui, non in testa: vedi nota (b) nell'intestazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT ok(
    (SELECT ef_mio IS NOT NULL AND ef_altro IS NOT NULL AND ef_mio <> ef_altro FROM _t_ef)
    AND (SELECT count(*) FROM _t_ba) = 4
    AND (SELECT auth_user_id FROM _t_sa) IS NOT NULL,
    '0. PRECONDIZIONI: due emittenti distinti + quattro BA + un super admin'
);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) Albero omogeneo: entrambi sull'emittente dell'operatore.
SELECT lives_ok($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio')
$$, '1. albero omogeneo: si aggancia');

UPDATE anagrafiche.billing_account SET parent_account_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');

-- ⭐ Da qui in poi si lavora come SUPER ADMIN: vedi la nota sulla fixture.
--   La veste resta OPERATORE (le policy la pretendono); cambia solo l'utente,
--   e con lui lo scope, che per il super admin e' l'universo.
SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id FROM _t_sa)::text, false);

-- 2) * MOVIMENTO 1: il padre e' di un altro emittente.
--    Si sposta il PADRE (ancora slegato: nessun albero da spaccare), poi si
--    tenta l'aggancio.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre');

SELECT throws_like($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio')
$$, '%emittenti fiscali diversi%',
    '2. * MOVIMENTO 1: agganciarsi a un padre di un altro emittente -> rifiutato');

-- Riporta il padre sul proprio emittente e costruisci l'albero omogeneo.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_mio FROM _t_ef)
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre');

UPDATE anagrafiche.billing_account
   SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');

-- 3) * MOVIMENTO 2: si cambia l'emittente del FIGLIO di un albero esistente.
SELECT throws_like($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
     WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio')
$$, '%emittenti fiscali diversi%',
    '3. * MOVIMENTO 2: spostare il FIGLIO su un altro emittente -> rifiutato');

-- 4) * MOVIMENTO 2, verso i FIGLI: si cambia l'emittente del PADRE.
--    E' il verso che si dimentica: il guard deve guardare anche in basso.
SELECT throws_like($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
     WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
$$, '%emittenti fiscali diversi%',
    '4. * MOVIMENTO 2 verso i FIGLI: spostare il PADRE -> rifiutato');

-- 5) * MOVIMENTO 3: si CANCELLA il mapping del figlio.
--    Il BA ricade sul gestore globale. Perche' il caso sia significativo
--    l'albero deve stare su un emittente DIVERSO dal gestore globale: si
--    spostano entrambi insieme (slegati) e poi si rilega.
UPDATE anagrafiche.billing_account SET parent_account_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');

UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
 WHERE billing_account_id IN (
       (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre'),
       (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio'));

UPDATE anagrafiche.billing_account
   SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');

SELECT CASE WHEN (SELECT ef_altro FROM _t_ef) IS DISTINCT FROM
                 (SELECT emittente_soggetto_ruolo_id
                    FROM anagrafiche.emittenti_fiscali_billing_account
                   WHERE is_default)
  THEN throws_like($$
        DELETE FROM anagrafiche.emittenti_fiscali_billing_account
         WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio')
    $$, '%emittenti fiscali diversi%',
        '5. * MOVIMENTO 3: cancellare il mapping fa ricadere sul gestore globale -> rifiutato')
  ELSE skip('5. il gestore globale coincide con l''emittente dell''albero: il ripiego non cambia nulla', 1)
END;

-- 6) Due alberi SEPARATI, stesso soggetto, emittenti diversi: LEGITTIMO (§3.1).
--    E' la regola sbagliata che assomiglia a quella giusta: cio' che si vieta
--    e' UN albero con un piede di qua e uno di la', non due alberi.
SELECT lives_ok($$
    UPDATE anagrafiche.billing_account
       SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2')
     WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio2')
$$, '6. due alberi separati dello stesso soggetto su emittenti diversi: legittimo');

-- 7) Il guard non e' cieco: il figlio sta su un emittente che l'operatore NON
--    vede, eppure il guard lo trova. Da SECURITY INVOKER questo test fallirebbe
--    passando — cioe' il difetto di §11.1.
SELECT ok(
    NOT anagrafiche.fn_check_ba_coppia_emittente_omogenea(
        (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio'),
        (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2')),
    '7. il check vede l''emittente anche di un BA fuori perimetro (SECURITY DEFINER, §11.1)'
);

-- ============================================================
-- 8-9) ⭐ I DUE CANALI STRUTTURATI — richiesta R-2 del perimetro BE
--
--   `script.fn_log_and_raise_error` manda al client due cose in canali
--   separati: il CODICE di dominio in CONSTRAINT e il NOME DEL CAMPO da
--   correggere in COLUMN. Il secondo lo legge da `p_context ->> 'campo'`.
--
--   ⚠️ I `throws_like` qui sopra NON coprono questa parte: verificano la
--   FRASE. Sono rimasti verdi per tutto il tempo in cui il guard scriveva
--   `'column'` invece di `'campo'` e il canale del campo usciva VUOTO —
--   verde per sottrazione, sul difetto stesso.
--
--   L'unico modo di leggere i due canali e' catturare l'eccezione:
--   `throws_ok` non espone COLUMN_NAME.
-- ============================================================
CREATE TEMP TABLE _t_diag AS
SELECT * FROM (
  SELECT NULL::text AS vincolo, NULL::text AS campo WHERE false
) z;

DO $diag$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        UPDATE anagrafiche.billing_account
           SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2')
         WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');
        -- Se arriva qui il guard non ha sollevato: si registra il vuoto, e le
        -- due asserzioni sotto falliscono dicendo cosa manca.
        INSERT INTO _t_diag VALUES (NULL, NULL);
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        INSERT INTO _t_diag VALUES (nullif(v_cst, ''), nullif(v_col, ''));
    END;
END $diag$;

SELECT is(
    (SELECT vincolo FROM _t_diag),
    'E_ALBERO_EMITTENTE_MISTO',
    '8. canale CONSTRAINT: il codice di dominio arriva strutturato, non solo nella frase'
);

SELECT is(
    (SELECT campo FROM _t_diag),
    'parent_account_id',
    '9. * canale COLUMN: il CAMPO da correggere arriva al client (context ''campo'', non ''column'')'
);

-- ============================================================
-- 10-11) ⭐ MOVIMENTO 4 — lo spostamento del GESTORE GLOBALE (raggio N)
--
--   E' l'unica operazione del cantiere che, con UNA riga, cambia l'emittente
--   di un numero arbitrario di BA: tutti quelli senza mapping specifico.
--
--   ⚠️ La condizione che conta e' la COPPIA MISTA, non «esiste un albero»
--   (decisione Q3). Se entrambi i lati sono non mappati si spostano INSIEME e
--   l'albero resta omogeneo: per questo servono DUE asserzioni, una per verso.
--   Con la sola 10 il guard potrebbe essere scritto su «esiste un albero senza
--   mapping» e restare verde bloccando anche cio' che e' lecito.
--
--   La scena si costruisce sul secondo albero (padre2/figlio2), che il test 6
--   ha lasciato agganciato e mappato:
--     - si portano entrambi sull'emittente del gestore globale ATTUALE
--       (qualunque sia: il file non presume che coincida con quello
--       dell'operatore, e senza questo passo il DELETE sotto sarebbe gia' lui
--       a sollevare, per il movimento 3 invece che per il 4);
--     - si toglie il mapping del solo FIGLIO -> resta appeso al gestore
--       globale, e la coppia diventa MISTA: padre mappato, figlio no.
--   Da li' spostare il gestore globale spacca l'albero.
--
--   ⚠️ Lo scollegamento prima di spostare i mapping non e' pignoleria: il
--   trigger e' AFTER ROW e scatta a ogni riga, quindi muovere padre e figlio
--   con un solo UPDATE li vedrebbe comunque disallineati a meta' strada.
-- ============================================================
CREATE TEMP TABLE _t_gg ON COMMIT DROP AS
SELECT d.emittente_soggetto_ruolo_id AS gg_attuale,
       CASE WHEN d.emittente_soggetto_ruolo_id = t.ef_altro
            THEN t.ef_mio ELSE t.ef_altro END AS gg_nuovo
  FROM anagrafiche.emittenti_fiscali_billing_account d
  CROSS JOIN _t_ef t
 WHERE d.is_default;

UPDATE anagrafiche.billing_account SET parent_account_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio2');

UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT gg_attuale FROM _t_gg)
 WHERE billing_account_id IN (
       (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2'),
       (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio2'));

UPDATE anagrafiche.billing_account
   SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2')
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio2');

-- Il figlio perde il mapping: ricade sul gestore globale, che in questo istante
-- e' lo STESSO emittente del padre. Lecito, e infatti non solleva.
DELETE FROM anagrafiche.emittenti_fiscali_billing_account
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio2');

-- 10) * Coppia MISTA: il figlio segue il gestore globale, il padre no.
SELECT throws_like($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT gg_nuovo FROM _t_gg)
     WHERE is_default
$$, '%emittenti fiscali diversi%',
    '10. * MOVIMENTO 4: spostare il GESTORE GLOBALE con una coppia mista -> rifiutato');

-- 11) Coppia OMOGENEA: tolto anche il mapping del padre, i due si spostano
--     insieme. Il guard deve LASCIAR PASSARE — e' il verso che dimostra che
--     la condizione e' la coppia mista e non la semplice esistenza di un
--     albero non mappato (decisione Q3).
DELETE FROM anagrafiche.emittenti_fiscali_billing_account
 WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre2');

SELECT lives_ok($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT gg_nuovo FROM _t_gg)
     WHERE is_default
$$, '11. MOVIMENTO 4: coppia non mista (entrambi non mappati) -> si sposta, lecito');

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
