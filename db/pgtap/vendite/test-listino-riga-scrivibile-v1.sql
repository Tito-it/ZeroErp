-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le scritture di una versione di listino (righe, prezzi dei componenti,
--   periodicita' dei kit) si fanno solo in bozza, con una regola sola, e le
--   superfici la dicono.
--   ChangeSet: 20261115-53 e -65 (script.fn_check_listino_riga_scrivibile), -54
--   e -68 (vendite.trgfn_listini_righe_guard_stato), -55 (il montaggio anche su
--   INSERT), -69 (vendite.trgfn_listini_righe_comp_guard_immutabilita_v5), -70
--   (vendite.trgfn_listini_kit_guard), -56 e -72 (vendite.vw_listini_versioni_azioni),
--   -57 (vendite.vw_listini_righe_azioni), -78 (la reason_key della check).
--   Brief: brief-db-stati-documento-dal-vocabolario, giri 6f-bis (D-LIST (a)),
--   6f-ter (§6.28) e 6f-quater (§6.29).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - in bozza si scrive tutto; in una versione CHIUSA niente
--     (E_RIGA_LISTINO_VERSIONE_CHIUSA); in una versione non in bozza e non
--     chiusa (l'ATTIVA) niente, per ogni operazione e ogni colonna
--     (E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA): ne' una riga nuova, ne' una
--     modifica, ne' un'eliminazione, ne' un prezzo di componente (attivo
--     compreso), ne' la periodicita' di un kit. Il prezzo di una riga in uso si
--     rettifica col verbo: lo prova vendite/test-listino-rettifica-riga-v1;
--   - le superfici della versione (quattro azioni) e delle righe dicono il primo
--     motivo che i guard sollevano, con una reason_key sua (righe_non_in_bozza),
--     non quella dell'eliminazione della versione (versione_non_in_bozza);
--   - i tre guard non riscrivono la regola: chiamano la check (presidio sulla
--     FORMA, dichiarato tale).
--
-- ⭐ I CASI SI COSTRUISCONO: la versione attiva dal builder (nata in bozza coi
--   suoi prezzi di kit, poi attivata dal verbo), la chiusa dal builder (dal job,
--   con la fine passata), la bozza dall'INSERT dell'applicazione; il composito K
--   con la sua distinta (F1, F2), i prezzi dei componenti e il kit sulla bozza e
--   sull'attiva. Nessuno skip.
-- ⭐ LA MARCA SPOSTATA: iniziale si sposta da BOZZA a CHIUSA: la chiusa si
--   scrive, e la bozza no.
-- ⚠️ Le righe del registro config.azioni_riga vengono dal CSV, che la prova in
--   transazione non carica: le verifica config/test-azioni-riga-registro-v1 dopo
--   l'apply.
--
-- Elenco test (plan 12):
--   1) contrasto: le quattro azioni della versione (riga nuova, variazione,
--      prezzi bundle, periodicita' del kit) accese in bozza, spente nell'attiva e
--      nella chiusa, col motivo (superficie della versione)
--   2) contrasto: la riga che c'e' si modifica in bozza, non nell'attiva ne'
--      nella chiusa (superficie delle righe)
--   3) contrasto: il guard delle righe sulla riga nuova: bozza passa, attiva e
--      chiusa no
--   4) contrasto: il guard delle righe sulla riga che c'e': la modifica
--      nell'attiva e l'eliminazione nella chiusa no, la modifica in bozza si'
--   5) contrasto: il guard dei componenti: nell'attiva ne' il prezzo ne'
--      attivo; in bozza il prezzo si'
--   6) contrasto: il guard del kit: nell'attiva la periodicita' no, in bozza si'
--   7) contrasto: la check da' il codice che il guard solleva
--   8) forma: i tre guard chiamano la check e non nominano stati
--   9) forma: la check non guarda i documenti (la propagazione e' della rettifica)
--  10) ⭐ iniziale su CHIUSA: la chiusa si scrive (superficie e guard)
--  11) ⭐ ... e la bozza, ora fuori dallo stato iniziale, non si scrive piu'
--  12) contrasto: nell'attiva la reason_key delle scritture e' righe_non_in_bozza,
--      quella dell'eliminazione versione_non_in_bozza (§6.29: erano la stessa)
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('riga di listino scrivibile');

-- L: l'attiva, nata in bozza per prendere il kit; L2: una versione nel 2020,
-- chiusa dal job.
CREATE TEMP TABLE t_l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_m), 'riga scrivibile',
                                          p_in_bozza => true);

