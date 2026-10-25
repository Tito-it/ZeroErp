-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i due ordini in bozza con la
--   riga da dbops.fn_pgtap_crea_ordine_con_righe (DRAFT, trigger SPEDITO, 2 x 10 con
--   l'articolo e l'IVA del test); a mano restano solo le transizioni, che sono il caso.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
--
-- Test: il lettore del montaggio dei lock «si tocca solo in bozza» e la
--   capability della promessa di consegna (fase 1).
--   ChangeSet 20261010-60 … -67.
-- Brief: brief-db-testata-dopo-emissione (§5-bis, R-1 e R-2)
--
-- Elenco test (plan 30):
--  La grammatica (script.fn_doc_lock_regola, 20261010-60)
--   1) RIGHE: i sei argomenti, contati da 0 come TG_ARGV, e il codice di default (rev 2026-10-11)
--   2) RIGHE: con due argomenti, i default (DRAFT, TESTATA, nessuna eccezione)
--   3) RIGHE: colonne senza stati, un livello che non e' un livello, un argomento solo: tre montaggi sbagliati
--   4) TESTATA: le terne, nell'ordine, col codice e gli stati aperti (rev 2026-10-10, fase 2)
--   5) TESTATA: argomenti che non fanno terne, terne monche, un building block che non esiste: montaggi sbagliati
--  La decisione (script.fn_doc_lock_colonna_bloccata, 20261010-61)
--   6) RIGHE: in bozza passa tutto, anche la riga intera
--   7) RIGHE: fuori bozza la riga intera (INSERT, DELETE) si ferma
--   8) RIGHE: nello stato dell'eccezione passano le ammesse e le tecniche, non le altre
--   9) RIGHE: fuori dall'eccezione si ferma anche la colonna ammessa, e anche un UPDATE che non cambia niente
--  10) RIGHE: lo stato NULL non e' la bozza
--  11) TESTATA: parla la prima colonna nominata nell'ordine del montaggio; le altre colonne sono libere;
--      una colonna con i suoi stati e' aperta li' e ferma negli altri
--  12) un montaggio sbagliato non lascia passare niente
--  Il lettore (script.fn_doc_lock_montaggi, 20261010-62)
--  13) su ogni tabella col lock, la regola del lettore e' la grammatica sugli argomenti del trigger
--  14) un trigger disabilitato non si legge
--  15) le righe d'ordine: l'eccezione e' la promessa di consegna, negli stati da evadere
--  La check generica (script.fn_doc_colonna_modificabile, 20261010-63)
--  16) la promessa di consegna, stato per stato del catalogo: aperta in bozza e negli stati del montaggio
--  17) le altre domande: una colonna di riga chiusa, una colonna di testata nominata e una no, una tabella senza lock
--  I due building block sulla grammatica (20261010-64, -65), su un montaggio di prova
--  18) testata: la prima colonna nominata che cambia parla col suo codice
--  19) testata: una colonna non nominata passa, fuori bozza
--  20) testata: in bozza passa anche la colonna nominata
--  21) testata: montata su un evento che non e' UPDATE e' un errore di montaggio
--  La promessa di consegna di un ordine vero (20261010-66, -67)
--  22) DRAFT: la check dice si', la capability la spegne col motivo della bozza
--  23) CONFERMATO: check vuota, capability accesa senza motivo
--  24) ... e il lock lascia cambiare la sola data: capability e lock dicono la stessa cosa
--  25) ANNULLATO: un motivo, col codice del lock e i valori della sua frase
--  26) ... la capability spenta con quel motivo
--  27) ... e il lock rifiuta col codice del motivo: capability e lock dicono la stessa cosa
--  28) i valori del motivo sono quanti ne chiede il messaggio
--  29) la check: un ordine che non c'e' non ha risposta; un id non valido e' un errore
--  30) ⭐ nessuno stato scritto nella check e nella capability: stanno solo nel montaggio
--
-- Scopo:
--  - ⭐ i casi si COSTRUISCONO: il mondo, l'ordine nato in bozza con la riga,
--    le transizioni vere (dbops.fn_pgtap_porta_a_stato). I montaggi di prova
--    stanno su tabelle TEMPORANEE del ruolo che gira: un trigger su una
--    tabella del dominio lo monterebbe solo l'owner. Le righe temporanee
--    puntano a ordini veri, e i lettori DEFINER li risolvono come sulle
--    tabelle del dominio.
--  - ⭐ 24 e 27 sono il punto: la capability e il lock, sullo stesso ordine,
--    rispondono la stessa cosa — perche' leggono lo stesso montaggio con la
--    stessa grammatica e decidono con la stessa funzione (30 prova che la
--    check non ha una sua copia degli stati).
--  - ⭐ i rifiuti si leggono dal canale CONSTRAINT (contratto «P0001 +
--    CONSTRAINT = codice»), non dalla frase.
--  - ⚠️ 13 itera sui montaggi che esistono: sono STRUTTURA (codice del
--    database, uguale su ogni installazione), non dati.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(30);

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
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- La regola di un montaggio di prova, con gli argomenti contati da 0 come
-- TG_ARGV (righe) o da 1 come dbops.fn_trigger_argomenti (testata).
CREATE FUNCTION pg_temp.righe(VARIADIC p text[]) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $f$
    -- TG_ARGV parte da 0: la grammatica deve contare giusto lo stesso.
    SELECT script.fn_doc_lock_regola('RIGHE', ('[0:' || (cardinality(p) - 1) || ']=' || p::text)::text[])
