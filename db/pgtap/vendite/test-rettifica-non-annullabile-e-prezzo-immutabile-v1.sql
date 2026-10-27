-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le due porte da cui una NOTA DI CREDITO era raggiungibile
--       (changeSet 20260820-10 e -11; segnalazione BE del 2026-08-20,
--        brief-design-note-credito-resi §42).
--
--   1. `vendite.fn_annulla_commessa_attivita` definiva «riga manuale» come
--      SOURCELESS. L'equazione ha smesso di essere vera quando
--      `fn_accredita_riga_reso` ha iniziato a scrivere rettifiche sourceless:
--      una riga di nota di credito passava il guard, si annullava, e il ponte
--      in `resi_righe_accrediti` sopravviveva — credito al cliente e nessun
--      documento, senza segnali.
--   2. Il prezzo di una rettifica e' COPIATO dalla riga di fattura che
--      rettifica: cambiarlo accrediterebbe un importo diverso da quello
--      fatturato. E si scrive con una UPDATE DIRETTA, quindi il blocco deve
--      stare nella tabella, non nel service.
--
-- Elenco test (plan 14):
--   1) codice 935 a catalogo, classe CONFLITTO_STATO
--   2) codice 936 a catalogo, classe CONFLITTO_STATO
--   3) la funzione guard del prezzo esiste
--   4) il trigger e' BEFORE UPDATE OF prezzo_snapshot, prezzo_bloccato
--   5) fixture: onere sourceless NON_EMESSA
--   6) fixture: rettifica sourceless NON_EMESSA
--   7) ⭐ annullare la rettifica solleva 935 (canale CONSTRAINT)
--   8) dopo il rifiuto la rettifica e' ancora NON_EMESSA (nessuna scrittura)
--   9) l'onere si annulla ancora: nessuna regressione sul caso legittimo
--  10) cambiare prezzo_snapshot su una rettifica solleva 936 (canale CONSTRAINT)
--  11) cambiare prezzo_bloccato su una rettifica solleva 936
--  12) riscrivere lo STESSO prezzo passa (IS DISTINCT FROM)
--  13) cambiare il prezzo su un ONERE passa: il guard e' mirato
--  14) dopo i rifiuti il prezzo della rettifica e' invariato
--
-- ⚠️ COSA QUESTO TEST NON DIMOSTRA. La rettifica della fixture nasce da
--   `fn_upsert_commessa_attivita`, non da `fn_accredita_riga_reso`: il soggetto
--   e' la FORMA della riga (sourceless + RETTIFICA), non il modo in cui nasce,
--   e la catena reale (reso -> fattura -> accredito) costerebbe una fixture di
--   tre documenti per verificare lo stesso predicato. Che il varco fosse
--   REALE e' stato misurato sul dato vero, non dedotto: il 2026-08-20 in dbdev
--   quattro righe RETTIFICA passavano il gate e zero righe legittime lo
--   perdono col perimetro nuovo (brief §42.1).
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come `zeroerp_app` con RLS attiva. Qui
--   conta doppio: il test 10 fa una UPDATE DIRETTA sulla tabella, cioe' la
--   stessa strada del backend, e deve incontrare il guard da quella veste.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1..4  Gli oggetti a catalogo e nel database
-- ============================================================

SELECT is(
  (SELECT classe FROM config.codici_errore
    WHERE codice = 'E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE'),
  'CONFLITTO_STATO',
  '1. codice E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE a catalogo, classe CONFLITTO_STATO'
);

SELECT is(
  (SELECT classe FROM config.codici_errore
    WHERE codice = 'E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE'),
  'CONFLITTO_STATO',
  '2. codice E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE a catalogo, classe CONFLITTO_STATO'
);

SELECT has_function('vendite', 'trgfn_commesse_attivita_guard_prezzo_rettifica',
                    '3. la funzione guard del prezzo esiste');

-- ⚠️ Non basta che il trigger esista: deve essere BEFORE e su QUELLE colonne.
--   Un AFTER non potrebbe impedire la scrittura, e un trigger senza `UPDATE OF`
--   si sveglierebbe su ogni UPDATE della tabella — costo inutile su una tabella
--   che il push scrive a migliaia di righe.
SELECT ok(
  (SELECT pg_get_triggerdef(t.oid) LIKE 'CREATE TRIGGER % BEFORE UPDATE OF prezzo_snapshot, prezzo_bloccato ON vendite.commesse_attivita%'
     FROM pg_trigger t
     JOIN pg_class c ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'commesse_attivita'
      AND t.tgname = 'trg_commesse_attivita_a10_guard_prezzo_rettifica_upd'
      AND NOT t.tgisinternal),
  '4. il trigger e'' BEFORE UPDATE OF prezzo_snapshot, prezzo_bloccato'
);

