-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): famiglie di prova nate come sorgenti; DDT_VENDITA; test 11 sulla serie, test 20 sul guard (E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA), test 25 su una sorgente di prova su acquisti.ordini (L2c-1).
-- pgTAP test per Zero ERP
-- Test: il CRUD delle FAMIGLIE DI DOCUMENTO — i tre guard, le due porte del
--       provisioning, la madre e la superficie di lettura.
--       vendite.trgfn_famiglie_documento_guard_riferimenti   (20260901-13)
--       script.fn_check_famiglia_documento_disattivabile     (20260901-14)
--       vendite.trgfn_famiglie_documento_guard_disattivazione(20260901-15)
--       script.fn_check_famiglia_..._struttura_modificabile  (20260901-16)
--       vendite.trgfn_famiglie_documento_guard_struttura     (20260901-17)
--       vendite.fn_provision_registri*                       (20260901-18)
--       vendite.fn_crea_famiglia_documento                   (20260901-19)
--       vendite.vw_famiglie_documento_lista                  (20260901-20)
--       lock su codice_interno                               (20260901-21)
--       Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11
-- ------------------------------------------------------------
-- Elenco test (plan 28):
--  1) ⭐ Il trigger dei riferimenti NOMINA colonna_serie nella lista UPDATE OF
--  2) ⛔ Una colonna_serie che non esiste sul documento e' rifiutata
--  3) ⛔ ...e una che esiste ma NON discrimina il numero pure, con codice suo
--  4) ⭐ Il gemello positivo: la serie vera passa
--  5) ⭐ Una famiglia SPENTA puo' nominare riferimenti morti (e' storia)
--  6) ⛔ Non si spegne una famiglia con registri attivi
--  7) ⭐ Il gemello positivo: una famiglia senza figli si spegne
--  8) ⭐ Riaccendere e' sempre lecito
--  9) ⛔ La struttura non si cambia su una famiglia con registri
-- 10) ⭐ Il gemello positivo: senza registri la struttura si cambia
-- 11) ⭐⭐ L'ORDINE DEI GUARD: parla `chiave_struttura`, non `riferimenti`
-- 12) ⛔ codice_interno e' bloccato dal lock automatico
-- 13) ⭐ Il provisioning per famiglia da' un registro a ogni emittente...
-- 14) ⭐ ...con la FORMA dichiarata dalla famiglia
-- 15) ⭐ ...ed e' idempotente
-- 16) ⛔ Una famiglia SPENTA non provisiona niente
-- 17) ⛔ La madre rifiuta un riferimento inesistente...
-- 18) ⭐⭐ ...e NON lascia dietro la famiglia a meta' (l'atomicita')
-- 19) ⭐⭐ DERIVATO: ogni campo_sorgente a catalogo esiste nella vista
-- 20) ⛔ Due famiglie ATTIVE non nominano la stessa tabella
-- 21) ⭐ ...ma una RITIRATA si': il vincolo e' parziale, ed e' voluto
-- 22) ⭐⭐ DERIVATO: `ammette_regole_fiscali` e' vera esattamente sulla FATTURA
-- 23) ⭐⭐ ...e i DUE check che lo decidono nominano lo stesso letterale
-- 24) ⛔ La dichiarazione e' rifiutata su una famiglia non fiscale
-- 25) ⭐ rev 2026-09-14 (P-9): la madre ACCETTA una famiglia senza billing account e la
--     salva NULL — l'ordine di acquisto, la cui controparte non e' un cliente
-- 26) ⭐ ...e normalizza la stringa vuota a NULL, come per la serie
-- 27) ⭐ le due funzioni della storia emittente REGGONO una famiglia senza BA: la
--     saltano nella query che sceglie, e il format() non vede mai un NULL
-- 28) ⛔ ...e il guard di struttura la conta ancora fra le colonne immutabili:
--     NULL -> valore su una famiglia con registri e' un cambio, e viene rifiutato
--
-- Scopo:
--   ⭐ IL TEST CHE CONTA E' IL 19, ed e' DERIVATO. Gli altri provano un
--   comportamento; quello prova il CONTRATTO fra il catalogo delle liste e la
--   proiezione — «<ListaConfigurabile> legge data[campo_sorgente], e il
--   renderer di export fa lo stesso». Un rename nella vista non rompe niente
--   di visibile: fa uscire una cella vuota e una colonna vuota nel file.
--
--   ⭐⭐ E IL 18 E' L'ALTRO: prova che la madre non lascia una famiglia senza
--   registri. Una famiglia a meta' non fallisce — promette un documento che non
--   si numerera' mai, e nessun vincolo lo dice.
--
--   ⚠️ I gemelli positivi (4, 7, 8, 10) non sono di cortesia: senza, un guard
--   che rifiutasse SEMPRE passerebbe i test negativi esattamente come quello
--   giusto.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che il CRUD sia raggiungibile dal backend.
--   I GRANT ci sono, ma l'endpoint non esiste ancora (§11.10, BE-F4).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(28);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ La famiglia di prova punta a una tabella VUOTA (vendite.fatture_sdi) e
--   non a una dei documenti: serve una famiglia che si possa spegnere, e tutte
--   e cinque le tabelle dei documenti hanno righe numerate. ⛔ Non e' un trucco
--   per far passare il test: e' il caso «famiglia appena nata, nessun
--   documento», che e' esattamente quello che il CRUD produrra'.
-- ⚠️ Le due colonne nominate esistono davvero su quella tabella: il guard dei
--   riferimenti le verifica, e una fixture che non le rispettasse non
--   entrerebbe nemmeno.
CREATE TEMP TABLE tmp_fam AS
SELECT 'PGTAP-FAM'::varchar   AS codice,
       'vendite'::text        AS sch,
       'fatture_sdi'::text    AS tab,
       'identificativo_sdi'::text AS col_num,
       'fattura_id'::text     AS col_ba,
       (SELECT count(*) FROM anagrafiche.emittenti_fiscali) AS n_emittenti;

