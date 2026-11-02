-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_raise_primo_motivo_se_presente  (20260908-17)
--       Piano: brief-db-coda-primo-motivo-in-un-posto-solo, sezione 6 (P-1)
-- ------------------------------------------------------------
-- Elenco test (plan 15) — numerati come li stampa il TAP:
--  1) la funzione esiste con la firma a SEI parametri, nomi compresi
--  2) array vuoto        -> TACE
--  3) NULL               -> TACE
--  4) ⭐ non-array       -> RUMOROSO (22023): un contratto rotto non e' un «passa»
--  5) primo motivo       -> P0001 e il codice sul canale CONSTRAINT
--  6) i valori riempiono i segnaposto (la frase e' composta)
--  7) `valori` ASSENTE   -> non esplode, il codice esce lo stesso
--  8) ⭐ `valori` = null JSON -> NON 22023: e' il caso che COALESCE non copre
--  9) `campo` NULL       -> il canale COLUMN resta vuoto
-- 10) `campo` passato    -> il canale COLUMN lo porta
-- 11) ⭐ p_campo VINCE su dettaglio.campo (l'ordine di fusione, dichiarato)
-- 12) p_campo NULL       -> dettaglio.campo passa: il ripiego non si rompe
-- 13) ⭐ il SECONDO motivo non esce MAI
-- 14) ⭐ p_context_extra arriva: il bersaglio esce sul canale DATATYPE
-- 15) ⭐⭐ `motivi` COMPLETO nel contesto del log
--
-- Scopo:
--   L'helper esiste per TRE convenzioni che, sbagliate, non fanno fallire
--   niente: quale elemento dell'array si solleva, quale tx_id si passa, come si
--   spacchetta il VARIADIC. Un test che si limitasse a «solleva» non ne
--   verificherebbe nessuna: `throws_ok(..., 'P0001')` e' vero anche se esce il
--   motivo sbagliato, col campo sbagliato e la frase non composta.
--   ⇒ Qui si guardano i CANALI dell'eccezione uno per uno.
--
--   ⭐ I DUE TEST CHE CONTANO, e vale la pena sapere perche':
--
--   • l'8. La normalizzazione di `valori` e' sul TIPO e non con COALESCE, e
--     sembra pedanteria finche' non si guarda cosa succede: `-> 'valori'` su
--     una chiave ASSENTE torna SQL NULL (e COALESCE lo vede), ma su una chiave
--     che porta `null` JSON torna 'null'::jsonb — che COALESCE NON vede e che
--     fa alzare 22023 a jsonb_array_elements_text. Quell'errore scatterebbe
--     DENTRO il percorso d'errore, quindi il RAISE di dominio non verrebbe
--     mai eseguito: si perderebbe il RIFIUTO, non solo la frase. Scritto con
--     COALESCE, questo test e' rosso.
--
--   • l'11. In jsonb `||` vince la DESTRA, e nei siti vivi convivevano i due
--     ordini opposti: due guard mettevano `campo` a sinistra — quindi a
--     vincere era `dettaglio` — e otto a destra. Non falliva mai, e si sarebbe
--     visto solo il giorno in cui un `dettaglio` porta una chiave `campo`.
--     Qui l'ordine e' UNO, e questo test e' cio' che lo tiene.
--
--   ⛔ COSA QUESTO FILE NON PROVA, ed e' scritto per non lasciarlo credere:
--   che il messaggio renda BENE. L'ordine dei `valori` vive dentro la
--   fn_check_*, e l'incidente del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA
--   («Registro X1» dove X1 era la serie) sarebbe passato di qui indisturbato.
--   Quella difesa e' un throws_like sulla frase resa, sito per sito (P-0).
--
--   ⚠️ Il codice usato come cavia e' E_REGISTRO_SERIE_NON_AMMESSA perche' ha
--   DUE segnaposto: con uno solo il test 6 non distinguerebbe «i valori
--   arrivano» da «ne arriva uno». ⭐ E se un giorno quel messaggio a catalogo
--   perdesse un segnaposto, il test 6 diventa ROSSO invece di indebolirsi in
--   silenzio: cerca ENTRAMBI i valori nella frase resa, non uno.
--
--   ⚠️ Il percorso d'errore SCRIVE nel log attraverso dblink, quindi le righe
--   di questa corsa NON tornano indietro col ROLLBACK. E' come per ogni test
--   di guard; il test 15 se ne serve, ed e' il motivo per cui usa un
--   function_name suo invece di uno di dominio.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture — nessun dato: la funzione e' pura rispetto alle tabelle.
--   Serve solo il banco che CATTURA i canali dell'eccezione: pgTAP sa dire
--   «ha sollevato» e «con quale SQLSTATE», non «con quale CONSTRAINT».
-- ============================================================

