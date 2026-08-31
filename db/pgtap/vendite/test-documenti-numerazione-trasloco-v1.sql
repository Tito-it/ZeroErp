-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: P-2 / P-4 / P-5 — i documenti dopo il trasloco: registro, anno, forma
-- Oggetti:
--   vendite.trgfn_ddt_gen_numero_emesso        (20260831-08)
--   vendite.trgfn_ordini_gen_numero            (20260831-13)
--   vendite.fn_get_or_create_commessa          (20260831-16)
--   Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §3.6
-- ------------------------------------------------------------
-- Elenco test (plan 10):
-- 0) ⚠️ Precondizioni: la fixture non mente
-- 1) Il DDT emesso prende il registro DEL PROPRIO emittente
-- 2) ⭐⭐ L'ANNO SEGUE LA DATA DEL DOCUMENTO, non quella dell'INSERT
-- 3) La forma del numero DDT e' quella del catalogo dei formati
-- 4) L'ordine si numera all'INSERT, sul registro del proprio emittente
-- 5) ⭐ Il codice commessa e' CMM-<sigla>-<anno>-<9 cifre>
-- 6) ⭐ ...e la sigla dentro il codice e' QUELLA dell'emittente, non un'altra
-- 7) ⛔ Senza registro COMMESSA la commessa NON NASCE, e lo dice
-- 8) ⭐ Il RESO confermato prende numero, registro RESO e anno
-- 9) La forma del numero reso e' quella del catalogo dei formati
--
-- Scopo:
--   ⭐⭐ IL TEST 2 E' IL PIU' IMPORTANTE DEL FILE, e presidia una trappola
--   dichiarata prima di scrivere il cantiere: `vendite.ddt.anno` lo scriveva
--   il trigger di normalizzazione all'INSERT, da `CURRENT_DATE`, mentre il
--   contatore usa l'anno della DATA DEL DOCUMENTO. Sono due nozioni di «anno»
--   sulla stessa riga, e la UNIQUE usa la prima.
--   ⇒ Si costruisce il caso in cui divergono: un DDT nato con una data e
--   EMESSO con un'altra. Se l'anno seguisse l'INSERT, il numero girerebbe su
--   un contatore e la riga ne dichiarerebbe un altro — con la UNIQUE che
--   presidia il contatore sbagliato, in silenzio.
--
--   ⭐ IL TEST 6 NON E' UN DOPPIONE DEL 5. Il 5 prova che la forma ha quattro
--   pezzi; il 6 prova che il secondo pezzo e' la sigla GIUSTA. Un generatore
--   che ci mettesse una costante, o la sigla del primo emittente trovato,
--   passerebbe il 5 senza battere ciglio — ed e' proprio il difetto che
--   rendeva il vecchio codice commessa non attribuibile.
--
--   ⚠️ Il caso si FABBRICA: cercarlo fra i dati esistenti passerebbe a vuoto
--   in CI, dove il database e' ricostruito da zero.
-- ------------------------------------------------------------

-- =========================================================
-- Cleanup iniziale (idempotente, FUORI dalla transazione)
-- =========================================================
DO $$
BEGIN
    DELETE FROM vendite.ddt_indirizzi di
     WHERE di.ddt_id IN (SELECT d.id FROM vendite.ddt d
                          WHERE d.meta ->> 'test_scope' = 'pgtap_num_trasloco');
    DELETE FROM vendite.ddt_righe dr
     WHERE dr.ddt_id IN (SELECT d.id FROM vendite.ddt d
                          WHERE d.meta ->> 'test_scope' = 'pgtap_num_trasloco');
    DELETE FROM vendite.ddt d
     WHERE d.meta ->> 'test_scope' = 'pgtap_num_trasloco';

    DELETE FROM vendite.resi_righe rr
     WHERE rr.reso_id IN (SELECT re.id FROM vendite.resi re
                           WHERE re.meta ->> 'test_scope' = 'pgtap_num_trasloco');
    DELETE FROM vendite.resi re
     WHERE re.meta ->> 'test_scope' = 'pgtap_num_trasloco';

    DELETE FROM vendite.ordini_righe orr
     WHERE orr.ordine_id IN (SELECT o.id FROM vendite.ordini o
                              WHERE o.meta ->> 'test_scope' = 'pgtap_num_trasloco');
    DELETE FROM vendite.ordini o
     WHERE o.meta ->> 'test_scope' = 'pgtap_num_trasloco';