-- ⭐ rev 2026-10-20 (2c, G-5): una famiglia E' una sorgente (FK
--   fk_famiglie_documento_sorgenti) e la sua tabella e' la target_table della
--   sorgente. Le famiglie di prova nascono prima come sorgenti, ciascuna con la
--   tabella che serve al suo caso (NULL = il riferimento che manca).
DO $sorgenti$ BEGIN
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-FAM', 'vendite.fatture_sdi'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-MORTA');
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-ATOM');
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-DDT2', 'vendite.ddt'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-DDT3', 'vendite.ddt'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-ACQ', 'acquisti.ordini'::regclass);
    PERFORM dbops.fn_pgtap_crea_sorgente('PGTAP-ACQ-VUOTA', 'acquisti.ordini'::regclass);
END $sorgenti$;

-- ============================================================
-- 1) ⭐ Il trigger deve NOMINARE colonna_serie
-- ============================================================
-- ⚠️ Sembra un test sul nulla e non lo e': fino al 2026-09-01 la lista
--   `UPDATE OF` non conteneva colonna_serie, quindi la funzione validava una
--   colonna su cui non veniva MAI chiamata. Verde in ogni prova che passasse
--   dalle altre colonne, muta proprio sul caso per cui esiste.
SELECT matches(
    (SELECT pg_get_triggerdef(oid) FROM pg_trigger
      WHERE tgrelid = 'vendite.famiglie_documento'::regclass
        AND tgname  = 'trg_famiglie_documento_a10_guard_riferimenti_ins_upd'),
    'colonna_serie',
    '1) Il trigger dei riferimenti nomina colonna_serie nella lista UPDATE OF');

