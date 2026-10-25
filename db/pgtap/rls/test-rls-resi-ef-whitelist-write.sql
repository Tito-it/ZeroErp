-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE … FORCE ROW LEVEL SECURITY, locale alla
--   transazione — e' il FORCE a rendere l'owner soggetto alle policy, perche'
--   `titodb` non e' superuser e non puo' fare SET ROLE. E la fixture costruisce
--   DUE aziende: un operatore dentro un perimetro non potrebbe crearle.
-- pgTAP test FUNZIONALE scrittura RLS — vendite.resi (rls_resi_ef_whitelist)
--
-- Elenco test (plan 3):
--   1. OPERATORE in-scope  -> l'UPDATE tocca la riga
--   2. ⛔ OPERATORE off-scope -> tocca ZERO righe (la USING isola per emittente)
--   3. ⛔ nessun ruolo        -> tocca ZERO righe (fail-closed)
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ RISCRITTO IL 2026-09-09, e le tre cose che sono cambiate valgono la nota.
--
-- ⛔ 1) NON PASSA PIU' A VUOTO. La versione precedente cercava due emittenti e
--   un billing account gia' esistenti, costruiva la catena dentro un
--   `EXCEPTION WHEN OTHERS THEN NULL`, e ogni asserzione era della forma
--   `NOT prereq OR <la cosa vera>`. Su un database ricostruito dai changelog
--   quei soggetti non esistono: la fixture falliva in silenzio, `prereq`
--   diventava falso e i tre test passavano **senza verificare niente**. E' il
--   «verde per sottrazione»: un file che passa smettendo di misurare, in un'area
--   che sembra coperta. Adesso la fixture si COSTRUISCE
--   (`dbops.fn_pgtap_crea_emittente_operatore`, `fn_pgtap_crea_cliente_ba`) e
--   se non si costruisce il file diventa ROSSO, che e' l'informazione utile.
--
-- ⚠️ 2) L'INTESTAZIONE DICEVA IL FALSO. Diceva «la RLS non e' attiva
--   permanentemente su vendite.resi: qui si attiva ENABLE + FORCE locale».
--   `vendite.resi` e' armata (`relrowsecurity = t`, verificato 2026-09-09),
--   quindi quell'`ENABLE` era un no-op e la frase mandava fuori strada chi
--   legge. Resta il solo `FORCE`, che serve davvero: senza, l'owner e' esente e
--   il test misurerebbe zero.
--
-- ⭐ 3) GLI OPERATORI NON SE LI FABBRICA PIU' A MANO. C'era una
--   `pg_temp.mk_op()` di trenta righe che scriveva `django.auth_user`,
--   `identita_digitali` e `user_emittenti_fiscali`: e' esattamente cio' che fa
--   `dbops.fn_pgtap_crea_emittente_operatore()` (changeSet 20260909-26). Una
--   seconda scrittura della stessa regola prima o poi dissente dalla prima.
--
-- ⛔ E la CATENA DEL RESO si percorre tutta: un reso pretende un DDT
--   **consegnato** (`trgfn_resi_guard_ddt_consegnato`), quindi il DDT va portato
--   DRAFT -> EMESSO -> SPEDITO -> CONSEGNATO passando dai suoi guard — causale
--   di trasporto alla nascita (dopo e' immutabile), IVA sulla riga che ha un
--   prezzo, indirizzo `CON` obbligatorio.
--
-- Perimetro: questo file collauda la scrittura sulla TESTATA. I satelliti
-- (`resi_righe` e le tre figlie) stanno in test-rls-resi-satelliti.sql.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso, in bozza (nasce con una riga, che il test non legge); restano le policy esercitate a mano, che sono il caso.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): la bolla a CONSEGNATO con dbops.fn_pgtap_porta_a_stato (i passi col verbo), non piu' con tre UPDATE diretti dello stato che la porta ora rifiuta.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- ============================================================
-- I due mondi: A possiede il reso, B e' l'estraneo
-- ============================================================
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _cliente AS
SELECT m.emittente_fiscale_id, c.*
  FROM _mondi m
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA legato all'emittente del
  --   mondo. Il documento porta ora il BA, e il guard emittente <-> BA lo guarda.
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba('RLS resi write', NULL, m.soggetto_ruolo_id) c
 WHERE m.lato = 'A';

-- Il DDT di A, portato fino a CONSEGNATO.
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3a): l'articolo
--   si COSTRUISCE. Ordine e bolla ammettono solo merce non solo-componente, e
--   su un database ricostruito il catalogo ha solo i cinque ONERE_* (servizi):
--   cercarlo dava NULL e la riga moriva su E_UOM_MISSING.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-RLS-RESI-WR', false) AS id;