$f$;

CREATE FUNCTION pg_temp.testata(VARIADIC p text[]) RETURNS jsonb
LANGUAGE sql IMMUTABLE AS $f$ SELECT script.fn_doc_lock_regola('TESTATA', p) $f$;

-- =========================================================
-- 1-5) La grammatica
-- =========================================================
SELECT is(
    pg_temp.righe('ORDINE_VENDITA', 'ordine_id', 'DRAFT', 'TESTATA', ' data_consegna_confermata ', 'CONFERMATO, PARZIALMENTE_EVASO')
      - 'colonne_tecniche',
    jsonb_build_object(
        'building_block', 'RIGHE', 'documento', 'ORDINE_VENDITA', 'colonna_fk', 'ordine_id',
        'stato_bozza', 'DRAFT', 'livello', 'TESTATA',
        'colonne_ammesse', jsonb_build_array('data_consegna_confermata'),
        'stati_ammessi',   jsonb_build_array('CONFERMATO', 'PARZIALMENTE_EVASO'),
        -- rev 2026-10-11 (20261011-21): il codice da sollevare, settimo
        -- argomento; senza, quello delle righe.
        'codice',          'E_RIGA_DOC_NON_BOZZA',
        'errore', NULL),
    '1) RIGHE: i sei argomenti contati da 0 come TG_ARGV, liste ripulite dagli spazi; il codice di default'
);

SELECT is(
    (SELECT r ->> 'stato_bozza' || '|' || (r ->> 'livello') || '|' || (r -> 'colonne_ammesse')::text
            || '|' || (r -> 'stati_ammessi')::text || '|' || coalesce(r ->> 'errore', 'ok')
       FROM (SELECT pg_temp.righe('DDT_VENDITA', 'ddt_id') AS r) x),
    'DRAFT|TESTATA|[]|[]|ok',
    '2) RIGHE: con due argomenti, bozza DRAFT, livello TESTATA, nessuna eccezione'
);

SELECT is(
    ARRAY[(pg_temp.righe('ORDINE_VENDITA', 'ordine_id', 'DRAFT', 'TESTATA', 'a') ->> 'errore') IS NOT NULL,
          (pg_temp.righe('ORDINE_VENDITA', 'ordine_id', 'DRAFT', 'NIPOTE') ->> 'errore') IS NOT NULL,
          (pg_temp.righe('ORDINE_VENDITA') ->> 'errore') IS NOT NULL,
          (pg_temp.righe('ORDINE_VENDITA', 'ordine_id', 'DRAFT', 'TESTATA', ',', 'CONFERMATO') ->> 'errore') IS NOT NULL],
    ARRAY[true, true, true, true],
    '3) RIGHE: colonne senza stati, un livello sconosciuto, un argomento solo, una lista di sole virgole: montaggi sbagliati'
);

