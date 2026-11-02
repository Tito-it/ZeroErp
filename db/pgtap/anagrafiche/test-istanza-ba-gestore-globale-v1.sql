-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: spostare l'azienda predefinita (il gestore globale) non mette
--       un'istanza o un albero di billing account su due aziende emittenti,
--       CHIUNQUE la sposti.
-- Oggetti: anagrafiche.fn_guard_istanza_ba_gestore_globale,
--   anagrafiche.fn_guard_albero_ba_gestore_globale (movimento 4 dei trigger
--   su emittenti_fiscali_billing_account), script.fn_get_ba_emittente_sr_id_installazione.
-- Riferimento: brief-db-istanza-nasce-col-ba-residui (D-4, D-5); la regola e'
--   la D-4 di Tid del 2026-10-08 in brief-db-istanza-nasce-col-ba («un'istanza,
--   un emittente») e la P-1 di brief-db-perimetro-emittente (l'albero).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un billing account senza collegamento proprio appartiene, per
--     l'installazione, all'azienda predefinita; spostarla sposta lui;
--   - se un'istanza (o un albero padre/figlio) ha un BA collegato e uno no —
--     la coppia MISTA — la predefinita non si sposta su un'azienda diversa da
--     quella del collegato: E_ISTANZA_EMITTENTI_DIVERSI (E_ALBERO_EMITTENTE_MISTO);
--   - ⭐ il rifiuto non dipende da chi sposta: un utente con la sua azienda
--     e un super admin senza azienda ricevono lo stesso (D-5);
--   - verso l'azienda del collegato invece si sposta: la coppia torna omogenea.
--
-- Elenco test (plan 8):
--   0) PRECONDIZIONI: tre aziende distinte, un'istanza con due BA e un albero
--      padre/figlio sull'azienda del mondo, la predefinita sulla terza, un
--      super admin senza azienda
--   1) togliere il collegamento del secondo BA dell'istanza, da operatore -> vive
--   2) l'azienda per l'installazione: collegato -> il suo collegamento;
--      scollegato -> la predefinita, anche con l'operatore in sessione; NULL -> NULL
--   3) * DA OPERATORE (con la sua azienda), predefinita su un'altra azienda,
--      istanza mista -> E_ISTANZA_EMITTENTI_DIVERSI                      [D-5]
--   4) * da super admin, lo stesso -> rifiutato, e la frase nomina l'istanza
--      costruita qui (non un BA misto gia' nei dati)
--   5) ricollegato il secondo BA, togliere il collegamento del FIGLIO
--      dell'albero, da operatore -> vive
--   6) * DA OPERATORE, predefinita su un'altra azienda, albero misto
--      -> E_ALBERO_EMITTENTE_MISTO                                       [D-5]
--   7) predefinita sull'azienda del collegato -> vive
--
-- ⭐ PERCHE' L'OPERATORE E IL SUPER ADMIN. Il risolutore di sessione
--   (script.fn_get_ba_emittente_sr_id) risponde a tre livelli: collegamento,
--   l'azienda di CHI AGISCE, la predefinita. Fino al 2026-10-10 i guard del
--   movimento 4 lo usavano: con l'operatore in sessione il BA scollegato
--   «restava» alla sua azienda, e lo spostamento passava (i test 3 e 6 erano
--   la prova del difetto). Dal 20261010-58/-59 i guard chiedono l'azienda per
--   l'installazione (script.fn_get_ba_emittente_sr_id_installazione). Il
--   super admin, che non ha un'azienda, era l'unico contesto in cui il caso si
--   vedeva: resta come secondo verso (test 4).
-- ⭐ PERCHE' GLI SCOLLEGAMENTI DA OPERATORE (test 1 e 5). Da operatore il BA
--   scollegato si risolve ancora all'azienda del mondo, e il passo e' lecito
--   (i guard dei movimenti 1-3 guardano la sessione, ed e' giusto: e' chi sta
--   collegando). emittenti_fiscali_billing_account non ha RLS.
-- ⚠️ Il caso si COSTRUISCE, predefinita compresa. Tre aziende nuove: quella
--   del mondo (ef_mio), un'altra (ef_altro) e una terza (ef_terzo), su cui la
--   fixture porta la predefinita. ⛔ Fino al 2026-10-10 il file la lasciava
--   dov'era e pretendeva (test 0) che non fosse ne' ef_mio ne' ef_altro: vero
--   su dbdev per i DATI, falso su un database ricostruito, dove non c'e'
--   nessuna azienda e il bootstrap (trgfn_emittenti_fiscali_default_bootstrap)
--   fa predefinita la PRIMA creata, cioe' ef_mio. Rosso solo in CI, e il test
--   7 li' spostava la predefinita su se stessa, passando a vuoto. Con la
--   terza azienda la scena e' la stessa su ogni macchina.
-- ⚠️ I guard guardano TUTTI i BA scollegati, non solo quelli di questo file:
--   un BA misto gia' presente nei dati darebbe lo stesso codice. Per questo il
--   test 4 pretende nella frase il codice dell'istanza costruita qui. Lo
--   spostamento passa anche dal cancello della storia
--   (fn_guard_ba_gestore_globale_storia): un BA scollegato con fatture o
--   commesse lo fermerebbe prima, con un altro codice.
-- ⚠️ Ordine dei trigger sul movimento 4: z95_guard_albero_emittente prima di
--   z95_guard_istanza_ef. Per questo l'istanza si prova con l'albero ancora
--   omogeneo (test 3-4) e l'albero con l'istanza riportata omogenea (test 6).
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
--   (azienda e operatore propri); il test 4 passa al super admin e torna.