END;
$$;

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- =========================================================
-- Riferimenti — ogni scelta col suo ORDER BY
-- =========================================================
-- ⛔ L'EMITTENTE SI DERIVA DAL BILLING ACCOUNT, non si impone.
--   Prima questa fixture pretendeva che il BA appartenesse all'emittente
--   dell'operatore, e con zero righe `SELECT * INTO` lasciava ogni campo NULL:
--   il test moriva su un NOT NULL che non nominava la causa.
--   ⭐ Derivandolo, il DDT e' coerente col BA PER COSTRUZIONE — che e' anche
--   cio' che vendite.trgfn_ddt_guard_emittente_ba pretende.
CREATE TEMP TABLE tmp_num_refs AS
SELECT
    ba.id                                                    AS billing_account_id,
    ba.utility_id                                            AS utility_id,
    ba.soggetto_ruolo_id                                     AS soggetto_ruolo_id,
    ef.id                                                    AS emittente_fiscale_id,
    ef.soggetto_ruolo_id                                     AS emittente_sr_id,
    ef.codice                                                AS sigla,
    (SELECT a.id FROM catalogo.articoli a
      WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
      ORDER BY a.data_insert DESC NULLS LAST, a.id DESC LIMIT 1)          AS articolo_id,
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
    (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'DRAFT'  ORDER BY s.id LIMIT 1) AS stato_ddt_draft_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'EMESSO' ORDER BY s.id LIMIT 1) AS stato_ddt_emesso_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'SPEDITO' ORDER BY s.id LIMIT 1) AS stato_ddt_spedito_id,
    (SELECT s.id FROM config.stati_doc_ddt s
      WHERE s.codice_interno = 'CONSEGNATO' ORDER BY s.id LIMIT 1) AS stato_ddt_consegnato_id,
    (SELECT s.id FROM config.stati_doc_ordini s
      WHERE s.codice_interno = 'CONFERMATO' ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
    -- ⚠️ Qui l'aggancio e' su `codice` e NON su `codice_interno`, e non per
    --   scelta: config.causali_trasporto la colonna `codice_interno` non ce
    --   l'ha proprio. Resta quindi un aggancio FRAGILE — `codice` e'
    --   modificabile dall'utente, e un rename lo sgancia in silenzio — ed e'
    --   dichiarato qui invece di essere scoperto da chi vedra' il test
    --   diventare rosso senza capire perche'.
    (SELECT c.id FROM config.causali_trasporto c
      WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1)                   AS causale_vendita_id,
    (SELECT ti.id FROM config.tipi_indirizzi ti
      WHERE ti.codice_interno = 'CON' ORDER BY ti.id LIMIT 1)             AS tipo_ind_con_id,
    (SELECT so.id FROM config.sorgenti so
      WHERE so.codice_interno = 'DDT_VENDITA' AND so.attivo ORDER BY so.id LIMIT 1) AS sorgente_ddt_id,
    (SELECT s2.id FROM config.stati_doc_reso s2
      WHERE s2.codice_interno = 'DRAFT' ORDER BY s2.id LIMIT 1)           AS stato_reso_draft_id,
    (SELECT tr.id FROM config.tipi_reso tr
      WHERE tr.codice_interno = 'RESO_PER_RICONSEGNA' AND tr.attivo ORDER BY tr.id LIMIT 1) AS tipo_reso_id
  FROM anagrafiche.billing_account ba
  -- ⛔ `ef.soggetto_ruolo_id` e NON `ef.id`: anagrafiche.fn_get_emittente_fiscale_id
  --   restituisce il SOGGETTO_RUOLO dell'emittente, non la chiave di
  --   anagrafiche.emittenti_fiscali — il nome dice «fiscale_id» e trae in
  --   inganno. Agganciarla a `ef.id` non solleva niente: fa semplicemente
  --   zero righe, e la fixture muore molto piu' avanti su un NOT NULL che
  --   parla di tutt'altra colonna.
  JOIN anagrafiche.emittenti_fiscali ef
    ON ef.soggetto_ruolo_id = anagrafiche.fn_get_emittente_fiscale_id(ba.id)
 WHERE ba.utility_id IS NOT NULL
   AND ba.istanza_utility_id IS NOT NULL
   -- ⚠️ Il registro deve esserci gia': questo file prova la NUMERAZIONE, non
   --   il provisioning dei registri (che ha il suo posto altrove). Un BA il
   --   cui emittente non ha registro DDT farebbe fallire il test con l'errore
   --   giusto ma nel posto sbagliato.
   AND EXISTS (SELECT 1 FROM vendite.registri_fatturazione r
                WHERE r.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
                  AND r.famiglia_documento = 'DDT' AND r.attivo)
 ORDER BY ba.id
 LIMIT 1;

-- =========================================================
-- 0) ⚠️ La fixture non mente
-- =========================================================
-- ⛔ Senza questa riga, una fixture vuota non si vede: `SELECT * INTO` su zero
--   righe azzera ogni campo, e il file muore su un NOT NULL che parla di una
--   colonna invece che della causa.
-- ⭐ Non un AND monolitico: un booleano dice CHE manca qualcosa, non COSA — e
--   chi legge il rosso resta a indovinare. Qui l'asserzione NOMINA i campi
--   vuoti, e il diff di pgTAP li stampa.
SELECT is(
    COALESCE(
        (SELECT string_agg(x.campo, ', ' ORDER BY x.campo)
           FROM tmp_num_refs t,
                LATERAL (VALUES
                    ('billing_account_id',  t.billing_account_id  IS NULL),
                    ('utility_id',          t.utility_id          IS NULL),
                    ('soggetto_ruolo_id',   t.soggetto_ruolo_id   IS NULL),
                    ('emittente_fiscale_id',t.emittente_fiscale_id IS NULL),
                    ('emittente_sr_id',     t.emittente_sr_id     IS NULL),
                    ('sigla',               t.sigla               IS NULL),
                    ('articolo_id',         t.articolo_id         IS NULL),
                    ('valuta_id',           t.valuta_id           IS NULL),
                    ('iva_id',              t.iva_id              IS NULL),
                    ('stato_ddt_draft_id',  t.stato_ddt_draft_id  IS NULL),
                    ('stato_ddt_emesso_id', t.stato_ddt_emesso_id IS NULL),
                    ('stato_ddt_spedito_id',t.stato_ddt_spedito_id IS NULL),
                    ('stato_ddt_consegnato_id', t.stato_ddt_consegnato_id IS NULL),
                    ('stato_ord_conf_id',   t.stato_ord_conf_id   IS NULL),
                    ('causale_vendita_id',  t.causale_vendita_id  IS NULL),
                    ('tipo_ind_con_id',     t.tipo_ind_con_id     IS NULL),
                    ('sorgente_ddt_id',     t.sorgente_ddt_id     IS NULL),
                    ('stato_reso_draft_id', t.stato_reso_draft_id IS NULL),
                    ('tipo_reso_id',        t.tipo_reso_id        IS NULL)
                ) AS x(campo, mancante)
          WHERE x.mancante),
        CASE WHEN (SELECT count(*) FROM tmp_num_refs) = 0
             THEN 'NESSUNA RIGA: nessun billing account soddisfa i filtri della fixture'
             ELSE '' END),
    '',
    '0) Precondizioni: la fixture ha trovato tutti i riferimenti che le servono');