SELECT is(
    pg_temp.testata('DDT_VENDITA', 'DRAFT', 'causale_trasporto_id', 'E_DDT_CAUSALE_IMMUTABILE', '',
                    ' tracking_code ', 'E_DOC_CHIUSO', 'EMESSO, SPEDITO'),
    jsonb_build_object(
        'building_block', 'TESTATA', 'documento', 'DDT_VENDITA', 'stato_bozza', 'DRAFT',
        'colonne', jsonb_build_array(
            -- rev 2026-10-18: ogni colonna porta ferma_sempre (la terna con '-',
            --   test-doc-emittente-utility-fermi-v1)
            jsonb_build_object('colonna', 'causale_trasporto_id', 'codice', 'E_DDT_CAUSALE_IMMUTABILE',
                               'ferma_sempre', false, 'stati_ammessi', '[]'::jsonb),
            jsonb_build_object('colonna', 'tracking_code', 'codice', 'E_DOC_CHIUSO',
                               'ferma_sempre', false, 'stati_ammessi', jsonb_build_array('EMESSO', 'SPEDITO'))),
        'errore', NULL),
    '4) TESTATA: le terne nell''ordine degli argomenti, col codice e gli stati in cui la colonna resta aperta (vuoti = bloccata)'
);

SELECT is(
    ARRAY[(pg_temp.testata('DDT_VENDITA', 'DRAFT', 'causale_trasporto_id') ->> 'errore') IS NOT NULL,
          (pg_temp.testata('DDT_VENDITA', 'DRAFT', 'a', 'E_X') ->> 'errore') IS NOT NULL,
          (pg_temp.testata('DDT_VENDITA', 'DRAFT', 'a', '', '') ->> 'errore') IS NOT NULL,
          (pg_temp.testata('DDT_VENDITA', 'DRAFT', ' ', 'E_X', '') ->> 'errore') IS NOT NULL,
          (script.fn_doc_lock_regola('NON_ESISTE', ARRAY['x']) ->> 'errore') IS NOT NULL],
    ARRAY[true, true, true, true, true],
    '5) TESTATA: argomenti che non fanno terne, una terna senza codice o senza colonna, un building block sconosciuto: montaggi sbagliati'
);

-- =========================================================
-- 6-12) La decisione
-- =========================================================
CREATE TEMP TABLE _r AS
SELECT pg_temp.righe('ORDINE_VENDITA', 'ordine_id', 'DRAFT', 'TESTATA', 'data_consegna_confermata', 'CONFERMATO,PARZIALMENTE_EVASO') AS ecc,
       pg_temp.righe('DDT_VENDITA', 'ddt_id') AS secca,
       pg_temp.testata('DDT_VENDITA', 'DRAFT', 'magazzino_id', 'E_DDT_MAGAZZINO_IMMUTABILE', '',
                       'causale_trasporto_id', 'E_DDT_CAUSALE_IMMUTABILE', '',
                       'tracking_code', 'E_DOC_CHIUSO', 'EMESSO,SPEDITO') AS tst;

SELECT is(
    (SELECT ARRAY[script.fn_doc_lock_colonna_bloccata(ecc, 'DRAFT', NULL),
                  script.fn_doc_lock_colonna_bloccata(ecc, 'DRAFT', ARRAY['quantita'])]
       FROM _r),
    ARRAY[NULL, NULL]::text[],
    '6) RIGHE: in bozza passa tutto, anche la riga intera'
);

SELECT is(
    (SELECT script.fn_doc_lock_colonna_bloccata(ecc, 'CONFERMATO', NULL) FROM _r),
    '*',
    '7) RIGHE: fuori bozza la riga intera (INSERT, DELETE) si ferma, anche nello stato dell''eccezione'
);