-- ============================================================
-- 2/3/4/5) ⛔ Il guard dei riferimenti
-- ============================================================
PREPARE serie_inesistente AS
UPDATE vendite.famiglie_documento SET colonna_serie = 'colonna_che_non_esiste'
 WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_ok(
    'serie_inesistente', 'P0001',
    NULL,
    '2) Una colonna_serie che non esiste sul documento e'' rifiutata');

-- ⚠️ `causale_trasporto_id` esiste su vendite.ddt ma non sta in nessun vincolo
--   di unicita' col numero: e' il caso «nome giusto che non basta».
PREPARE serie_non_discrimina AS
UPDATE vendite.famiglie_documento SET colonna_serie = 'causale_trasporto_id'
 WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_ok(
    'serie_non_discrimina', 'P0001',
    NULL,
    '3) ...e una che esiste ma NON discrimina il numero pure');

SELECT lives_ok(
    $$UPDATE vendite.famiglie_documento SET colonna_serie = 'serie' WHERE codice_interno = 'DDT_VENDITA'$$,
    '4) Il gemello positivo: la serie vera passa');

-- ⭐ Una famiglia spenta puo' nominare quello che vuole: e' storia, non
--   configurazione. Si crea spenta apposta, per non toccare le cinque vere.
SELECT lives_ok(
    $$INSERT INTO vendite.famiglie_documento
          (codice_interno, descrizione, colonna_numero,
           colonna_billing_account, colonna_serie, attivo, user_insert)
      VALUES ('PGTAP-MORTA', 'Famiglia ritirata',
              'numero', 'billing_account_id', 'serie', FALSE, 'pgtap')$$,
    '5) Una famiglia SPENTA puo'' nominare riferimenti che non esistono piu''');

-- ============================================================
-- 6/7/8) ⛔ Lo spegnimento
-- ============================================================
PREPARE spegni_ddt AS
UPDATE vendite.famiglie_documento SET attivo = FALSE WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_ok(
    'spegni_ddt', 'P0001',
    NULL,
    '6) Non si spegne una famiglia che ha ancora registri attivi');

-- La famiglia di prova: nessun registro, nessun documento numerato.
INSERT INTO vendite.famiglie_documento
    (codice_interno, descrizione, colonna_numero,
     colonna_billing_account, prefisso_default, lunghezza_default, user_insert)
SELECT f.codice, 'Famiglia pgTAP', f.col_num, f.col_ba, 'PGT', 9, 'pgtap'
  FROM tmp_fam f;

SELECT lives_ok(
    $$UPDATE vendite.famiglie_documento SET attivo = FALSE WHERE codice_interno = 'PGTAP-FAM'$$,
    '7) Il gemello positivo: una famiglia senza registri e senza documenti si spegne');

SELECT lives_ok(
    $$UPDATE vendite.famiglie_documento SET attivo = TRUE WHERE codice_interno = 'PGTAP-FAM'$$,
    '8) Riaccendere e'' sempre lecito: rimette in gioco un presidio, non lo toglie');

-- ============================================================
-- 9/10/11) ⛔ La struttura, e l'ordine dei guard
-- ============================================================
PREPARE cambia_struttura_ddt AS
UPDATE vendite.famiglie_documento SET colonna_serie = NULL WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_ok(
    'cambia_struttura_ddt', 'P0001',
    NULL,
    '9) La struttura non si cambia su una famiglia che ha gia'' dei registri');

SELECT lives_ok(
    $$UPDATE vendite.famiglie_documento SET colonna_numero = 'nome_file'
       WHERE codice_interno = 'PGTAP-FAM'$$,
    '10) Il gemello positivo: senza registri la struttura si cambia');