CREATE FUNCTION pg_temp.canali(
    -- ⛔ `p_motivi` e `p_campo` NUDI e non per fretta: il primo e' il valore di
    --   ritorno di una fn_check_* (nessuna colonna dietro), il secondo e' il
    --   NOME di una colonna e non il suo valore — la stessa ragione per cui
    --   script.fn_log_and_raise_error dichiara `v_campo text` e lo difende con
    --   un commento.
    p_motivi jsonb,
    p_campo  text  DEFAULT NULL,
    -- ⭐ Questo invece e' un frammento di dbops.error_log.context: si ancora,
    --   come nella funzione sotto esame.
    p_extra  dbops.error_log.context%TYPE DEFAULT '{}'::jsonb)
-- ⛔ RETURNS TABLE tutto `text`, ed e' l'unica forma giusta: queste cinque
--   colonne NON riflettono nessuna tabella — sono i canali dell'eccezione letti
--   da GET STACKED DIAGNOSTICS (RETURNED_SQLSTATE, MESSAGE_TEXT,
--   CONSTRAINT_NAME, COLUMN_NAME, PG_DATATYPE_NAME), che sono `text` per
--   definizione del linguaggio. Ancorarli direbbe una cosa falsa.
RETURNS TABLE(stato text, messaggio text, codice text, campo text, bersaglio text)
LANGUAGE plpgsql AS $banco$
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'pgtap',
        'test_fn_raise_primo_motivo_se_presente',
        p_motivi, p_campo, NULL::uuid, p_extra);
    -- Arrivare qui significa che ha TACIUTO.
    RETURN QUERY SELECT 'TACE'::text, NULL::text, NULL::text, NULL::text, NULL::text;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS
        stato     = RETURNED_SQLSTATE,
        messaggio = MESSAGE_TEXT,
        codice    = CONSTRAINT_NAME,
        campo     = COLUMN_NAME,
        bersaglio = PG_DATATYPE_NAME;
    RETURN NEXT;
END; $banco$;

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) La firma. ⚠️ Sei parametri e non quattro: `p_context_extra` c'e' dal primo
--    giorno perche' CREATE OR REPLACE non cambia la lista dei parametri, e
--    aggiungerlo dopo vorrebbe dire DROP + tutti i siti da ripuntare.
-- ⚠️ E si confronta la stringa CON I NOMI, perche'
--    pg_get_function_identity_arguments() li INCLUDE: scritta come
--    'text, text, jsonb, ...' questa asserzione e' rossa a vuoto — provato.
--    ⭐ E i nomi sono contratto quanto i tipi: `p_campo` e `p_context_extra`
--    si passano per nome nei siti che saltano i default.
-- ⭐ I %TYPE della firma NON si vedono da qui, e non e' un buco del test: in
--    firma si RISOLVONO alla CREATE (sono una fotografia), quindi dal catalogo
--    un `dbops.error_log.area%TYPE` e un `text` scritto a mano sono la stessa
--    cosa. L'ancoraggio si presidia rileggendo il sorgente, non da pg_proc.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'fn_raise_primo_motivo_se_presente'),
    'p_area text, p_funzione text, p_motivi jsonb, p_campo text, p_tx_id uuid, p_context_extra jsonb',
    'la firma e'' quella dichiarata: sei parametri, nell''ordine e coi nomi del brief');

-- ---- Le DUE uscite silenziose. ⛔ Non e' fail-open: «nessun motivo» e'
--      esattamente la risposta che dice *passa*. La terza forma - il non-array -
--      NON e' silenziosa, ed e' il test 4.
SELECT is((SELECT stato FROM pg_temp.canali('[]'::jsonb)),
          'TACE', 'array vuoto: non solleva');

SELECT is((SELECT stato FROM pg_temp.canali(NULL::jsonb)),
          'TACE', 'NULL: non solleva');

-- 4) ⭐ Il non-array NON e' una terza uscita silenziosa, ed e' una decisione:
--    NULL e `[]` sono «nessun motivo», ma un oggetto al posto di un array e' un
--    CONTRATTO ROTTO della check. Deve restare rumoroso — jsonb_array_length
--    alza 22023 da solo — perche' renderlo silenzioso vorrebbe dire togliere un
--    rifiuto senza far fallire niente: la stessa classe di difetto che questo
--    helper esiste per chiudere. ⛔ Se qualcuno «ripulisce» il guard con un
--    jsonb_typeof, questo test diventa rosso, ed e' il suo mestiere.
SELECT is((SELECT stato FROM pg_temp.canali('{"codice":"E_QUALCOSA"}'::jsonb)),
          '22023',
          'un oggetto al posto di un array: RUMOROSO (22023), non un «passa» silenzioso');

-- ---- Il sollevamento, canale per canale.
SELECT is(
    (SELECT stato || '|' || codice
       FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["FATTURA","X1"]}]'::jsonb)),
    'P0001|E_REGISTRO_SERIE_NON_AMMESSA',
    'solleva P0001 e il codice esce sul canale CONSTRAINT (contratto del 2026-08-05)');

