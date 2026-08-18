-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- ⛔ Verde dopo 20260819-05 (intestazione + registri del secondo emittente).
--    ⭐ Il test 6 e' verde GIA' ORA: il guard sulla disattivazione esisteva
--    gia', ed e' questo file ad averlo scoperto — il piano lo dava per
--    mancante perche' cercava la famiglia prevent_deactivate_if_children.
--
-- Indice test (1..6):
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
--      account mappati fallisce
--
-- ⚠️ SCOSTAMENTO DAL PIANO, dichiarato. Il §8/5e chiedeva di esercitare il
--    test 6 «su un emittente di prova, non su 72 o 159». Si usa invece un
--    emittente reale, e per due ragioni: (a) il file gira in una transazione
--    che finisce SEMPRE in ROLLBACK, quindi la distinzione non protegge
--    niente; (b) costruire un emittente sintetico vorrebbe dire soddisfare
--    tre guard (ruolo emi_fis, normalize, default bootstrap) e finirebbe per
--    collaudare la fixture invece della configurazione vera.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Riferimenti — per CHIAVE NATURALE, mai per id nudo.
-- ============================================================
CREATE TEMP TABLE tmp_ref_reg AS
SELECT
  (SELECT m.emittente_soggetto_ruolo_id
     FROM anagrafiche.emittenti_fiscali_billing_account m
    WHERE m.is_default IS TRUE)                                          AS ef_principale,
  (SELECT ef.soggetto_ruolo_id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
      AND ef.soggetto_ruolo_id IS DISTINCT FROM
          (SELECT m2.emittente_soggetto_ruolo_id
             FROM anagrafiche.emittenti_fiscali_billing_account m2
            WHERE m2.is_default IS TRUE)
    ORDER BY ef.id LIMIT 1)                                              AS ef_secondo,
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
-- 6) ⭐ IL GUARD DI D-P6-1 — CHE ESISTEVA GIA', e l'ha scoperto questo test.
--    Il cancello sta sulla DISATTIVAZIONE e non sulla numerazione: il
--    problema si ferma dove nasce — chi disattiva — invece che davanti a un
--    operatore che sta fatturando e non capisce perche' non puo'.
--    ⚠️ Lo tiene anagrafiche.trgfn_emittenti_fiscali_guard_attivo, un guard
--    SCRITTO A MANO con codice dedicato (E_EMITTENTE_DISATTIVAZIONE_BLOCCATA),
--    non un trigger della famiglia prevent_deactivate_if_children. Il piano
--    cercava quella famiglia e concludeva che il presidio mancasse: cercava
--    nel posto sbagliato. ⭐ Qui il test smette di essere una richiesta e
--    diventa il PRESIDIO di un invariante che nessuno aveva fissato.
--    Il discriminante e' la FRASE: senza, throws_ok accetterebbe qualunque
--    errore, compreso un guard diverso che scatta per un'altra ragione.
-- ============================================================
SELECT throws_like(
  format($$ UPDATE anagrafiche.emittenti_fiscali SET attivo = false
             WHERE soggetto_ruolo_id = %s $$,
         (SELECT ef_secondo FROM tmp_ref_reg)),
  '%mapping billing_account presente%',
  '6) il guard morde (ed esisteva gia''): un emittente con billing account mappati non si disattiva'
);

SELECT * FROM finish();
ROLLBACK;
