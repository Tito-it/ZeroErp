-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ⚠️ IL MOTIVO ORIGINALE E' DECADUTO IL 2026-08-26, e il
--   marcatore resta in attesa di D-5.
--   Era: «la fixture azzera vendite.commesse.emittente_soggetto_ruolo_id per
--   raggiungere il ramo emittente mancante di fn_check_commessa_pronta_fatturazione,
--   l'unica via rimasta per lo scenario tutte le azioni spente». Quella colonna
--   e' NOT NULL dal changeSet 20260826-41: l'UPDATE non e' piu' scrivibile da
--   NESSUNO, owner compreso, e lo scenario e' uscito dal modello (vedi la nota
--   estesa al test 14).
--   ⛔ Il marcatore NON si toglie qui: farlo significherebbe cambiare il ruolo
--   con cui gira tutto il file in un commit che sta chiudendo un'altra cosa, e
--   scoprire i rossi da RLS mescolati a questi. Va rivalutato quando D-5 si
--   chiude — brief-db-emittente-commessa-invariante §7.12.
-- pgTAP test per Zero ERP
-- Test: guard di USCITA dalla commessa (->CHIUSA / ->ANNULLATA),
--       arco IN_ESECUZIONE->CHIUSA e capabilities con enabled/reasons.
-- Brief: brief-db-guard-uscita-commessa-e-capabilities (2026-07-24).
--
-- PERCHE' ESISTE: CHIUSA e ANNULLATA sono stati TERMINALI (nessun arco uscente
-- in vendite.transizioni_stati_commessa) e non emittibili. Chiudere una commessa
-- con righe APPROVATE+NON_EMESSE le perde per sempre; annullarne una con righe
-- EMESSE le fa sparire dalla dashboard di competenza mentre le fatture restano
-- vive. Nessuna via applicativa di recupero -> il guard e' l'unica difesa.
--
-- SORGENTE UNICA: la regola vive nelle funzioni pure
-- script.fn_check_commessa_chiudibile / _annullabile, usate SIA dal guard
-- (che solleva) SIA da script.fn_available_actions_commessa (che espone
-- enabled/reasons). I test 5/9/12 verificano le fn, i test 6/13/15 il guard,
-- i test 7/8/10/14 le capabilities: se le due strade divergessero, questi
-- gruppi si contraddirebbero.
--
-- Nota fixture: NON si usa fn_emit (esige una ROOT source documentale reale).
-- Le righe EMESSE si creano direttamente via fn_upsert_commessa_attivita: il
-- guard di immutabilita' quantita' agisce su UPDATE, non su INSERT.
-- Il guard tipo_doc_emittibile scatta solo su APPROVATA+NON_EMESSA, ma il
-- tipo_doc si passa comunque ovunque per realismo.
--
-- Nota TAP: le chiamate di setup NON assertive stanno dentro blocchi DO/PERFORM.
-- Un `SELECT fn(...)` nudo emetterebbe righe di risultato nel flusso che
-- pg_prove interpreta come TAP, sporcando l'esito.
-- ------------------------------------------------------------
-- Indice test (1..17):
--   1   script.fn_check_commessa_chiudibile presente
--   2   script.fn_check_commessa_annullabile presente
--   3   matrice: arco APERTA->CHIUSA (2->5) presente, attivo e manuale (rev 2026-10-26)
--   4   codici errore 558/559 presenti a catalogo
--   5   [A] _chiudibile: motivo 559 con righe APPROVATE+NON_EMESSE
--   6   [A] ->CHIUSA con righe pendenti rifiutata
--   7   [A] capabilities: azione chiudi presente con enabled=false
--   8   [A] capabilities: reasons di chiudi porta il reason_key
--   9   [B] _chiudibile: [] quando non resta nulla di pendente
--  10   [B] capabilities in APERTA: chiudi esposta ed enabled=true
--  11   [B] ->CHIUSA da APERTA ammessa  <- chiude il vicolo cieco
--  12   [C] _annullabile: motivo 558 con righe EMESSE
--  13   [C] ->ANNULLATA con righe emesse rifiutata
--  14a  [C] da APERTA: annulla e chiudi spente, rendi_pronta accesa
--  14   [C] SKIP dichiarato: lo scenario «tutte spente» e' uscito dal modello (D-5)
--  15   [D] ->ANNULLATA senza righe emesse ammessa (dal verbo con conferma, rev 2026-10-12)
--  16   fn_get_commessa_stato espone commessa_codice e cliente_display
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): IN_ESECUZIONE
--   ritirato (C-3); il test 3 guarda l'arco che chiude il vicolo cieco nel
--   modello nuovo, APERTA->CHIUSA. Sullo scratch il file si tronca al test 5 su
--   «p_billing_account_id obbligatorio» (la fixture prende il cliente dai dati:
--   debito preesistente, non di questo giro); su dbdev arriva in fondo.
-- rev 2026-10-26 (giro 10, dopo la corsa di Tid su dbdev): gli scenari B, C, D
--   erano costruiti in IN_ESECUZIONE (BOZZA -> APERTA -> IN_ESECUZIONE), che non
--   esiste piu'. La commessa intermedia ora e' APERTA, la commessa RIAPERTA:
--   ci si arriva da PRONTA_FATTURAZIONE con «riapri», e a PRONTA serve una riga
--   approvata da emettere. Quindi:
--   [B] il vicolo cieco e' la commessa riaperta e TUTTA EMESSA (la riga va a
--       PRONTA, l'emissione la marca EMESSA, poi «riapri»): niente di pendente,
--       «chiudi» la fa uscire;
--   [C] la commessa riaperta con una riga EMESSA e una APPROVATA da emettere;
--   [D] la commessa riaperta senza righe emesse: la riga da emettere e' il suo
--       legame, l'annullo confermato passa.
--   L'azione cambia_stato_commessa all'utente del contesto in testa: il file
--   prova i guard d'uscita, non il permesso (C-1).
--   Attese dei test invariate; cambiano lo stato di partenza (APERTA invece di
--   IN_ESECUZIONE) e le frasi dei test 10, 11, 14a che lo nominano.
-- ⚠️ Attesa cambiata: test 3 da IN_ESECUZIONE->CHIUSA (3->5) ad APERTA->CHIUSA
--   (2->5), perche' IN_ESECUZIONE e' ritirato (attivo = false, arco 12 spento) e
--   la riapertura ora porta in APERTA: la sua uscita verso CHIUSA e' l'arco 14.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- rev 2026-10-26 (giro 10, C-1): «rendi pronta», «riapri», «chiudi» e l'annullo
--   fuori dalla bozza chiedono l'azione; il file prova i guard d'uscita.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');

