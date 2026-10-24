-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   la natura merce ha destinazione ORDINE_VENDITA, il codice della sorgente (era ORDINE).
-- pgTAP test per Zero ERP
--
-- La distinta base ha un livello solo, e un articolo-onere non e' merce.
-- Brief: brief-db-articoli-ammessi-per-documento (§8.4 D-4, §8.6 A-9, §9.1)
-- ChangeSet: 20261013-01 -> -06
--
-- Elenco test (plan 14):
--  Distinta a un livello (D-4), sul legame
--   1) componente composito in un legame attivo -> E_BOM_COMPONENTE_COMPOSITO
--   2) componente semplice -> ammesso
--   3) legame SPENTO con componente composito -> ammesso (non e' distinta)
--   4) riaccensione di quel legame -> E_BOM_COMPONENTE_COMPOSITO
--  L'ordine dei rifiuti (nome dei trigger _a10_)
--   5) padre NON composito e componente composito -> parla il padre
--      (E_ARTICOLO_NON_COMPOSITO): senza padre composito la distinta non c'e'
--   6) componente composito con IVA diversa dal padre -> parla il livello,
--      non l'IVA (E_BOM_COMPONENTE_COMPOSITO prima di E_BOM_IVA_DISCORDANTE)
--  Distinta a un livello, dal lato articolo
--   7) componente di una distinta in vigore -> non diventa composito
--   8) componente di una distinta FUTURA -> non diventa composito
--   9) componente di una distinta SCADUTA -> diventa composito
--  10) il form spegne is_composito sul componente in vigore
--      (dbops.fn_non_editable_fields, regola gemella 20261013-04)
--  Articolo-onere (A-9)
--  11) onere con natura che va in ordine -> E_ARTICOLO_ONERE_NATURA_MERCE
--  12) onere con natura di servizio -> ammesso
--  13) onere che passa a una natura che va in ordine -> E_ARTICOLO_ONERE_NATURA_MERCE
--  14) articolo semplice che diventa onere tenendo la natura merce
--      -> E_ARTICOLO_ONERE_NATURA_MERCE (il guard guarda anche causale_onere_id)
--
-- Scopo:
--  - il guard catalogo.trgfn_articoli_componenti_guard_un_livello e il
--    check 3 di catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva;
--  - catalogo.trgfn_articoli_guard_onere_natura.
--  Il mondo si costruisce: articoli, distinte e causale propri. Le nature si
--  leggono dal vocabolario per DESTINAZIONE (la regola legge quella), non per id.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
-- Padre e i due kit nascono compositi; gli altri nascono semplici.
CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-BOM1L-PADRE', false, p_is_composito => true)   AS padre,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-PADRE-NC', false)                        AS padre_non_comp,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-KIT', false, p_is_composito => true)     AS kit,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-KIT-IVA', false, p_is_composito => true) AS kit_iva,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-SEMPL', false)                           AS semplice,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-FUTURO', false)                          AS futuro,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-SCADUTO', false)                         AS scaduto;

-- Due aliquote diverse, scelte UNA volta. Si fissano PRIMA dei legami: con
-- una distinta attiva l'IVA del padre e dei componenti non si cambia piu'
-- (trgfn_articoli_guard_iva_bom_attiva). Tutti con l'IVA A, tranne kit_iva
-- (test 6).
CREATE TEMP TABLE _t_iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1)          AS iva_a,
       (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1 OFFSET 1) AS iva_b;

UPDATE catalogo.articoli SET iva_id = (SELECT iva_a FROM _t_iva)
 WHERE id IN (SELECT unnest(ARRAY[padre, padre_non_comp, kit, semplice, futuro, scaduto]) FROM _t_art);
UPDATE catalogo.articoli SET iva_id = (SELECT iva_b FROM _t_iva)
 WHERE id = (SELECT kit_iva FROM _t_art);

-- Le nature per destinazione, come le legge la regola.
CREATE TEMP TABLE _t_nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1)   AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

-- Due causali onere proprie: la causale e' 1:1 con l'articolo-onere
-- (uq_articoli_causale_onere), e quelle del seed sono gia' prese.
CREATE TEMP TABLE _t_causale AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_BOM1L_ONERE_A', 'PGT_BOM1L_ONERE_A', 'Fixture pgTAP: onere A'),
           ('PGT_BOM1L_ONERE_B', 'PGT_BOM1L_ONERE_B', 'Fixture pgTAP: onere B')
    RETURNING id, codice_interno
)
SELECT (SELECT id FROM ins WHERE codice_interno = 'PGT_BOM1L_ONERE_A') AS onere_a,
       (SELECT id FROM ins WHERE codice_interno = 'PGT_BOM1L_ONERE_B') AS onere_b;

-- Un legame della distinta, con le date scelte dal test.
CREATE FUNCTION pg_temp.legame(p_padre uuid, p_comp uuid, p_dal date, p_al date,
                               p_attivo boolean DEFAULT true)
RETURNS uuid AS $l$
DECLARE v_id uuid;
BEGIN
    INSERT INTO catalogo.articoli_componenti (
        prodotto_id, componente_id, coeff_qta, obbligatorio,
        esposizione_in_fattura, valido_dal, valido_al, attivo)
    VALUES (p_padre, p_comp, 1, true, 'NASCOSTO', p_dal, p_al, p_attivo)
    RETURNING id INTO v_id;
    RETURN v_id;
