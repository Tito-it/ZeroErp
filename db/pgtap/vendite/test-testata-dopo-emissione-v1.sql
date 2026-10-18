-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la testata dopo la bozza (fase 2): che cosa si cambia ancora,
--   documento per documento, colonna per colonna, stato per stato.
--   ChangeSet 20261010-68, -69.
-- Brief: brief-db-testata-dopo-emissione (§4, §6, §9; D-1 … D-10 di Tid)
--
-- Elenco test (plan 22):
--  I montaggi (struttura)
--   1) le sei testate hanno il lock, e nominano esattamente le colonne decise
--   2) ogni colonna nominata esiste, e nessuna e' generata
--   3) ⭐ la matrice: ogni colonna nominata, per ogni stato del catalogo,
--      e' aperta solo in bozza e negli stati decisi (§9.2)
--   4) il lock post-attivazione del contratto e' ritirato, e il lock di testata parla prima del guard del listino
--  Un ordine vero (fuori bozza)
--   5) CONFERMATO: la data no (identita')
--   6) ... il termine di pagamento no (condizioni)
--   7) ... la utility no (cliente)
--   8) ... la sorgente no
--   9) ... le note si'
--  10) ... i totali (scritti dal database) si'
--  11) ANNULLATO: le note no (documento chiuso)
--  12) ANNULLATO: e nel rifiuto parla la prima colonna del montaggio (la data prima delle note)
--  Un preventivo vero
--  13) EMESSO: competenza_mese si', si sceglie accettando (D-9)
--  14) ... e fatturazione_immediata anche (la governa il guard di commessa)
--  15) ... il cliente no
--  16) ... il termine di pagamento no
--  17) ... la validita' no
--  18) l'accettazione del backend passa: competenza e modalita' scritte in EMESSO, poi ACCETTATO
--  19) ACCETTATO: le note si'
--  20) la capability generica dice le stesse cose: competenza_mese aperta in ACCETTATO, chiusa in EVASO
--  21) ⭐ capability e lock: su ogni colonna nominata del preventivo, in EMESSO, la capability e
--      l'UPDATE rispondono uguale
--  22) i codici nuovi sono a catalogo, CONFLITTO_STATO, con il messaggio
--  La terza copia ritirata: le capability leggono la testata dal montaggio (20261010-70 … -76)
--  23) ordine CONFERMATO: can_edit_testata vero (le note si cambiano), e fra i non modificabili
--      ci sono data e termine ma non le note
--  24) ordine ANNULLATO: can_edit_testata falso, e le note sono fra i non modificabili
--  25) preventivo ACCETTATO: competenza_mese modificabile, il cliente no; in testa la prima colonna
--      del montaggio (rev 2026-10-18: la lista «sempre» del preventivo e' ritirata)
--  26) nessuna capability porta piu' una lista scritta a mano dei campi bloccati fuori bozza
--
-- Scopo:
--  - ⭐ 3 e' il cuore: la matrice attesa la scrive il test, dal brief, e
--    la confronta con quello che il montaggio dice (letto dal lettore della
--    fase 1, che decide con la funzione del trigger). Una colonna nominata
--    in piu' o in meno la rompe (1), uno stato spostato la rompe (3).
--  - ⭐ i documenti si COSTRUISCONO: nascono in bozza, prendono le righe,
--    cambiano stato con le transizioni vere (dbops.fn_pgtap_porta_a_stato).
--  - i rifiuti si leggono dal canale CONSTRAINT (P0001 + codice).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- =========================================================
-- Le decisioni del brief, scritte dal test (non lette dal montaggio):
--   una riga per colonna nominata, con gli stati (oltre alla bozza) in cui
--   resta aperta. Vuoto = bloccata fuori bozza. '-' = ferma sempre, bozza
--   compresa (rev 2026-10-18: utility ed emittente di preventivo, offerta e
--   contratto, §8.7 di brief-db-indirizzi-documento-seguono-il-cliente).
-- =========================================================
CREATE TEMP TABLE _atteso (tabella text, colonna text, aperta_in text);
INSERT INTO _atteso VALUES
  -- DDT (D-1, D-5, D-10)
  ('ddt','data',''),('ddt','valuta_id',''),('ddt','anno',''),('ddt','serie',''),('ddt','registro_id',''),
  ('ddt','causale_trasporto_id',''),('ddt','billing_account_id',''),('ddt','utility_id',''),
  ('ddt','destinatario_soggetto_ruolo_id',''),('ddt','magazzino_id',''),('ddt','magazzino_arrivo_id',''),
  ('ddt','emittente_fiscale_id',''),('ddt','sorgente_tipo_id',''),('ddt','sorgente_uid',''),
  ('ddt','mittente_soggetto_ruolo_id','CONSEGNATO,EMESSO,SPEDITO'),('ddt','vettore_soggetto_ruolo_id','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','aspetto_bene_id','CONSEGNATO,EMESSO,SPEDITO'),('ddt','modalita_addebito_trasporto_id','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','num_colli','CONSEGNATO,EMESSO,SPEDITO'),('ddt','peso_lordo','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','peso_netto','CONSEGNATO,EMESSO,SPEDITO'),('ddt','volume','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','targa','CONSEGNATO,EMESSO,SPEDITO'),('ddt','autista','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','data_ora_partenza','CONSEGNATO,EMESSO,SPEDITO'),('ddt','data_ora_consegna_prev','CONSEGNATO,EMESSO,SPEDITO'),
  ('ddt','tracking_code','CONSEGNATO,EMESSO,SPEDITO'),('ddt','meta','CONSEGNATO,EMESSO,SPEDITO'),
  -- reso (D-2, D-5, D-10)
  ('resi','data',''),('resi','valuta_id',''),('resi','anno',''),('resi','registro_id',''),
  ('resi','magazzino_id',''),('resi','emittente_fiscale_id',''),('resi','sorgente_tipo_id',''),('resi','sorgente_uid',''),
  ('resi','meta','CONFERMATO'),
  -- ordine (D-3, D-5, D-7, D-10)
  ('ordini','data',''),('ordini','valuta_id',''),('ordini','tasso_cambio',''),('ordini','anno',''),
  ('ordini','serie',''),('ordini','registro_id',''),('ordini','utility_id',''),('ordini','emittente_fiscale_id',''),
  ('ordini','modalita_pagamento_id',''),('ordini','termine_pagamento_id',''),('ordini','agente_soggetto_ruolo_id',''),
  ('ordini','fatturazione_trigger',''),('ordini','sorgente_tipo_id',''),('ordini','sorgente_uid',''),
  ('ordini','documento_origine_tipo',''),('ordini','documento_origine_id',''),
  ('ordini','meta','ALLOCATO,CONFERMATO,CONSEGNATO,EVASO,PARZIALMENTE_EVASO,SPEDITO'),
  -- preventivo (D-3, D-6, D-7, D-9, D-10)
  ('preventivi','data',''),('preventivi','valuta_id',''),('preventivi','rev',''),
  ('preventivi','billing_account_id',''),('preventivi','istanza_utility_id',''),('preventivi','utility_id','-'),
  ('preventivi','emittente_fiscale_id','-'),('preventivi','termine_pagamento_id',''),
  ('preventivi','validita_dal',''),('preventivi','validita_al',''),
  ('preventivi','competenza_mese','ACCETTATO,EMESSO'),('preventivi','meta','ACCETTATO,EMESSO'),
  -- offerta (D-3, D-6, D-7, D-10)
  ('offerte_commerciali','valuta_id',''),('offerte_commerciali','billing_account_id',''),
  ('offerte_commerciali','istanza_utility_id',''),('offerte_commerciali','utility_id','-'),
  ('offerte_commerciali','emittente_fiscale_id','-'),('offerte_commerciali','listino_id',''),
  ('offerte_commerciali','listino_versione_id',''),('offerte_commerciali','tipo_variazione_globale',''),
  ('offerte_commerciali','valore_variazione_globale',''),('offerte_commerciali','validita_dal',''),
  ('offerte_commerciali','validita_al',''),
  ('offerte_commerciali','meta','ACCETTATA,EMESSA'),('offerte_commerciali','motivazione_rifiuto','ACCETTATA,EMESSA'),
  -- contratto (D-3, D-5, D-6, D-7, D-10)
  ('contratti','data',''),('contratti','valuta_id',''),('contratti','billing_account_id',''),
  ('contratti','istanza_utility_id',''),('contratti','utility_id','-'),('contratti','emittente_fiscale_id','-'),
  ('contratti','listino_id',''),('contratti','listino_versione_id',''),('contratti','tipo_variazione_globale',''),
  ('contratti','valore_variazione_globale',''),('contratti','ambito',''),('contratti','valido_dal',''),
  ('contratti','parent_contratto_id',''),('contratti','categoria_cliente_id_snapshot',''),('contratti','offerta_id',''),('contratti','sorgente_tipo_id',''),
  ('contratti','sorgente_uid',''),
  ('contratti','valido_al','ATTIVO'),('contratti','codice_cig','ATTIVO'),('contratti','codice_cup','ATTIVO'),
  ('contratti','codice_commessa','ATTIVO'),('contratti','meta','ATTIVO');

