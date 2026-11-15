-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: P-6 / 5e — i registri di numerazione sono intestati a un emittente
--       (changeset 20260819-04 + automazione + 20260819-05)
-- ------------------------------------------------------------
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto del test e' la CONFIGURAZIONE FISCALE di
--   TUTTI gli emittenti — per definizione anche di quello che l'operatore
--   collegato non puo' vedere. Asserire «nessun registro e' raggiungibile da
--   due emittenti» leggendo come applicazione misurerebbe solo la meta' del
--   perimetro visibile, e il verde sarebbe per sottrazione. E' il caso 2 del
--   criterio in scripts/testpgtap.sh: la fixture guarda un mondo che
--   l'operatore non deve vedere.
--
-- pgtap-contesto: escluso — discende dalla riga sopra: se il test gira come
--   owner PROPRIO PER non essere limitato al perimetro di un operatore,
--   chiamare fn_pgtap_set_contesto_operatore() rimetterebbe quel limite
--   dall'altra parte. Le GUC app.* qui non servono: nessuna delle tabelle
--   lette (registri_fatturazione, tipi_doc_fiscale_registri,
--   emittenti_fiscali) ha RLS, e cio' che si asserisce e' una proprieta'
--   GLOBALE della configurazione fiscale — «nessun registro e' raggiungibile
--   da due emittenti» — che ha senso solo vedendoli tutti.
--
-- ⛔ Verde dopo 20260819-05 (intestazione + registri del secondo emittente).
--    ⭐ Il test 6 era verde gia' allora: il guard sulla disattivazione esisteva
--    gia', ed e' questo file ad averlo scoperto — il piano lo dava per
--    mancante perche' cercava la famiglia prevent_deactivate_if_children.
--
-- ⛔ rev 2026-08-20 — IL TEST 6 E' DIVENTATO ROSSO DA SOLO, senza che nessuno
--    lo toccasse, ed e' il caso che vale la pena ricordare. Il 19 pomeriggio
--    era verde; la notte l'automazione ATTIVO ha generato un trigger generico
--    sulla stessa coppia (la FK era appena nata con 20260819-04), quello ha
--    cominciato a scattare PRIMA per ordine alfabetico, e il messaggio letto
--    dall'operatore e' cambiato. Nessun comportamento rotto: solo un'altra voce
--    che parlava. Da qui 20260820-01 (il messaggio generico impara a nominare
--    la tabella) e 20260820-02 (via il doppione scritto a mano).
--    ⚠️ Il test 6 di oggi asserisce quindi un'ALTRA cosa, e il test 7 e' nuovo:
--    verde solo dopo quei due changeSet.
--
-- Indice test (1..7):
--   1) ogni registro attivo ha un emittente: e' il presidio che impedisce di
--      tornare indietro a un registro «di nessuno»
--   2) ⭐ nessuna coppia (tipo_doc, natura) porta due emittenti sullo STESSO
--      registro — e' l'asserzione che dice che i BUCHI NELLA SERIE (C-4) non
--      possono ripresentarsi
--   3) per l'emittente principale il registro si risolve, ed e' SUO
--   4) ⭐ per il secondo si risolve un registro DIVERSO
--   5) ⭐ EM-1 CHIUSA: la catena reale passa l'emittente — l'emittente di un
--      billing account arriva fino alla scelta del registro
--   6) ⭐ il guard di D-P6-1 morde: disattivare un emittente con billing
--      account mappati fallisce, con la frase del ramo B (figlia senza attivo)
--   7) ⛔ il trigger generato che tiene quella regola esiste — e' il costo
--      dichiarato di 20260820-02, reso misurabile
--
-- ⛔ rev 2026-10-13 — IL TEST 6 GIRA SU UN EMITTENTE COSTRUITO, come chiedeva
--    il piano (§8/5e: «su un emittente di prova, non su 72 o 159»).
--    Fino a oggi usava il secondo emittente REALE, e lo scostamento era
--    dichiarato qui: il ROLLBACK lo rendeva innocuo, e un emittente sintetico
--    sembrava costare tre guard. Il conto e' arrivato dai dati: dalla notte
--    del 2026-10-12 il 159 ha template e documenti generati, e disattivandolo
--    parla PRIMA il guard di documenti_generati (ordine dei nomi:
--    «...documenti_generati...» < «...emittenti_fiscali_billing_acco...»),
--    con un messaggio che non nomina la tabella attesa. Il test asseriva il
--    messaggio di un guard, ma lo chiedeva a un emittente di cui non
--    controllava i figli: verde finche' i dati non ne producevano altri.
--    Oggi i builder ci sono (dbops.fn_pgtap_crea_emittente, e
--    dbops.fn_pgtap_crea_cliente_ba col terzo parametro, da owner): un
--    emittente nuovo ha come unico figlio il billing account che gli si lega.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Riferimenti — per CHIAVE NATURALE, mai per id nudo.
-- rev 2026-10-27 (lotto 4 di D7): i due emittenti si COSTRUISCONO
--   (dbops.fn_pgtap_crea_emittente: nascendo, ciascuno fa nascere i propri
--   registri e la mappatura, vendite.fn_provision_registri_emittente), e il
--   billing account del test 5 si lega al secondo
--   (dbops.fn_pgtap_crea_cliente_ba col terzo parametro). Prima il
--   principale era «il» mapping is_default del DB e il secondo «il primo
--   emittente diverso»: da zero non c'erano, e il test 3 moriva su
--   E_CONFIG_MANCANTE. Tipo documento e natura restano letti dal catalogo
--   di seed. I test 1-2 leggono TUTTA la configurazione per scelta
--   (proprieta' globale, vedi la testata): non sono pesche.
-- ============================================================
CREATE TEMP TABLE tmp_ef_reg_principale AS
SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e;

CREATE TEMP TABLE tmp_ef_reg_secondo AS
SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e;

DO $t5$ BEGIN
  PERFORM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP registri t5', NULL, (SELECT soggetto_ruolo_id FROM tmp_ef_reg_secondo));
END $t5$;

CREATE TEMP TABLE tmp_ref_reg AS
SELECT
  (SELECT soggetto_ruolo_id FROM tmp_ef_reg_principale)                 AS ef_principale,
  (SELECT soggetto_ruolo_id FROM tmp_ef_reg_secondo)                    AS ef_secondo,
  (SELECT t.id FROM config.tipi_doc_fiscale t
    WHERE t.codice_interno = 'FRONTOFFICE' ORDER BY t.id LIMIT 1)        AS tipo_fo_id,
  (SELECT n.id FROM config.nature_doc_fiscale n
    WHERE n.codice_interno = 'FATTURA' ORDER BY n.id LIMIT 1)            AS natura_fatt_id;

-- ============================================================
-- 1) Nessun registro «di nessuno». Finche' un registro ha l'emittente a NULL
--    fa da fallback per CHIUNQUE (livello 4 della gerarchia di
--    fn_get_registro_id): e' esattamente la condizione che ha prodotto due
--    aziende che numerano sullo stesso registro.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.registri_fatturazione r
    WHERE r.attivo IS TRUE AND r.emittente_soggetto_ruolo_id IS NULL),
  0,
  '1) ogni registro attivo e'' intestato: nessuno fa piu'' da fallback per chiunque'
);

