-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_dash_competenza_gruppi — colonne del CLIENTE DI FATTURAZIONE
-- Brief: brief-db-dash-competenza-gruppi-cliente-e-ricerca (D-2/D-3/D-4/D-5, §5.2)
-- Changeset coperti: 20260817-04, 20260817-05
-- ------------------------------------------------------------
-- Indice test (1..8):
--  1) vw_dash_competenza_attivita espone billing_account_id
--  2) vw_dash_competenza_gruppi espone le quattro colonne nuove
--  3) ⭐ ANTI FAN-OUT: le colonne nuove non aggiungono righe
--  4) senza padre: ba_fatturazione_id = BA della commessa
--  5) ⭐ con padre: ba_fatturazione_id = il PADRE, come fn_build_fattura_key
--  6) ⭐ con padre: ba_codice_fatturazione = codice del PADRE, non del figlio
--  7) D-2: cliente_fatturazione_display coincide con cliente_display
--  8) D-5: mai id_fiscale valorizzato senza ba_codice_fatturazione
-- ------------------------------------------------------------
-- ⭐ IL TEST 3 e' quello che protegge il vincolo piu' importante del brief.
--    Se le colonne nuove moltiplicassero le righe cambierebbero il conteggio e
--    i totali della lista, e il «seleziona tutto» della pagina manderebbe
--    DOPPIONI a fatturare. Non e' un timore teorico: sarebbe bastato un join a
--    anagrafiche.resellers_billing_account, che e' 1-N per billing account.
--    Il confronto e' con la grana VECCHIA ricalcolata a mano dalla vista base,
--    non con un numero scritto qui: cosi' resta valido al crescere dei dati.
--
-- ⭐ I TEST 5 e 6 sono il cuore del brief. `cliente_display` mostra il soggetto
--    del BA della COMMESSA (il figlio); `fn_build_fattura_key` aggrega invece su
--    COALESCE(parent_account_id, billing_account_id) — il PADRE. Se la vista
--    esponesse il figlio, filtrare per cliente darebbe una selezione che NON
--    corrisponde alla fattura che ne nasce: l'esatto contrario dello scopo.
--    ⚠️ Per questo il padre viene COSTRUITO e non cercato: un ramo si verifica
--    dal percorso che lo attraversa. Se i dati non permettono di costruirlo, i
--    due test SKIPPANO con motivo esplicito invece di passare per assenza di
--    casi — che sarebbe verde per sottrazione.
--
-- ⚠️ COSA QUESTO FILE NON COPRE (limite dichiarato). Il caso (b) della
--    decisione D-5 — BA della riga visibile ma PADRE fuori scope RLS, quindi
--    ba_fatturazione_id valorizzato e le tre descrittive NULL — non e'
--    esercitato: servirebbe un padre mappato a un emittente fuori dallo scope
--    dell'operatore, cioe' un albero che attraversa due emittenti. Quella e'
--    proprio la cosa che il cantiere
--    brief-db-perimetro-emittente-liste-e-gerarchia-ba si propone di rendere
--    IMPOSSIBILE (P-1). Costruirla qui significherebbe seminare il difetto per
--    collaudare la rete. Il test 8 verifica l'invariante che regge quel caso
--    (le descrittive non si valorizzano a meta'), che e' cio' che serve davvero.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Contesto applicativo: questo test gira come l'APPLICAZIONE (ruolo
--   OPERATORE + RLS attiva), non come owner. Senza, l'owner salterebbe la RLS e
--   il test non eserciterebbe mai le policy su anagrafiche.billing_account —
--   che sono proprio quelle da cui dipende la decisione D-5.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: nel DB ce ne sono 365, scattano al COMMIT, e qui il
--   COMMIT non arriva mai (si chiude in ROLLBACK). Senza questa riga non
--   verrebbero mai esercitati e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture — riferimenti
-- ⚠️ Niente LIMIT 1 senza ORDER BY, e la scelta si fa UNA volta sola: due
--   sotto-select indipendenti sullo stesso predicato possono pescare righe
--   diverse quando il planner cambia.
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE. Prima si pescava
--   il primo BA autonomo con un emittente risolvibile: da zero non c'era, e la
--   commessa moriva su «p_billing_account_id obbligatorio». Il BA costruito e'
--   autonomo per costruzione (il padre lo mettiamo noi, sotto) e legato
--   all'azienda di chi agisce. Articolo onere e tipo documento restano letture
--   del catalogo di seed (articoli_onere.csv, config.tipi_doc_fiscale).
CREATE TEMP TABLE tmp_cf_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('dash competenza gruppi cliente');

CREATE TEMP TABLE tmp_cf_ba AS
SELECT ba.id, ba.utility_id, ba.istanza_utility_id, ba.soggetto_ruolo_id,
       ba.categoria_cliente_id, ba.codice, ba.parent_account_id
  FROM anagrafiche.billing_account ba
 WHERE ba.id = (SELECT billing_account_id FROM tmp_cf_cli);

CREATE TEMP TABLE tmp_cf_refs AS
SELECT
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND a.causale_onere_id IS NOT NULL
    ORDER BY a.id LIMIT 1)                            AS articolo_onere_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
      AND EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m
                   WHERE m.tipo_doc_fiscale_id = t.id)
    ORDER BY t.id LIMIT 1)                            AS tipo_doc_fiscale_id;