-- Gli stati di ogni documento, dal suo catalogo.
CREATE TEMP TABLE _stati AS
          SELECT 'ddt'::text AS tabella, codice_interno::text AS stato FROM config.stati_doc_ddt
UNION ALL SELECT 'resi', codice_interno FROM config.stati_doc_reso
UNION ALL SELECT 'ordini', codice_interno FROM config.stati_doc_ordini
UNION ALL SELECT 'preventivi', codice_interno FROM config.stati_doc_preventivi
UNION ALL SELECT 'offerte_commerciali', codice_interno FROM config.stati_doc_offerte
UNION ALL SELECT 'contratti', codice_interno FROM config.stati_doc_contratti;

-- Le colonne che il montaggio nomina, lette dal lettore della fase 1.
CREATE TEMP TABLE _nominate AS
SELECT x.tabella, e ->> 'colonna' AS colonna, m.regola ->> 'stato_bozza' AS bozza
  FROM (VALUES ('ddt'), ('resi'), ('ordini'), ('preventivi'), ('offerte_commerciali'), ('contratti')) AS x(tabella)
  CROSS JOIN LATERAL script.fn_doc_lock_montaggi(('vendite.' || x.tabella)::regclass) AS m
  CROSS JOIN LATERAL jsonb_array_elements(m.regola -> 'colonne') AS e
 WHERE m.regola ->> 'building_block' = 'TESTATA';