SELECT plan(18);

-- ============================================================
-- 1..4 STRUTTURA
-- ============================================================

SELECT has_function('script', 'fn_check_commessa_chiudibile',
    '1) script.fn_check_commessa_chiudibile presente');

SELECT has_function('script', 'fn_check_commessa_annullabile',
    '2) script.fn_check_commessa_annullabile presente');

-- L'arco che chiude il vicolo cieco: senza, una commessa riaperta e tutta
-- emessa non ha piu' uscite se non ANNULLATA (che il guard vieta).
-- rev 2026-10-26: la riapertura porta in APERTA (IN_ESECUZIONE e' ritirato),
-- quindi l'arco e' APERTA->CHIUSA.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM vendite.transizioni_stati_commessa t
      JOIN vendite.stati_commessa sd ON sd.id = t.stato_da_id
      JOIN vendite.stati_commessa sa ON sa.id = t.stato_a_id
     WHERE sd.codice_interno = 'APERTA'
       AND sa.codice_interno = 'CHIUSA'
       AND t.attivo IS TRUE
       AND (t.meta->>'action_key') = 'chiudi'
       AND COALESCE((t.meta->>'manuale')::boolean, false) IS TRUE
  ),
  '3) matrice: arco APERTA->CHIUSA presente, attivo e manuale');

SELECT is(
  (SELECT count(*)::int FROM config.messaggi_errore
    WHERE codice IN ('E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE',
                     'E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI')
      AND lingua = 'it'),
  2,
  '4) codici errore 558/559 presenti a catalogo');

-- ============================================================
-- FIXTURE COMUNI
-- ============================================================

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA legato all'azienda di chi agisce):
--   prima il BA si pescava con LIMIT 1, e da zero non c'era.
CREATE TEMP TABLE tmp_cli_guc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('guard uscita commessa');

CREATE TEMP TABLE tmp_refs_guc AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_guc) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_guc) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_guc) AS istanza_utility_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1) AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE
    ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id;

