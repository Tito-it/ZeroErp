-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: P-2 / P-4 / P-5 — i documenti dopo il trasloco: registro, anno, forma
-- Oggetti:
--   vendite.trgfn_ddt_gen_numero_emesso        (20260831-08)
--   vendite.trgfn_ordini_gen_numero            (20260831-13)
--   vendite.fn_get_or_create_commessa          (20260831-16)
--   vendite.fn_assegna_numero_documento        (20260831-55 — la lunghezza dal registro)
--   Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, §3.6
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c/2d): la famiglia della bolla e' DDT_VENDITA.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso in bozza dal builder dbops.fn_pgtap_crea_reso; resta scritta la conferma dal verbo vendite.fn_conferma_reso, perche' e' il passo che numera (8-9).
-- ------------------------------------------------------------
-- Elenco test (plan 11):
-- 0) ⚠️ Precondizioni: la fixture non mente
-- 1) Il DDT emesso prende il registro DEL PROPRIO emittente
-- 2) ⭐⭐ L'ANNO SEGUE LA DATA DEL DOCUMENTO, non quella dell'INSERT
-- 3) La forma del numero DDT e' quella del REGISTRO che l'ha numerato
-- 4) L'ordine si numera all'INSERT, sul registro del proprio emittente
-- 5) ⭐⭐ Il codice commessa ha la forma del registro — NOVE cifre
-- 6) ⭐ ...e la sigla dentro il codice e' QUELLA dell'emittente, non un'altra
-- 7) ⛔ Senza registro COMMESSA la commessa NON NASCE, e lo dice
-- 8) ⭐ Il RESO confermato prende numero, registro RESO e anno
-- 9) La forma del numero reso e' quella del REGISTRO che l'ha numerato
-- 10) ⛔ Nessuna funzione di `vendite` LEGGE piu' il catalogo dei formati
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

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Un'azienda nuova col suo operatore — il contesto passa
--   su di lui, ed e' a lui che si concede l'azione qui sotto — e il cliente
--   legato a lei (dbops.fn_pgtap_crea_mondo_cliente). L'azienda nasce coi suoi
--   registri (DDT, ORDINE, COMMESSA, RESO): la numerazione si prova su quelli.
--   Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP num trasloco');

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

SELECT plan(11);

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
    -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non gestito: il test
    --   misura la numerazione, non il magazzino).
    dbops.fn_pgtap_crea_articolo('PGTAP-NUM-TRASLOCO', false)               AS articolo_id,
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
    (SELECT s.id FROM config.stati_doc_ordini s
      WHERE s.codice_interno = 'DRAFT' ORDER BY s.id LIMIT 1) AS stato_ord_draft_id,
    -- ⚠️ Qui l'aggancio e' su `codice` e NON su `codice_interno`, e non per
    --   scelta: config.causali_trasporto la colonna `codice_interno` non ce
    --   l'ha proprio. Resta quindi un aggancio FRAGILE — `codice` e'
    --   modificabile dall'utente, e un rename lo sgancia in silenzio — ed e'
    --   dichiarato qui invece di essere scoperto da chi vedra' il test
    --   diventare rosso senza capire perche'.
    (SELECT c.id FROM config.causali_trasporto c
      WHERE c.codice = 'VENDITA' ORDER BY c.id LIMIT 1)                   AS causale_vendita_id,
    (SELECT ti.id FROM config.tipi_indirizzi ti
      WHERE ti.codice_interno = 'CON' ORDER BY ti.id LIMIT 1)             AS tipo_ind_con_id
  FROM anagrafiche.billing_account ba
  -- ⛔ rev 2026-10-13: il BA e' quello COSTRUITO, non «il primo che soddisfa i
  --   filtri»; i filtri restano, e la precondizione 0) li verifica.
  JOIN _m m ON m.billing_account_id = ba.id
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
                  AND r.famiglia_documento = 'DDT_VENDITA' AND r.attivo)
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
                    ('stato_ord_draft_id',  t.stato_ord_draft_id  IS NULL),
                    ('causale_vendita_id',  t.causale_vendita_id  IS NULL),
                    ('tipo_ind_con_id',     t.tipo_ind_con_id     IS NULL)
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
    'DDT_VENDITA|true',
    '1) Il DDT emesso sta su un registro di famiglia DDT del PROPRIO emittente');

SELECT is(
    (SELECT d.anno FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)),
    2102::smallint,
    '2) L''anno segue la DATA DEL DOCUMENTO (2102), non quella dell''INSERT');

