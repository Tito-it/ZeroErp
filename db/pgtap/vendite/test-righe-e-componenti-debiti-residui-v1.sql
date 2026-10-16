-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: righe e componenti di documento, i debiti rimasti (D-1, D-3).
--   ChangeSet 20261008-87 … -94.
-- Brief: brief-db-righe-e-componenti-debiti-residui
--
-- Elenco test (plan 24):
--  L'helper di fixture (20261008-94)
--   1) dbops.fn_pgtap_porta_a_stato porta l'ordine DRAFT, con le righe, a CONFERMATO
--   2) ... e rifiuta uno stato che il catalogo non ha
--   3) ... e un documento che non conosce
--  D-1, righe d'ordine (20261008-90): ordine CONFERMATO
--   4) la quantita' di una riga SEMPLICE non cambia (il buco del brief §1)
--   5) la data di consegna confermata cambia (l'eccezione del montaggio)
--   6) data e descrizione insieme no: l'eccezione e' SOLO la data
--   7) una riga nuova non si aggiunge
--   8) una riga non si toglie
--   9) ordine ANNULLATO: nemmeno la data cambia (stato fuori dall'eccezione)
--  D-1, righe del preventivo (20261008-91): preventivo EMESSO
--  10) in DRAFT la riga si modifica (il controllo dei rifiuti)
--  11) la quantita' di una riga semplice non cambia
--  12) una riga nuova non si aggiunge
--  13) una riga non si toglie
--  14) nessuna eccezione per le marche di approvazione
--  Il building block (20261008-89), montaggio e livello RIGA
--  15) i tre montaggi: argomenti in tgargs
--  16) [4] senza [5] e' un errore di montaggio
--  17) una colonna ammessa che la riga non ha e' un errore di montaggio
--  18) livello RIGA con eccezione: la colonna ammessa cambia nello stato ammesso
--  19) ... un'altra colonna no
--  20) prelievi: il guard non dice piu' lo stato, lo dice il building block, che parla prima
--  D-3 (20261008-87, -88): un componente SPENTO in attesa si copia senza marca
--  21) preventivo: lo spento PENDING arriva sulla rev N+1 con stato e pratica NULL
--  22) preventivo: approvato e rifiutato si copiano 1:1, con la pratica
--  23) offerta: lo spento PENDING arriva sulla rev N+1 con stato e pratica NULL
--  24) offerta: approvato e rifiutato si copiano 1:1, con la pratica
--
-- Scopo:
--  - ⭐ i casi si COSTRUISCONO: mondo, articoli, kit con la distinta, pratiche,
--    documenti. Niente pescato dal DB.
--  - ⭐ i documenti nascono in DRAFT, prendono le righe, poi cambiano stato
--    con le transizioni vere (dbops.fn_pgtap_porta_a_stato): e' la forma che
--    il lock delle righe impone, ed e' quella della produzione.
--  - ⭐ i rifiuti si leggono dal canale CONSTRAINT (contratto «P0001 +
--    CONSTRAINT = codice»), non dalla frase.
--  - ⚠️ il montaggio (16-19) si prova su una tabella TEMPORANEA del ruolo
--    che gira: un trigger su una tabella del dominio lo potrebbe montare
--    solo l'owner. La tabella temporanea punta a righe vere, e i lettori
--    DEFINER del building block le risolvono come sulle tabelle del dominio.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- Il codice di dominio di un errore, dal canale CONSTRAINT (P0001); per gli
-- altri, SQLSTATE e vincolo. 'PASSA' se non solleva.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    -- P0001 col codice nel canale CONSTRAINT: il codice. Senza codice (un
    -- RAISE nudo, come quelli dell'helper di fixture): 'P0001'.
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- =========================================================
-- Il mondo, gli articoli, il kit.
--   S: articolo semplice.
--   P: kit. F obbligatorio, G e R opzionali (G si spegne in attesa, R si
--      spegne rifiutato).
-- P nasce composito dal builder:
-- catalogo.trgfn_articoli_componenti_guard_is_composito rifiuta la distinta
-- di un articolo semplice.
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP debiti residui');

DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m));
END $ctx$;

CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _m), 'pgTAP debiti residui');

CREATE TEMP TABLE _art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGT-DR-' || v.sigla,
                                             p_is_composito => v.sigla = 'P') AS id
  FROM (VALUES ('S'), ('P'), ('F'), ('G'), ('R')) AS v(sigla);