-- ============================================================
-- 2) ⭐ L'ASSERZIONE DI C-4. Il difetto non erano le collisioni di numero —
--    quelle le impedisce uq_fatture_numero — ma i BUCHI nella serie, che
--    nessun vincolo puo' vedere: due emittenti sullo stesso registro
--    ottengono numeri ALTERNATI, e ogni sezionale deve essere continuo.
--    Qui si verifica che nessun registro sia condiviso.
--    ⚠️ ONESTA' SUL VERDE: finche' i registri hanno l'emittente a NULL questo
--    test e' verde PER SOTTRAZIONE — count(DISTINCT NULL) e' 0, non 1. Da solo
--    non misura niente: e' il test 1 a renderlo significativo, pretendendo che
--    nessun registro attivo resti senza emittente. I due vanno letti insieme.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM (
      SELECT m.registro_id
        FROM vendite.tipi_doc_fiscale_registri m
        JOIN vendite.registri_fatturazione r ON r.id = m.registro_id
       WHERE r.attivo IS TRUE
       GROUP BY m.registro_id
      HAVING count(DISTINCT r.emittente_soggetto_ruolo_id) > 1) x),
  0,
  '2) nessun registro e'' raggiungibile da due emittenti: i buchi nella serie non possono ripresentarsi'
);