-- =========================================================
-- 1/2/3) IL DDT — registro, anno, forma
-- =========================================================
-- ⭐⭐ Il DDT NASCE con una data e viene EMESSO con un'altra: e' l'unico modo
--   di far divergere «l'anno dell'INSERT» dall'«anno della data documento».
--   ⚠️ Gli anni sono FISSI e lontani da quelli veri, cosi' il caso non dipende
--   da quando gira la suite — il tempo non si simula, si costruisce.
CREATE TEMP TABLE tmp_num_ddt (ddt_id bigint);

DO $$
DECLARE
    v_ddt bigint;
    r     record;
BEGIN
    SELECT * INTO r FROM tmp_num_refs;

    INSERT INTO vendite.ddt (
        destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
        billing_account_id, valuta_id, causale_trasporto_id,
        emittente_fiscale_id, storicizza, meta)
    VALUES (r.soggetto_ruolo_id, r.stato_ddt_draft_id, DATE '2101-12-20',
            r.billing_account_id, r.valuta_id, r.causale_vendita_id,
            r.emittente_fiscale_id, false,
            jsonb_build_object('test_scope', 'pgtap_num_trasloco'))
    RETURNING id INTO v_ddt;

    INSERT INTO vendite.ddt_righe (
        ddt_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ddt, 1, r.articolo_id, 'Riga numerazione', 3, 3, 10, r.iva_id, true, false,
            jsonb_build_object('test_scope', 'pgtap_num_trasloco'));

    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb)
    ON CONFLICT DO NOTHING;

    INSERT INTO tmp_num_ddt VALUES (v_ddt);
END;
$$;