CREATE FUNCTION pg_temp.art(p_sigla text) RETURNS uuid
LANGUAGE sql STABLE AS $f$ SELECT id FROM _art WHERE sigla = p_sigla $f$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, obbligatorio, valido_dal)
VALUES (pg_temp.art('P'), pg_temp.art('F'), 1, true,  script.fn_data_operativa() - 30),
       (pg_temp.art('P'), pg_temp.art('G'), 1, false, script.fn_data_operativa() - 30),
       (pg_temp.art('P'), pg_temp.art('R'), 1, false, script.fn_data_operativa() - 30);

CREATE TEMP TABLE _k AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id;

-- Due pratiche di approvazione prezzo, come le crea il backend: una per il
-- componente approvato, una per lo spento in attesa. Il rifiutato ne ha una
-- sua: la marca 1:1 si prova con la pratica, non solo con lo stato.
CREATE TEMP TABLE _pr AS
SELECT x.tag,
       pratiche.fn_crea_pratica(
           m.emittente_fiscale_id,
           (SELECT tp.id FROM pratiche.tipi_prestazione tp WHERE tp.codice_interno = 'APPROVAZIONE_PREZZO'),
           NULL, NULL, NULL, NULL,
           'pgTAP debiti residui — ' || x.tag,
           jsonb_build_object('test_scope', 'pgtap_debiti_residui')) AS pratica_id
  FROM _m m, (VALUES ('approvata'), ('in_attesa'), ('rifiutata')) AS x(tag);