-- ⭐⭐ L'ORDINE DEI GUARD, e si prova sulla FRASE.
-- ⚠️ rev 2026-10-20 (2c): la tabella non e' piu' una colonna della famiglia (la
--   dice la sorgente). Lo stesso conflitto si costruisce con una colonna_serie
--   che non esiste, su una famiglia con registri: due guard hanno qualcosa da
--   dire, `riferimenti` (la colonna non c'e') e `chiave_struttura` (quella
--   colonna non si cambia affatto). I BEFORE ROW
--   scattano in ordine alfabetico, e il nome `chiave` esiste per far parlare il
--   secondo. Se un domani qualcuno rinomina il trigger, questo test diventa
--   rosso — che e' esattamente cio' che deve fare.
PREPARE sposta_tabella_ddt AS
UPDATE vendite.famiglie_documento SET colonna_serie = 'colonna_che_non_esiste' WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_like(
    'sposta_tabella_ddt',
    '%non si modificano%',
    '11) Su una serie inesistente sotto un registro parla il guard della CHIAVE, non quello dei riferimenti');

-- ============================================================
-- 12) ⛔ Il lock su codice_interno
-- ============================================================
PREPARE rinomina_codice AS
UPDATE vendite.famiglie_documento SET codice_interno = 'PGTAP-RINOMINATA'
 WHERE codice_interno = 'PGTAP-FAM';

SELECT throws_ok(
    'rinomina_codice', 'P0001',
    NULL,
    '12) codice_interno non si rinomina: lo blocca il lock automatico');

-- ============================================================
-- 13/14/15/16) ⭐ Le due porte del provisioning
-- ============================================================
SELECT is(
    (SELECT vendite.fn_provision_registri_famiglia('PGTAP-FAM')),
    (SELECT n_emittenti::integer FROM tmp_fam),
    '13) Il provisioning per famiglia da'' un registro a OGNI emittente');

SELECT results_eq(
    $$SELECT DISTINCT r.prefisso::text, r.lunghezza_numero
        FROM vendite.registri_fatturazione r
       WHERE r.famiglia_documento = 'PGTAP-FAM'$$,
    $$VALUES ('PGT'::text, 9)$$,
    '14) ...e i registri nascono con la FORMA dichiarata dalla famiglia');

SELECT is(
    (SELECT vendite.fn_provision_registri_famiglia('PGTAP-FAM')),
    0,
    '15) ...ed e'' idempotente: la seconda chiamata non crea niente');

-- ⚠️ Si spengono prima i registri, altrimenti e' il guard del test 6 a
--   rifiutare — e si proverebbe quello, non questo.
UPDATE vendite.registri_fatturazione SET attivo = FALSE WHERE famiglia_documento = 'PGTAP-FAM';
UPDATE vendite.famiglie_documento    SET attivo = FALSE WHERE codice_interno     = 'PGTAP-FAM';
DELETE FROM vendite.registri_fatturazione WHERE famiglia_documento = 'PGTAP-FAM';

SELECT is(
    (SELECT vendite.fn_provision_registri_famiglia('PGTAP-FAM')),
    0,
    '16) Una famiglia SPENTA non provisiona nessun registro');

-- ============================================================
-- 17/18) ⭐⭐ L'ATOMICITA' DELLA MADRE
-- ============================================================
-- ⛔ E' il test che giustifica la madre: se la creazione e il provisioning non
--   fossero una cosa sola, un fallimento a meta' lascerebbe una famiglia senza
--   registri — cioe' un documento promesso che non si numerera' mai, e che
--   nessun vincolo segnala.
-- ⚠️ Il fallimento si costruisce con un riferimento inesistente, che e' il modo
--   in cui la seconda meta' della madre puo' saltare per davvero.
SELECT throws_ok(
    $$SELECT * FROM vendite.fn_crea_famiglia_documento(
          'PGTAP-ATOM', 'Famiglia atomica', 'numero', 'billing_account_id')$$,
    'P0001',
    NULL,
    '17) La madre rifiuta un riferimento inesistente');

SELECT is(
    (SELECT count(*)::int FROM vendite.famiglie_documento WHERE codice_interno = 'PGTAP-ATOM'),
    0,
    '18) ...e NON lascia dietro la famiglia a meta''');