-- Commessa fixture sul BA scelto, con un onere: un gruppo sourceless
-- 'MAN:<commessa>' basta a far esistere una riga nella vista.
CREATE TEMP TABLE tmp_cf_comm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT id FROM tmp_cf_ba),
  p_utility_id             => (SELECT utility_id FROM tmp_cf_ba),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2082-03-01',
  p_competenza_al          => DATE '2082-03-31',
  p_meta                   => jsonb_build_object('test_scope', 'pgtap_gruppi_cliente'),
  p_force_new              => true
) AS commessa_id;

SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => (SELECT commessa_id FROM tmp_cf_comm),
  p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_cf_ba),
  p_articolo_onere_id   => (SELECT articolo_onere_id FROM tmp_cf_refs),
  p_importo             => 250.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_cf_refs),
  p_motivo              => 'pgtap cliente fatturazione',
  p_data_attivita       => DATE '2082-03-10'
);

-- ============================================================
-- ⚠️ SESSIONE OPERATORE. La vista base e' FAIL-CLOSED senza GUC:
--   fn_get_emittenti_scope_sr_ids(NULL) restituisce l'array VUOTO, e il
--   predicato `sr_ids IS NULL OR emittente = ANY(sr_ids)` non lascia passare
--   nulla. Un test che non impostasse la sessione misurerebbe zero per il
--   motivo sbagliato.
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): la sessione e' quella del CONTESTO, aperta in
--   testa. Prima qui si pescava il primo operatore non super admin, gli si
--   riscriveva il perimetro (config.user_emittenti_fiscali) sull'emittente
--   della commessa e ci si ripuntava la GUC: era un utente pescato, e su un
--   altro database poteva essere chiunque. Ora il BA e' dell'azienda di chi
--   agisce, quindi l'emittente della commessa e' gia' nel suo perimetro.

-- ============================================================
-- TEST 1: la colonna che il -04 aggiunge alla vista base. Senza, il -05 non ha
--   da dove prendere il BA e l'intera funzione non esiste.
-- ============================================================
SELECT has_column(
  'vendite', 'vw_dash_competenza_attivita', 'billing_account_id',
  '1) vw_dash_competenza_attivita espone billing_account_id (changeSet -04)'
);

-- ============================================================
-- TEST 2: le quattro colonne del -05, in un colpo solo.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name   = 'vw_dash_competenza_gruppi'
      AND column_name IN ('ba_fatturazione_id', 'ba_codice_fatturazione',
                          'cliente_fatturazione_display', 'id_fiscale')),
  4,
  '2) vw_dash_competenza_gruppi espone le quattro colonne del cliente di fatturazione'
);