-- ⚠️ La DATA cambia PRIMA dell'emissione: da dicembre 2101 a gennaio 2102.
--   Se l'anno seguisse l'INSERT (o CURRENT_DATE), resterebbe indietro.
UPDATE vendite.ddt d
   SET data = DATE '2102-01-08'
 WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt);

-- ⚠️ Il verbo in un'istruzione SEPARATA dalle asserzioni: la transizione
--   scrive numero, anno e registro.
UPDATE vendite.ddt d
   SET stato_doc_ddt_id = (SELECT stato_ddt_emesso_id FROM tmp_num_refs)
 WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt);

SELECT is(
    (SELECT reg.famiglia_documento::text || '|' ||
            (reg.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs))::text
       FROM vendite.ddt d
       JOIN vendite.registri_fatturazione reg ON reg.id = d.registro_id
      WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)),
    'DDT|true',
    '1) Il DDT emesso sta su un registro di famiglia DDT del PROPRIO emittente');

SELECT is(
    (SELECT d.anno FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)),
    2102::smallint,
    '2) L''anno segue la DATA DEL DOCUMENTO (2102), non quella dell''INSERT');

-- ⚠️ Si asserisce la FORMA, non il numero: il progressivo dipende da quanti
--   documenti quel registro ha gia' emesso, e un test che lo fissasse
--   misurerebbe la popolazione invece della regola.
SELECT ok(
    (SELECT d.numero ~ ('^' || COALESCE(sc.prefisso, '') || COALESCE(sc.separatore, '')
                             || '[0-9]{' || sc.lunghezza_numero || '}$')
       FROM vendite.ddt d
       CROSS JOIN config.sistema_codici sc
      WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)
        AND sc.codice_interno = 'ddt'),
    '3) Il numero DDT ha la forma dichiarata in config.sistema_codici');

-- =========================================================
-- 4) L'ORDINE — si numera all'INSERT, sul proprio registro
-- =========================================================
-- ⚠️ L'ordine si costruisce CON la sua riga: un ordine senza righe non e' un
--   caso reale, e le testate di questo dominio portano constraint trigger che
--   pretendono il satellite — con `SET CONSTRAINTS ALL IMMEDIATE` scatterebbero
--   subito.
CREATE TEMP TABLE tmp_num_ord (ordine_id bigint);

DO $$
DECLARE
    v_ord bigint;
    r     record;
BEGIN
    SELECT * INTO r FROM tmp_num_refs;

    -- ⚠️ `stato_doc_ordine_id` al SINGOLARE, mentre la tabella di catalogo e'
    --   `config.stati_doc_ordini` al plurale. L'asimmetria e' reale e non si
    --   deduce per analogia col DDT (`stato_doc_ddt_id`): si legge.
    INSERT INTO vendite.ordini (
        soggetto_ruolo_id, stato_doc_ordine_id, data,
        billing_account_id, valuta_id, utility_id, emittente_fiscale_id,
        storicizza, meta)
    VALUES (r.soggetto_ruolo_id, r.stato_ord_conf_id, script.fn_data_operativa(),
            r.billing_account_id, r.valuta_id, r.utility_id, r.emittente_fiscale_id,
            false, jsonb_build_object('test_scope', 'pgtap_num_trasloco'))
    RETURNING id INTO v_ord;

    INSERT INTO vendite.ordini_righe (
        ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ord, 1, r.articolo_id, 'Riga numerazione ordine', 2, 2, 10, r.iva_id,
            true, false, jsonb_build_object('test_scope', 'pgtap_num_trasloco'));

    INSERT INTO tmp_num_ord VALUES (v_ord);
END;
$$;

SELECT is(
    (SELECT (o.numero IS NOT NULL)::text || '|' || reg.famiglia_documento::text || '|' ||
            (reg.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs))::text
       FROM vendite.ordini o
       JOIN vendite.registri_fatturazione reg ON reg.id = o.registro_id
      WHERE o.id = (SELECT ordine_id FROM tmp_num_ord)),
    'true|ORDINE|true',
    '4) L''ordine nasce gia'' numerato, sul registro ORDINE del proprio emittente');

-- =========================================================
-- 5/6) LA COMMESSA — la forma, e la SIGLA GIUSTA
-- =========================================================
-- ⚠️ Il verbo separato: fn_get_or_create_commessa SCRIVE.
CREATE TEMP TABLE tmp_num_cmm AS
SELECT vendite.fn_get_or_create_commessa(
           p_billing_account_id => (SELECT billing_account_id FROM tmp_num_refs),
           p_utility_id         => (SELECT utility_id FROM tmp_num_refs),
           p_force_new          => true) AS commessa_id;