SELECT plan(8);

-- Il codice di dominio di un errore, letto dal canale CONSTRAINT (contratto
-- P0001 + CONSTRAINT = codice); per gli altri errori, SQLSTATE e vincolo.
-- NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- ============================================================
-- Fixture
-- ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('gestore globale istanza');

-- L'azienda del mondo (su cui i BA nascono) e una seconda, costruita.
CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_soggetto_ruolo_id AS ef_mio,
       (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e) AS ef_altro,
       NULL::bigint AS ef_terzo
  FROM _t_mondo m;

-- La terza azienda, che diventa la predefinita (vedi l'intestazione). In
-- un'istruzione separata dalla precedente: due chiamate al builder nella
-- stessa SELECT non sono ordinate.
UPDATE _t_ef SET ef_terzo = (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e);

-- Il super admin, SENZA azienda (vedi l'intestazione).
CREATE TEMP TABLE _t_sa AS
SELECT ou.auth_user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('gestore globale istanza', p_super_admin := true) ou;

CREATE TEMP TABLE _t_ref AS
SELECT m.cliente_soggetto_id       AS soggetto_id,
       m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       m.utility_id                AS utility_1,
       (SELECT u.id FROM config.utilities u
         WHERE u.id <> m.utility_id ORDER BY u.id LIMIT 1) AS utility_2,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = m.billing_account_id) AS categoria_cliente_id,
       m.auth_user_id              AS operatore_id
  FROM _t_mondo m;

-- Un'istanza con due BA (uno per utility) e due istanze di un BA ciascuna,
-- che diventano padre e figlio. Una saga (ogni istanza pretende il suo BA al
-- COMMIT): la finestra differita si riapre dichiarandola. Tutti i BA nascono
-- collegati all'azienda dell'operatore (trigger z90).
CREATE TEMP TABLE _t_ba (etichetta text, ba_id bigint, istanza_id bigint);

SET CONSTRAINTS ALL DEFERRED;

DO $fx$
DECLARE
    r    record;
    v_iu bigint;
    v_ba bigint;
    e    text;
BEGIN
    SELECT * INTO r FROM _t_ref;
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    VALUES (r.soggetto_id, true, 'TST-GG-IU') RETURNING id INTO v_iu;

    INSERT INTO anagrafiche.billing_account
           (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.soggetto_ruolo_id, r.utility_1, r.categoria_cliente_id, script.fn_data_operativa())
    RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('collegato', v_ba, v_iu);

    INSERT INTO anagrafiche.billing_account
           (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
    VALUES (v_iu, r.soggetto_ruolo_id, r.utility_2, r.categoria_cliente_id, script.fn_data_operativa())
    RETURNING id INTO v_ba;
    INSERT INTO _t_ba VALUES ('scollegato', v_ba, v_iu);

    FOREACH e IN ARRAY ARRAY['padre', 'figlio'] LOOP
        INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
        VALUES (r.soggetto_id, true, 'TST-GG-IU-' || upper(e)) RETURNING id INTO v_iu;
        INSERT INTO anagrafiche.billing_account
               (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
        VALUES (v_iu, r.soggetto_ruolo_id, r.utility_1, r.categoria_cliente_id, script.fn_data_operativa())
        RETURNING id INTO v_ba;
        INSERT INTO _t_ba VALUES (e, v_ba, v_iu);
    END LOOP;
END
$fx$;

SET CONSTRAINTS ALL IMMEDIATE;

-- L'albero: entrambi sull'azienda dell'operatore, quindi omogeneo.
UPDATE anagrafiche.billing_account
   SET parent_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
 WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio');

-- La predefinita sulla terza azienda. Qui tutti i BA della fixture sono
-- collegati: lo spostamento non apre nessuna coppia mista.
UPDATE anagrafiche.emittenti_fiscali_billing_account
   SET emittente_soggetto_ruolo_id = (SELECT ef_terzo FROM _t_ef)
 WHERE is_default;

-- ============================================================
-- 0) Precondizioni
-- ============================================================
SELECT ok(
    (SELECT ef_mio IS NOT NULL AND ef_altro IS NOT NULL AND ef_terzo IS NOT NULL
            AND ef_mio <> ef_altro AND ef_terzo NOT IN (ef_mio, ef_altro) FROM _t_ef)
    AND (SELECT count(*) = 4 FROM anagrafiche.emittenti_fiscali_billing_account e
          WHERE e.billing_account_id IN (SELECT ba_id FROM _t_ba)
            AND e.emittente_soggetto_ruolo_id = (SELECT ef_mio FROM _t_ef))
    AND (SELECT parent_account_id FROM anagrafiche.billing_account
          WHERE id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio'))
        = (SELECT ba_id FROM _t_ba WHERE etichetta = 'padre')
    AND (SELECT d.emittente_soggetto_ruolo_id
           FROM anagrafiche.emittenti_fiscali_billing_account d WHERE d.is_default)
        = (SELECT ef_terzo FROM _t_ef)
    AND script.fn_is_super_admin((SELECT auth_user_id FROM _t_sa))
    AND NOT EXISTS (SELECT 1 FROM config.user_emittenti_fiscali uef
                     WHERE uef.auth_user_id = (SELECT auth_user_id FROM _t_sa)),
    '0. PRECONDIZIONI: tre aziende distinte, istanza e albero sull''azienda del mondo, la predefinita sulla terza, un super admin senza azienda'
);

-- ============================================================
-- 1) Da operatore, il secondo BA dell'istanza perde il collegamento: lecito
-- ============================================================
SELECT lives_ok($$
    DELETE FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'scollegato')
$$, '1. Da operatore, togliere il collegamento del secondo BA dell''istanza: vive');

-- ============================================================
-- 2) L'azienda per l'installazione (il BB), anche in sessione
-- ============================================================
SELECT is(
    (SELECT (script.fn_get_ba_emittente_sr_id_installazione(
                 (SELECT ba_id FROM _t_ba WHERE etichetta = 'collegato')) = t.ef_mio)::text
            || '/' ||
            (script.fn_get_ba_emittente_sr_id_installazione(
                 (SELECT ba_id FROM _t_ba WHERE etichetta = 'scollegato'))
             = (SELECT d.emittente_soggetto_ruolo_id
                  FROM anagrafiche.emittenti_fiscali_billing_account d WHERE d.is_default))::text
            || '/' ||
            (script.fn_get_ba_emittente_sr_id_installazione(NULL) IS NULL)::text
       FROM _t_ef t),
    'true/true/true',
    '2. fn_get_ba_emittente_sr_id_installazione: collegato -> il suo collegamento; scollegato -> la predefinita, anche con l''operatore in sessione; NULL -> NULL'
);