-- ⚠️ Si asserisce la FORMA, non il numero: il progressivo dipende da quanti
--   documenti quel registro ha gia' emesso, e un test che lo fissasse
--   misurerebbe la popolazione invece della regola.
-- ⛔ L'attesa si costruisce dal REGISTRO CHE HA NUMERATO QUESTO DOCUMENTO, non
--   da un catalogo a parte. Fino al 2026-08-31 veniva da config.sistema_codici:
--   quando il 20260831-53 ne ha tolto le righe, il CROSS JOIN ha smesso di
--   trovarne una e l'asserzione e' diventata NULL — cioe' rossa per il motivo
--   sbagliato, dopo aver taciuto sul motivo giusto.
-- ⛔ rev 2026-10-13: la forma comprende l'ANNO quando il registro lo vuole
--   (`anno_nel_numero`, dal 20260908 il default per DDT e RESO): stessa
--   composizione di vendite.fn_assegna_numero_documento, `<anno>-` dopo il
--   corpo. Era verde solo sul registro vecchio di dbdev, che l'anno non l'ha.
SELECT ok(
    (SELECT d.numero ~ ('^' || COALESCE(reg.prefisso, '')
                             || CASE WHEN reg.anno_nel_numero THEN '[0-9]{4}-' ELSE '' END
                             || '[0-9]{' || reg.lunghezza_numero || '}'
                             || COALESCE(reg.suffisso, '') || '$')
       FROM vendite.ddt d
       JOIN vendite.registri_fatturazione reg ON reg.id = d.registro_id
      WHERE d.id = (SELECT ddt_id FROM tmp_num_ddt)),
    '3) Il numero DDT ha la forma del REGISTRO che l''ha numerato');

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
    -- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce
    --   DRAFT, prende la riga, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato —
    --   fuori bozza le righe non si scrivono piu' (20261008-90).
    VALUES (r.soggetto_ruolo_id, r.stato_ord_draft_id, script.fn_data_operativa(),
            r.billing_account_id, r.valuta_id, r.utility_id, r.emittente_fiscale_id,
            false, jsonb_build_object('test_scope', 'pgtap_num_trasloco'))
    RETURNING id INTO v_ord;

    INSERT INTO vendite.ordini_righe (
        ordine_id, riga_nr, articolo_id, descrizione,
        qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ord, 1, r.articolo_id, 'Riga numerazione ordine', 2, 2, 10, r.iva_id,
            true, false, jsonb_build_object('test_scope', 'pgtap_num_trasloco'));
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');

    INSERT INTO tmp_num_ord VALUES (v_ord);
END;
$$;

SELECT is(
    (SELECT (o.numero IS NOT NULL)::text || '|' || reg.famiglia_documento::text || '|' ||
            (reg.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs))::text
       FROM vendite.ordini o
       JOIN vendite.registri_fatturazione reg ON reg.id = o.registro_id
      WHERE o.id = (SELECT ordine_id FROM tmp_num_ord)),
    'true|ORDINE_VENDITA|true',
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
-- ⭐⭐ QUESTA E' L'ASSERZIONE CHE HA TROVATO IL DIFETTO DEL 20260831-55, ed e'
--   il motivo per cui l'attesa deve venire dal REGISTRO: la commessa e' l'unica
--   delle quattro famiglie a volere NOVE cifre, quindi e' l'unica su cui un
--   ripiego a 7 si vede. Le altre tre passavano lo stesso — il valore di
--   ripiego coincideva col loro — e questo e' il genere di caso che decide se
--   un presidio serve davvero.
-- ⚠️ La commessa NON ha una colonna `registro_id`: la sua identita' e' la
--   stringa nuda, e il registro si ritrova dall'emittente, come fa il
--   generatore.
-- ⚠️ Il trattino FRA i pezzi (sigla-anno-) e' del dominio commessa e si scrive
--   qui; quello davanti al prefisso non esiste piu', sta DENTRO `CMM-`.
SELECT ok(
    (SELECT c.codice ~ ('^' || COALESCE(reg.prefisso, '')
                             || '[A-Z0-9]{2,10}-'
                             || '[0-9]{4}-'
                             || '[0-9]{' || reg.lunghezza_numero || '}'
                             || COALESCE(reg.suffisso, '') || '$')
       FROM vendite.commesse c
       JOIN vendite.registri_fatturazione reg
         ON reg.emittente_soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
        AND reg.famiglia_documento = 'COMMESSA'
        AND reg.utility_id IS NULL
        AND reg.attivo
      WHERE c.id = (SELECT commessa_id FROM tmp_num_cmm)),
    '5) Il codice commessa ha la forma del REGISTRO: CMM-<sigla>-<anno>-<cifre>');

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

-- ⛔ E DAL 2026-09-02 I PASSI SONO TRE, non due. `vendite.commesse` ha
--   guadagnato `registro_id` (changeSet 20260902-07) e l'automazione ATTIVO ha
--   montato il SETTIMO guard di disattivazione da sola, a partire dalla FK: le
--   commesse gia' numerate su questo registro lo trattengono.
-- ⚠️ E qui non c'e' un «figli prima»: `vendite.commesse` NON ha la colonna
--   `attivo`, quindi il guard cade nel ramo dell'ESISTENZA — ne basta UNA
--   qualsiasi, e spegnerla non e' un'opzione. L'unico modo di liberare il padre
--   e' STACCARLE.
-- ⭐ Il caso piu' stretto e' che il test se lo procura da solo: il 5) ha appena
--   creato una commessa su QUESTO registro, quindi senza questa riga il file si
--   blocca su cio' che ha appena fatto.
-- ⚠️ Lo stacco vive dentro la transazione che il file annulla: non tocca il
--   database oltre il ROLLBACK, ed e' fixture, non un rimedio di dominio. Nella
--   realta' un registro che ha numerato una commessa non si spegne piu' — ed e'
--   la durezza che script.fn_check_registro_disattivabile ora DICHIARA prima
--   del click (motivo HA_COMMESSE, changeSet 20260902-12).
UPDATE vendite.commesse cm
   SET registro_id = NULL
 WHERE cm.registro_id IN (SELECT registro_id FROM tmp_num_reg_cmm);

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
-- ℹ️ Il reso in bozza dal builder (dbops.fn_pgtap_crea_reso): destinatario ed
--   emittente non li passa, li deriva il DB dal DDT sorgente. La conferma e'
--   il passo del test.
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