-- ⚠️ 2026-11-10 (brief-db-revisione-catalogo, giro 2-bis, D26/Q30): un'attivita'
--   senza fattore prende quello alla data, e un'unita' che per l'articolo non si
--   converte si rifiuta (E_UOM_MISSING). «Un'unita' qualunque» accanto a «un
--   articolo qualunque» passava col fattore 1 per difetto: l'unita' e' la base
--   dell'articolo scelto.
UPDATE tmp_refs_guc SET uom_id = (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = tmp_refs_guc.articolo_id);

-- Scopo: crea una commessa isolata (force_new) che nasce in BOZZA.
CREATE OR REPLACE FUNCTION pg_temp.fx_commessa(p_scope text)
RETURNS vendite.commesse.id%TYPE LANGUAGE sql AS $fx$
  SELECT vendite.fn_get_or_create_commessa(
    p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_guc),
    p_utility_id             => (SELECT utility_id FROM tmp_refs_guc),
    p_tipo_commessa          => 'AUTO',
    p_policy_fatturazione    => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa     => 'NORMALE',
    p_competenza_dal         => DATE '2026-09-01',
    p_competenza_al          => DATE '2026-09-30',
    p_meta                   => jsonb_build_object('test_scope', p_scope),
    p_force_new              => true);
$fx$;

-- Scopo: aggiunge una riga alla commessa negli stati richiesti.
CREATE OR REPLACE FUNCTION pg_temp.fx_riga(
  p_commessa_id vendite.commesse.id%TYPE,
  p_seg         vendite.commesse_attivita.segment_key%TYPE,
  p_appr        vendite.commesse_attivita.stato_approvazione%TYPE,
  p_emis        vendite.commesse_attivita.stato_emissione%TYPE)
RETURNS vendite.commesse_attivita.id%TYPE LANGUAGE sql AS $fx$
  SELECT r.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                   => p_commessa_id,
      -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
      p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa(p_commessa_id) x),
      p_sorgente_chiave => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa(p_commessa_id) x),
      p_segment_key                   => ((SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa(p_commessa_id) x) || ':' || p_seg)::varchar,
      p_articolo_id                   => (SELECT articolo_id FROM tmp_refs_guc),
      p_istanza_utility_id            => (SELECT istanza_utility_id FROM tmp_refs_guc),
      p_data_attivita                 => DATE '2026-09-15',
      p_uom_id                        => (SELECT uom_id FROM tmp_refs_guc),
      p_quantita                      => 1.000000,
      p_competenza_mese               => DATE '2026-09-01',
      p_competenza_dal                => DATE '2026-09-01',
      p_competenza_al                 => DATE '2026-09-30',
      p_prezzo_snapshot               => 10.0000000000,
      p_prezzo_base_snapshot          => NULL,
      p_origine_prezzo                => NULL,
      p_tipo_variazione_applicata     => NULL,
      p_valore_variazione_applicata   => NULL,
      p_promo_id                      => NULL,
      p_contratto_id                  => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot     => NULL,
      p_tipo_doc_fiscale_id           => (SELECT tipo_doc_fiscale_id FROM tmp_refs_guc),
      p_stato_approvazione            => p_appr,
      p_stato_emissione               => p_emis,
      p_tipo_movimento                => 'NORMALE',
      p_meta                          => jsonb_build_object('case', 'GUC')
    ) r;
$fx$;

-- ============================================================
-- [A] PRONTA_FATTURAZIONE con una riga APPROVATA + NON_EMESSA
-- ============================================================

CREATE TEMP TABLE tmp_a AS SELECT pg_temp.fx_commessa('guard_uscita_A') AS commessa_id;

DO $setup$
DECLARE v_id vendite.commesse.id%TYPE := (SELECT commessa_id FROM tmp_a);
BEGIN
  PERFORM pg_temp.fx_riga(v_id, 'SEG-GUC-A1', 'APPROVATA', 'NON_EMESSA');
  -- BOZZA -> PRONTA_FATTURAZIONE (arco 1->4): la precondizione di INGRESSO
  -- (>=1 riga APPROVATA+NON_EMESSA) e' soddisfatta dalla riga appena creata.
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'PRONTA_FATTURAZIONE');
END
$setup$;