-- ============================================================
-- 3) * DA OPERATORE: la predefinita su un'altra azienda, istanza mista
--    Fino al 20261010-58 passava: il guard vedeva il BA scollegato restare
--    all'azienda dell'operatore. Per l'installazione segue la predefinita.
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        UPDATE anagrafiche.emittenti_fiscali_billing_account
           SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
         WHERE is_default $sql$),
    'E_ISTANZA_EMITTENTI_DIVERSI',
    '3. * Da operatore con la sua azienda, spostare la predefinita con un''istanza mista: E_ISTANZA_EMITTENTI_DIVERSI'
);

-- ============================================================
-- 4) * Da super admin: lo stesso rifiuto, e la frase nomina l'istanza di qui
-- ============================================================
SELECT set_config('app.current_user_id', (SELECT auth_user_id FROM _t_sa)::text, true) IS NOT NULL AS contesto_super_admin;

SELECT throws_like($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
     WHERE is_default
$$, '%istanza TST-GG-IU %',
    '4. * Da super admin, lo stesso rifiuto; la frase nomina l''istanza costruita qui');

SELECT set_config('app.current_user_id', (SELECT operatore_id FROM _t_ref)::text, true) IS NOT NULL AS contesto_operatore;

-- ============================================================
-- 5) Istanza riportata omogenea; da operatore il FIGLIO dell'albero perde il
--    collegamento: lecito
-- ============================================================
INSERT INTO anagrafiche.emittenti_fiscali_billing_account
       (emittente_soggetto_ruolo_id, billing_account_id, is_default)
SELECT ef_mio, (SELECT ba_id FROM _t_ba WHERE etichetta = 'scollegato'), false FROM _t_ef;

SELECT lives_ok($$
    DELETE FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE billing_account_id = (SELECT ba_id FROM _t_ba WHERE etichetta = 'figlio')
$$, '5. Da operatore, togliere il collegamento del figlio dell''albero: vive');

-- ============================================================
-- 6) * DA OPERATORE: la predefinita su un'altra azienda, albero misto
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        UPDATE anagrafiche.emittenti_fiscali_billing_account
           SET emittente_soggetto_ruolo_id = (SELECT ef_altro FROM _t_ef)
         WHERE is_default $sql$),
    'E_ALBERO_EMITTENTE_MISTO',
    '6. * Da operatore con la sua azienda, spostare la predefinita con un albero misto: E_ALBERO_EMITTENTE_MISTO'
);

-- ============================================================
-- 7) La predefinita sull'azienda del collegato: il figlio scollegato la
--    segue e l'albero resta omogeneo. E' il verso che dimostra che la
--    condizione e' la coppia MISTA, non la sola presenza di uno scollegato.
-- ============================================================
SELECT lives_ok($$
    UPDATE anagrafiche.emittenti_fiscali_billing_account
       SET emittente_soggetto_ruolo_id = (SELECT ef_mio FROM _t_ef)
     WHERE is_default
$$, '7. Spostare la predefinita sull''azienda del collegato: vive');

SELECT * FROM finish();
ROLLBACK;