-- 6) I valori riempiono i segnaposto. ⚠️ Il pattern non attraversa un `%s`:
--    si cercano i due valori nella frase resa, non la frase intera.
SELECT ok(
    (SELECT messaggio LIKE '%FATTURA%' AND messaggio LIKE '%X1%' AND messaggio NOT LIKE '%\%s%'
       FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["FATTURA","X1"]}]'::jsonb)),
    'i due valori del motivo riempiono i due segnaposto: la frase e'' composta');

-- 7) `valori` assente: il VARIADIC parte vuoto, la frase non si compone, ma il
--    RIFIUTO c'e' e il codice pure — che e' la cosa che non deve perdersi.
SELECT is(
    (SELECT codice FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA"}]'::jsonb)),
    'E_REGISTRO_SERIE_NON_AMMESSA',
    'valori assente: il rifiuto e il codice restano');

-- 8) ⭐ Il caso che COALESCE non copre. Scritto con COALESCE, qui esce 22023.
SELECT is(
    (SELECT stato || '|' || codice
       FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":null}]'::jsonb)),
    'P0001|E_REGISTRO_SERIE_NON_AMMESSA',
    'valori = null JSON: resta un errore di DOMINIO, non un 22023 dentro il percorso d''errore');

-- ---- Il canale COLUMN, cioe' quale input il frontend accende.
-- 9) ⚠️ Su un errore di classe TECNICO non c'e' nessun campo da accendere, e
--    promettere al client un input che non esiste e' peggio che tacere.
SELECT is(
    (SELECT coalesce(campo, '') FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"]}]'::jsonb, NULL)),
    '', 'p_campo NULL: il canale COLUMN resta vuoto');

SELECT is(
    (SELECT campo FROM pg_temp.canali('[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"]}]'::jsonb, 'serie_default')),
    'serie_default', 'p_campo passato: il canale COLUMN lo porta');

-- 11) ⭐ L'ordine di fusione. In jsonb `||` vince la destra: p_campo sta a
--     destra, quindi un `dettaglio` che portasse la stessa chiave NON vince.
SELECT is(
    (SELECT campo
       FROM pg_temp.canali(
           '[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"],"dettaglio":{"campo":"NON_QUESTO"}}]'::jsonb,
           'serie_default')),
    'serie_default',
    'ordine di fusione: p_campo vince su dettaglio.campo');

-- 12) ...e senza p_campo il `dettaglio` passa: l'helper non distrugge la
--     convenzione che c'era, la ordina.
SELECT is(
    (SELECT campo
       FROM pg_temp.canali(
           '[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"],"dettaglio":{"campo":"da_dettaglio"}}]'::jsonb,
           NULL)),
    'da_dettaglio',
    'p_campo NULL: dettaglio.campo arriva comunque al canale COLUMN');

-- 13) ⭐ Il primo e solo il primo. ⚠️ L'ordine dell'array e' il contratto della
--     check (§12.5.2): qui si prova che l'helper lo rispetta, non che sia
--     giusto — quello si decide nella check.
SELECT is(
    (SELECT codice
       FROM pg_temp.canali(
           '[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"]},
             {"codice":"E_CONFIG_MANCANTE","valori":["secondo"]}]'::jsonb)),
    'E_REGISTRO_SERIE_NON_AMMESSA',
    'con due motivi esce il PRIMO, mai il secondo');

-- 14) ⭐ p_context_extra arriva davvero al contesto, e si vede da un canale
--     STRUTTURATO invece che dal log: il bersaglio esce su DATATYPE nella
--     forma compatta TIPO:id.
SELECT is(
    (SELECT bersaglio
       FROM pg_temp.canali(
           '[{"codice":"E_REGISTRO_SERIE_NON_AMMESSA","valori":["A","B"]}]'::jsonb,
           NULL,
           '{"bersaglio":[{"tipo":"FATTURA","id":"820"}]}'::jsonb)),
    'FATTURA:820',
    'p_context_extra arriva al contesto: il bersaglio esce sul canale DATATYPE');

-- 15) ⭐⭐ L'elenco COMPLETO dei motivi viaggia nel contesto, anche quando la
--     frase ne nomina uno: e' cio' che permette al backend di mostrarli tutti.
--     ⚠️ Si legge dal log perche' il contesto non ha nessun altro sbocco — e
--     il log e' scritto via dblink, quindi e' committato e visibile da qui.
SELECT is(
    (SELECT jsonb_array_length(e.context -> 'motivi')
       FROM dbops.error_log e
      WHERE e.area = 'pgtap'
        AND e.function_name = 'test_fn_raise_primo_motivo_se_presente'
      ORDER BY e.id DESC
      LIMIT 1),
    1,
    'il contesto porta `motivi`, l''elenco completo che il backend puo'' mostrare');

SELECT * FROM finish();
ROLLBACK;