-- ============================================================
-- 19) ⭐⭐ DERIVATO — il contratto fra catalogo e proiezione
-- ============================================================
-- ⭐ Nessun elenco a mano: i campo_sorgente si leggono dal catalogo, le colonne
--   dalla vista dichiarata in `vista_sql`. Una colonna nuova a catalogo, o un
--   rename nella vista, fanno rosso PRIMA del merge.
-- ⚠️ Il difetto che presidia non fallisce a runtime: la cella esce vuota e
--   l'export scrive una colonna vuota con la sua intestazione.
-- 🔴 IL PREDICATO SI SCRIVE COME LO SCRIVE IL GUARD, non come lo promette la
--   DDL. Il commento di ui.lista_colonna dice «campo_sorgente NULL per
--   tipo_colonna=azione», ma il loader di Liquibase scrive la STRINGA VUOTA:
--   in questo database le colonne con campo_sorgente NULL sono ZERO, e le 31
--   colonne `azione` hanno tutte ''. Un test scritto sulla promessa della DDL
--   (`campo_sorgente IS NOT NULL`) cerca la colonna `azioni` dentro la vista e
--   fallisce — trovato lanciandolo come applicazione, dopo il migrate.
-- ⭐ Qui si escludono le stesse cose che esclude
--   ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente: le colonne `azione` e
--   quelle senza sorgente. Due predicati sulla stessa invariante, prima o poi,
--   dissentono — e a dissentire per primo e' stato questo.
SELECT is(
    (SELECT count(*)::int
       FROM ui.lista_definizione d
       JOIN ui.lista_colonna c ON c.lista_id = d.id AND c.attivo
      WHERE d.codice = 'vendite.famiglie_documento'
        AND c.tipo_colonna <> 'azione'
        AND COALESCE(btrim(c.campo_sorgente), '') <> ''
        AND NOT EXISTS (
            SELECT 1 FROM pg_attribute a
             WHERE a.attrelid = (d.schema_dati || '.' || d.vista_sql)::regclass
               AND NOT a.attisdropped
               AND a.attnum > 0
               AND a.attname = c.campo_sorgente)),
    0,
    '19) Ogni campo_sorgente del catalogo esiste davvero nella vista dichiarata');

-- ============================================================
-- 20/21) ⛔ Una tabella, una famiglia
-- ============================================================
-- ⭐ La decisione (Tid, 2026-09-01): la famiglia NON e' un modo di chiamare i
--   documenti, E' il tipo di documento — e il tipo di documento e' la tabella
--   in cui vive. Due righe sulla stessa tabella sono due nomi per la stessa
--   cosa, e il presidio sul cambio emittente conterebbe quei documenti DUE
--   VOLTE, elencandoli sotto due nomi diversi.
-- ⚠️ rev 2026-10-20 (2c): la regola era l'indice uq_famiglie_documento_tabella_attiva
--   (23505); dalla G-5 la tabella viene dalla sorgente e la regola sta nel guard dei
--   riferimenti, col codice E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA. Si prova sulla
--   frase, che nomina la famiglia che occupa gia' la tabella.
SELECT throws_like(
    $$INSERT INTO vendite.famiglie_documento
          (codice_interno, descrizione, colonna_numero,
           colonna_billing_account, colonna_serie, user_insert)
      VALUES ('PGTAP-DDT2', 'Un secondo nome per i ddt',
              'numero', 'billing_account_id', 'serie', 'pgtap')$$,
    '%gia'' numerata dalla famiglia attiva DDT_VENDITA%',
    '20) Due famiglie ATTIVE non possono numerare la stessa tabella');