-- ============================================================
-- TEST 3 ⭐ ANTI FAN-OUT. Il numero di righe della vista deve coincidere con la
--   grana VECCHIA — l'aggregazione senza le colonne nuove — ricalcolata qui
--   dalla vista base. Entrambi i lati leggono la stessa sorgente sotto lo
--   stesso scope, quindi il confronto e' onesto.
--
--   ⚠️ Il confronto e' su TUTTO il perimetro visibile, non sulla sola commessa
--   fixture: un fan-out si manifesta dove i dati sono ricchi, e la fixture e'
--   povera per costruzione. La fixture serve a garantire che il perimetro non
--   sia vuoto — se lo fosse, 0 = 0 sarebbe verde per sottrazione, ed e' il
--   motivo del ramo skip.
-- ============================================================
SELECT CASE
  WHEN (SELECT count(*) FROM vendite.vw_dash_competenza_gruppi) = 0
  THEN skip('perimetro vuoto per questo operatore: il confronto 0 = 0 non verificherebbe nulla', 1)
  ELSE is(
    (SELECT count(*)::bigint FROM vendite.vw_dash_competenza_gruppi),
    (SELECT count(*)::bigint FROM (
        SELECT a.competenza_mese, a.gruppo_key, a.sorgente_tipo_id, a.sorgente_uid,
               a.commessa_id, a.commessa_codice, a.emittente_soggetto_ruolo_id,
               a.cliente_display, a.stadio, a.commessa_emittibile,
               a.commessa_stato_codice_interno, a.commessa_stato_descrizione
          FROM vendite.vw_dash_competenza_attivita a
         GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12
     ) vecchia_grana),
    '3) le colonne del cliente non aggiungono righe: la grana resta quella di prima'
  )
END;

-- ============================================================
-- TEST 4: ramo SENZA padre. Il BA della fixture non ne ha (scelto cosi'),
--   quindi ba_fatturazione_id deve essere il BA stesso.
-- ============================================================
SELECT is(
  (SELECT g.ba_fatturazione_id
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.commessa_id = (SELECT commessa_id FROM tmp_cf_comm)
      AND g.gruppo_key  = 'MAN:' || (SELECT commessa_id::text FROM tmp_cf_comm)),
  (SELECT id FROM tmp_cf_ba),
  '4) senza padre: ba_fatturazione_id = billing account della commessa'
);

-- ============================================================
-- Fixture del PADRE, costruita e non cercata.
--
-- Un secondo BA sullo STESSO istanza_utility con una utility DIVERSA:
--   · uq_billing_instance_utility(istanza_utility_id, utility_id) -> ok
--   · trgfn_billing_account_guard_soggetto_coerenza_istanza: stesso istanza
--     ⇒ stesso soggetto -> ok
--   · trgfn_billing_account_guard_normalize §2.2 (coerenza CF padre/figlio):
--     stesso soggetto ⇒ stesso id_fiscale_univoco_cf_piva -> ok
--
-- `codice` non si passa: lo genera trgfn_billing_account_gen_codice (BEFORE).
-- `valido_dal` e' obbligatorio sul FIGLIO quando si aggancia un padre.
--
-- Se non esiste una seconda utility utilizzabile il padre non e' costruibile:
-- i test 5 e 6 skippano con motivo, invece di passare per assenza di casi.
-- ============================================================
CREATE TEMP TABLE tmp_cf_utility_altra AS
SELECT u.id
  FROM config.utilities u
 WHERE u.id <> (SELECT utility_id FROM tmp_cf_ba)
   AND NOT EXISTS (
       SELECT 1 FROM anagrafiche.billing_account b2
        WHERE b2.istanza_utility_id = (SELECT istanza_utility_id FROM tmp_cf_ba)
          AND b2.utility_id = u.id)
 ORDER BY u.id
 LIMIT 1;

CREATE TEMP TABLE tmp_cf_padre (id bigint, codice varchar);

DO $padre$
DECLARE
  v_utility_altra config.utilities.id%TYPE;
  v_padre_id      anagrafiche.billing_account.id%TYPE;
BEGIN
  SELECT id INTO v_utility_altra FROM tmp_cf_utility_altra;
  IF v_utility_altra IS NULL THEN
    RETURN;                       -- padre non costruibile: i test 5/6 skippano
  END IF;

  -- ⚠️ `validita` NON si valorizza: e' una colonna GENERATA, derivata da
  --   valido_dal/valido_al. Passarla fa fallire l'INSERT con «impossibile
  --   inserire un valore non DEFAULT in una colonna generata».
  INSERT INTO anagrafiche.billing_account (
      istanza_utility_id, soggetto_ruolo_id, utility_id,
      categoria_cliente_id, valido_dal, valido_al)
  SELECT b.istanza_utility_id, b.soggetto_ruolo_id, v_utility_altra,
         b.categoria_cliente_id, DATE '2082-01-01', NULL
    FROM tmp_cf_ba b
  RETURNING id INTO v_padre_id;

  -- ⚠️ Padre e figlio in DUE istruzioni, non in una CTE sola: le CTE che
  --   scrivono condividono la stessa snapshot, e una policy che risolve il
  --   perimetro dal padre non lo troverebbe (nega fail-closed).
  UPDATE anagrafiche.billing_account
     SET parent_account_id = v_padre_id,
         valido_dal        = COALESCE(valido_dal, DATE '2082-01-01')
   WHERE id = (SELECT id FROM tmp_cf_ba);

  INSERT INTO tmp_cf_padre (id, codice)
  SELECT b.id, b.codice FROM anagrafiche.billing_account b WHERE b.id = v_padre_id;
END
$padre$;

-- ============================================================
-- TEST 5 ⭐ Con il padre agganciato, ba_fatturazione_id deve spostarsi sul
--   PADRE — lo stesso elemento che fn_build_fattura_key mette in chiave. Se
--   restasse il figlio, filtrare per cliente darebbe una selezione che non
--   corrisponde alla fattura che ne nasce.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_cf_padre)
  THEN skip('nessuna utility libera sull''istanza: padre non costruibile su questi dati', 1)
  ELSE is(
    (SELECT g.ba_fatturazione_id
       FROM vendite.vw_dash_competenza_gruppi g
      WHERE g.commessa_id = (SELECT commessa_id FROM tmp_cf_comm)
        AND g.gruppo_key  = 'MAN:' || (SELECT commessa_id::text FROM tmp_cf_comm)),
    (SELECT id FROM tmp_cf_padre),
    '5) con padre: ba_fatturazione_id = il PADRE (come fn_build_fattura_key)'
  )