CREATE TEMP TABLE _ddt AS
WITH d AS (
    -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il BA del cliente, non la sola
    --   utility — chk_ddt_ba_utility_insieme vuole tutti e due o nessuno.
    INSERT INTO vendite.ddt
        (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, emittente_fiscale_id,
         utility_id, billing_account_id, causale_trasporto_id)
    SELECT c.soggetto_ruolo_id,
           (SELECT st.id FROM config.stati_doc_ddt st WHERE st.codice_interno = 'DRAFT'),
           c.emittente_fiscale_id,
           c.utility_id,
           c.billing_account_id,
           (SELECT ct.id FROM config.causali_trasporto ct WHERE ct.attivo ORDER BY ct.id LIMIT 1)
      FROM _cliente c
    RETURNING id, uid, emittente_fiscale_id, destinatario_soggetto_ruolo_id
)
SELECT * FROM d;

INSERT INTO vendite.ddt_righe
    (ddt_id, riga_nr, articolo_id, descrizione, quantita, qta_operativa,
     prezzo_unitario, iva_id)
SELECT d.id, 1,
       (SELECT id FROM _art),
       'Riga DDT da rendere', 10, 10, 25.00,
       (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1)
  FROM _ddt d;

INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT d.id,
       (SELECT ti.id FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'CON'),
       '{"pgtap": true}'::jsonb
  FROM _ddt d;

-- ⛔ Tutti e tre i passi (la matrice non ammette il salto a CONSEGNATO), e
--   ciascuno col verbo: la porta sullo stato rifiuta l'UPDATE diretto. Il
--   percorso EMESSO -> SPEDITO -> CONSEGNATO lo segue il BB dalla matrice.
--   Il verbo legge la bolla nel perimetro di chi agisce: il contesto e'
--   l'operatore di A, che la possiede (i casi sotto aprono ciascuno il suo).
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx$;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', d.id, 'CONSEGNATO')
  FROM _ddt d;

-- Il reso in bozza dal builder: destinatario ed emittente li deriva il
-- normalize dalla bolla. La riga che il builder gli da' non pesa: il test
-- collauda la testata.
CREATE TEMP TABLE _reso AS
SELECT b.reso_id
  FROM dbops.fn_pgtap_crea_reso('RLS resi write', (SELECT id FROM _ddt), 1,
                                p_stato_codice_interno => 'DRAFT') b;

-- ⛔ Guard sul RISULTATO: se la fixture non si e' costruita il file deve
--   diventare ROSSO qui, non passare tre asserzioni a vuoto piu' in giu'.
DO $prereq$
BEGIN
    IF (SELECT count(*) FROM _reso) <> 1 OR (SELECT count(*) FROM _mondi) <> 2 THEN
        RAISE EXCEPTION
            'fixture non costruita: % resi, % mondi (attesi 1 e 2)',
            (SELECT count(*) FROM _reso), (SELECT count(*) FROM _mondi);
    END IF;
END
$prereq$;

-- ============================================================
-- Il perimetro, esercitato
-- ============================================================
-- ⚠️ Solo FORCE: `vendite.resi` la RLS ce l'ha gia' accesa in permanenza. Il
--   FORCE serve perche' il runner e' l'owner, che altrimenti sarebbe esente.
ALTER TABLE vendite.resi FORCE ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, n_righe integer);

DO $casi$
DECLARE
    v_reso vendite.resi.id%TYPE;
    v_in   integer;
    v_out  integer;
    v_n    integer;
BEGIN
    SELECT reso_id INTO v_reso FROM _reso;
    SELECT auth_user_id INTO v_in  FROM _mondi WHERE lato = 'A';
    SELECT auth_user_id INTO v_out FROM _mondi WHERE lato = 'B';

    -- 1) L'operatore dell'azienda che possiede il reso.
    PERFORM script.fn_pgtap_set_contesto_operatore(v_in);
    UPDATE vendite.resi SET meta = meta WHERE id = v_reso;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('in_scope', v_n);

    -- 2) L'operatore dell'ALTRA azienda: la USING lo isola.
    PERFORM script.fn_pgtap_set_contesto_operatore(v_out);
    UPDATE vendite.resi SET meta = meta WHERE id = v_reso;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('off_scope', v_n);

    -- 3) Utente giusto, nessuna veste: la policy e' condizionata al ruolo, e
    --    senza ruolo non deve passare NIENTE. Il verso sbagliato — passare
    --    tutto — sarebbe il difetto peggiore e non farebbe rumore.
    PERFORM set_config('app.current_user_id', v_in::text, true);
    PERFORM set_config('app.ruolo_applicativo', '', true);
    UPDATE vendite.resi SET meta = meta WHERE id = v_reso;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('senza_veste', v_n);
END
$casi$;

ALTER TABLE vendite.resi NO FORCE ROW LEVEL SECURITY;

-- ===================== Asserzioni =====================
SELECT is((SELECT n_righe FROM _res WHERE caso = 'in_scope'), 1,
    '1. OPERATORE in-scope: l''UPDATE tocca la riga (perimetro emittente ok)');

SELECT is((SELECT n_righe FROM _res WHERE caso = 'off_scope'), 0,
    '2. OPERATORE di un''altra azienda: zero righe (la USING isola per emittente)');

SELECT is((SELECT n_righe FROM _res WHERE caso = 'senza_veste'), 0,
    '3. utente noto ma senza veste applicativa: zero righe, fail-closed');

SELECT * FROM finish();
ROLLBACK;