-- ============================================================
-- Fixture: una commessa con un ONERE e una RETTIFICA
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO.
--   Prima si pescavano il primo BA con emittente e l'ultimo articolo attivo, e
--   su un database ricostruito da zero non c'erano: ora il BA viene da
--   dbops.fn_pgtap_crea_cliente_ba (legato all'azienda di chi agisce, emittente
--   derivato dal BA) e l'articolo da dbops.fn_pgtap_crea_articolo (servizio,
--   non gestito a magazzino). Restano letture di catalogo di SEED:
--   tipi_doc_fiscale, articolo-onere, unita_misura.
CREATE TEMP TABLE tmp_cli_rnp AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('rettifica non annullabile');

CREATE TEMP TABLE tmp_refs_rnp AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_rnp) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_rnp) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_rnp) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_rnp) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA') AS articolo_onere_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-RNP-ART', false) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id;

CREATE TEMP TABLE tmp_com_rnp AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id          => (SELECT billing_account_id FROM tmp_refs_rnp),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_rnp),
  p_tipo_commessa               => 'AUTO',
  p_policy_fatturazione         => 'DA_DOCUMENTO',
  p_fatturazione_immediata      => false,
  p_priorita_operativa          => 'NORMALE',
  p_competenza_dal              => DATE '2026-07-01',
  p_competenza_al               => DATE '2026-07-31',
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_rettifica_non_annullabile'),
  p_force_new                   => true
) AS commessa_id;

-- L'ONERE: la riga che il verbo di annullo DEVE continuare a servire.
CREATE TEMP TABLE tmp_onere_rnp AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => (SELECT commessa_id FROM tmp_com_rnp),
  p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_refs_rnp),
  p_articolo_onere_id   => (SELECT articolo_onere_id FROM tmp_refs_rnp),
  p_importo             => 120.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_rnp),
  p_motivo              => 'onere di prova — pgtap',
  p_data_attivita       => DATE '2026-07-15'
) AS id;

-- La RETTIFICA: sourceless come le scrive fn_accredita_riga_reso, quantita'
-- NEGATIVA, prezzo bloccato. Vedi la nota in testa su cosa questo NON dimostra.
CREATE TEMP TABLE tmp_rett_rnp AS
SELECT r.attivita_id AS id
FROM vendite.fn_upsert_commessa_attivita(
  p_commessa_id         => (SELECT commessa_id FROM tmp_com_rnp),
  p_segment_key         => ('SEG-RNP-' || substr(md5(clock_timestamp()::text), 1, 12) || '#RET:1')::varchar,
  p_articolo_id         => (SELECT articolo_id FROM tmp_refs_rnp),
  p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_refs_rnp),
  p_data_attivita       => DATE '2026-07-16',
  p_uom_id              => (SELECT uom_id FROM tmp_refs_rnp),
  p_quantita            => -1.000000,
  p_competenza_mese     => DATE '2026-07-01',
  p_competenza_dal      => DATE '2026-07-16',
  p_competenza_al       => DATE '2026-07-16',
  p_prezzo_snapshot     => 2.5000000000,
  -- Gli otto senza DEFAULT vanno passati anche a NULL.
  p_prezzo_base_snapshot          => 2.5000000000,
  p_origine_prezzo                => 'MANUALE',
  p_tipo_variazione_applicata     => 'NESSUNA',
  p_valore_variazione_applicata   => NULL,
  p_promo_id                      => NULL,
  p_contratto_id                  => NULL,
  p_categoria_cliente_id_snapshot => NULL,
  p_classe_utenza_id_snapshot     => NULL,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_rnp),
  p_prezzo_bloccato     => true,
  p_stato_approvazione  => 'APPROVATA',
  p_stato_emissione     => 'NON_EMESSA',
  p_sorgente_tipo_id    => NULL,
  p_sorgente_uid        => NULL,
  p_tipo_movimento      => 'RETTIFICA',
  p_meta                => jsonb_build_object('case', 'RNP_RETTIFICA')
) r;

SELECT is(
  (SELECT ca.tipo_movimento::text || '/' || ca.stato_emissione::text || '/' ||
          (ca.sorgente_tipo_id IS NULL)::text
     FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT id FROM tmp_onere_rnp)),
  'ONERE/NON_EMESSA/true',
  '5. fixture: onere sourceless NON_EMESSA'
);

SELECT is(
  (SELECT ca.tipo_movimento::text || '/' || ca.stato_emissione::text || '/' ||
          (ca.sorgente_tipo_id IS NULL)::text
     FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT id FROM tmp_rett_rnp)),
  'RETTIFICA/NON_EMESSA/true',
  '6. fixture: rettifica sourceless NON_EMESSA (la riga che PRIMA si annullava)'
);

-- ============================================================
-- 7..9  Il verbo di annullo: rifiuta la rettifica, serve ancora l'onere
-- ============================================================
-- ⚠️ Il codice si legge dal canale CONSTRAINT dell'eccezione, non dal testo:
--   cosi' l'asserzione e' verde anche prima che il mirror CSV carichi la voce,
--   e un `throws_like` sulla frase sarebbe rosso per un motivo che non c'entra
--   con il guard.

CREATE TEMP TABLE tmp_esito_rnp(caso text, sqlstate text, codice text);