-- =========================================================
-- 1-4) I montaggi
-- =========================================================
SELECT is(
    (SELECT string_agg(coalesce(a.tabella, n.tabella) || '.' || coalesce(a.colonna, n.colonna)
                       || CASE WHEN a.colonna IS NULL THEN ' (in piu'')' ELSE ' (manca)' END, ', ')
       FROM _atteso a
       FULL JOIN _nominate n ON n.tabella = a.tabella AND n.colonna = a.colonna
      WHERE a.colonna IS NULL OR n.colonna IS NULL),
    NULL,
    '1) le sei testate nominano esattamente le colonne decise nel brief'
);

SELECT is(
    (SELECT string_agg(n.tabella || '.' || n.colonna, ', ')
       FROM _nominate n
       LEFT JOIN pg_attribute a ON a.attrelid = ('vendite.' || n.tabella)::regclass
                               AND a.attname = n.colonna AND NOT a.attisdropped
      WHERE a.attname IS NULL OR a.attgenerated <> ''),
    NULL,
    '2) ogni colonna nominata esiste, e nessuna e'' generata (in un BEFORE una generata vale NULL e sembrerebbe cambiata sempre)'
);

SELECT is(
    (SELECT string_agg(a.tabella || '.' || a.colonna || '@' || s.stato, ', ' ORDER BY 1)
       FROM _atteso a
       JOIN _stati s ON s.tabella = a.tabella
       JOIN (SELECT DISTINCT tabella, bozza FROM _nominate) b ON b.tabella = a.tabella
      WHERE script.fn_doc_colonna_modificabile(('vendite.' || a.tabella)::regclass, a.colonna::name, s.stato)
            IS DISTINCT FROM (a.aperta_in IS DISTINCT FROM '-'
                              AND (s.stato = b.bozza
                                   OR coalesce(s.stato = ANY (string_to_array(nullif(a.aperta_in, ''), ',')), false)))),
    NULL,
    '3) la matrice: ogni colonna nominata, in ogni stato del catalogo, e'' aperta solo in bozza e negli stati decisi (§9.2); le ferme sempre in nessuno'
);