SELECT is(
    (SELECT ARRAY[coalesce(script.fn_doc_lock_colonna_bloccata(ecc, 'CONFERMATO', ARRAY['data_consegna_confermata']), 'passa'),
                  coalesce(script.fn_doc_lock_colonna_bloccata(ecc, 'PARZIALMENTE_EVASO', ARRAY['data_consegna_confermata', 'data_update', 'user_update', 'tx_id']), 'passa'),
                  coalesce(script.fn_doc_lock_colonna_bloccata(ecc, 'CONFERMATO', ARRAY['data_consegna_confermata', 'quantita']), 'passa'),
                  coalesce(script.fn_doc_lock_colonna_bloccata(ecc, 'CONFERMATO', ARRAY[]::text[]), 'passa')]
       FROM _r),
    ARRAY['passa', 'passa', 'quantita', 'passa'],
    '8) RIGHE: nello stato dell''eccezione passano la colonna ammessa e le tecniche (e un UPDATE che non cambia niente); un''altra colonna no'
);

SELECT is(
    (SELECT ARRAY[script.fn_doc_lock_colonna_bloccata(ecc, 'EVASO', ARRAY['data_consegna_confermata']),
                  script.fn_doc_lock_colonna_bloccata(ecc, 'EVASO', ARRAY['data_update']),
                  script.fn_doc_lock_colonna_bloccata(secca, 'EMESSO', ARRAY[]::text[])]
       FROM _r),
    ARRAY['data_consegna_confermata', '*', '*'],
    '9) RIGHE: fuori dall''eccezione si ferma anche la colonna ammessa, e anche un UPDATE che cambia solo colonne tecniche o niente'
);

SELECT is(
    (SELECT script.fn_doc_lock_colonna_bloccata(ecc, NULL, ARRAY['data_consegna_confermata']) FROM _r),
    'data_consegna_confermata',
    '10) RIGHE: lo stato NULL non e'' la bozza, e non e'' nell''eccezione'
);

SELECT is(
    (SELECT ARRAY[script.fn_doc_lock_colonna_bloccata(tst, 'EMESSO', ARRAY['causale_trasporto_id', 'magazzino_id']),
                  coalesce(script.fn_doc_lock_colonna_bloccata(tst, 'EMESSO', ARRAY['tracking_code', 'num_colli']), 'passa'),
                  coalesce(script.fn_doc_lock_colonna_bloccata(tst, 'DRAFT', ARRAY['magazzino_id']), 'passa'),
                  script.fn_doc_lock_colonna_bloccata(tst, NULL, ARRAY['causale_trasporto_id']),
                  coalesce(script.fn_doc_lock_colonna_bloccata(tst, 'SPEDITO', ARRAY['tracking_code']), 'passa'),
                  script.fn_doc_lock_colonna_bloccata(tst, 'ANNULLATO', ARRAY['tracking_code']),
                  script.fn_doc_lock_colonna_bloccata(tst, NULL, ARRAY['tracking_code'])]
       FROM _r),
    ARRAY['magazzino_id', 'passa', 'passa', 'causale_trasporto_id', 'passa', 'tracking_code', 'tracking_code'],
    '11) TESTATA: parla la prima nominata nell''ordine del montaggio; le non nominate sono libere; in bozza passa; una colonna con i suoi stati e'' aperta li'' e ferma negli altri'
);

SELECT is(
    ARRAY[script.fn_doc_lock_colonna_bloccata(pg_temp.righe('ORDINE_VENDITA'), 'DRAFT', ARRAY['quantita']),
          script.fn_doc_lock_colonna_bloccata(pg_temp.testata('DDT_VENDITA', 'DRAFT', 'a'), 'EMESSO', ARRAY['z']),
          script.fn_doc_lock_colonna_bloccata(NULL, 'DRAFT', NULL)],
    ARRAY['*', '*', '*'],
    '12) un montaggio sbagliato (o assente) non lascia passare niente, nemmeno in bozza'
);

