-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture costruisce un'AZIENDA — emittente fiscale,
--   utente tecnico e identita' digitale (dbops.fn_pgtap_crea_emittente_operatore)
--   — e un operatore dentro un perimetro non crea l'azienda in cui lavora.
--   E' il criterio 2 di scripts/testpgtap.sh.
-- pgTAP test — il billing account e' OBBLIGATORIO su attivita_fatturabili,
--   e il guard di coerenza BA/utility valida DAVVERO.
--   ChangeSet: 20260910-25 (NOT NULL + backfill), 20260910-26 (guard).
--   Brief: brief-db-perimetro-emittente-righe-documento.md §11.13
--
-- Elenco test (plan 6):
--   1) struttura: billing_account_id e' NOT NULL
--   2) ⛔ struttura: il guard non porta piu' l'uscita anticipata
--   3) la catena costruisce una riga fatturabile, e il BA c'e'
--   4) ⛔ IL GUARD MORDE: un BA di un'altra istanza di utility e' RIFIUTATO
--   5) ⭐ e il gemello positivo: un BA coerente passa
--   6) ⛔ l'invariante sui dati: nessuna riga dissente dal proprio BA
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' `billing_account_id` E' OBBLIGATORIO — l'argomento e' di dominio.
--   Se un'attivita' e' FATTURABILE deve avere un billing account. E la tabella
--   BA esiste apposta, separata da `clienti`, per rendere possibile la
--   fatturazione PRIMA che un cliente sia definito — l'utility del gas che
--   fattura un allaccio. ⇒ «non c'e' ancora un cliente» non e' un motivo per
--   cui il BA possa mancare: e' la ragione per cui il BA esiste.
--   ⭐ E la struttura lo conferma da sola: `commessa_id` e' NOT NULL e
--   `vendite.commesse.billing_account_id` pure, quindi il BA e' raggiungibile
--   per una catena di sole colonne obbligatorie.
--
-- 🔴 E IL GUARD NON VALIDAVA NIENTE, fino al 2026-09-10.
--   `trgfn_attivita_fatturabili_guard_ba_coerenza` apriva con
--   `IF NEW.commessa_attivita_id IS NOT NULL THEN RETURN NEW`. Ma quella
--   colonna e' NOT NULL: l'uscita valeva per ogni riga che sopravvive. Un
--   presidio che sembrava esserci e non c'era, e che nessun cancello poteva
--   trovare — la funzione esiste, e' montata, e non solleva mai.
--   ⇒ Il test 2 lo pinna sul CORPO, cosi' rimetterla non passa inosservato.
--   ⚠️ E' un presidio sul TESTO: ha per perimetro questa funzione sola, e vale
--   finche' l'uscita si scrive cosi'. E' il motivo per cui accanto c'e' il
--   test 4, che misura il COMPORTAMENTO.
--
-- ⚠️ IL TEST 5 NON E' SIMMETRIA PER BELLEZZA. Senza, un guard che rifiutasse
--   *tutto* — per esempio per un confronto sbagliato — passerebbe il test 4 e
--   sembrerebbe piu' severo del necessario. Il verso positivo e' l'unico che
--   distingue «presidia» da «blocca».
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1..2. La struttura, e il corpo del guard
-- ============================================================
SELECT is(
    (SELECT a.attnotnull FROM pg_attribute a
      WHERE a.attrelid = 'vendite.attivita_fatturabili'::regclass
        AND a.attname  = 'billing_account_id'),
    true,
    '1. vendite.attivita_fatturabili.billing_account_id e'' NOT NULL'
);