-- ============================================================
-- 3-4) La risoluzione, per ciascuno dei due. ⭐ Il test 4 e' quello che conta:
--      se i due emittenti risolvessero lo STESSO registro, l'intestazione
--      sarebbe cosmetica.
-- ============================================================
SELECT is(
  (SELECT r.emittente_soggetto_ruolo_id
     FROM vendite.fn_get_registro_id(
              p_tipo_doc_fiscale_id         => (SELECT tipo_fo_id FROM tmp_ref_reg),
              p_natura_doc_id               => (SELECT natura_fatt_id FROM tmp_ref_reg),
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id => (SELECT ef_principale FROM tmp_ref_reg)) g
     JOIN vendite.registri_fatturazione r ON r.id = g.registro_id),
  (SELECT ef_principale FROM tmp_ref_reg),
  '3) l''emittente principale risolve un registro, ed e'' intestato a lui'
);

SELECT isnt(
  (SELECT g.registro_id FROM vendite.fn_get_registro_id(
              p_tipo_doc_fiscale_id         => (SELECT tipo_fo_id FROM tmp_ref_reg),
              p_natura_doc_id               => (SELECT natura_fatt_id FROM tmp_ref_reg),
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id => (SELECT ef_secondo FROM tmp_ref_reg)) g),
  (SELECT g.registro_id FROM vendite.fn_get_registro_id(
              p_tipo_doc_fiscale_id         => (SELECT tipo_fo_id FROM tmp_ref_reg),
              p_natura_doc_id               => (SELECT natura_fatt_id FROM tmp_ref_reg),
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id => (SELECT ef_principale FROM tmp_ref_reg)) g),
  '4) il secondo emittente risolve un registro DIVERSO: l''intestazione non e'' cosmetica'
);

-- ============================================================
-- 5) ⭐ EM-1, CHIUSA E FISSATA. Il rilievo diceva «i registri intestati a un
--    emittente sono irraggiungibili dalla pipeline». Non e' piu' vero, e
--    questo test lo tiene: si parte da un BILLING ACCOUNT — cioe' da dove
--    parte davvero fn_build_fattura_key — e si arriva al registro.
--    ⚠️ Si passa da anagrafiche.fn_get_emittente_fiscale_id, che dal
--    20260819-03 delega a script.fn_get_ba_emittente_sr_id: il test copre
--    quindi anche la delega di 5b.
-- ============================================================
SELECT is(
  (SELECT r.emittente_soggetto_ruolo_id
     FROM anagrafiche.emittenti_fiscali_billing_account m
     CROSS JOIN LATERAL vendite.fn_get_registro_id(
              p_tipo_doc_fiscale_id         => (SELECT tipo_fo_id FROM tmp_ref_reg),
              p_natura_doc_id               => (SELECT natura_fatt_id FROM tmp_ref_reg),
              p_utility_id                  => NULL,
              p_emittente_soggetto_ruolo_id =>
                  anagrafiche.fn_get_emittente_fiscale_id(m.billing_account_id)) g
     JOIN vendite.registri_fatturazione r ON r.id = g.registro_id
    WHERE m.emittente_soggetto_ruolo_id = (SELECT ef_secondo FROM tmp_ref_reg)
      AND m.billing_account_id IS NOT NULL
    ORDER BY m.billing_account_id
    LIMIT 1),
  (SELECT ef_secondo FROM tmp_ref_reg),
  '5) EM-1: dal billing account si arriva al registro del SUO emittente — la catena passa l''emittente'
);