-- =========================================================
-- 13-15) Il lettore
-- =========================================================
SELECT is(
    (SELECT count(*)::integer
       FROM pg_trigger t
       JOIN pg_proc p ON p.oid = t.tgfoid
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('trgfn_doc_righe_lock_fuori_bozza', 'trgfn_doc_testata_lock_fuori_bozza')
        AND NOT t.tgisinternal
        AND NOT EXISTS (
              SELECT 1
                FROM script.fn_doc_lock_montaggi(t.tgrelid::regclass) AS m
               WHERE m.trigger_nome = t.tgname
                 AND m.regola = script.fn_doc_lock_regola(
                       CASE p.proname WHEN 'trgfn_doc_righe_lock_fuori_bozza' THEN 'RIGHE' ELSE 'TESTATA' END,
                       dbops.fn_trigger_argomenti(t.tgargs))
                 AND m.regola ->> 'errore' IS NULL)),
    0,
    '13) ogni lock montato si legge, e il lettore da'' la regola della grammatica sui suoi argomenti, senza errori'
);

CREATE TEMP TABLE _tmp_spento (id bigint PRIMARY KEY, ordine_id bigint, a int);
CREATE TRIGGER trg_tmp_spento_a05_lock
    BEFORE INSERT OR UPDATE OR DELETE ON _tmp_spento FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE_VENDITA', 'ordine_id');

CREATE TEMP TABLE _letti_prima AS
SELECT count(*)::integer AS n FROM script.fn_doc_lock_montaggi('_tmp_spento'::regclass);

ALTER TABLE _tmp_spento DISABLE TRIGGER trg_tmp_spento_a05_lock;

SELECT is(
    (SELECT n FROM _letti_prima) || '|'
    || (SELECT count(*)::integer FROM script.fn_doc_lock_montaggi('_tmp_spento'::regclass)),
    '1|0',
    '14) un trigger disabilitato non ferma niente, e il lettore non lo legge (prima di disabilitarlo lo leggeva)'
);

SELECT is(
    (SELECT (m.regola -> 'colonne_ammesse')::text || ' in ' || (m.regola -> 'stati_ammessi')::text
       FROM script.fn_doc_lock_montaggi('vendite.ordini_righe'::regclass) AS m),
    '["data_consegna_confermata"] in ["CONFERMATO", "PARZIALMENTE_EVASO"]',
    '15) le righe d''ordine: un lock solo, e l''eccezione e'' la promessa di consegna negli stati da evadere (20261008-90)'
);

-- =========================================================
-- 16-17) La check generica
-- =========================================================
SELECT is(
    (SELECT string_agg(s.codice_interno, ',' ORDER BY s.codice_interno)
       FROM config.stati_doc_ordini s
      WHERE script.fn_doc_colonna_modificabile('vendite.ordini_righe'::regclass,
                                               'data_consegna_confermata', s.codice_interno)),
    'CONFERMATO,DRAFT,PARZIALMENTE_EVASO',
    '16) la promessa di consegna, per ogni stato del catalogo: aperta in bozza e negli stati del montaggio, chiusa negli altri'
);

SELECT is(
    ARRAY[script.fn_doc_colonna_modificabile('vendite.ordini_righe'::regclass, 'quantita', 'CONFERMATO'),
          script.fn_doc_colonna_modificabile('vendite.ddt'::regclass, 'causale_trasporto_id', 'EMESSO'),
          script.fn_doc_colonna_modificabile('vendite.ddt'::regclass, 'tracking_code', 'EMESSO'),
          script.fn_doc_colonna_modificabile('config.stati_doc_ordini'::regclass, 'descrizione', 'QUALUNQUE')],
    ARRAY[false, false, true, true],
    '17) chiusa la quantita'' di una riga confermata e la causale di una bolla emessa; aperta una colonna che il lock della bolla non nomina; una tabella senza lock risponde come il database'
);

-- =========================================================
-- Il mondo e due ordini veri, nati in bozza con una riga
-- =========================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP lock montaggio');

DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m));
END $ctx$;

CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-LM-S') AS id;

CREATE TEMP TABLE _k AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
         ORDER BY i.id LIMIT 1) AS iva_id;