END;

-- ============================================================
-- TEST 6 ⭐ Il codice BA e' l'UNICO dato che differisce fra figlio e padre
--   (ragione sociale e id fiscale coincidono per costruzione, guard §2.2).
--   Per questo e' la colonna che rende distinguibili due alberi dello stesso
--   soggetto — ed e' obbligatoria nell'etichetta del filtro cliente.
--   Se qui uscisse il codice del FIGLIO, la colonna direbbe la cosa sbagliata
--   proprio nel solo caso in cui serve.
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_cf_padre)
  THEN skip('nessuna utility libera sull''istanza: padre non costruibile su questi dati', 1)
  ELSE is(
    (SELECT g.ba_codice_fatturazione
       FROM vendite.vw_dash_competenza_gruppi g
      WHERE g.commessa_id = (SELECT commessa_id FROM tmp_cf_comm)
        AND g.gruppo_key  = 'MAN:' || (SELECT commessa_id::text FROM tmp_cf_comm)),
    (SELECT codice FROM tmp_cf_padre),
    '6) con padre: ba_codice_fatturazione = codice del PADRE, non del figlio'
  )
END;

-- ============================================================
-- TEST 7 (D-2): la premessa su cui poggia «cliente_display non si tocca».
--   Il guard trgfn_billing_account_guard_normalize §2.2 impone lo stesso
--   id_fiscale_univoco_cf_piva fra padre e figlio, e anagrafiche.soggetti ha
--   UNIQUE(stato_id, id_fiscale_univoco_cf_piva): stesso codice fiscale ⇒
--   stesso soggetto ⇒ stessa ragione sociale.
--   ⚠️ Se questo test diventa rosso NON va silenziato: significa che la
--   premessa di D-2 non regge su questi dati, e allora `cliente_display` va
--   ridefinito sul BA di fatturazione.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.cliente_display IS NOT NULL
      AND g.cliente_fatturazione_display IS NOT NULL
      AND g.cliente_display IS DISTINCT FROM g.cliente_fatturazione_display),
  0,
  '7) D-2: dove entrambi sono risolti, cliente_display = cliente_fatturazione_display'
);

-- ============================================================
-- TEST 8 (D-5): le tre colonne descrittive descrivono TUTTE il BA di
--   fatturazione, e non si valorizzano a meta'. Una riga con l'id fiscale pieno
--   e il codice BA vuoto mostrerebbe come risolto un cliente che non lo e' —
--   ed e' esattamente il ripiego sui dati del figlio che il changeSet -05
--   rifiuta di fare.
--   `billing_account.codice` e' NOT NULL: se ba_codice_fatturazione e' NULL,
--   il padre non e' stato raggiunto affatto.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_dash_competenza_gruppi g
    WHERE g.id_fiscale IS NOT NULL
      AND g.ba_codice_fatturazione IS NULL),
  0,
  '8) D-5: mai id_fiscale valorizzato senza ba_codice_fatturazione'
);

SELECT * FROM finish();
ROLLBACK;
