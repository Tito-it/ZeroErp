-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine confermato con la riga gestita da dbops.fn_pgtap_crea_ordine_con_righe (p_articolo_id); restano a mano il magazzino, il carico e la bolla (il caso: generazione, emissione, magazzino scelto).
-- pgTAP test per Zero ERP
--
-- Test: una bolla generata da un ordine arriva fino all'emissione — il giro
--   ordine -> vendite.fn_genera_ddt_da_ordine -> vendite.fn_cambia_stato_ddt
--   che nessun test faceva. La bolla nasce senza emittente (lo eredita
--   dall'ordine trg_ddt_normalize_ins_upd), e i trigger che lo leggono
--   (magazzino predefinito e suo guard, perimetro, numero) devono girare
--   DOPO il normalize. ChangeSet 20261013-53.
--
-- ⭐ Il mondo lo FABBRICA: due aziende nuove (la seconda solo per un suo
--   magazzino), il cliente e l'ordine della prima, un magazzino predefinito,
--   un articolo gestito caricato con un inventario. Gira uguale su un
--   database ricostruito da zero.
-- ⚠️ Prima del 20261013-53 erano rossi 1 e dal 3 al 9: la bolla nasceva
--   senza magazzino, la check dell'emissione diceva
--   E_DDT_MAGAZZINO_OBBLIGATORIO, e un magazzino passato a mano era
--   confrontato con un emittente NULL (falso E_DDT_MAGAZZINO_INCOERENTE).
--   Il 10 e' verde anche prima, per un motivo sbagliato (stesso NULL): prova
--   che il guard, spostato, rifiuta ancora il magazzino di un'altra azienda.
-- ⚠️ Il ripiego dell'emittente dal billing account (bolla senza ordine,
--   nessun emittente di sessione) e il perimetro su una bolla da ordine non
--   si provano sul comportamento: il primo vuole una sessione senza
--   operatore, che il guard di perimetro respinge per chi subisce la RLS; il
--   secondo vuole un ordine fuori perimetro, che la RLS nasconde gia' al
--   normalize. Li copre la forma (test 1): nessun lettore dell'emittente
--   gira prima di chi lo risolve.
--
-- Elenco test (plan 11):
--   FORMA
--    1) i quattro BEFORE INSERT che leggono l'emittente girano dopo trg_ddt_normalize_ins_upd
--    2) il default del magazzino gira prima del suo guard
--   IL GIRO
--    3) la bolla generata ha l'emittente dell'ordine
--    4) ...e il magazzino predefinito di quell'emittente
--    5) con indirizzo di consegna e causale, la check dell'emissione non ha motivi
--    6) il verbo emette
--    7) la bolla e' EMESSA e numerata
--    8) uno scarico SCARICO_VEN di 3 dal magazzino predefinito
--   IL MAGAZZINO SCELTO A MANO
--    9) bolla da ordine con un altro magazzino della stessa azienda: nasce
--   10) ...e lo tiene
--   11) bolla da ordine col magazzino di un'altra azienda: E_DDT_MAGAZZINO_INCOERENTE
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- FIXTURE
-- ============================================================
-- L'altra azienda e un suo magazzino: si costruisce con il contesto su di lei.
CREATE TEMP TABLE _az2 AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az2)); END $ctx$;
CREATE TEMP TABLE _mag2 AS SELECT dbops.fn_pgtap_crea_magazzino('PGT-EPL-ALTRA', false) AS id;

-- L'azienda del test: NUOVA, non quella dell'operatore di sviluppo (su dbdev
-- ha gia' dei magazzini, e forse un predefinito).
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
-- Le azioni dell'operatore: il carico qui sotto, l'emissione al test 6.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _az), 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _az), 'registra_magazzino');
END $az$;