SELECT is(
  (SELECT (m ->> 'codice') || '|' || (m ->> 'dettaglio')
     FROM (SELECT script.fn_check_commessa_chiudibile(
                    (SELECT commessa_id FROM tmp_a)) -> 0 AS m) x),
  'E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI|1',
  '5) _chiudibile: motivo 559 con dettaglio = numero righe pendenti');

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_a), 'CHIUSA') $$,
  'P0001', NULL,
  '6) ->CHIUSA con righe APPROVATE+NON_EMESSE rifiutata');

SELECT is(
  (SELECT (a ->> 'enabled')::boolean
     FROM jsonb_array_elements(
            script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_a))
              -> 'available_actions') AS a
    WHERE a ->> 'key' = 'chiudi'),
  false,
  '7) capabilities: azione chiudi presente ma enabled=false');

SELECT is(
  (SELECT a -> 'reasons' -> 0 ->> 'reason_key'
     FROM jsonb_array_elements(
            script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_a))
              -> 'available_actions') AS a
    WHERE a ->> 'key' = 'chiudi'),
  'vendite.commesse.azione_reason.righe_da_emettere',
  '8) capabilities: reasons di chiudi porta il reason_key per il tooltip');

-- ============================================================
-- [B] La commessa RIAPERTA e tutta emessa: niente di pendente.
--     E' il caso del vicolo cieco: non puo' andare a PRONTA (nessuna
--     riga da emettere) e senza l'arco APERTA->CHIUSA non potrebbe
--     chiudersi. rev 2026-10-26 (giro 10): prima era IN_ESECUZIONE con
--     una riga in BOZZA; IN_ESECUZIONE e' ritirato.
-- ============================================================

CREATE TEMP TABLE tmp_b AS SELECT pg_temp.fx_commessa('guard_uscita_B') AS commessa_id;

DO $setup$
DECLARE v_id vendite.commesse.id%TYPE := (SELECT commessa_id FROM tmp_b);
BEGIN
  -- La ROOT, che l'emissione pretende: la commessa radice di se' stessa.
  PERFORM vendite.fn_link_commessa_sorgente(
    p_commessa_id      => v_id,
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s
                            WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE),
    p_sorgente_chiave  => v_id::text);
  PERFORM pg_temp.fx_riga(v_id, 'SEG-GUC-B1', 'APPROVATA', 'NON_EMESSA');
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'PRONTA_FATTURAZIONE');
  -- L'emissione marca la riga EMESSA: la strada vera, non un UPDATE.
  PERFORM * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id => v_id, p_only_approved => true, p_dry_run => false);
  -- «Riapri»: la commessa riaperta, tutta emessa.
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'APERTA');
END
$setup$;

SELECT is(
  script.fn_check_commessa_chiudibile((SELECT commessa_id FROM tmp_b)),
  '[]'::jsonb,
  '9) _chiudibile: nessun motivo quando non resta nulla di pendente');

SELECT is(
  (SELECT (a ->> 'enabled')::boolean
     FROM jsonb_array_elements(
            script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_b))
              -> 'available_actions') AS a
    WHERE a ->> 'key' = 'chiudi'),
  true,
  '10) capabilities: in APERTA chiudi e'' esposta e abilitata');

SELECT lives_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_b), 'CHIUSA') $$,
  '11) ->CHIUSA da APERTA ammessa: il vicolo cieco e'' chiuso');

-- ============================================================
-- [C] La commessa RIAPERTA con una riga EMESSA + una APPROVATA/NON_EMESSA.
--     Entrambe le uscite manuali sono ostruite. rev 2026-10-26 (giro 10):
--     prima IN_ESECUZIONE; ora la commessa riaperta (PRONTA, poi «riapri»).
-- ============================================================

CREATE TEMP TABLE tmp_c AS SELECT pg_temp.fx_commessa('guard_uscita_C') AS commessa_id;

DO $setup$
DECLARE v_id vendite.commesse.id%TYPE := (SELECT commessa_id FROM tmp_c);
BEGIN
  PERFORM pg_temp.fx_riga(v_id, 'SEG-GUC-C1', 'APPROVATA', 'EMESSA');
  PERFORM pg_temp.fx_riga(v_id, 'SEG-GUC-C2', 'APPROVATA', 'NON_EMESSA');
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'PRONTA_FATTURAZIONE');
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'APERTA');
END
$setup$;