SELECT is(
    (SELECT count(*)::integer FROM pg_proc WHERE proname = 'trgfn_contratti_lock_post_attivazione')
    || '|' ||
    (SELECT string_agg(t.tgname, ',' ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.contratti'::regclass
        AND t.tgname IN ('trg_contratti_a05_lock_fuori_bozza_upd', 'trg_contratti_a10_guard_listino_documento_upd')),
    '0|trg_contratti_a05_lock_fuori_bozza_upd,trg_contratti_a10_guard_listino_documento_upd',
    '4) il lock post-attivazione e'' ritirato; il lock di testata (a05) parla prima del guard del listino (a10)'
);

-- =========================================================
-- Il mondo: due ordini e un preventivo, nati in bozza con una riga
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP testata dopo emissione');

DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m));
END $ctx$;

CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('PGT-TDE-S') AS id;

CREATE TEMP TABLE _k AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id;

CREATE TEMP TABLE _doc (chiave text PRIMARY KEY, id bigint);

DO $fixture$
DECLARE
    c    record;
    k    record;
    v_id bigint;
BEGIN
    SELECT * INTO c FROM _m;
    SELECT * INTO k FROM _k;

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
            (ordine_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa, prezzo_unitario, iva_id)
        VALUES (v_id, 1, (SELECT id FROM _art), 'Riga pgTAP', 2, 2, 10, k.iva_id);

        INSERT INTO _doc VALUES (CASE i WHEN 1 THEN 'ORD_CONF' ELSE 'ORD_ANN' END, v_id);
    END LOOP;

    INSERT INTO vendite.preventivi
        (numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
         billing_account_id, data, emittente_fiscale_id, valuta_id)
    VALUES
        ('PGT-TDE-' || substring(md5(clock_timestamp()::text) FOR 6),
         (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         c.utility_id, c.istanza_utility_id, c.billing_account_id,
         script.fn_data_operativa(), c.emittente_fiscale_id, k.valuta_id)
    RETURNING id INTO v_id;

    INSERT INTO vendite.preventivi_righe
        (preventivo_id, articolo_id, quantita, qta_operativa, prezzo_unitario, iva_id, ordine)
    VALUES (v_id, (SELECT id FROM _art), 2, 2, 10, k.iva_id, 1);

    INSERT INTO _doc VALUES ('PREV', v_id);

    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT id FROM _doc WHERE chiave = 'ORD_CONF'), 'CONFERMATO');
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', (SELECT id FROM _doc WHERE chiave = 'ORD_ANN'), 'ANNULLATO');
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_id, 'EMESSO');
END
$fixture$;

CREATE FUNCTION pg_temp.doc(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT id FROM _doc WHERE chiave = p $f$;

-- =========================================================
-- 5-12) Un ordine vero
-- =========================================================
SELECT is(pg_temp.esito(format('UPDATE vendite.ordini SET data = data + 1 WHERE id = %s', pg_temp.doc('ORD_CONF'))),
          'E_DOC_IDENTITA_FUORI_BOZZA', '5) ordine CONFERMATO: la data non cambia (identita'')');

SELECT is(pg_temp.esito(format($$UPDATE vendite.ordini
                                    SET termine_pagamento_id = (SELECT t.id FROM config.termini_pagamento t
                                                                 WHERE t.id IS DISTINCT FROM ordini.termine_pagamento_id
                                                                 ORDER BY t.id LIMIT 1)
                                  WHERE id = %s$$, pg_temp.doc('ORD_CONF'))),
          'E_DOC_CONDIZIONI_FUORI_BOZZA', '6) ordine CONFERMATO: il termine di pagamento non cambia (condizioni)');

