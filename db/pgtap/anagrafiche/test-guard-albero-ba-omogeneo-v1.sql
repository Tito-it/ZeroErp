-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 4 (P-1) del cantiere «perimetro emittente»: un singolo albero di
-- billing account non puo' attraversare due emittenti fiscali.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §3.5, §11.2, §11.3
--
-- Elenco test (plan 8):
--   0) PRECONDIZIONI: due emittenti distinti + fixture creata
--   1) albero omogeneo                                  -> PASSA
--   2) * MOVIMENTO 1: padre di un altro emittente       -> E_ALBERO_EMITTENTE_MISTO
--   3) * MOVIMENTO 2: si cambia l'emittente del FIGLIO  -> E_ALBERO_EMITTENTE_MISTO
--   4) * MOVIMENTO 2: si cambia l'emittente del PADRE   -> E_ALBERO_EMITTENTE_MISTO
--        (il verso «verso i figli», quello che si dimentica)
--   5) * MOVIMENTO 3: si CANCELLA il mapping del figlio -> E_ALBERO_EMITTENTE_MISTO
--        (ricade sul gestore globale, che e' un altro emittente)
--   6) due alberi SEPARATI dello stesso soggetto        -> PASSA (§3.1, legittimo)
--   7) il guard non e' cieco: vede un figlio FUORI dal perimetro di chi scrive
--
-- ⚠️ COSA QUESTO FILE NON COPRE, dichiarato:
--   il MOVIMENTO 4 (spostamento del gestore globale, raggio N). Spostarlo
--   richiede DELETE+INSERT della riga default nella stessa transazione, perche'
--   il constraint trigger differito trgfn_emittenti_fiscali_default_guard
--   pretende esattamente un default al COMMIT — e in un file che chiude in
--   ROLLBACK quel COMMIT non arriva mai. Il ramo e' verificato indirettamente
--   dal test 5 (stessa funzione fn_guard_albero_ba_emittente, stessa
--   condizione), non direttamente. Non e' coperto: e' dichiarato.
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

SELECT plan(8);

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
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