SELECT is(
  (SELECT (m ->> 'codice') || '|' || (m ->> 'dettaglio')
     FROM (SELECT script.fn_check_commessa_annullabile(
                    (SELECT commessa_id FROM tmp_c)) -> 0 AS m) x),
  'E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE|1',
  '12) _annullabile: motivo 558 con dettaglio = numero righe emesse');

-- ⭐ P-1 — LA FRASE RESA. E' l'unica verifica che vede l'ORDINE dei valori:
--   il ramo C di test-catalogo-messaggi-errore-completo.sql prova che sono
--   TANTI QUANTI i segnaposto, non che siano quelli giusti al posto giusto.
--   Il precedente e' del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA — due
--   valori, due segnaposto, «Registro X1» a video con la serie al posto della
--   famiglia — e nel 2026-09-09 lo stesso difetto e' stato trovato VIVO su due
--   siti di questo cantiere.
-- ⚠️ Si confronta con la frase composta dai valori letti dalla TABELLA: se la
--   check li emettesse invertiti, le due stringhe divergerebbero. Un `matches`
--   su un pezzo di frase non lo vedrebbe.
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file.
--   E scritto con un `<>` nudo non guarderebbe niente: `jsonb_typeof(NULL) <>
--   'array'` vale NULL, non vero.
SELECT is(
  (WITH v AS (SELECT script.fn_check_commessa_annullabile((SELECT commessa_id FROM tmp_c)) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT format((SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE' AND m.lingua = 'it'),
                 c.codice, '1')
     FROM vendite.commesse c WHERE c.id = (SELECT commessa_id FROM tmp_c)),
  '12-bis) la frase resa nomina il CODICE della commessa e poi il conteggio, in quest''ordine');

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_cambia_stato_commessa(
       (SELECT commessa_id FROM tmp_c), 'ANNULLATA') $$,
  'P0001', NULL,
  '13) ->ANNULLATA con righe EMESSE rifiutata');

-- Discriminante del ricalcolo: TUTTE le azioni manuali da IN_ESECUZIONE
-- (dal 2026-10-26 da APERTA, la commessa riaperta) sono disabilitate. Col vecchio jsonb_array_length(actions) > 0 questo
-- test fallirebbe.
--
-- ⚠️ Adeguamento 2026-08-04 (brief-db-emittibilita-visibile-e-sbloccabile,
-- changeSet 20260804-27): da IN_ESECUZIONE le azioni manuali sono diventate
-- TRE — si e' aggiunta `rendi_pronta`. Le prime due si disabilitano da sole
-- con la fixture C (riga EMESSA => annulla no; riga APPROVATA+NON_EMESSA =>
-- chiudi no), ma quella stessa riga pendente e' esattamente cio' che ABILITA
-- `rendi_pronta`: le due condizioni sono l'una il complemento dell'altra, e
-- sulle righe lo scenario «tutte disabilitate» non e' piu' raggiungibile.
--
-- ⛔ 2026-08-26 — LA TERZA LEVA E' CADUTA, E CON LEI LO SCENARIO.
--    Qui si azzerava l'emittente della commessa C: era il secondo motivo di
--    fn_check_commessa_pronta_fatturazione, una condizione di TESTATA, e
--    l'ultima via rimasta per spegnere anche `rendi_pronta`.
--    Dal changeSet 20260826-41 `vendite.commesse.emittente_soggetto_ruolo_id`
--    e' NOT NULL — la colonna e' la chiave di perimetro della commessa, e con
--    un NULL la commessa spariva a chiunque avesse un perimetro ristretto —
--    quindi quell'UPDATE non e' piu' scrivibile da nessuno.
--
--    ⭐ E lo scenario «tutte e tre spente» non e' piu' UNO STATO DEL MODELLO,
--    non per caso ma per costruzione:
--      - `chiudi` spento      <=> esiste una riga APPROVATA + NON_EMESSA;
--      - `rendi_pronta` spento <=> NON esiste una riga
--                                  APPROVATA + NON_EMESSA + tipo_doc;
--      - e vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile impone
--        APPROVATA + NON_EMESSA => tipo_doc NOT NULL.
--    ⇒ `chiudi` spento IMPLICA `rendi_pronta` acceso: sono complementari.
--    (Le tre `enabled` vengono SOLO dalle tre fn pure — verificato su
--     script.fn_available_actions_commessa: nessun gate di permesso.)
--
--    Questo file l'aveva gia' visto arrivare sull'asse delle RIGHE (nota del
--    2026-08-04) e aveva tappato il buco spostandosi sulla TESTATA. Ora e'
--    chiuso anche quello — ed era gia' scritto nell'intestazione che il ramo
--    era «raggiungibile solo da un ruolo BYPASSRLS, mai da un operatore».
--
--    ▶ Decisione aperta D-5: brief-db-emittente-commessa-invariante §7.12.