-- ============================================================
-- 6) ⭐ IL GUARD DI D-P6-1 MORDE. Il cancello sta sulla DISATTIVAZIONE e non
--    sulla numerazione: il problema si ferma dove nasce — chi disattiva —
--    invece che davanti a un operatore che sta fatturando e non capisce
--    perche' non puo'.
--
--    ⭐ CHI lo tiene e' cambiato il 2026-08-20, e la storia vale la pena.
--    Fino al 19 lo teneva anagrafiche.trgfn_emittenti_fiscali_guard_attivo,
--    scritto a mano: il piano cercava la famiglia generica
--    prevent_deactivate_if_children e concludeva che il presidio mancasse —
--    cercava nel posto sbagliato, non nel posto vuoto, e l'ha scoperto questo
--    test. Poi 20260819-04 ha dato alla tabella dei mapping una FK verso
--    emittenti_fiscali, l'automazione notturna ha generato il trigger
--    generico, e quello ha cominciato a scattare PRIMA (i BEFORE ROW vanno in
--    ordine alfabetico: «...billing_acco_b98811» < «...guard_attivo_upd»).
--    I due erano doppioni esatti — la tabella figlia non ha colonna `attivo`,
--    quindi anche il ramo «solo figli attivi» del generico coincideva — e
--    20260820-02 ha tolto quello a mano.
--
-- ⭐ E QUESTO FILE E' IL TESTIMONE DEL RAMO B (rev 2026-08-20, 20260820-08).
--    Il guard ha due rami e due codici: `emittenti_fiscali_billing_account`
--    NON ha una colonna attivo, quindi blocca su QUALUNQUE riga collegata e
--    il rimedio e' TOGLIERLE — codice E_ATTIVO_BLOCK_CHILDREN_EXIST (125),
--    messaggio SENZA la parola «attive». Il ramo A (figlia con la colonna, si
--    disattivano) e' presidiato da
--    db/pgtap/dbops/test-trgfn-prevent-deactivate-if-children-pdp.sql (test 4)
--    e da db/pgtap/catalogo/test-fn-riattiva-articolo-v1.sql (test 1).
--    ⚠️ Si asserisce la frase ESATTA del ramo B: le due frasi si escludono
--    («righe collegate attive» contro «righe collegate»), quindi se il guard
--    sbagliasse ramo questo test diventerebbe rosso — ed e' il suo secondo
--    mestiere. La frase non nomina tabelle (brief-db-revisione-dbops, S-BE-1):
--    quale tabella blocca sta nel contesto del diario, e l'emittente costruito
--    qui ha un solo figlio, il billing account.
-- ============================================================
-- L'emittente del test 6: costruito, con un solo figlio — il billing account
-- che gli si lega qui (vedi la nota in testa, rev 2026-10-13).
CREATE TEMP TABLE tmp_ef_t6 AS
SELECT e.emittente_fiscale_id, e.soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_emittente() e;

DO $t6$ BEGIN
  PERFORM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP registri t6', NULL, (SELECT soggetto_ruolo_id FROM tmp_ef_t6));
END $t6$;

SELECT throws_ok(
  format($$ UPDATE anagrafiche.emittenti_fiscali SET attivo = false
             WHERE id = %s $$,
         (SELECT emittente_fiscale_id FROM tmp_ef_t6)),
  'P0001',
  (SELECT m.messaggio FROM config.messaggi_errore m
    WHERE m.codice = 'E_ATTIVO_BLOCK_CHILDREN_EXIST' AND m.lingua = 'it'),
  '6) il guard morde, col ramo B: la frase di E_ATTIVO_BLOCK_CHILDREN_EXIST (figlia senza colonna attivo)'
);

-- ============================================================
-- 7) ⛔ IL COSTO DI 20260820-02, RESO VISIBILE.
--    Tolto il guard scritto a mano, la regola vive in un trigger GENERATO
--    dall'automazione ATTIVO. Se un giorno la FK di
--    emittenti_fiscali_billing_account sparisse o cambiasse bersaglio,
--    l'automazione toglierebbe il trigger e il divieto se ne andrebbe IN
--    SILENZIO: nessun errore, nessun changeSet, solo un emittente che da
--    quel giorno si disattiva.
--    ⚠️ Questo non poteva essere una preCondition del changeSet: su un
--    database ricostruito da zero le automazioni girano in `ci_apply`, cioe'
--    DOPO 20_code, e la preCondition sarebbe rossa a ogni build. Il presidio
--    va qui, dove si misura a build finita.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
     JOIN pg_class c   ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     JOIN pg_proc p    ON p.oid = t.tgfoid
    WHERE n.nspname = 'anagrafiche'
      AND c.relname = 'emittenti_fiscali'
      AND p.proname = 'trgfn_prevent_deactivate_if_children'
      AND NOT t.tgisinternal
      -- la coppia esatta: figlia + colonna FK, lette dagli argomenti
      AND pg_get_triggerdef(t.oid) LIKE '%''emittenti_fiscali_billing_account'', ''emittente_soggetto_ruolo_id''%'),
  1,
  '7) il trigger generato che tiene la regola c''e'': se sparisse, il divieto se ne andrebbe in silenzio'
);

SELECT * FROM finish();
ROLLBACK;