DO $t$
DECLARE v_ss text; v_c text;
BEGIN
    PERFORM vendite.fn_annulla_commessa_attivita(
        (SELECT id FROM tmp_rett_rnp), 'tentativo di annullo — pgtap');
    INSERT INTO tmp_esito_rnp VALUES ('annullo_rettifica', 'NESSUN_ERRORE', NULL);
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_ss = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    INSERT INTO tmp_esito_rnp VALUES ('annullo_rettifica', v_ss, v_c);
END
$t$;

SELECT is(
  (SELECT sqlstate || '/' || COALESCE(codice,'?') FROM tmp_esito_rnp WHERE caso = 'annullo_rettifica'),
  'P0001/E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE',
  '7. annullare una rettifica solleva 935 sul canale CONSTRAINT'
);

-- ⚠️ L'esito, non l'ordine delle istruzioni: il blocco EXCEPTION apre una
--   sottotransazione che annulla comunque le scritture eventuali. Qui si
--   verifica che la riga sia rimasta quella che era.
SELECT is(
  (SELECT stato_emissione::text FROM vendite.commesse_attivita
    WHERE id = (SELECT id FROM tmp_rett_rnp)),
  'NON_EMESSA',
  '8. dopo il rifiuto la rettifica e'' ancora NON_EMESSA'
);

-- ⭐ La contro-prova: il perimetro si e'' STRETTO, non spostato. Un guard che
--   blocca anche il caso legittimo non e'' una correzione, e'' una regressione.
SELECT lives_ok($$
  SELECT vendite.fn_annulla_commessa_attivita(
      (SELECT id FROM tmp_onere_rnp), 'annullo legittimo — pgtap')
$$, '9. l''onere si annulla ancora: nessuna regressione sul caso legittimo');

-- ============================================================
-- 10..14  Il prezzo della rettifica: immutabile, e mirato
-- ============================================================
-- ⚠️ UPDATE DIRETTE, non chiamate a funzione: e' la strada che percorre
--   `update_attivita_prezzo` nel repository, ed e' la ragione per cui il guard
--   sta nella tabella e non nel service.

-- ⚠️ Non `throws_ok('P0001')` e basta: quello accetterebbe QUALUNQUE errore di
--   dominio, compreso il crash di un altro guard sulla stessa UPDATE. Si legge
--   il codice dal canale CONSTRAINT, come al test 7.
DO $t$
DECLARE v_ss text; v_c text;
BEGIN
    UPDATE vendite.commesse_attivita
       SET prezzo_snapshot = 99.0000000000
     WHERE id = (SELECT id FROM tmp_rett_rnp);
    INSERT INTO tmp_esito_rnp VALUES ('prezzo_rettifica', 'NESSUN_ERRORE', NULL);
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_ss = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    INSERT INTO tmp_esito_rnp VALUES ('prezzo_rettifica', v_ss, v_c);
END
$t$;

SELECT is(
  (SELECT sqlstate || '/' || COALESCE(codice,'?') FROM tmp_esito_rnp WHERE caso = 'prezzo_rettifica'),
  'P0001/E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE',
  '10. cambiare prezzo_snapshot su una rettifica solleva 936 (UPDATE diretta)'
);

SELECT throws_ok($$
  UPDATE vendite.commesse_attivita
     SET prezzo_bloccato = false
   WHERE id = (SELECT id FROM tmp_rett_rnp)
$$, 'P0001', NULL,
   '11. cambiare prezzo_bloccato su una rettifica solleva');

-- ⭐ Il guard blocca il CAMBIAMENTO, non la scrittura: senza questo,
--   l'ON CONFLICT DO UPDATE dell'upsert — che riassegna prezzo_snapshot anche
--   quando il valore e' identico — si romperebbe su ogni ri-scrittura.
SELECT lives_ok($$
  UPDATE vendite.commesse_attivita
     SET prezzo_snapshot = prezzo_snapshot,
         prezzo_bloccato = prezzo_bloccato
   WHERE id = (SELECT id FROM tmp_rett_rnp)
$$, '12. riscrivere lo STESSO prezzo passa (IS DISTINCT FROM, non uguaglianza)');

-- ⭐ E il guard e' MIRATO: un onere e' una voce di valore manuale, il suo
--   prezzo E' l'importo e si corregge. Se questo test diventasse rosso, il
--   guard avrebbe smesso di essere una regola sulle rettifiche per diventare
--   una regola sui prezzi.
SELECT lives_ok($$
  UPDATE vendite.commesse_attivita
     SET prezzo_snapshot = 130.0000000000
   WHERE id = (SELECT id FROM tmp_onere_rnp)
$$, '13. cambiare il prezzo su un ONERE passa: il guard e'' mirato');

SELECT is(
  (SELECT prezzo_snapshot FROM vendite.commesse_attivita
    WHERE id = (SELECT id FROM tmp_rett_rnp)),
  2.5000000000::numeric,
  '14. dopo i rifiuti il prezzo della rettifica e'' quello di partenza'
);

SELECT * FROM finish();

ROLLBACK;