-- ⭐ IL GEMELLO CHE SPIEGA IL PREDICATO: il vincolo e' PARZIALE su `attivo`, e
--   una famiglia ritirata NON tiene occupata la sua tabella. ⛔ Un UNIQUE pieno
--   sarebbe un cancello su uno stato persistente: la riga ritirata resta per
--   sempre (non si cancella), quindi nessun successore potrebbe mai nascere.
-- ⚠️ E' l'opposto di cio' che vale sui registri, dove `attivo = false` non
--   libera lo slot: la' lo slot e' la chiave del contatore.
SELECT lives_ok(
    $$INSERT INTO vendite.famiglie_documento
          (codice_interno, descrizione, colonna_numero,
           colonna_billing_account, colonna_serie, attivo, user_insert)
      VALUES ('PGTAP-DDT3', 'Un ddt ritirato',
              'numero', 'billing_account_id', 'serie', FALSE, 'pgtap')$$,
    '21) ...ma una famiglia RITIRATA si'': il vincolo e'' parziale, e non blocca per sempre');

-- ============================================================
-- 22/23/24) ⭐ La famiglia DICE se ammette le regole fiscali
-- ============================================================
-- ⭐ La colonna esiste per togliere due letterali 'FATTURA' scritti a mano
--   fuori dal database (il service dei registri e le costanti del frontend).
--   ⛔ Ma una dichiarazione libera accanto a un CHECK che dice la stessa cosa
--   e' una seconda verita' che puo' contraddirlo: qui si verifica che non lo
--   faccia — sui DATI (22) e sulla STRUTTURA (23).
SELECT is(
    (SELECT count(*)::int
       FROM vendite.famiglie_documento f
      WHERE f.ammette_regole_fiscali <> (f.codice_interno = 'FATTURA')),
    0,
    '22) `ammette_regole_fiscali` e'' vera esattamente sulla famiglia FATTURA');

-- ⚠️ Il presidio vero e' questo: i due CHECK nominano lo STESSO letterale, e il
--   giorno che la fattura smettera' di essere l'unica si cambiano INSIEME.
--   Se qualcuno ne tocca uno solo, questo test diventa rosso — che e'
--   esattamente cio' che deve fare.
SELECT is(
    (SELECT count(*)::int
       FROM pg_constraint
      WHERE conname IN ('chk_registri_fatturazione_famiglia_regole_fattura',
                        'chk_famiglie_documento_regole_fiscali_solo_fattura')
        AND pg_get_constraintdef(oid) LIKE '%FATTURA%'),
    2,
    '23) ...e i due CHECK che decidono cosa e'' fiscale nominano lo stesso letterale');

PREPARE dichiara_ddt_fiscale AS
UPDATE vendite.famiglie_documento SET ammette_regole_fiscali = TRUE
 WHERE codice_interno = 'DDT_VENDITA';

SELECT throws_ok(
    'dichiara_ddt_fiscale', '23514',
    NULL,
    '24) Una famiglia non fiscale non puo'' dichiarare di ammettere le regole fiscali');

-- ============================================================
-- 25-28) ⭐ P-9 — la famiglia SENZA billing account (20260914-07 → -11)
-- ============================================================
-- ⛔ Il primo documento senza billing account e' l'ordine di acquisto: la sua
--   controparte e' un soggetto_ruolo. Fino al 14-09 la madre lo rifiutava con
--   E_VENDITE_VALIDATION e campo = colonna_billing_account, e il guard cercava
--   su pg_attribute una colonna che non deve esistere. La forma e' quella di
--   colonna_serie: il vuoto e' una dichiarazione.
-- ⚠️ La tabella e' quella VERA del caso d'uso e non ha ancora una famiglia
--   attiva (uq_famiglie_documento_tabella_attiva). Il provisioning dei
--   registri parte come per ogni famiglia: qui non e' il soggetto, e il
--   ROLLBACK lo disfa.
CREATE TEMP TABLE _fam_noba AS
SELECT famiglia_id, codice_interno, registri_creati
  FROM vendite.fn_crea_famiglia_documento(
       -- rev 2026-10-20 (2c): una sorgente di PROVA su acquisti.ordini. ⚠️ Non la
       --   sorgente vera ORDINE_ACQUISTO: il codice del registro provvisionato prende
       --   le prime tre lettere della famiglia (vendite.fn_codice_registro_provisionato)
       --   e ORD collide col registro di ORDINE_VENDITA. Difetto latente del modello,
       --   registrato nel brief (L2c-1, §13.3-bis), non di questo test.
       p_codice_interno        => 'PGTAP-ACQ',
       p_descrizione           => 'Ordine di acquisto (pgTAP, senza billing account)',
       p_colonna_numero        => 'numero',
       p_colonna_billing_account => NULL);