SELECT is(pg_temp.esito(format($$UPDATE vendite.ordini
                                    SET utility_id = (SELECT u.id FROM config.utilities u
                                                       WHERE u.id IS DISTINCT FROM ordini.utility_id
                                                       ORDER BY u.id LIMIT 1)
                                  WHERE id = %s$$, pg_temp.doc('ORD_CONF'))),
          'E_DOC_CLIENTE_FUORI_BOZZA', '7) ordine CONFERMATO: la utility non cambia (cliente)');

SELECT is(pg_temp.esito(format('UPDATE vendite.ordini SET sorgente_uid = gen_random_uuid() WHERE id = %s', pg_temp.doc('ORD_CONF'))),
          'E_DOC_SORGENTE_FUORI_BOZZA', '8) ordine CONFERMATO: la sorgente non cambia');

SELECT is(pg_temp.esito(format($$UPDATE vendite.ordini SET meta = coalesce(meta, '{}'::jsonb) || '{"nota":"pgTAP"}' WHERE id = %s$$,
                               pg_temp.doc('ORD_CONF'))),
          'PASSA', '9) ordine CONFERMATO: le note si scrivono');

SELECT is(pg_temp.esito(format('UPDATE vendite.ordini SET imponibile_tot = imponibile_tot WHERE id = %s; SELECT vendite.fn_ricalcola_totali_ordine(%s)',
                               pg_temp.doc('ORD_ANN'), pg_temp.doc('ORD_ANN'))),
          'PASSA', '10) anche su un ordine ANNULLATO i totali li riscrive il database: colonne non nominate');

SELECT is(pg_temp.esito(format($$UPDATE vendite.ordini SET meta = coalesce(meta, '{}'::jsonb) || '{"nota":"pgTAP"}' WHERE id = %s$$,
                               pg_temp.doc('ORD_ANN'))),
          'E_DOC_CHIUSO', '11) ordine ANNULLATO: nemmeno le note, il documento e'' chiuso');

SELECT is(pg_temp.esito(format($$UPDATE vendite.ordini SET meta = '{"x":1}', data = data + 1 WHERE id = %s$$,
                               pg_temp.doc('ORD_ANN'))),
          'E_DOC_IDENTITA_FUORI_BOZZA', '12) ordine ANNULLATO, data e note insieme: parla la prima del montaggio (la data)');

-- =========================================================
-- 13-21) Un preventivo vero, EMESSO
-- =========================================================
SELECT is(pg_temp.esito(format($$UPDATE vendite.preventivi SET competenza_mese = date_trunc('month', script.fn_data_operativa())::date WHERE id = %s$$,
                               pg_temp.doc('PREV'))),
          'PASSA', '13) preventivo EMESSO: competenza_mese si sceglie accettando, quindi si cambia (D-9)');

SELECT is(pg_temp.esito(format('UPDATE vendite.preventivi SET fatturazione_immediata = NOT coalesce(fatturazione_immediata, false) WHERE id = %s',
                               pg_temp.doc('PREV'))),
          'PASSA', '14) preventivo EMESSO: anche fatturazione_immediata (la governa il guard di commessa, non il lock)');

SELECT is(pg_temp.esito(format($$UPDATE vendite.preventivi
                                    SET billing_account_id = (SELECT b.id FROM anagrafiche.billing_account b
                                                               WHERE b.id <> preventivi.billing_account_id ORDER BY b.id LIMIT 1)
                                  WHERE id = %s$$, pg_temp.doc('PREV'))),
          'E_DOC_CLIENTE_FUORI_BOZZA', '15) preventivo EMESSO: il cliente non cambia (D-6)');

SELECT is(pg_temp.esito(format($$UPDATE vendite.preventivi
                                    SET termine_pagamento_id = (SELECT t.id FROM config.termini_pagamento t
                                                                 WHERE t.id IS DISTINCT FROM preventivi.termine_pagamento_id
                                                                 ORDER BY t.id LIMIT 1)
                                  WHERE id = %s$$, pg_temp.doc('PREV'))),
          'E_DOC_CONDIZIONI_FUORI_BOZZA', '16) preventivo EMESSO: il termine di pagamento non cambia (D-3)');