CREATE TEMP TABLE t_l2 AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM t_m), 'riga scrivibile, chiusa',
                                          '2020-01-01'::date, '2020-12-31'::date);

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_l2), 'CHIUSA');

CREATE TEMP TABLE t_bozza AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    SELECT listino_id, 'PGTAP_6FT_BOZZA', '2021-01-01'::date, '2021-12-31'::date FROM t_l
    RETURNING id
)
SELECT id FROM ins;

-- Gli articoli: B per la bozza, C2 da aggiungere, il composito K coi
-- componenti F1 e F2. ⚠️ Il builder in un'istruzione sua.
CREATE TEMP TABLE t_art AS
SELECT s.sigla,
       dbops.fn_pgtap_crea_articolo(('PGT-6FT-' || s.sigla || '-' || substr(md5(clock_timestamp()::text || s.sigla), 1, 10))::varchar,
                                    false, p_listino_tipologia_id => (SELECT tipologia_id FROM t_l),
                                    p_is_composito => s.sigla = 'K') AS id
  FROM (VALUES ('B'), ('C2'), ('K'), ('F1'), ('F2')) s(sigla);

CREATE FUNCTION pg_temp.art(p_sigla text)   -- text: la sigla del caso
RETURNS uuid LANGUAGE sql STABLE AS $$
    SELECT id FROM t_art WHERE sigla = p_sigla
$$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('K'), pg_temp.art('F1'), 2, '2020-01-01'),
       (pg_temp.art('K'), pg_temp.art('F2'), 1, '2020-01-01');

SELECT dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM t_bozza), ARRAY[pg_temp.art('B')]);

-- I prezzi dei componenti di K e il kit, sulla bozza e su L (ancora in bozza),
-- nel periodo della versione.
INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal, valido_al)
SELECT v.id, ac.id, ac.prodotto_id, ac.componente_id, 10, lv.valido_dal, lv.valido_al
  FROM (VALUES ((SELECT listino_versione_id FROM t_l)), ((SELECT id FROM t_bozza))) v(id)
  JOIN vendite.listini_versioni lv ON lv.id = v.id
  CROSS JOIN catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('K');

INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES ((SELECT listino_versione_id FROM t_l), pg_temp.art('K'), 'MENSILE'),
       ((SELECT id FROM t_bozza), pg_temp.art('K'), 'MENSILE');

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', (SELECT listino_versione_id FROM t_l), 'ATTIVA');