CREATE TEMP TABLE tmp_num_reso AS
SELECT reso_id
  FROM dbops.fn_pgtap_crea_reso('num_trasloco', (SELECT ddt_id FROM tmp_num_ddt), 1,
                                'RESO_PER_RICONSEGNA', 'DRAFT');

-- ⭐ La madre, non un UPDATE: e' la transizione vera.
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_num_reso));

SELECT is(
    (SELECT (re.numero IS NOT NULL)::text || '|' || reg.famiglia_documento::text || '|' ||
            (reg.emittente_soggetto_ruolo_id = (SELECT emittente_sr_id FROM tmp_num_refs))::text || '|' ||
            (re.anno = EXTRACT(YEAR FROM re.data)::smallint)::text
       FROM vendite.resi re
       JOIN vendite.registri_fatturazione reg ON reg.id = re.registro_id
      WHERE re.id = (SELECT reso_id FROM tmp_num_reso)),
    'true|RESO_VENDITA|true|true',
    '8) Il reso confermato ha numero, registro RESO del proprio emittente e anno dalla data');

-- ⚠️ Si asserisce la FORMA, non il numero: il progressivo dipende da quanti
--   documenti quel registro ha gia'' emesso, e fissarlo misurerebbe la
--   popolazione invece della regola.
-- ⛔ L'attesa viene dal REGISTRO che ha numerato questo reso: stessa correzione
--   del test 3, e stessa ragione.
-- ⛔ rev 2026-10-13: la forma comprende l'ANNO quando il registro lo vuole
--   (`anno_nel_numero`, dal 20260908 il default per DDT e RESO): stessa
--   composizione di vendite.fn_assegna_numero_documento, `<anno>-` dopo il
--   corpo. Era verde solo sul registro vecchio di dbdev, che l'anno non l'ha.
SELECT ok(
    (SELECT re.numero ~ ('^' || COALESCE(reg.prefisso, '')
                              || CASE WHEN reg.anno_nel_numero THEN '[0-9]{4}-' ELSE '' END
                              || '[0-9]{' || reg.lunghezza_numero || '}'
                              || COALESCE(reg.suffisso, '') || '$')
       FROM vendite.resi re
       JOIN vendite.registri_fatturazione reg ON reg.id = re.registro_id
      WHERE re.id = (SELECT reso_id FROM tmp_num_reso)),
    '9) Il numero reso ha la forma del REGISTRO che l''ha numerato');

-- =========================================================
-- 10) ⛔ IL PRESIDIO DI CLASSE — nessuno legge piu' il catalogo
-- =========================================================
-- ⭐ E' il test che sarebbe servito il 2026-08-31, ed e' l'unico dei dieci che
--   non guarda un documento: guarda il CODICE. Il 20260831-53 ha cancellato
--   quattro righe di config.sistema_codici, e nessuna delle sue preCondition
--   chiedeva CHI LE LEGGE ANCORA — verificavano solo che la sede nuova fosse
--   popolata. vendite.fn_assegna_numero_documento continuava a leggerle: zero
--   righe, lunghezza NULL, sette cifre a tutti — giusto per caso su DDT,
--   ordini e resi, e sbagliato sulla commessa, che ne vuole nove.
-- ⚠️ SI CERCA LA LETTURA (`FROM config.sistema_codici`), NON LA PAROLA, e la
--   prima stesura sbagliava proprio qui. Cercare la parola sembrava piu'
--   severo — «una funzione che NOMINA una tabella vuota manda chi indaga nella
--   direzione sbagliata» — ma e' una regola che nessuno puo' rispettare: le
--   correzioni del 20260831-55/56 DEVONO poter dire da dove veniva prima la
--   lunghezza, o si perde l'unica spiegazione del perche' la commessa aveva
--   sette cifre. ⇒ Un presidio che vieta di raccontare la storia viene
--   aggirato scrivendo commenti piu' vaghi: si sarebbe pagato in chiarezza.
-- ⭐ Deriva dal catalogo di sistema, quindi copre da sola anche il generatore
--   che qualcuno scrivesse domani.
SELECT is(
    (SELECT COALESCE(string_agg(p.proname, ', ' ORDER BY p.proname), '')
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.prosrc ~ 'FROM\s+config\.sistema_codici'),
    '',
    '10) Nessuna funzione di `vendite` LEGGE piu'' il catalogo dei formati');

SELECT * FROM finish();
ROLLBACK;