CREATE FUNCTION pg_temp.pratica(p_tag text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT pratica_id FROM _pr WHERE tag = p_tag $f$;

-- La distinta del kit come righe da copiare sui componenti di un documento:
-- F attivo APPROVED, G spento PENDING, R spento REJECTED, ciascuno con la sua
-- pratica.
CREATE TEMP TABLE _bom AS
SELECT ac.id AS bom_id, ac.componente_id AS cmp_id, ar.uom_id,
       s.sigla,
       (s.sigla = 'F') AS attivo,
       CASE s.sigla WHEN 'F' THEN 'APPROVED' WHEN 'G' THEN 'PENDING' ELSE 'REJECTED' END
           ::config.stato_approvazione_prezzo AS stato,
       pg_temp.pratica(CASE s.sigla WHEN 'F' THEN 'approvata' WHEN 'G' THEN 'in_attesa' ELSE 'rifiutata' END) AS pratica_id,
       CASE s.sigla WHEN 'F' THEN 1 WHEN 'G' THEN 2 ELSE 3 END AS ordine
  FROM catalogo.articoli_componenti ac
  JOIN catalogo.articoli ar ON ar.id = ac.componente_id
  JOIN _art s ON s.id = ac.componente_id
 WHERE ac.prodotto_id = pg_temp.art('P');

-- =========================================================
-- I documenti: tutti nati DRAFT, con le righe scritte in bozza.
-- Padre e figli in istruzioni separate: la policy della riga risolve il
-- perimetro passando dalla testata.
-- =========================================================
CREATE TEMP TABLE _doc (chiave text PRIMARY KEY, testata_id bigint, riga_id bigint, riga_kit_id bigint);

DO $fixture$
DECLARE
    c       record;
    k       record;
    v_id    bigint;
    v_riga  bigint;
    v_kit   bigint;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

    -- ORDINE da confermare (4-8) e ORDINE da annullare (9): una riga semplice
    FOR i IN 1..2 LOOP
        INSERT INTO vendite.ordini
            (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
             fatturazione_trigger, emittente_fiscale_id, valuta_id, data)
        VALUES
            (c.cliente_soggetto_ruolo_id, c.billing_account_id,
             (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT'),
             'SPEDITO', c.emittente_fiscale_id, k.valuta_id, script.fn_data_operativa())
        RETURNING id INTO v_id;

        INSERT INTO vendite.ordini_righe
            (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
             prezzo_unitario, iva_id)
        VALUES (v_id, 1, pg_temp.art('S'), 'Riga semplice pgTAP', 2, 2, 10, k.iva_id)
        RETURNING id INTO v_riga;

        INSERT INTO _doc VALUES (CASE i WHEN 1 THEN 'ORDINE' ELSE 'ORDINE_ANN' END, v_id, v_riga, NULL);
    END LOOP;

    -- PREVENTIVO: una riga semplice e una riga kit con i tre componenti
    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id, valuta_id)
    VALUES
        ('PGT-DR-' || substring(md5(clock_timestamp()::text) FOR 6),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id, k.valuta_id)
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
    VALUES (v_id, pg_temp.art('S'), 2, 2, 10, k.iva_id, 1)
    RETURNING id INTO v_riga;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
    VALUES (v_id, pg_temp.art('P'), 1, 1, 100, k.iva_id, 2)
    RETURNING id INTO v_kit;

    INSERT INTO vendite.preventivi_righe_componenti
        (riga_preventivo_id, articolo_componente_id, componente_id, coeff_qta_snapshot,
         quantita, prezzo_unitario, origine_prezzo, uom_operativa_id, ordine, attivo,
         stato_approvazione_prezzo, pratica_approvazione_prezzo_id)
    SELECT v_kit, b.bom_id, b.cmp_id, 1, 1, 10, 'MANUALE', b.uom_id, b.ordine, b.attivo,
           b.stato, b.pratica_id
      FROM _bom b;

    INSERT INTO _doc VALUES ('PREVENTIVO', v_id, v_riga, v_kit);

    -- OFFERTA: un'eccezione kit con i tre componenti
    INSERT INTO vendite.offerte_commerciali
        (codice, emittente_fiscale_id, billing_account_id, istanza_utility_id,
         utility_id, listino_id, listino_versione_id, validita_dal, validita_al, stato_doc_offerta_id)
    SELECT 'PGT-DR-' || substr(gen_random_uuid()::text, 1, 8),
           c.emittente_fiscale_id, c.billing_account_id, c.istanza_utility_id,
           c.utility_id, l.listino_id, l.listino_versione_id, script.fn_data_operativa(), script.fn_data_operativa() + 365,
           (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
      FROM _l l
    RETURNING id INTO v_id;

    INSERT INTO vendite.offerte_commerciali_eccezioni
        (offerta_id, articolo_id, tipo_eccezione, prezzo_unitario, tipo_erogazione,
         fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)
    SELECT v_id, a.id, 'AGGIUNTA', 1, 'UNA_TANTUM', 'FISSA', 1, 1, a.uom_id
      FROM catalogo.articoli a WHERE a.id = pg_temp.art('P')
    RETURNING id INTO v_kit;

    INSERT INTO vendite.offerte_commerciali_eccezioni_componenti
        (eccezione_offerta_id, articolo_componente_id, componente_id, coeff_qta_snapshot,
         quantita, uom_operativa_id, prezzo_unitario, origine_prezzo, ordine, attivo,
         stato_approvazione_prezzo, pratica_approvazione_prezzo_id)
    SELECT v_kit, b.bom_id, b.cmp_id, 1, 1, b.uom_id, 10, 'MANUALE', b.ordine, b.attivo,
           b.stato, b.pratica_id
      FROM _bom b;

    INSERT INTO _doc VALUES ('OFFERTA', v_id, NULL, v_kit);
END
$fixture$;

CREATE FUNCTION pg_temp.doc(p_chiave text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT testata_id FROM _doc WHERE chiave = p_chiave $f$;
CREATE FUNCTION pg_temp.riga(p_chiave text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT riga_id FROM _doc WHERE chiave = p_chiave $f$;

-- =========================================================
-- 1-3) L'helper di fixture
-- =========================================================
SELECT is(
    dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.doc('ORDINE'), 'CONFERMATO'),
    'CONFERMATO',
    '1) fn_pgtap_porta_a_stato: l''ordine DRAFT con le righe arriva a CONFERMATO per la matrice'
);

SELECT is(
    pg_temp.esito(format($$SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', %s, 'NON_ESISTE')$$,
                         pg_temp.doc('ORDINE_ANN'))),
    'P0001',
    '2) fn_pgtap_porta_a_stato: uno stato che il catalogo non ha e'' un''eccezione, non un ritorno muto'
);

SELECT is(
    pg_temp.esito($$SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', 1, 'EMESSO')$$),
    'P0001',
    '3) fn_pgtap_porta_a_stato: un documento che non conosce e'' un''eccezione'
);

-- =========================================================
-- 4-9) D-1: le righe d'ordine fuori bozza
-- =========================================================
SELECT is(
    pg_temp.esito(format('UPDATE vendite.ordini_righe SET qta_operativa = 3 WHERE id = %s',
                         pg_temp.riga('ORDINE'))),
    'E_RIGA_DOC_NON_BOZZA',
    '4) ordine CONFERMATO: la quantita'' di una riga semplice non cambia (prima passava: solo un kit la fermava)'
);

SELECT is(
    pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 10 WHERE id = %s',
                         pg_temp.riga('ORDINE'))),
    'PASSA',
    '5) ordine CONFERMATO: la data di consegna confermata cambia (eccezione dichiarata nel montaggio)'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.ordini_righe
                              SET data_consegna_confermata = script.fn_data_operativa() + 11, descrizione = 'altra'
                            WHERE id = %s$$, pg_temp.riga('ORDINE'))),
    'E_RIGA_DOC_NON_BOZZA',
    '6) ordine CONFERMATO: data e descrizione insieme no — l''eccezione e'' la sola data'
);