CREATE FUNCTION pg_temp.v(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS vendite.listini_versioni.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT CASE p_caso WHEN 'attiva' THEN (SELECT listino_versione_id FROM t_l)
                       WHEN 'bozza'  THEN (SELECT id FROM t_bozza)
                       WHEN 'chiusa' THEN (SELECT listino_versione_id FROM t_l2) END
$$;

-- La riga del caso: la riga d'appoggio del builder per l'attiva (A) e la
-- chiusa (C), la riga di B per la bozza.
CREATE FUNCTION pg_temp.r(p_caso text)   -- text: 'A', 'B' o 'C'
RETURNS vendite.listini_righe.id%TYPE LANGUAGE sql STABLE AS $$
    SELECT min(r.id) FROM vendite.listini_righe r
     WHERE r.listino_versione_id = pg_temp.v(CASE p_caso WHEN 'A' THEN 'attiva'
                                                         WHEN 'B' THEN 'bozza'
                                                         WHEN 'C' THEN 'chiusa' END)
$$;

-- La superficie della versione: i motivi delle quattro azioni, ripetuti se
-- uguali ('-' = accesa).
CREATE FUNCTION pg_temp.azioni(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS text LANGUAGE sql STABLE AS $$        -- text: le reason, nessuna colonna
    SELECT concat_ws('/', COALESCE(a.aggiunta_riga_blocco_reason, '-'),
                          COALESCE(a.variazione_blocco_reason, '-'),
                          COALESCE(a.prezzi_bundle_blocco_reason, '-'),
                          COALESCE(a.periodicita_kit_blocco_reason, '-'))
      FROM vendite.vw_listini_versioni_azioni a WHERE a.versione_id = pg_temp.v(p_caso)
$$;

-- La superficie delle righe: il motivo per cui la riga non si modifica ('-' = si modifica).
CREATE FUNCTION pg_temp.modifica(p_caso text)   -- text: 'A', 'B' o 'C'
RETURNS text LANGUAGE sql STABLE AS $$          -- text: una reason, nessuna colonna
    SELECT COALESCE(a.modifica_blocco_reason, '-')
      FROM vendite.vw_listini_righe_azioni a WHERE a.listino_riga_id = pg_temp.r(p_caso)
$$;

-- Il codice della check per la riga (o per la riga nuova, senza): '-' se passa.
CREATE FUNCTION pg_temp.codice_check(p_versione text, p_riga text)   -- text: i casi
RETURNS text LANGUAGE sql STABLE AS $$                                -- text: un codice d'errore
    SELECT COALESCE(script.fn_check_listino_riga_scrivibile(pg_temp.v(p_versione), pg_temp.r(p_riga)) -> 0 ->> 'codice', '-')
$$;

-- Il guard: cio' che rifiuta l'istruzione, 'passa' se passa.
CREATE FUNCTION pg_temp.guard(p_sql text)   -- text: l'istruzione
RETURNS text LANGUAGE sql AS $$             -- text: un codice d'errore, nessuna colonna
    SELECT COALESCE(dbops.fn_pgtap_codice_errore(p_sql), 'passa')
$$;

CREATE FUNCTION pg_temp.nuova_riga(p_caso text)   -- text: 'attiva', 'bozza' o 'chiusa'
RETURNS text LANGUAGE sql AS $$                   -- text: l'istruzione
    SELECT format('SELECT dbops.fn_pgtap_listino_aggiungi_articoli(%s, ARRAY[%L::uuid])',
                  pg_temp.v(p_caso), pg_temp.art('C2'))
$$;

CREATE FUNCTION pg_temp.cambia_riga(p_caso text)   -- text: 'A', 'B' o 'C'
RETURNS text LANGUAGE sql AS $$                    -- text: l'istruzione
    SELECT format('UPDATE vendite.listini_righe SET prezzo = prezzo + 1 WHERE id = %s', pg_temp.r(p_caso))
$$;

CREATE FUNCTION pg_temp.cambia_componente(p_caso text, p_set text)   -- text: il caso, la SET
RETURNS text LANGUAGE sql AS $$                                     -- text: l'istruzione
    SELECT format('UPDATE vendite.listini_righe_componenti SET %s WHERE listino_versione_id = %s',
                  p_set, pg_temp.v(p_caso))
$$;

CREATE FUNCTION pg_temp.cambia_kit(p_caso text)   -- text: 'attiva' o 'bozza'
RETURNS text LANGUAGE sql AS $$                   -- text: l'istruzione
    SELECT format('UPDATE vendite.listini_kit SET periodicita = %L WHERE listino_versione_id = %s',
                  'TRIMESTRALE', pg_temp.v(p_caso))
$$;

-- ============================================================
-- 1-7) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.azioni('bozza'), pg_temp.azioni('attiva'), pg_temp.azioni('chiusa')),
    '-/-/-/- VERSIONE_NON_IN_BOZZA/VERSIONE_NON_IN_BOZZA/VERSIONE_NON_IN_BOZZA/VERSIONE_NON_IN_BOZZA '
    || 'VERSIONE_CHIUSA/VERSIONE_CHIUSA/VERSIONE_CHIUSA/VERSIONE_CHIUSA',
    '1. contrasto: le quattro azioni della versione accese in bozza, spente nell''attiva e nella chiusa'
);