SELECT is(pg_temp.esito(format('UPDATE vendite.preventivi SET validita_al = coalesce(validita_al, script.fn_data_operativa()) + 30 WHERE id = %s',
                               pg_temp.doc('PREV'))),
          'E_DOC_CONDIZIONI_FUORI_BOZZA', '17) preventivo EMESSO: la validita'' non cambia (D-3)');

SELECT is(pg_temp.esito(format($$UPDATE vendite.preventivi
                                    SET fatturazione_immediata = true,
                                        competenza_mese = date_trunc('month', script.fn_data_operativa())::date
                                  WHERE id = %s;
                                 SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi', %s, 'ACCETTATO')$$,
                               pg_temp.doc('PREV'), pg_temp.doc('PREV'))),
          'PASSA', '18) l''accettazione come la fa il backend: competenza e modalita'' scritte in EMESSO, poi ACCETTATO');

SELECT is(pg_temp.esito(format($$UPDATE vendite.preventivi SET meta = coalesce(meta, '{}'::jsonb) || '{"nota":"pgTAP"}' WHERE id = %s$$,
                               pg_temp.doc('PREV'))),
          'PASSA', '19) preventivo ACCETTATO: le note si scrivono');

SELECT is(
    ARRAY[script.fn_doc_colonna_modificabile('vendite.preventivi'::regclass, 'competenza_mese', 'ACCETTATO'),
          script.fn_doc_colonna_modificabile('vendite.preventivi'::regclass, 'competenza_mese', 'EVASO')],
    ARRAY[true, false],
    '20) la capability generica: competenza_mese aperta in ACCETTATO, chiusa in EVASO'
);

-- 21) Su ogni colonna nominata del preventivo, nello stato in cui e' ora
--     (ACCETTATO): l'UPDATE della sola colonna passa se e solo se la
--     capability dice aperta. Il valore nuovo e' il vecchio cambiato senza
--     violare tipi: si riscrive con se stesso via jsonb e un marcatore, quindi
--     si prova la DECISIONE del lock, non i vincoli della colonna.
CREATE FUNCTION pg_temp.prova_colonna(p_tab regclass, p_id bigint, p_col text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_stato text; v_cap boolean; v_esito text; v_nullo boolean;
BEGIN
    -- Una colonna gia' NULL non cambierebbe: non si puo' provare cosi'.
    EXECUTE format('SELECT %I IS NULL FROM %s WHERE id = $1', p_col, p_tab) INTO v_nullo USING p_id;
    IF v_nullo THEN
        RETURN NULL;
    END IF;
    SELECT t.stato INTO v_stato FROM script.fn_get_stato_testata_documento('PREVENTIVO', p_id) t;
    v_cap := script.fn_doc_colonna_modificabile(p_tab, p_col::name, v_stato);
    -- Un cambio vero e innocuo: la colonna a NULL e ritorno, dentro un
    -- sotto-blocco che si annulla. Il lock guarda il cambio, non il valore.
    BEGIN
        EXECUTE format('UPDATE %s SET %I = NULL WHERE id = $1', p_tab, p_col) USING p_id;
        v_esito := 'PASSA';
        RAISE EXCEPTION USING ERRCODE = 'P0099', MESSAGE = 'annulla';
    EXCEPTION
        WHEN SQLSTATE 'P0099' THEN NULL;
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS v_esito = CONSTRAINT_NAME;
            -- Un NOT NULL o un CHECK non e' il lock: la colonna la si prova
            -- solo se a rifiutare e' un codice di lock.
            IF coalesce(v_esito, '') NOT IN ('E_DOC_IDENTITA_FUORI_BOZZA', 'E_DOC_CONDIZIONI_FUORI_BOZZA',
                                             'E_DOC_CLIENTE_FUORI_BOZZA', 'E_DOC_SORGENTE_FUORI_BOZZA',
                                             'E_DOC_CHIUSO', 'E_DOC_EMITTENTE_FUORI_BOZZA',
                                             'E_DOC_EMITTENTE_IMMUTABILE', 'E_DOC_UTILITY_IMMUTABILE') THEN
                v_esito := 'NON_PROVABILE';
            END IF;
    END;
    RETURN CASE
             WHEN v_esito = 'NON_PROVABILE' THEN NULL
             WHEN v_cap = (v_esito = 'PASSA') THEN NULL
             ELSE p_col || ':cap=' || v_cap || ',lock=' || v_esito
           END;
END
$f$;

SELECT is(
    (SELECT string_agg(r, ', ')
       FROM (SELECT pg_temp.prova_colonna('vendite.preventivi'::regclass, pg_temp.doc('PREV'), n.colonna) AS r
               FROM _nominate n
              WHERE n.tabella = 'preventivi') x
      WHERE r IS NOT NULL),
    NULL,
    '21) preventivo ACCETTATO: su ogni colonna nominata, capability e lock rispondono uguale'
);

SELECT is(
    (SELECT string_agg(c.codice || ':' || c.classe || ':' || (m.messaggio IS NOT NULL)::text, ',' ORDER BY c.codice)
       FROM config.codici_errore c
       LEFT JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice IN ('E_DOC_IDENTITA_FUORI_BOZZA', 'E_DOC_CONDIZIONI_FUORI_BOZZA', 'E_DOC_CLIENTE_FUORI_BOZZA',
                         'E_DOC_SORGENTE_FUORI_BOZZA', 'E_DOC_CHIUSO')),
    'E_DOC_CHIUSO:CONFLITTO_STATO:true,E_DOC_CLIENTE_FUORI_BOZZA:CONFLITTO_STATO:true,E_DOC_CONDIZIONI_FUORI_BOZZA:CONFLITTO_STATO:true,'
    || 'E_DOC_IDENTITA_FUORI_BOZZA:CONFLITTO_STATO:true,E_DOC_SORGENTE_FUORI_BOZZA:CONFLITTO_STATO:true',
    '22) i cinque codici nuovi sono a catalogo, CONFLITTO_STATO, col messaggio'
);

-- =========================================================
-- 23-26) Le capability leggono la testata dal montaggio
-- =========================================================
CREATE FUNCTION pg_temp.cap_testata(p_cap jsonb) RETURNS text
LANGUAGE sql IMMUTABLE AS $f$
    SELECT (p_cap ->> 'can_edit_testata') || '|'
           || (p_cap -> 'non_editable_fields' ? 'data')::text || '|'
           || (p_cap -> 'non_editable_fields' ? 'termine_pagamento_id')::text || '|'
           || (p_cap -> 'non_editable_fields' ? 'meta')::text