SELECT is(
    pg_temp.esito(format($$INSERT INTO vendite.ordini_righe
                              (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario, iva_id)
                            VALUES (%s, 2, %L, 'nuova', 1, 1, 1, %s)$$,
                         pg_temp.doc('ORDINE'), pg_temp.art('S'), (SELECT iva_id FROM _k))),
    'E_RIGA_DOC_NON_BOZZA',
    '7) ordine CONFERMATO: una riga nuova non si aggiunge'
);

SELECT is(
    pg_temp.esito(format('DELETE FROM vendite.ordini_righe WHERE id = %s', pg_temp.riga('ORDINE'))),
    'E_RIGA_DOC_NON_BOZZA',
    '8) ordine CONFERMATO: una riga non si toglie'
);

SELECT is(
    dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.doc('ORDINE_ANN'), 'ANNULLATO')
    || ' | ' ||
    pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 12 WHERE id = %s',
                         pg_temp.riga('ORDINE_ANN'))),
    'ANNULLATO | E_RIGA_DOC_NON_BOZZA',
    '9) ordine ANNULLATO: nemmeno la data cambia — l''eccezione vale solo negli stati da evadere'
);

-- =========================================================
-- 10) In DRAFT la riga del preventivo si modifica (il controllo dei rifiuti)
-- =========================================================
SELECT is(
    pg_temp.esito(format('UPDATE vendite.preventivi_righe SET qta_operativa = 3 WHERE id = %s',
                         pg_temp.riga('PREVENTIVO'))),
    'PASSA',
    '10) preventivo DRAFT: la riga si modifica (il controllo dei rifiuti 11-14)'
);

-- Il preventivo esce dalla bozza. Lo spento in attesa non lo ferma: i
-- prezzi non autorizzati contano solo sui componenti ATTIVI.
-- ⚠️ In un DO: un SELECT nudo stamperebbe una riga che non e' TAP.
DO $emetti$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', pg_temp.doc('PREVENTIVO'), 'EMESSO');
END $emetti$;

-- =========================================================
-- 11-14) D-1: le righe del preventivo fuori bozza
-- =========================================================
SELECT is(
    pg_temp.esito(format('UPDATE vendite.preventivi_righe SET qta_operativa = 4 WHERE id = %s',
                         pg_temp.riga('PREVENTIVO'))),
    'E_RIGA_DOC_NON_BOZZA',
    '11) preventivo EMESSO: la quantita'' di una riga semplice non cambia'
);