CREATE TEMP TABLE _fix (mag_p bigint, mag_x bigint, art uuid, sorg_ord bigint, ddt_draft bigint);
DO $fix$
DECLARE v_p bigint; v_x bigint; v_art uuid; v_inv bigint;
BEGIN
    v_p := dbops.fn_pgtap_crea_magazzino('PGT-EPL-PRED', false);
    v_x := dbops.fn_pgtap_crea_magazzino('PGT-EPL-ALTRO', false);
    -- Il predefinito si sceglie con un UPDATE: la fixture nasce non predefinita.
    UPDATE magazzino.magazzini SET predefinito = true WHERE id = v_p;
    v_art := dbops.fn_pgtap_crea_articolo('PGT-EPL-GEST', true, false, false);

    -- Il carico: 10 pezzi nel predefinito.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_p) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario) VALUES (v_inv, v_art, 10, 5);
    UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = v_inv;
    PERFORM magazzino.fn_posta_inventario(v_inv);

    INSERT INTO _fix VALUES (
        v_p, v_x, v_art,
        (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
        (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno = 'DRAFT'));
END $fix$;

-- L'ordine CONFERMATO con una riga dell'articolo gestito (3 a 10). Con il
-- contesto aperto, il mondo dell'ordine riusa l'azienda di chi agisce.
CREATE TEMP TABLE _o AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('emittente prima dei lettori',
         p_quantita => 3, p_prezzo => 10, p_articolo_id => (SELECT art FROM _fix));

-- ============================================================
-- FORMA
-- ============================================================
-- 1) BEFORE (tgtype & 2) e INSERT (tgtype & 4). COLLATE "C": e' l'ordine
--    in cui PostgreSQL scatena i trigger.
SELECT is(
    (SELECT format('%s trovati, %s prima del normalize: %s',
                   count(*), count(*) FILTER (WHERE t.tgname::text COLLATE "C" <= 'trg_ddt_normalize_ins_upd'),
                   coalesce(string_agg(t.tgname::text, ', ' ORDER BY t.tgname::text COLLATE "C")
                                FILTER (WHERE t.tgname::text COLLATE "C" <= 'trg_ddt_normalize_ins_upd'), '-'))
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE t.tgrelid = 'vendite.ddt'::regclass
        AND NOT t.tgisinternal
        AND (t.tgtype & 2) = 2 AND (t.tgtype & 4) = 4
        AND (n.nspname, p.proname) IN (('vendite', 'trgfn_ddt_default_magazzino'),
                                       ('vendite', 'trgfn_ddt_guard_magazzino'),
                                       ('vendite', 'trgfn_ddt_gen_numero_emesso'),
                                       ('script',  'trgfn_guard_emittente_scope'))),
    '4 trovati, 0 prima del normalize: -',
    '1) i lettori dell''emittente girano dopo trg_ddt_normalize_ins_upd, che lo eredita');

-- 2) la proposta prima del giudizio
SELECT ok(
    (SELECT max(t.tgname::text COLLATE "C") FILTER (WHERE p.proname = 'trgfn_ddt_default_magazzino')
          < max(t.tgname::text COLLATE "C") FILTER (WHERE p.proname = 'trgfn_ddt_guard_magazzino')
       FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE t.tgrelid = 'vendite.ddt'::regclass AND NOT t.tgisinternal),
    '2) il default del magazzino gira prima del suo guard');

-- ============================================================
-- IL GIRO
-- ============================================================
CREATE TEMP TABLE _d AS SELECT vendite.fn_genera_ddt_da_ordine((SELECT ordine_id FROM _o)) AS id;

-- 3-4) l'emittente e il magazzino
SELECT is(
    (SELECT d.emittente_fiscale_id FROM vendite.ddt d WHERE d.id = (SELECT id FROM _d)),
    (SELECT emittente_fiscale_id FROM _o),
    '3) la bolla generata ha l''emittente dell''ordine');
SELECT is(
    (SELECT d.magazzino_id FROM vendite.ddt d WHERE d.id = (SELECT id FROM _d)),
    (SELECT mag_p FROM _fix),
    '4) ...e nasce col magazzino predefinito di quell''emittente');

-- 5) quello che la bolla chiede all'operatore prima di emettere: la
--    consegna e la causale. Il magazzino no.
INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT (SELECT id FROM _d),
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
       '{"display":"CON pgTAP"}'::jsonb