-- Due ordini del cliente del mondo, in bozza con una riga: uno si conferma, uno
-- si annulla (le transizioni sono il caso, piu' sotto).
CREATE TEMP TABLE _doc AS
SELECT x.chiave, b.ordine_id, b.ordine_riga_id AS riga_id
  FROM (VALUES (1, 'CONF'), (2, 'ANN')) x(n, chiave)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_ordine_con_righe('pgTAP lock montaggio ' || x.chiave, 'DRAFT',
           p_billing_account_id   => (SELECT billing_account_id FROM _m),
           p_fatturazione_trigger => 'SPEDITO',
           p_righe => jsonb_build_array(jsonb_build_object(
               'articolo_id', (SELECT id FROM _art), 'quantita', 2, 'prezzo', 10,
               'iva_id', (SELECT iva_id FROM _k), 'descrizione', 'Riga pgTAP'))) b
 ORDER BY x.n;

CREATE FUNCTION pg_temp.ord(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT ordine_id FROM _doc WHERE chiave = p $f$;
CREATE FUNCTION pg_temp.riga(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT riga_id FROM _doc WHERE chiave = p $f$;
CREATE FUNCTION pg_temp.cap(p text) RETURNS text
LANGUAGE sql STABLE AS $f$
    SELECT (c ->> 'can_edit_data_consegna_confermata') || '|'
           || coalesce(c ->> 'can_edit_data_consegna_confermata_reason', 'null') || '|'
           || coalesce(c ->> 'can_edit_data_consegna_confermata_reason_key', 'null')
      FROM (SELECT script.fn_available_actions_ordine(pg_temp.ord(p)) AS c) x
$f$;

-- =========================================================
-- 18-21) Il lock della testata sulla grammatica, su un montaggio di prova
--   La riga temporanea ha l'id di un ordine vero: il lettore DEFINER ne
--   legge lo stato come per vendite.ordini. 'CONF' e' ancora in DRAFT qui.
-- =========================================================
CREATE TEMP TABLE _tmp_testata (id bigint PRIMARY KEY, a int, b int, libera int);
INSERT INTO _tmp_testata VALUES (pg_temp.ord('CONF'), 0, 0, 0), (pg_temp.ord('ANN'), 0, 0, 0);

CREATE TRIGGER trg_tmp_testata_a05_lock
    BEFORE UPDATE ON _tmp_testata FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza(
        'ORDINE_VENDITA', 'DRAFT', 'b', 'E_DDT_CAUSALE_IMMUTABILE', '', 'a', 'E_DOC_EMITTENTE_FUORI_BOZZA', '');

DO $ann$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.ord('ANN'), 'ANNULLATO');
END $ann$;

SELECT is(
    pg_temp.esito(format('UPDATE _tmp_testata SET a = 1, b = 1 WHERE id = %s', pg_temp.ord('ANN'))),
    'E_DDT_CAUSALE_IMMUTABILE',
    '18) testata fuori bozza: cambiano due colonne nominate, parla la prima del montaggio col suo codice'
);

SELECT is(
    pg_temp.esito(format('UPDATE _tmp_testata SET libera = 1 WHERE id = %s', pg_temp.ord('ANN'))),
    'PASSA',
    '19) testata fuori bozza: una colonna che il montaggio non nomina passa'
);

SELECT is(
    pg_temp.esito(format('UPDATE _tmp_testata SET a = 2, b = 2 WHERE id = %s', pg_temp.ord('CONF'))),
    'PASSA',
    '20) testata in bozza: passano anche le colonne nominate'
);

CREATE TRIGGER trg_tmp_testata_a05_ins
    BEFORE INSERT ON _tmp_testata FOR EACH ROW
    EXECUTE FUNCTION vendite.trgfn_doc_testata_lock_fuori_bozza(
        'ORDINE_VENDITA', 'DRAFT', 'a', 'E_DOC_EMITTENTE_FUORI_BOZZA', '');

SELECT is(
    pg_temp.esito('INSERT INTO _tmp_testata VALUES (-1, 0, 0, 0)'),
    'E_DOC_RIGHE_LOCK_MONTAGGIO',
    '21) testata montata su INSERT: errore di montaggio, non di dato'
);

-- =========================================================
-- 22-30) La promessa di consegna di un ordine vero
-- =========================================================
SELECT is(
    script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('CONF'))::text || ' | ' || pg_temp.cap('CONF'),
    '[] | false|ORDINE_IN_BOZZA|vendite.ordini.data_consegna_confermata_reason.in_bozza',
    '22) DRAFT: il lock lascia cambiare la data (la riga intera si modifica), ma la capability spegne il verbo: in bozza la data si scrive dalla riga'
);