SELECT is(
    pg_temp.esito(format($$INSERT INTO vendite.preventivi_righe
                              (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
                            VALUES (%s, %L, 1, 1, 1, %s, 9)$$,
                         pg_temp.doc('PREVENTIVO'), pg_temp.art('S'), (SELECT iva_id FROM _k))),
    'E_RIGA_DOC_NON_BOZZA',
    '12) preventivo EMESSO: una riga nuova non si aggiunge'
);

SELECT is(
    pg_temp.esito(format('DELETE FROM vendite.preventivi_righe WHERE id = %s', pg_temp.riga('PREVENTIVO'))),
    'E_RIGA_DOC_NON_BOZZA',
    '13) preventivo EMESSO: una riga non si toglie'
);

SELECT is(
    pg_temp.esito(format($$UPDATE vendite.preventivi_righe SET stato_approvazione_prezzo = 'APPROVED' WHERE id = %s$$,
                         pg_temp.riga('PREVENTIVO'))),
    'E_RIGA_DOC_NON_BOZZA',
    '14) preventivo EMESSO: nessuna eccezione per le marche di approvazione (l''esito arriva in bozza)'
);

-- =========================================================
-- 15) I tre montaggi del building block, letti da tgargs
-- =========================================================
SELECT is(
    (SELECT string_agg(c.relname || ':' || t.tgname || ':' || array_to_string(dbops.fn_trigger_argomenti(t.tgargs), '|'),
                       ' ; ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       JOIN pg_proc p      ON p.oid = t.tgfoid
      WHERE n.nspname = 'vendite'
        AND c.relname IN ('ordini_righe', 'preventivi_righe', 'ddt_righe_prelievi')
        AND p.proname = 'trgfn_doc_righe_lock_fuori_bozza'
        AND NOT t.tgisinternal
        -- tre porte: INSERT (4), DELETE (8), UPDATE (16), BEFORE ROW (2|1)
        AND t.tgtype & (4 | 8 | 16 | 2 | 1) = (4 | 8 | 16 | 2 | 1)),
    'ddt_righe_prelievi:trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt:DDT|ddt_riga_id|DRAFT|RIGA|ubicazione_arrivo_id|EMESSO,SPEDITO'
    || ' ; ordini_righe:trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt:ORDINE|ordine_id|DRAFT|TESTATA|data_consegna_confermata|CONFERMATO,PARZIALMENTE_EVASO'
    || ' ; preventivi_righe:trg_preventivi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt:PREVENTIVO|preventivo_id',
    '15) i tre montaggi BEFORE ROW sulle tre porte, con gli argomenti decisi (D-1 e la copia dei prelievi)'
);

-- =========================================================
-- 16-19) Montaggio e livello RIGA, su una tabella temporanea
--   La riga temporanea punta alla riga d'ordine CONFERMATO di 4-8.
-- =========================================================
CREATE TEMP TABLE _tmp_lock (id bigint PRIMARY KEY, riga_ordine_id bigint, a int, b int);
INSERT INTO _tmp_lock VALUES (1, pg_temp.riga('ORDINE'), 0, 0);

CREATE TRIGGER trg_tmp_lock_a05_monco
    BEFORE UPDATE ON _tmp_lock FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE', 'riga_ordine_id', 'DRAFT', 'RIGA', 'a');

SELECT is(
    pg_temp.esito('UPDATE _tmp_lock SET a = 1 WHERE id = 1'),
    'E_DOC_RIGHE_LOCK_MONTAGGIO',
    '16) colonne ammesse senza gli stati: errore di MONTAGGIO, non un lock a meta'''
);

DROP TRIGGER trg_tmp_lock_a05_monco ON _tmp_lock;
CREATE TRIGGER trg_tmp_lock_a05_refuso
    BEFORE UPDATE ON _tmp_lock FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE', 'riga_ordine_id', 'DRAFT', 'RIGA', 'a,non_esiste', 'CONFERMATO');

SELECT is(
    pg_temp.esito('UPDATE _tmp_lock SET a = 1 WHERE id = 1'),
    'E_DOC_RIGHE_LOCK_MONTAGGIO',
    '17) una colonna ammessa che la riga non ha: errore di MONTAGGIO (l''eccezione non scatterebbe mai)'
);

DROP TRIGGER trg_tmp_lock_a05_refuso ON _tmp_lock;
CREATE TRIGGER trg_tmp_lock_a05_riga
    BEFORE UPDATE ON _tmp_lock FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE', 'riga_ordine_id', 'DRAFT', 'RIGA', 'a', 'CONFERMATO');

SELECT is(
    pg_temp.esito('UPDATE _tmp_lock SET a = 2 WHERE id = 1'),
    'PASSA',
    '18) livello RIGA con eccezione: la colonna ammessa cambia nello stato ammesso'
);

SELECT is(
    pg_temp.esito('UPDATE _tmp_lock SET b = 2 WHERE id = 1'),
    'E_RIGA_DOC_NON_BOZZA',
    '19) livello RIGA con eccezione: un''altra colonna no'
);

-- =========================================================
-- 20) I prelievi: la copia della regola e' ritirata, e il building block
--   parla prima della regola del kit (nome minore nella stessa fascia)
-- =========================================================
SELECT is(
    concat_ws(' | ',
        (SELECT p.prosrc NOT LIKE '%E_RIGA_DOC_NON_BOZZA%'
           FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_ddt_righe_prelievi_guard'),
        (SELECT string_agg(t.tgname, ' < ' ORDER BY t.tgname)
           FROM pg_trigger t
          WHERE t.tgrelid = 'vendite.ddt_righe_prelievi'::regclass
            AND NOT t.tgisinternal
            AND t.tgname LIKE 'trg_ddt_righe_prelievi_a05_%')),
    't | trg_ddt_righe_prelievi_a05_doc_bozza_ins_upd_dlt < trg_ddt_righe_prelievi_a05_guard_ins_upd_dlt',
    '20) prelievi: il guard non dice piu'' lo stato della bolla; lo dice il building block, che parla prima'
);

-- =========================================================
-- 21-24) D-3: le revisioni
-- =========================================================
CREATE TEMP TABLE _rev_prev AS
SELECT r.nuovo_preventivo_id
  FROM vendite.fn_crea_revisione_preventivo(pg_temp.doc('PREVENTIVO'), 'pgtap') r;