-- ⭐ Quattro pezzi: prefisso, sigla, anno, progressivo a lunghezza fissa.
--   ⛔ E' esattamente cio' che il vecchio `CMM-<timestamp>-<md5>` non aveva.
SELECT ok(
    (SELECT c.codice ~ ('^' || COALESCE(sc.prefisso, 'CMM') || COALESCE(sc.separatore, '-')
                             || '[A-Z0-9]{2,10}' || COALESCE(sc.separatore, '-')
                             || '[0-9]{4}' || COALESCE(sc.separatore, '-')
                             || '[0-9]{' || COALESCE(sc.lunghezza_numero, 9) || '}$')
       FROM vendite.commesse c
       CROSS JOIN config.sistema_codici sc
      WHERE c.id = (SELECT commessa_id FROM tmp_num_cmm)
        AND sc.codice_interno = 'commessa'),
    '5) Il codice commessa e'' CMM-<sigla>-<anno>-<progressivo a lunghezza fissa>');

-- ⭐ Non e' un doppione del 5: qui si guarda CHE COSA c'e' nel secondo pezzo.
--   Un generatore che ci mettesse una costante passerebbe il 5 e non questo.
SELECT is(
    (SELECT split_part(c.codice, '-', 2)
       FROM vendite.commesse c
      WHERE c.id = (SELECT commessa_id FROM tmp_num_cmm)),
    (SELECT sigla::text FROM tmp_num_refs),
    '6) La sigla dentro il codice e'' quella dell''emittente della commessa');

-- =========================================================
-- 7) ⛔ Senza registro COMMESSA la commessa NON NASCE
-- =========================================================
-- ⭐ E' il fail-closed nuovo, e va provato che sia RUMOROSO: un emittente
--   configurato a meta' deve fermare la creazione con una frase, non produrre
--   un documento senza numero che si scopre molto piu' tardi.
-- ⚠️ Si spegne il registro invece di cancellarlo: la FK dalle commesse
--   esistenti lo tratterrebbe, e `attivo = false` e' comunque il modo in cui
--   un registro si ritira davvero.
-- ⛔ E si spegne in DUE PASSI, «figli prima, padre poi»: il test 5) ha appena
--   fatto girare il contatore, quindi su quel registro c'e' una riga ATTIVA in
--   vendite.registri_fatturazione_progressivi e dbops.trgfn_prevent_deactivate_if_children
--   rifiuta di spegnere il padre. Non e' un intralcio da aggirare: e' il
--   presidio che impedisce di ritirare un sezionale lasciandogli sotto un
--   contatore vivo — e il rimedio e' quello che il messaggio stesso indica.
CREATE TEMP TABLE tmp_num_reg_cmm AS
SELECT r.id AS registro_id
  FROM vendite.registri_fatturazione r
 WHERE r.famiglia_documento = 'COMMESSA'
   AND r.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs);

UPDATE vendite.registri_fatturazione_progressivi p
   SET attivo = false
 WHERE p.registro_id IN (SELECT registro_id FROM tmp_num_reg_cmm);

UPDATE vendite.registri_fatturazione r
   SET attivo = false
 WHERE r.id IN (SELECT registro_id FROM tmp_num_reg_cmm);

PREPARE num_commessa_senza_registro AS
SELECT vendite.fn_get_or_create_commessa(
           p_billing_account_id => (SELECT billing_account_id FROM tmp_num_refs),
           p_utility_id         => (SELECT utility_id FROM tmp_num_refs),
           p_force_new          => true);

SELECT throws_ok(
    'EXECUTE num_commessa_senza_registro',
    'P0001',
    NULL,
    '7) Senza registro COMMESSA attivo la commessa non nasce, e lo dice');