END $l$ LANGUAGE plpgsql;

-- ============================================================
-- Distinta a un livello, sul legame (1-4)
-- ============================================================
SELECT throws_like(
    $$ SELECT pg_temp.legame((SELECT padre FROM _t_art), (SELECT kit FROM _t_art),
                             script.fn_data_operativa(), NULL) $$,
    '%a sua volta un articolo composito%',
    '1) componente composito in un legame attivo: rifiutato (E_BOM_COMPONENTE_COMPOSITO)');

CREATE TEMP TABLE _t_legame (scenario text, id uuid);

SELECT lives_ok(
    $$ INSERT INTO _t_legame
       SELECT 'semplice', pg_temp.legame((SELECT padre FROM _t_art), (SELECT semplice FROM _t_art),
                                         script.fn_data_operativa() - 30, NULL) $$,
    '2) componente semplice: ammesso');

SELECT lives_ok(
    $$ INSERT INTO _t_legame
       SELECT 'spento', pg_temp.legame((SELECT padre FROM _t_art), (SELECT kit FROM _t_art),
                                       script.fn_data_operativa() - 30, NULL, false) $$,
    '3) legame spento con componente composito: ammesso, non e'' parte della distinta');

SELECT throws_like(
    $$ UPDATE catalogo.articoli_componenti SET attivo = true
        WHERE id = (SELECT id FROM _t_legame WHERE scenario = 'spento') $$,
    '%a sua volta un articolo composito%',
    '4) riaccensione del legame col componente composito: rifiutata');

-- ============================================================
-- L'ordine dei rifiuti (5-6)
-- ============================================================
SELECT throws_like(
    $$ SELECT pg_temp.legame((SELECT padre_non_comp FROM _t_art), (SELECT kit FROM _t_art),
                             script.fn_data_operativa(), NULL) $$,
    '%indicato non _ composito%',
    '5) padre non composito e componente composito: parla il padre (E_ARTICOLO_NON_COMPOSITO)');

SELECT throws_like(
    $$ SELECT pg_temp.legame((SELECT padre FROM _t_art), (SELECT kit_iva FROM _t_art),
                             script.fn_data_operativa(), NULL) $$,
    '%a sua volta un articolo composito%',
    '6) componente composito con IVA diversa: parla il livello, non l''IVA');

-- ============================================================
-- Dal lato articolo (7-10)
-- ============================================================
SELECT pg_temp.legame((SELECT padre FROM _t_art), (SELECT futuro FROM _t_art),
                      script.fn_data_operativa() + 10, NULL);
SELECT pg_temp.legame((SELECT padre FROM _t_art), (SELECT scaduto FROM _t_art),
                      script.fn_data_operativa() - 60, script.fn_data_operativa() - 10);

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET is_composito = true WHERE id = (SELECT semplice FROM _t_art) $$,
    '%componente della distinta di PGT-BOM1L-PADRE%',
    '7) componente di una distinta in vigore: non diventa composito (E_BOM_COMPONENTE_DIVENTA_COMPOSITO)');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET is_composito = true WHERE id = (SELECT futuro FROM _t_art) $$,
    '%componente della distinta di PGT-BOM1L-PADRE%',
    '8) componente di una distinta futura: non diventa composito');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli SET is_composito = true WHERE id = (SELECT scaduto FROM _t_art) $$,
    '9) componente di una distinta scaduta: diventa composito');

SELECT ok(
    'is_composito' = ANY (dbops.fn_non_editable_fields('catalogo', 'articoli',
                                                       (SELECT semplice FROM _t_art)::text)),
    '10) il form spegne is_composito sul componente di una distinta in vigore');

-- ============================================================
-- Articolo-onere (11-14)
-- ============================================================
CREATE TEMP TABLE _t_onere AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-BOM1L-ONERE-OK', false)   AS onere_ok,
       dbops.fn_pgtap_crea_articolo('PGT-BOM1L-DIVENTA', false,
           p_natura_vendita_id => (SELECT merce FROM _t_nat))      AS diventa;

SELECT throws_like(
    $$ UPDATE catalogo.articoli
          SET causale_onere_id  = (SELECT onere_a FROM _t_causale),
              natura_vendita_id = (SELECT merce FROM _t_nat)
        WHERE id = (SELECT onere_ok FROM _t_onere) $$,
    '%e'' un onere, e un onere non puo'' avere la natura%',
    '11) onere con natura che va in ordine: rifiutato (E_ARTICOLO_ONERE_NATURA_MERCE)');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli
          SET causale_onere_id  = (SELECT onere_a FROM _t_causale),
              natura_vendita_id = (SELECT servizio FROM _t_nat)
        WHERE id = (SELECT onere_ok FROM _t_onere) $$,
    '12) onere con natura di servizio: ammesso');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET natura_vendita_id = (SELECT merce FROM _t_nat)
        WHERE id = (SELECT onere_ok FROM _t_onere) $$,
    '%e'' un onere, e un onere non puo'' avere la natura%',
    '13) onere che passa a una natura che va in ordine: rifiutato');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET causale_onere_id = (SELECT onere_b FROM _t_causale)
        WHERE id = (SELECT diventa FROM _t_onere) $$,
    '%e'' un onere, e un onere non puo'' avere la natura%',
    '14) articolo merce che diventa onere: rifiutato');

SELECT * FROM finish();
ROLLBACK;