SELECT is(
    (SELECT f.colonna_billing_account IS NULL AND f.attivo
       FROM vendite.famiglie_documento f
      WHERE f.id = (SELECT famiglia_id FROM _fam_noba)),
    true,
    '25) La madre accetta una famiglia SENZA billing account e la salva NULL (l''ordine di acquisto)');

-- ⚠️ Spenta, per non collidere sulla tabella con la 25: qui il soggetto e' la
--   normalizzazione, non il guard (che una famiglia spenta non attraversa).
-- ⚠️ In due istruzioni: una riga scritta da una funzione nello stesso
--   statement non e' visibile alla scansione di quello statement.
CREATE TEMP TABLE _fam_vuota AS
SELECT famiglia_id
  FROM vendite.fn_crea_famiglia_documento(
           'PGTAP-ACQ-VUOTA', 'Stessa cosa, con la stringa vuota',
           'numero', '   ', NULL, NULL, 7, false);

SELECT is(
    (SELECT f.colonna_billing_account IS NULL
       FROM vendite.famiglie_documento f
      WHERE f.id = (SELECT famiglia_id FROM _fam_vuota)),
    true,
    '26) ...e normalizza la stringa vuota a NULL, come per la serie: un '''' salvato sarebbe una colonna che si chiama cosi''');

-- ⭐ Il punto in cui il difetto avrebbe morso: le due funzioni compongono SQL
--   dinamico con %I, e format('%I', NULL) solleva un errore di PostgreSQL senza
--   codice di dominio. Con la famiglia senza BA ATTIVA nel catalogo, il giro
--   della storia deve passarci sopra senza fiatare. Il BA e' un id qualunque:
--   il giro e' sulle famiglie, non sui documenti.
SELECT lives_ok(
    $$SELECT anagrafiche.fn_ba_ha_storia_emittente(
            (SELECT COALESCE(max(id), 1) FROM anagrafiche.billing_account)),
            count(*)
       FROM anagrafiche.fn_get_storia_emittente_ba(
            (SELECT COALESCE(max(id), 1) FROM anagrafiche.billing_account))$$,
    '27) fn_ba_ha_storia_emittente e fn_get_storia_emittente_ba reggono una famiglia attiva senza billing account');

-- ⛔ La famiglia della 25 ha appena ricevuto i suoi registri (ne ha uno per
--   emittente): cambiare colonna_billing_account da NULL a un valore e' un
--   cambio di struttura a registri vivi, e il guard lo rifiuta con IS DISTINCT
--   FROM. Un guard che confrontasse con `=` lascerebbe passare il NULL.
PREPARE noba_cambia_struttura AS
UPDATE vendite.famiglie_documento
   SET colonna_billing_account = 'soggetto_ruolo_id'
 WHERE id = (SELECT famiglia_id FROM _fam_noba)
   AND (SELECT registri_creati FROM _fam_noba) > 0;

SELECT CASE
    WHEN (SELECT registri_creati FROM _fam_noba) > 0
    THEN throws_ok('EXECUTE noba_cambia_struttura', 'P0001', NULL,
         '28) NULL -> valore su una famiglia con registri e'' un cambio di struttura, e viene rifiutato')
    ELSE skip('28) nessun emittente: la famiglia non ha registri e il guard di struttura non ha niente da difendere', 1)
END;

SELECT * FROM finish();
ROLLBACK;