-- =========================================================
-- 8/9) ⭐ IL RESO — l'ultimo dei quattro, e il piu' scoperto
-- =========================================================
-- ⛔ PERCHE' QUESTO TEST VALE PIU' DEGLI ALTRI, e va detto: senza, un
--   generatore del reso ROTTO non lo scoprirebbe nessuno. I presidi
--   strutturali di test-identita-documenti-derivata guardano la CHIAVE, non il
--   comportamento; e quello sui dati chiede «chi ha il registro ha anche
--   l'anno», quindi un reso nato SENZA registro — cioe' esattamente il sintomo
--   di un generatore rotto — cade nel ramo del pregresso e passa.
--   ⇒ Il buco era coperto due volte male. Si chiude solo provando il caso dal
--   lato giusto: non «non ci sono resi rotti», ma «un reso confermato ADESSO
--   riceve il numero».
--
-- ⭐ Il reso si CONFERMA con la madre (vendite.fn_conferma_reso), non con un
--   UPDATE dello stato: e' il percorso reale, ed e' l'unico che prova anche che
--   il trigger sia montato dove serve.
-- ⚠️ La riga del reso vuole `ddt_riga_id` (NOT NULL): il DDT costruito sopra
--   serve anche a questo, e non se ne fabbrica un secondo.
-- ℹ️ destinatario ed emittente NON si passano benche' siano NOT NULL: li
--   deriva il DB dal DDT sorgente. Passarli a mano nasconderebbe il giorno in
--   cui quella derivazione smette di funzionare.
-- ⛔ IL DDT VA PORTATO A `CONSEGNATO`, e il guard che lo pretende ha ragione:
--   «non si rende cio' che non e' stato consegnato». I test 1..3 hanno gia'
--   letto numero, registro e anno subito dopo l'emissione — la transizione non
--   li tocca.
-- ⚠️ Uno stato alla volta: la matrice delle transizioni non ammette salti
--   (EMESSO -> SPEDITO -> CONSEGNATO), e un UPDATE diretto a CONSEGNATO
--   verrebbe respinto da vendite.trgfn_ddt_guard_transizione.
UPDATE vendite.ddt d
   SET stato_doc_ddt_id = (SELECT stato_ddt_spedito_id FROM tmp_num_refs)
 WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt);

UPDATE vendite.ddt d
   SET stato_doc_ddt_id = (SELECT stato_ddt_consegnato_id FROM tmp_num_refs)
 WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt);

CREATE TEMP TABLE tmp_num_reso (reso_id bigint);

DO $$
DECLARE
    v_reso bigint;
    r      record;
BEGIN
    SELECT * INTO r FROM tmp_num_refs;

    INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid,
                              storicizza, meta)
    SELECT r.stato_reso_draft_id, r.sorgente_ddt_id, d.uid, false,
           jsonb_build_object('test_scope', 'pgtap_num_trasloco')
      FROM vendite.ddt d
     WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)
    RETURNING id INTO v_reso;

    INSERT INTO vendite.resi_righe (
        reso_id, riga_nr, ddt_riga_id, articolo_id, descrizione,
        qta_operativa, uom_operativa_id, factor_to_base, tipo_reso_id, storicizza, meta)
    SELECT v_reso, 1, dr.id, dr.articolo_id, dr.descrizione,
           1, dr.uom_operativa_id, dr.factor_to_base, r.tipo_reso_id, false,
           jsonb_build_object('test_scope', 'pgtap_num_trasloco')
      FROM vendite.ddt_righe dr
     WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_num_ddt)
     ORDER BY dr.id
     LIMIT 1;

    -- ⭐ La madre, non un UPDATE: e' la transizione vera.
    PERFORM vendite.fn_conferma_reso(v_reso);

    INSERT INTO tmp_num_reso VALUES (v_reso);
END;
$$;

SELECT is(
    (SELECT (re.numero IS NOT NULL)::text || '|' || reg.famiglia_documento::text || '|' ||
            (reg.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs))::text || '|' ||
            (re.anno = EXTRACT(YEAR FROM re.data)::smallint)::text
       FROM vendite.resi re
       JOIN vendite.registri_fatturazione reg ON reg.id = re.registro_id
      WHERE re.id = (SELECT reso_id FROM tmp_num_reso)),
    'true|RESO|true|true',
    '8) Il reso confermato ha numero, registro RESO del proprio emittente e anno dalla data');

-- ⚠️ Si asserisce la FORMA, non il numero: il progressivo dipende da quanti
--   documenti quel registro ha gia'' emesso, e fissarlo misurerebbe la
--   popolazione invece della regola.
SELECT ok(
    (SELECT re.numero ~ ('^' || COALESCE(sc.prefisso, '') || COALESCE(sc.separatore, '')
                              || '[0-9]{' || sc.lunghezza_numero || '}$')
       FROM vendite.resi re
       CROSS JOIN config.sistema_codici sc
      WHERE re.id = (SELECT reso_id FROM tmp_num_reso)
        AND sc.codice_interno = 'reso'),
    '9) Il numero reso ha la forma dichiarata in config.sistema_codici');

SELECT * FROM finish();
ROLLBACK;