$f$;

SELECT is(pg_temp.cap_testata(script.fn_available_actions_ordine(pg_temp.doc('ORD_CONF'))),
          'true|true|true|false',
          '23) ordine CONFERMATO: testata modificabile (le note), data e termine fra i non modificabili, le note no');

SELECT is(pg_temp.cap_testata(script.fn_available_actions_ordine(pg_temp.doc('ORD_ANN'))),
          'false|true|true|true',
          '24) ordine ANNULLATO: testata non modificabile, e anche le note fra i non modificabili');

SELECT is(
    (SELECT (c ->> 'can_edit_testata') || '|' || (c -> 'non_editable_fields' -> 0 ->> 0) || '|'
            || (c -> 'non_editable_fields' ? 'competenza_mese')::text || '|'
            || (c -> 'non_editable_fields' ? 'billing_account_id')::text
       FROM (SELECT script.fn_available_actions_preventivo(pg_temp.doc('PREV')) AS c) x),
    -- rev 2026-10-18: la capability del preventivo non ha piu' colonne
    --   «sempre» sue (20261018-68): la utility ferma la dice il montaggio, e
    --   in testa c'e' la prima colonna del montaggio, la data.
    'true|data|false|true',
    '25) preventivo ACCETTATO: competenza_mese modificabile (D-9), il cliente no; in testa la prima colonna del montaggio'
);

SELECT is(
    (SELECT string_agg(p.proname, ',' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname LIKE 'fn_available_actions_%'
        AND p.prosrc ~ '(c_non_edit_tutti|c_non_edit_attivo|c_non_edit_extra)'),
    NULL,
    '26) nessuna capability porta piu'' le liste a mano dei campi bloccati fuori bozza: le dice il montaggio'
);

SELECT * FROM finish();
ROLLBACK;