SELECT is(
    concat_ws(' ', pg_temp.modifica('B'), pg_temp.modifica('A'), pg_temp.modifica('C')),
    '- VERSIONE_NON_IN_BOZZA VERSIONE_CHIUSA',
    '2. contrasto: la riga che c''e'' si modifica in bozza, non nell''attiva ne'' nella chiusa'
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.nuova_riga('bozza')), pg_temp.guard(pg_temp.nuova_riga('attiva')),
                   pg_temp.guard(pg_temp.nuova_riga('chiusa'))),
    'passa E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA',
    '3. contrasto: la riga nuova entra nella bozza, non nell''attiva ne'' nella chiusa'
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.cambia_riga('A')),
                   pg_temp.guard(format('DELETE FROM vendite.listini_righe WHERE id = %s', pg_temp.r('C'))),
                   pg_temp.guard(pg_temp.cambia_riga('B'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA passa',
    '4. contrasto: la riga dell''attiva non si modifica, quella della chiusa non si elimina, quella della bozza si'''
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.cambia_componente('attiva', 'prezzo = prezzo + 1')),
                   pg_temp.guard(pg_temp.cambia_componente('attiva', 'attivo = false')),
                   pg_temp.guard(pg_temp.cambia_componente('bozza', 'prezzo = prezzo + 1'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA passa',
    '5. contrasto: i prezzi dei componenti dell''attiva non cambiano, nemmeno attivo; quelli della bozza si'''
);

SELECT is(
    concat_ws(' ', pg_temp.guard(pg_temp.cambia_kit('attiva')), pg_temp.guard(pg_temp.cambia_kit('bozza'))),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA passa',
    '6. contrasto: la periodicita'' del kit dell''attiva non cambia, quella della bozza si'''
);

SELECT is(
    concat_ws(' ', pg_temp.codice_check('attiva', 'A'), pg_temp.codice_check('chiusa', 'C'),
                   pg_temp.codice_check('attiva', NULL), pg_temp.codice_check('bozza', 'B')),
    'E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_CHIUSA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA -',
    '7. contrasto: la check da'' il codice che il guard solleva'
);

-- ============================================================
-- 8-9) La forma — presidio sulla FORMA, dichiarato tale
-- ============================================================
-- ⚠️ Prova che la regola non e' ricopiata nei guard, non che sia giusta. Il
--   conteggio in testa lo fa fallire se un guard cambia nome.
SELECT is(
    (SELECT count(*)::int
       FROM unnest(ARRAY['vendite.trgfn_listini_righe_guard_stato()',
                         'vendite.trgfn_listini_righe_comp_guard_immutabilita_v5()',
                         'vendite.trgfn_listini_kit_guard()']) g(f)
      CROSS JOIN LATERAL (SELECT regexp_replace(pg_get_functiondef(g.f::regprocedure), '--[^\n]*', '', 'g') AS t) x
      WHERE x.t ~ 'script\.fn_check_listino_riga_scrivibile\s*\('
        AND x.t !~ '''(BOZZA|ATTIVA|CHIUSA)'''
        AND x.t !~ 'stati_doc_listino_versioni'),
    3,
    '8. forma: i tre guard chiamano la check e non nominano stati ne'' il vocabolario'
);

SELECT ok(
    regexp_replace(pg_get_functiondef('script.fn_check_listino_riga_scrivibile'::regproc), '--[^\n]*', '', 'g')
        !~ 'listino_riga_id\s*=',
    '9. forma: la check non guarda i documenti che citano la riga (e'' la domanda della rettifica)'
);

-- ============================================================
-- 12) La reason_key: le scritture hanno la loro, non quella dell'eliminazione
-- ============================================================
-- ⚠️ Prima del -78 la scrivibile dava versione_non_in_bozza, la chiave
--   dell'eliminabile: il FE avrebbe mostrato sul pulsante «Aggiungi riga» la
--   frase dell'eliminazione. Si legge dalle superfici, come il FE.
SELECT is(
    (SELECT concat_ws(' ', a.aggiunta_riga_blocco_reason_key, a.variazione_blocco_reason_key,
                           a.prezzi_bundle_blocco_reason_key, a.periodicita_kit_blocco_reason_key,
                           (SELECT r.modifica_blocco_reason_key FROM vendite.vw_listini_righe_azioni r
                             WHERE r.listino_riga_id = pg_temp.r('A')),
                           a.eliminazione_blocco_reason_key)
       FROM vendite.vw_listini_versioni_azioni a WHERE a.versione_id = pg_temp.v('attiva')),
    concat_ws(' ', VARIADIC array_fill('vendite.listini.azione_reason.righe_non_in_bozza'::text, ARRAY[5])
                   || 'vendite.listini.azione_reason.versione_non_in_bozza'::text),
    '12. contrasto: nell''attiva le scritture dicono righe_non_in_bozza, l''eliminazione versione_non_in_bozza'
);

-- ============================================================
-- 10-11) ⭐ La marca spostata: iniziale su CHIUSA
-- ============================================================
UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'CHIUSA';

SELECT is(
    concat_ws(' ', pg_temp.azioni('chiusa'), pg_temp.modifica('C'), pg_temp.guard(pg_temp.cambia_riga('C'))),
    '-/-/-/- - passa',
    '10. con iniziale su CHIUSA, la chiusa si scrive: le superfici lo dicono, il guard lo lascia fare'
);

SELECT is(
    concat_ws(' ', pg_temp.modifica('B'), pg_temp.guard(pg_temp.cambia_riga('B')),
                   pg_temp.guard(pg_temp.cambia_kit('bozza'))),
    'VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA',
    '11. ... e la bozza, ora fuori dallo stato iniziale, non si scrive piu'': righe e kit'
);

UPDATE config.stati_doc_listino_versioni SET iniziale = false WHERE codice_interno = 'CHIUSA';
UPDATE config.stati_doc_listino_versioni SET iniziale = true  WHERE codice_interno = 'BOZZA';

SELECT * FROM finish();

ROLLBACK;