DO $conf$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.ord('CONF'), 'CONFERMATO');
END $conf$;

SELECT is(
    script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('CONF'))::text || ' | ' || pg_temp.cap('CONF'),
    '[] | true|null|null',
    '23) CONFERMATO: check vuota, capability accesa senza motivo'
);

SELECT is(
    pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 7 WHERE id = %s',
                         pg_temp.riga('CONF'))),
    'PASSA',
    '24) CONFERMATO: il lock lascia cambiare la sola data — capability e lock dicono la stessa cosa'
);

SELECT is(
    (SELECT m ->> 'codice' || '|' || (m ->> 'reason') || '|' || (m ->> 'reason_key') || '|'
            || (m -> 'dettaglio' ->> 'stato') || '|' || (m -> 'valori')::text
       FROM (SELECT script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('ANN')) -> 0 AS m,
                    jsonb_array_length(script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('ANN'))) AS n) x
      WHERE n = 1),
    'E_RIGA_DOC_NON_BOZZA|STATO_NON_AMMETTE|vendite.ordini.data_consegna_confermata_reason.stato_non_ammette|ANNULLATO|'
    || jsonb_build_array(
           (SELECT t.etichetta FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', pg_temp.ord('ANN')) t),
           'ANNULLATO', 'modificare')::text,
    '25) ANNULLATO: un motivo solo, col codice che il lock solleva e i valori della sua frase'
);

SELECT is(
    pg_temp.cap('ANN'),
    'false|STATO_NON_AMMETTE|vendite.ordini.data_consegna_confermata_reason.stato_non_ammette',
    '26) ANNULLATO: la capability spenta col primo motivo della check'
);

SELECT is(
    pg_temp.esito(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = script.fn_data_operativa() + 7 WHERE id = %s',
                         pg_temp.riga('ANN'))),
    script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('ANN')) -> 0 ->> 'codice',
    '27) ANNULLATO: il lock rifiuta col codice del motivo — capability e lock dicono la stessa cosa'
);

SELECT is(
    jsonb_array_length(script.fn_check_ordine_data_consegna_confermata(pg_temp.ord('ANN')) -> 0 -> 'valori'),
    (SELECT (length(me.messaggio) - length(replace(me.messaggio, '%s', ''))) / 2
       FROM config.messaggi_errore me
      WHERE me.codice = 'E_RIGA_DOC_NON_BOZZA' AND me.lingua = 'it'),
    '28) i valori del motivo sono quanti ne chiede il messaggio del codice'
);

SELECT is(
    coalesce(script.fn_check_ordine_data_consegna_confermata(
                 (SELECT coalesce(max(o.id), 0) + 1000000 FROM vendite.ordini o))::text, 'NULL')
    || ' | ' || pg_temp.esito('SELECT script.fn_check_ordine_data_consegna_confermata(0)'),
    'NULL | E_PARAMETRO_INVALIDO',
    '29) la check: un ordine che non c''e'' non ha risposta (non [], che vorrebbe dire si''); un id non valido e'' un errore'
);

SELECT is(
    (SELECT string_agg(p.proname, ',' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname IN ('fn_check_ordine_data_consegna_confermata', 'fn_available_actions_ordine',
                          'fn_doc_colonna_modificabile', 'fn_doc_lock_montaggi',
                          'fn_doc_lock_colonna_bloccata', 'fn_doc_lock_regola')
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ '''(PARZIALMENTE_EVASO|EVASO|ALLOCATO|SPEDITO|CONSEGNATO|FATTURATO)'''),
    NULL,
    '30) nessuno degli stati dell''ordine fuori dalla bozza e dall''annullo e'' scritto nel codice della check, della capability e dei lettori: gli stati stanno solo nel montaggio'
);

SELECT * FROM finish();
ROLLBACK;