-- 14a) Lo STATO VERO, ed e' ancora un'asserzione forte: le tre azioni ci sono
--      tutte, e si dice esattamente QUALI sono spente. Se un giorno l'array
--      tornasse vuoto, o se `rendi_pronta` si spegnesse insieme a `chiudi`
--      (cioe' se l'invariante del tipo_doc cadesse), questo diventa rosso.
SELECT is(
  (SELECT jsonb_object_agg(e->>'key', (e->>'enabled')::boolean)
     FROM jsonb_array_elements(
       script.fn_available_actions_commessa((SELECT commessa_id FROM tmp_c))
         -> 'available_actions') e),
  '{"annulla": false, "chiudi": false, "rendi_pronta": true}'::jsonb,
  '14a) da APERTA: annulla e chiudi spente, rendi_pronta accesa');

-- 14) ⛔ SKIP DICHIARATO, non asserzione indebolita.
--     Questo test nasceva per distinguere «azioni presenti ma tutte spente»
--     da «nessuna azione» — il suo commento diceva: *col vecchio
--     jsonb_array_length(actions) > 0 questo test fallirebbe*. Quello stato
--     non esiste piu' (vedi sopra), e riscrivere l'asserzione su
--     `can_change_state = true` la farebbe passare SMETTENDO di verificare
--     proprio quella distinzione: sarebbe verde per sottrazione.
--     Il debito resta qui, visibile, finche' D-5 non e' chiusa.
SELECT skip('14) can_change_state con tutte le azioni spente: scenario ritirato dal NOT NULL sull''emittente (20260826-41), in attesa di D-5 — brief-db-emittente-commessa-invariante §7.12', 1);

-- ============================================================
-- [D] La commessa RIAPERTA senza righe emesse -> annullamento lecito.
--     rev 2026-10-26 (giro 10): prima IN_ESECUZIONE con una riga in BOZZA;
--     ora la riga e' quella da emettere che l'ha portata a PRONTA.
-- ============================================================

CREATE TEMP TABLE tmp_d AS SELECT pg_temp.fx_commessa('guard_uscita_D') AS commessa_id;

DO $setup$
DECLARE v_id vendite.commesse.id%TYPE := (SELECT commessa_id FROM tmp_d);
BEGIN
  PERFORM pg_temp.fx_riga(v_id, 'SEG-GUC-D1', 'APPROVATA', 'NON_EMESSA');
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'PRONTA_FATTURAZIONE');
  PERFORM * FROM vendite.fn_cambia_stato_commessa(v_id, 'APERTA');
END
$setup$;

-- ⭐ rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte, D-1/D-2): la riga
--   NON_EMESSA e' un legame della commessa, e l'annullo passa dal verbo con la
--   conferma (dal verbo di stato l'avviso E_DOC_ANNULLO_CON_LEGAMI lo
--   rifiuterebbe). Il guard di uscita qui deve lasciar passare: nessuna riga e'
--   emessa. Si dichiara il legame visto, 1.
SELECT lives_ok(
  $$ SELECT vendite.fn_annulla_commessa((SELECT commessa_id FROM tmp_d), 1) $$,
  '15) ->ANNULLATA senza righe emesse ammessa (dal verbo, confermando la riga non emessa)');

-- ============================================================
-- [16] Testata identificabile (D6)
-- ============================================================

SELECT ok(
  (SELECT s.commessa_codice IS NOT NULL
      AND s.commessa_codice = (SELECT c.codice FROM vendite.commesse c
                                WHERE c.id = (SELECT commessa_id FROM tmp_a))
      AND s.cliente_display IS NOT NULL
     FROM vendite.fn_get_commessa_stato((SELECT commessa_id FROM tmp_a)) s),
  '16) fn_get_commessa_stato espone commessa_codice e cliente_display');

SELECT * FROM finish();
ROLLBACK;