ON CONFLICT DO NOTHING;
UPDATE vendite.ddt
   SET causale_trasporto_id = (SELECT ct.id FROM config.causali_trasporto ct WHERE ct.codice = 'VENDITA' ORDER BY ct.id LIMIT 1)
 WHERE id = (SELECT id FROM _d);
SELECT is(
    (SELECT script.fn_check_ddt_emittibile(d) FROM vendite.ddt d WHERE d.id = (SELECT id FROM _d)),
    '[]'::jsonb,
    '5) con consegna e causale, la check dell''emissione non ha motivi (niente E_DDT_MAGAZZINO_OBBLIGATORIO)');

-- 6-8) l'emissione, dal verbo: la bolla muove merce
-- _em esiste comunque: se il verbo rifiuta, l'8 e' rosso e non un errore.
CREATE TEMP TABLE _em (movimento_id bigint, prelievo_id bigint, qta numeric);
SELECT lives_ok(
    format('INSERT INTO _em SELECT * FROM vendite.fn_cambia_stato_ddt(%s, %L)', (SELECT id FROM _d), 'EMESSO'),
    '6) il verbo emette la bolla generata dall''ordine');
SELECT is(
    (SELECT s.codice_interno || ':' || (d.numero IS NOT NULL AND btrim(d.numero) <> '')::text
       FROM vendite.ddt d JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
      WHERE d.id = (SELECT id FROM _d)),
    'EMESSO:true',
    '7) la bolla e'' EMESSA e numerata');
SELECT is(
    (SELECT string_agg(c.codice_interno || ':' || trim_scale(m.qta)::text || ':' || (m.magazzino_id = f.mag_p)::text, ' ')
       FROM _em e
       JOIN magazzino.movimenti m ON m.id = e.movimento_id
       JOIN magazzino.causali c ON c.id = m.causale_id
       CROSS JOIN _fix f),
    'SCARICO_VEN:-3:true',
    '8) la merce esce dal magazzino predefinito: uno scarico di 3');

-- ============================================================
-- IL MAGAZZINO SCELTO A MANO, su una bolla che l'emittente lo eredita
-- ============================================================
-- La forma di fn_genera_ddt_da_ordine (niente emittente, la sorgente
-- dell'ordine), piu' il magazzino.
SELECT lives_ok(
    format($q$INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                                      sorgente_tipo_id, sorgente_uid, magazzino_id)
              VALUES (script.fn_data_operativa(), %s, %s, %s, %L, %s)$q$,
           (SELECT ddt_draft FROM _fix), (SELECT cliente_soggetto_ruolo_id FROM _o),
           (SELECT sorg_ord FROM _fix), (SELECT ordine_uid FROM _o), (SELECT mag_x FROM _fix)),
    '9) bolla da ordine con un altro magazzino della stessa azienda: nasce');
SELECT is(
    (SELECT count(*)::int FROM vendite.ddt d
      WHERE d.sorgente_uid = (SELECT ordine_uid FROM _o) AND d.magazzino_id = (SELECT mag_x FROM _fix)),
    1,
    '10) ...e tiene il suo (il default non sovrascrive)');

-- 11) il guard, spostato, giudica ancora: il magazzino e' di un'altra azienda.
--     Sotto RLS non si vede, da proprietario si vede d'un altro emittente: la
--     risposta e' la stessa.
SELECT throws_like(
    format($q$INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                                      sorgente_tipo_id, sorgente_uid, magazzino_id)
              VALUES (script.fn_data_operativa(), %s, %s, %s, %L, %s)$q$,
           (SELECT ddt_draft FROM _fix), (SELECT cliente_soggetto_ruolo_id FROM _o),
           (SELECT sorg_ord FROM _fix), (SELECT ordine_uid FROM _o), (SELECT id FROM _mag2)),
    '%non appartiene all''azienda che emette la bolla%',
    '11) bolla da ordine col magazzino di un''altra azienda: E_DDT_MAGAZZINO_INCOERENTE');

SELECT * FROM finish();
ROLLBACK;