-- I componenti di un documento in forma confrontabile: sigla:stato:pratica
CREATE FUNCTION pg_temp.marche_prev(p_preventivo bigint, p_sigle text[]) RETURNS text
LANGUAGE sql STABLE AS $f$
  SELECT string_agg(a.sigla || ':' || c.attivo || ':' || coalesce(c.stato_approvazione_prezzo::text, 'NULL')
                    || ':' || CASE WHEN c.pratica_approvazione_prezzo_id IS NULL THEN 'NULL'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('approvata') THEN 'pratica_approvata'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('in_attesa') THEN 'pratica_in_attesa'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('rifiutata') THEN 'pratica_rifiutata'
                                   ELSE 'altra' END,
                    ' ' ORDER BY a.sigla)
    FROM vendite.preventivi_righe r
    JOIN vendite.preventivi_righe_componenti c ON c.riga_preventivo_id = r.id
    JOIN _art a ON a.id = c.componente_id
   WHERE r.preventivo_id = p_preventivo AND a.sigla = ANY (p_sigle);
$f$;

SELECT is(
    pg_temp.marche_prev((SELECT nuovo_preventivo_id FROM _rev_prev), ARRAY['G']),
    'G:false:NULL:NULL',
    '21) preventivo: lo spento IN ATTESA arriva sulla rev N+1 senza marca ne'' pratica (D-3)'
);

SELECT is(
    pg_temp.marche_prev((SELECT nuovo_preventivo_id FROM _rev_prev), ARRAY['F', 'R']),
    'F:true:APPROVED:pratica_approvata R:false:REJECTED:pratica_rifiutata',
    '22) preventivo: approvato e rifiutato si copiano 1:1, con la loro pratica'
);

-- L'offerta: emessa (la transizione non e' in esame, come nei test della
-- revisione dell'offerta), poi revisionata.
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'EMESSA')
 WHERE id = pg_temp.doc('OFFERTA');

CREATE TEMP TABLE _rev_off AS
SELECT vendite.fn_crea_revisione_offerta(pg_temp.doc('OFFERTA'), 'pgtap') AS offerta_id;

CREATE FUNCTION pg_temp.marche_off(p_offerta bigint, p_sigle text[]) RETURNS text
LANGUAGE sql STABLE AS $f$
  SELECT string_agg(a.sigla || ':' || c.attivo || ':' || coalesce(c.stato_approvazione_prezzo::text, 'NULL')
                    || ':' || CASE WHEN c.pratica_approvazione_prezzo_id IS NULL THEN 'NULL'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('approvata') THEN 'pratica_approvata'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('in_attesa') THEN 'pratica_in_attesa'
                                   WHEN c.pratica_approvazione_prezzo_id = pg_temp.pratica('rifiutata') THEN 'pratica_rifiutata'
                                   ELSE 'altra' END,
                    ' ' ORDER BY a.sigla)
    FROM vendite.offerte_commerciali_eccezioni e
    JOIN vendite.offerte_commerciali_eccezioni_componenti c ON c.eccezione_offerta_id = e.id
    JOIN _art a ON a.id = c.componente_id
   WHERE e.offerta_id = p_offerta AND a.sigla = ANY (p_sigle);
$f$;

SELECT is(
    pg_temp.marche_off((SELECT offerta_id FROM _rev_off), ARRAY['G']),
    'G:false:NULL:NULL',
    '23) offerta: lo spento IN ATTESA arriva sulla rev N+1 senza marca ne'' pratica (D-3)'
);

SELECT is(
    pg_temp.marche_off((SELECT offerta_id FROM _rev_off), ARRAY['F', 'R']),
    'F:true:APPROVED:pratica_approvata R:false:REJECTED:pratica_rifiutata',
    '24) offerta: approvato e rifiutato si copiano 1:1, con la loro pratica'
);

SELECT * FROM finish();
ROLLBACK;