-- ⛔ L'uscita anticipata non deve tornare. Si cerca la condizione, non la
--   riga intera: il rientro piu' probabile e' una riscrittura, non un
--   copia-incolla.
-- 🔴 E SI CERCA NEL CODICE PRIVATO DEI COMMENTI. La prima stesura guardava
--   `prosrc` intero ed era ROSSA: la stringa compare nel commento che spiega
--   il difetto, dentro la funzione stessa. E' la trappola nota del presidio
--   che si accende sulla PROSA invece che sul codice — qui l'ha presa subito
--   perche' il commento c'era gia'; su una funzione senza commenti avrebbe
--   fatto il contrario, cioe' sarebbe stata verde per la ragione sbagliata.
SELECT is(
    (SELECT position('commessa_attivita_id IS NOT NULL' IN
                     regexp_replace(p.prosrc, '--[^\n]*', '', 'g'))
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'trgfn_attivita_fatturabili_guard_ba_coerenza'),
    0,
    '2. il guard non esce piu'' su commessa_attivita_id: quella colonna e'' NOT NULL, e l''uscita valeva per ogni riga'
);

-- ============================================================
-- La catena: azienda -> cliente/BA -> commessa -> attivita' -> emit
-- ============================================================
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE _cliente AS
SELECT c.*
  FROM _mondo m
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_cliente_ba(
      'AF billing account', NULL, m.soggetto_ruolo_id) c;

-- ⛔ Un SECONDO billing account, di un'altra istanza di utility: e' il caso
--   che il guard deve rifiutare, e che prima passava perche' usciva subito.
-- ⚠️ Si costruisce QUI, con il mondo e da owner, per due ragioni: creare un BA
--   non e' un gesto dell'operatore, e `uq_emittenti_fiscali_ba` e' UNIQUE sul
--   billing account — un BA ha esattamente un emittente, quindi questo resta
--   slegato. Al guard non serve: confronta istanze di utility, non emittenti.
CREATE TEMP TABLE _altro_ba AS
SELECT c.billing_account_id, c.istanza_utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba('AF billing account ALTRO') c;

-- ⚠️ L'articolo se lo costruisce: `catalogo/articoli.csv` e' vuoto, quindi su
--   un database ricostruito da zero non ce n'e' nessuno.
CREATE TEMP TABLE _articolo AS
WITH a AS (
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id)
    SELECT 'PGTAP-AF-BA', 'Articolo pgTAP AF billing account',
           (SELECT um.id FROM catalogo.unita_misura um ORDER BY um.id LIMIT 1)
    RETURNING id, uom_id
)
SELECT id AS articolo_id, uom_id FROM a;

-- ⭐ Da qui si lavora NEI PANNI DELL'OPERATORE che la fixture ha appena
--   creato: la catena commessa -> attivita' -> emit e' esattamente quella che
--   gira l'applicazione, e girarla da owner non eserciterebbe ne' la RLS di
--   `vendite.commesse` ne' il guard di scope emittente.
-- ⚠️ Il mondo (azienda, cliente, articolo) resta costruito da owner: un
--   operatore dentro un perimetro non crea l'azienda in cui lavora.
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;

CREATE TEMP TABLE _commessa AS
SELECT vendite.fn_get_or_create_commessa(
    p_billing_account_id     => (SELECT billing_account_id FROM _cliente),
    p_utility_id             => (SELECT utility_id FROM _cliente),
    p_tipo_commessa          => 'AUTO',
    p_policy_fatturazione    => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa     => 'NORMALE',
    p_competenza_dal         => date_trunc('month', script.fn_data_operativa())::date,
    p_competenza_al          => (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
    p_meta                   => jsonb_build_object('test_scope', 'pgtap_af_ba_notnull'),
    p_force_new              => true
) AS commessa_id;

CREATE TEMP TABLE _attivita AS
SELECT r.attivita_id AS commessa_attivita_id
  FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM _commessa),
    p_segment_key                   => ('SEG-AFBA-' || substr(md5(clock_timestamp()::text), 1, 12))::varchar,
    p_articolo_id                   => (SELECT articolo_id FROM _articolo),
    p_istanza_utility_id            => (SELECT istanza_utility_id FROM _cliente),
    p_data_attivita                 => script.fn_data_operativa(),
    p_uom_id                        => (SELECT uom_id FROM _articolo),
    p_quantita                      => 1.000000,
    p_competenza_mese               => date_trunc('month', script.fn_data_operativa())::date,
    p_competenza_dal                => date_trunc('month', script.fn_data_operativa())::date,
    p_competenza_al                 => (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
    p_prezzo_snapshot               => 50.0000000000,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_stato_approvazione            => 'APPROVATA',
    p_stato_emissione               => 'NON_EMESSA',
    p_sorgente_tipo_id              => (SELECT s.id FROM config.sorgenti s
                                         WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1),
    p_sorgente_uid                  => (SELECT commessa_id FROM _commessa)::text,
    p_tipo_movimento                => 'NORMALE',
    p_meta                          => jsonb_build_object('case', 'AF_BA_NOTNULL')
  ) r;

SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id      => (SELECT commessa_id FROM _commessa),
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1),
    p_sorgente_uid     => (SELECT commessa_id FROM _commessa)::text
);

UPDATE vendite.commesse
   SET stato_commessa_id = (SELECT s.id FROM vendite.stati_commessa s
                             WHERE s.codice_interno = 'PRONTA_FATTURAZIONE')
 WHERE id = (SELECT commessa_id FROM _commessa);

CREATE TEMP TABLE _emit AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id  => (SELECT commessa_id FROM _commessa),
    p_only_approved => true,
    p_dry_run       => false);

CREATE TEMP TABLE _af AS
SELECT af.id, af.billing_account_id, af.istanza_utility_id
  FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM _attivita);

SELECT ok(
    (SELECT count(*) = 1 AND bool_and(billing_account_id IS NOT NULL) FROM _af),
    '3. la catena produce una riga fatturabile, e il billing account c''e'''
);

-- ============================================================
-- 4..5. Il guard, nei due versi
-- ============================================================
DO $prova$
DECLARE
    v_af  vendite.attivita_fatturabili.id%TYPE;
    v_ba  anagrafiche.billing_account.id%TYPE;
    v_iu  anagrafiche.billing_account.istanza_utility_id%TYPE;
BEGIN
    SELECT id INTO v_af FROM _af;
    SELECT billing_account_id, istanza_utility_id INTO v_ba, v_iu FROM _altro_ba;

    -- ⛔ Il BA cambia, l'istanza di utility della riga NO: incoerenti.
    BEGIN
        UPDATE vendite.attivita_fatturabili SET billing_account_id = v_ba WHERE id = v_af;
        PERFORM set_config('pgtap.incoerente', 'PASSATA', true);
    EXCEPTION WHEN raise_exception THEN
        PERFORM set_config('pgtap.incoerente', 'RIFIUTATA', true);
    END;

    -- ⭐ Il gemello positivo: BA e istanza cambiano INSIEME, quindi coerenti.
    BEGIN
        UPDATE vendite.attivita_fatturabili
           SET billing_account_id = v_ba, istanza_utility_id = v_iu
         WHERE id = v_af;
        PERFORM set_config('pgtap.coerente', 'PASSATA', true);
    EXCEPTION WHEN raise_exception THEN
        PERFORM set_config('pgtap.coerente', 'RIFIUTATA', true);
    END;
END
$prova$;

SELECT is(current_setting('pgtap.incoerente', true), 'RIFIUTATA',
          '4. IL GUARD MORDE: un billing account di un''altra istanza di utility e'' rifiutato');

SELECT is(current_setting('pgtap.coerente', true), 'PASSATA',
          '5. e un billing account COERENTE passa: il guard presidia, non blocca');

-- ============================================================
-- 6. L'invariante sui dati
-- ============================================================
-- ⚠️ Su un database ricostruito questa asserzione e' vera a vuoto (nessuna
--   riga): non prova il guard — quello lo provano il 4 e il 5 — ma dice che il
--   pregresso non lo contraddice.
SELECT is_empty(
    $$SELECT af.id
        FROM vendite.attivita_fatturabili af
        JOIN anagrafiche.billing_account b ON b.id = af.billing_account_id
       WHERE af.istanza_utility_id IS DISTINCT FROM b.istanza_utility_id$$,
    '6. nessuna riga fatturabile dissente dall''istanza di utility del proprio billing account'
);

SELECT * FROM finish();

ROLLBACK;
