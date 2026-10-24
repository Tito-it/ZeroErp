-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — questo file non interroga NESSUN dato di dominio:
--   legge il catalogo di PostgreSQL (pg_proc) attraverso due viste dbops. Un
--   contesto operatore non cambierebbe una riga del risultato, e metterlo
--   darebbe l'impressione che la RLS qui sia esercitata, che sarebbe falso.
-- pgtap-runner: owner
-- pgtap-runner-motivo: i test 3..16 CREANO uno schema di prova e funzioni
--   plpgsql (in transazione, poi annullata) perche' un criterio si prova
--   COSTRUENDO i casi. E' DDL piu' CREATE FUNCTION: il ruolo applicativo non
--   ne fa e non ne deve fare. Stesso criterio del gemello
--   dbops/test-stati-check-scrittori-v1.sql.
--
-- pgTAP test ANTI-REGRESSIONE — la meta' PL/pgSQL del PRESIDIO C2: la
-- `ui_action` promessa e il canale che la realizza.
--
-- ChangeSet di riferimento: 20260921-40 (risalita condivisa), 20260921-42
--                           (la misura), 20260921-43..49 (la sanatura, 30 A),
--                           20260922-11..13 (i 9 A del §4-ter.2),
--                           20260924-08 (la delega fra check, t.15-16)
-- Brief: brief-be-presidio-ui-action-e-canale-campi §2, §3-bis.4, §4, §4-bis, §4-ter
--
-- Indice test (plan 16):
--   1) ⛔ LA SANATURA NON SI DISFA: i 27 guard sanati il 21-09 e le 8 funzioni
--      del 22-09 portano ancora il canale (IN_CHIAMATA, chiave campo) per i
--      loro codici — un corpo riemesso da uno YAML stantio qui diventa rosso
--   2) ⛔ nessun ramo cieco: ogni sito PRIMO_MOTIVO si lega ad almeno un codice
--   3) ⭐ 'campo' nella chiamata -> IN_CHIAMATA / campo (COSTRUITO)
--   4) ⭐ 'parametro' nella chiamata -> IN_CHIAMATA / parametro, e 'campo'
--      vince su 'parametro' quando ci sono entrambe (COSTRUITO)
--   5) ⭐ il context in una VARIABILE del corpo -> IN_VARIABILE (COSTRUITO —
--      i «forse» del §3-bis)
--   6) ⛔ la colonna come CHIAVE del context -> CHIAVE_NON_LETTA con
--      nome_in_chiave = la colonna (COSTRUITO — il difetto di meccanismo
--      del §3-bis.4)
--   7) ⭐ nessuna chiave, nessuna colonna -> NESSUNO (COSTRUITO)
--   8) ⛔ il CODICE in variabile: la chiave c'e' ma non e' attribuibile ->
--      IN_VARIABILE, MAI IN_CHIAMATA (COSTRUITO — pessimista dove serve)
--   9) ⭐ PRIMO_MOTIVO via helper con p_campo letterale -> IN_CHIAMATA per
--      TUTTI i codici della check (COSTRUITO)
--  10) ⭐ PRIMO_MOTIVO via helper SENZA p_campo: il canale viene dal MOTIVO
--      — il codice il cui motivo porta 'campo' e' IN_CHIAMATA, l'altro
--      NESSUNO — e la risalita condivisa lo dice (motivo_chiave) (COSTRUITO)
--  11) ⭐ PRIMO_MOTIVO a mano (`->> 'codice'`, la coda del rubinetto) con la
--      chiave nella chiamata -> IN_CHIAMATA (COSTRUITO)
--  12) ⭐ una funzione che NOMINA il codice senza sollevarlo -> NOMINATO,
--      canale NULL (COSTRUITO)
--  13) ⭐ tre chiamate, due col campo: canale IN_CHIAMATA («almeno un
--      punto»), n_chiamate 3, n_con_canale 2 (COSTRUITO)
--  14) ⚠️ IL LIMITE: la chiave dentro un letterale jsonb ('{"campo":…}') non
--      si vede — NESSUNO (COSTRUITO — dichiara il punto cieco)
--  15) ⭐ LA DELEGA (20260924-08): una check che RESTITUISCE i motivi di
--      un'altra ne eredita i codici — tutti se li accoda, i soli del filtro
--      (`->> 'codice' = …`) se li filtra (COSTRUITO — la forma di
--      script.fn_check_prezzi_in_attesa, che il 24-09 faceva ramo cieco nel 2)
--  16) ⛔ IL CONSUMO non e' delega: una check che CONTA i motivi di un'altra
--      emette il suo, e non eredita ne' codici ne' `valori` (COSTRUITO — il
--      falso che la prima stesura di -08 dava al rubinetto)
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL PROBLEMA, E PERCHE' NON SI VEDE.
--   Un codice porta a catalogo una promessa all'interfaccia: ui_action =
--   highlight_form_fields, «evidenzia il campo». Ma il campo lo accende un
--   ALTRO canale — fields nell'envelope, che nasce dalla COLUMN che
--   script.fn_log_and_raise_error legge dal context (chiave 'campo', ripiego
--   'parametro'). Se il context non la porta, a video esce un toast e nessun
--   campo rosso: la promessa e' vuota, e niente fallisce. Il 21-09 erano 37
--   codici a soli siti PL/pgSQL, e in molti il nome della colonna c'era — come
--   CHIAVE del context (`'quantita', NEW.quantita`), nel posto che l'helper
--   non legge.
--
-- ⛔ NON E' UNA MISURA SUI DATI. Il presidio guarda la FORMA della chiamata
--   nel sorgente vivo (pg_proc), cioe' la struttura.
--
-- ⚠️ IL CANCELLO VERO E' NEL BACKEND. Questa vista e' la meta' PL/pgSQL del
--   criterio; il test Django del brief (decisione 3-4 di Tid) incrocia
--   ui_action a catalogo con questa vista e col sorgente Python, nei due
--   versi. Qui si prova che la vista CLASSIFICA come dichiara — e che la
--   sanatura non si disfa in silenzio.
--
-- ⚠️ COSA QUESTO TEST NON DICE. Che il nome nel canale sia quello dell'input
--   giusto: quello e' un giudizio (strada A/B del brief), non una forma.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- I casi costruiti — da qui in giu' si semina
-- ============================================================
-- ⛔ Da qui il database contiene apposta siti senza canale. I test 1..2
--   leggono la stessa copia della vista, ma ESCLUSO lo schema pgtap_c2: il
--   loro perimetro sono le funzioni vere, e i casi seminati non ci entrano.
-- ⚠️ Uno schema VERO e non pg_temp: la risalita cerca la fn_check_* per
--   `schema.nome` in pg_namespace, e `pg_temp` e' un alias che li' non c'e'.
CREATE SCHEMA pgtap_c2;

-- La check di prova: due motivi, uno col campo nel dettaglio e uno senza.
CREATE FUNCTION pgtap_c2.fn_check_pgtap_canale(p_x int)
RETURNS jsonb LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    IF p_x = 1 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice', 'E_PGTAP_MOTIVO_SENZA',
            'reason', 'SENZA',
            'dettaglio', jsonb_build_object('x', p_x),
            'valori', jsonb_build_array(p_x::text));
    END IF;
    IF p_x = 2 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice', 'E_PGTAP_MOTIVO_CON',
            'reason', 'CON',
            'dettaglio', jsonb_build_object('campo', 'x', 'x', p_x),
            'valori', jsonb_build_array(p_x::text));
    END IF;
    RETURN v_motivi;
END
$f$;

-- 3) 'campo' nella chiamata.
CREATE FUNCTION pgtap_c2.fn_in_chiamata() RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_IN_CHIAMATA',
        jsonb_build_object('campo', 'quantita', 'quantita', 3), NULL::uuid, VARIADIC ARRAY[]::text[]);
END
$f$;

-- 4) 'parametro' nella chiamata, e una con entrambe.
CREATE FUNCTION pgtap_c2.fn_parametro(p_nome text) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    IF p_nome IS NULL THEN
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_PARAMETRO',
            jsonb_build_object('parametro', 'p_nome'), NULL::uuid, VARIADIC ARRAY[]::text[]);
    END IF;
    IF p_nome = '' THEN
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_ENTRAMBE',
            jsonb_build_object('parametro', 'p_nome', 'campo', 'nome'), NULL::uuid, VARIADIC ARRAY[]::text[]);
    END IF;
END
$f$;

-- 5) il context in una variabile del corpo (la forma di fn_validate_cf_piva_it).
CREATE FUNCTION pgtap_c2.fn_variabile() RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    l_error_ctx jsonb;
BEGIN
    l_error_ctx := jsonb_build_object('campo', 'codice_fiscale', 'valore', 'x');
    PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_VARIABILE',
        l_error_ctx, NULL::uuid, VARIADIC ARRAY[]::text[]);
END
$f$;

-- 6) la colonna come CHIAVE (la forma dei guard dei resi).
CREATE FUNCTION pgtap_c2.trgfn_chiave_non_letta() RETURNS trigger LANGUAGE plpgsql AS $f$
BEGIN
    IF NEW.quantita <= 0 THEN
        PERFORM script.fn_log_and_raise_error('dbops', TG_NAME, 'E_PGTAP_CHIAVE_NON_LETTA',
            jsonb_build_object('quantita', NEW.quantita), NULL::uuid, NEW.quantita::text);
    END IF;
    RETURN NEW;
END
$f$;

-- 7) niente.
CREATE FUNCTION pgtap_c2.fn_nessuno() RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_NESSUNO',
        jsonb_build_object('table', 'x'), NULL::uuid, VARIADIC ARRAY[]::text[]);
END
$f$;

-- 8) il codice in variabile (la forma di fn_get_next_progressivo).
CREATE FUNCTION pgtap_c2.fn_codice_in_variabile(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    v_codice text;
BEGIN
    v_codice := CASE WHEN p_x = 1 THEN 'E_PGTAP_VAR_A' ELSE 'E_PGTAP_VAR_B' END;
    PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', v_codice,
        jsonb_build_object('campo', 'data'), NULL::uuid, VARIADIC ARRAY[]::text[]);
END
$f$;

-- 9) primo motivo via helper, p_campo letterale.
CREATE FUNCTION pgtap_c2.fn_primo_motivo_p_campo(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb;
BEGIN
    v_motivi := pgtap_c2.fn_check_pgtap_canale(p_x);
    PERFORM script.fn_raise_primo_motivo_se_presente('dbops', 'pgtap', v_motivi, 'x', NULL::uuid);
END
$f$;

-- 10) primo motivo via helper, SENZA p_campo: il canale e' del motivo.
CREATE FUNCTION pgtap_c2.fn_primo_motivo_dal_motivo(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb;
BEGIN
    v_motivi := pgtap_c2.fn_check_pgtap_canale(p_x);
    PERFORM script.fn_raise_primo_motivo_se_presente('dbops', 'pgtap', v_motivi, NULL, NULL::uuid,
        jsonb_build_object('riga_id', p_x));
END
$f$;

-- 11) primo motivo A MANO (la coda del rubinetto), chiave nella chiamata.
CREATE FUNCTION pgtap_c2.fn_primo_motivo_a_mano(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb;
    v_primo  jsonb;
BEGIN
    v_motivi := pgtap_c2.fn_check_pgtap_canale(p_x);
    IF jsonb_array_length(v_motivi) > 0 THEN
        v_primo := v_motivi -> 0;
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', v_primo ->> 'codice',
            jsonb_build_object('campo', 'x'), NULL::uuid,
            VARIADIC ARRAY(SELECT jsonb_array_elements_text(v_primo -> 'valori')));
    END IF;
END
$f$;

-- 12) nomina il codice, non lo solleva.
CREATE FUNCTION pgtap_c2.fn_nominato(p_code text) RETURNS boolean LANGUAGE plpgsql AS $f$
BEGIN
    RETURN p_code = 'E_PGTAP_NOMINATO';
END
$f$;

-- 13) tre chiamate, due col campo (la forma di fn_pubblica_template_documento_versione).
CREATE FUNCTION pgtap_c2.fn_tre_chiamate(p_id int, p_dal date, p_al date) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    IF p_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_TRE',
            jsonb_build_object('id', p_id), NULL::uuid, 'id');
    END IF;
    IF p_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_TRE',
            jsonb_build_object('campo', 'valido_dal'), NULL::uuid, 'dal');
    END IF;
    IF p_al < p_dal THEN
        PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_TRE',
            jsonb_build_object('campo', 'valido_al'), NULL::uuid, 'al');
    END IF;
END
$f$;

-- 14) il limite: la chiave dentro un letterale jsonb.
CREATE FUNCTION pgtap_c2.fn_limite_letterale() RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_log_and_raise_error('dbops', 'pgtap', 'E_PGTAP_LIMITE',
        '{"campo": "x"}'::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]);
END
$f$;

-- 15) ⭐ LA DELEGA (20260924-08): una check che restituisce i motivi di
--     un'altra. Filtrata (la forma di script.fn_check_prezzi_in_attesa) e
--     accodata (la forma di fn_check_ddt_emittibile).
CREATE FUNCTION pgtap_c2.fn_check_pgtap_filtra(p_x int)
RETURNS jsonb LANGUAGE plpgsql AS $f$
BEGIN
    RETURN (
        SELECT COALESCE(jsonb_agg(m.motivo ORDER BY m.pos), '[]'::jsonb)
          FROM jsonb_array_elements(pgtap_c2.fn_check_pgtap_canale(p_x))
               WITH ORDINALITY AS m(motivo, pos)
         WHERE m.motivo ->> 'codice' = 'E_PGTAP_MOTIVO_CON');
END
$f$;

CREATE FUNCTION pgtap_c2.fn_check_pgtap_accoda(p_x int)
RETURNS jsonb LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
BEGIN
    v_motivi := v_motivi || pgtap_c2.fn_check_pgtap_canale(p_x);
    RETURN v_motivi;
END
$f$;

CREATE FUNCTION pgtap_c2.fn_delega_filtrata(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente('dbops', 'pgtap',
        pgtap_c2.fn_check_pgtap_filtra(p_x), NULL, NULL::uuid);
END
$f$;

CREATE FUNCTION pgtap_c2.fn_delega_accodata(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente('dbops', 'pgtap',
        pgtap_c2.fn_check_pgtap_accoda(p_x), NULL, NULL::uuid);
END
$f$;

-- 16) ⛔ IL CONSUMO non e' una delega (la forma di
--     fn_check_preventivo_annullabile): la check CONTA i motivi dell'altra ed
--     emette un motivo SUO, senza `valori`.
CREATE FUNCTION pgtap_c2.fn_check_pgtap_conta(p_x int)
RETURNS jsonb LANGUAGE plpgsql AS $f$
DECLARE
    v_motivi jsonb := '[]'::jsonb;
    v_n      integer;
BEGIN
    SELECT count(*) INTO v_n
      FROM jsonb_array_elements(pgtap_c2.fn_check_pgtap_canale(p_x)) AS m
     WHERE m ->> 'codice' = 'E_PGTAP_MOTIVO_CON';
    IF v_n > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice', 'E_PGTAP_CONTATO',
            'reason', 'CONTATO');
    END IF;
    RETURN v_motivi;
END
$f$;

CREATE FUNCTION pgtap_c2.fn_consumo(p_x int) RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    PERFORM script.fn_raise_primo_motivo_se_presente('dbops', 'pgtap',
        pgtap_c2.fn_check_pgtap_conta(p_x), NULL, NULL::uuid);
END
$f$;

-- ⚠️ Le due viste si leggono UNA volta sola, dopo la semina, e le asserzioni
--   leggono le copie. Sono scansioni di tutto pg_proc (~3,8 s la prima, ~1,1 s
--   la seconda, misura del 2026-09-26 su dbdev) e un filtro su `funzione` NON
--   le accorcia: il predicato non scende dentro la vista, che calcola tutto e
--   filtra dopo. Prima erano cinque letture — t.1, t.2, _c2, t.10, t.16.
--   Non indebolisce niente: la copia e' esattamente cio' che la vista dice.
CREATE TEMP TABLE _punti AS
SELECT * FROM dbops.vw_punti_canale_campo;

CREATE TEMP TABLE _c2 AS
SELECT * FROM _punti WHERE funzione LIKE 'pgtap_c2.%';

CREATE TEMP TABLE _c2_check AS
SELECT * FROM dbops.vw_funzioni_check_codici WHERE funzione LIKE 'pgtap_c2.%';

-- ============================================================
-- 1. ⛔ LA SANATURA NON SI DISFA
-- ============================================================
-- ⛔ I ventisette guard sanati il 2026-09-21 (changeSet -43..-49) e le otto
--   funzioni del 2026-09-22 (i 9 A del §4-ter.2, changeSet 20260922-11..13:
--   il test BE li aveva trovati ROSSI la sera stessa, fuori dai 37), con i
--   loro codici. Restano scritti qui APPOSTA: e' la prova che nessuno ha
--   riemesso uno di questi corpi da uno YAML piu' vecchio della sanatura —
--   il modo in cui una correzione sparisce senza che nessun altro test lo
--   veda (memoria: fn_escludi_documento_da_giro, 2026-09-09).
-- ⚠️ Solo il SITO sanato: E_DATA_AL_MINORE_DAL in vendite.fn_get_or_create_commessa
--   e E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO nelle due *_componenti_init
--   restano NESSUNO di proposito (nessun input della pagina, §4-ter.2) e non
--   sono qui: il verso 1 chiede «almeno un» sito.
SELECT is(
    (SELECT string_agg(a.funzione || ' / ' || a.codice || ' = ' || coalesce(v.canale, '?') || '/' || coalesce(v.chiave, '-'),
                       ', ' ORDER BY a.funzione, a.codice)
       FROM (VALUES
            ('anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza', 'E_BA_SOGGETTO_INCOERENTE_ISTANZA'),
            ('anagrafiche.trgfn_soggetti_conti_bancari_guard',                    'E_CONTO_BANCARIO'),
            ('anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard',              'E_CONTO_BANCARIO'),
            ('anagrafiche.trgfn_sepa_mandati_guard',                              'E_DATA_ERRATA'),
            ('anagrafiche.trgfn_dati_societari_guard_forma_giuridica',            'E_FORMA_GIURIDICA_PAESE'),
            ('anagrafiche.trgfn_risorse_umane_guard_ruolo',                       'E_RISORSA_UMANA_SOGGETTO_MISMATCH'),
            ('anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo',       'E_TIPO_INDIRIZZO_NON_PERMESSO'),
            ('config.trgfn_iva_guard_conti_iva',                                  'E_IVA_CONTO_ACQ_ERR'),
            ('config.trgfn_iva_guard_conti_iva',                                  'E_IVA_CONTO_VEN_ERR'),
            ('config.trgfn_toponomastica_normalize',                              'E_NAZIONE_NON_TROVATA'),
            ('config.trgfn_profili_accesso_bindings_guard_coerenza',              'E_PROFILO_ACCESSO_BINDING_INCOERENTE'),
            ('config.trgfn_stati_doc_guard_esito_verdetto',                       'E_STATO_DOC_ESITO_NON_VERDETTO'),
            ('documenti.fn_pubblica_template_documento_versione',                 'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO'),
            ('pratiche.trgfn_flussi_guard_esito_classe',                          'E_FLUSSI_ESITO_NON_AMMESSO'),
            ('pratiche.trgfn_template_flussi_guard_modalita_esito',               'E_TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO'),
            ('pratiche.trgfn_template_flussi_guard_modalita_esito',               'E_TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA'),
            ('pratiche.trgfn_template_flussi_guard_modalita_esito',               'E_TEMPLATE_FLUSSO_DOMINIO_ESITO_DEFAULT_VIETATO'),
            ('pratiche.trgfn_template_flussi_guard_modalita_esito',               'E_TEMPLATE_FLUSSO_ESITO_DEFAULT_NON_VERDETTO'),
            ('script.trgfn_qta_from_operativa',                                   'E_QTA_MISSING'),
            ('script.trgfn_qta_from_operativa',                                   'E_QTA_OPERATIVA_NON_INTERA'),
            ('script.trgfn_qta_from_operativa',                                   'E_QTA_OPER_STEP_INVALIDO'),
            ('script.trgfn_qta_from_operativa',                                   'E_UOM_MISSING'),
            -- rev 2026-10-13 (sera, Lotto 3c): vendite.trgfn_listini_righe_guard_tipologia
            --   ritirato (20261013-61); E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE e' un motivo di
            --   script.fn_check_articolo_riga, col campo nel dettaglio.
            ('vendite.trgfn_commesse_attivita_guard_tipo_doc_emittibile',         'E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO'),
            -- rev 2026-10-13 (sera): script.trgfn_righe_guard_aggiunta_fuori_listino
            --   ritirato (20261013-57); E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO e' ora un
            --   motivo di script.fn_check_articolo_riga, col campo nel dettaglio.
            ('vendite.trgfn_contratti_utilities_guard_tipo_classe',               'E_CONTRATTO_CLASSE_TIPO_INCOERENTE'),
            ('vendite.trgfn_contratti_utilities_guard_tipo_classe',               'E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI'),
            ('vendite.trgfn_contratti_utilities_guard_tipo_classe',               'E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI'),
            ('vendite.trgfn_listini_guard_tipologia_utility',                     'E_LISTINO_TIPOLOGIA_UTILITY'),
            ('vendite.trgfn_ordini_ful_guard_consistenza',                        'E_QTA_NON_POSITIVA'),
            ('vendite.trgfn_resi_accrediti_guard',                                'E_QTA_NON_POSITIVA'),
            ('vendite.trgfn_resi_riconsegne_guard',                               'E_QTA_NON_POSITIVA'),
            ('vendite.trgfn_resi_righe_guard_quantita',                           'E_QTA_NON_POSITIVA'),
            ('vendite.trgfn_resi_rinunce_guard',                                  'E_QTA_NON_POSITIVA'),
            ('vendite.trgfn_preventivi_guard_utility_istanza_coerenza',           'E_PREV_UTILITY_ISTANZA_INCOERENTE'),
            -- i 9 A del §4-ter.2 (22-09, changeSet 20260922-11..13)
            ('anagrafiche.fn_crea_risorsa_umana_v2',                              'E_ADMIN_UO_NON_TROVATA'),
            ('anagrafiche.trgfn_billing_account_guard_normalize',                 'E_PARENT_SELF'),
            -- ⭐ 2026-09-23: i tre controlli sulle date di validita' che stavano
            --   qui (billing_account e i due legami ai conti bancari) sono stati
            --   ritirati (20260923-43..-45): la regola ha UNA sede, il guard
            --   comune. Il canale si pretende ora su di lui.
            --   2026-09-24: stessa sorte per E_BOM_VALIDO_AL_INVALIDO nel trigger
            --   della BoM (20260924-01, codice ritirato). La pubblicazione dei
            --   template (sopra) resta: il suo codice vive sul ramo di valido_dal.
            ('script.trgfn_guard_date_validita',                                  'E_DATA_AL_MINORE_DAL'),
            ('script.fn_disdetta_cliente',                                        'E_DATA_CESSAZIONE_INVALIDA'),
            ('script.fn_guard_soggetto_pf_pura',                                  'E_AUTH_USER_SOGGETTO_CON_PIVA'),
            ('script.trgfn_componenti_check_prezzo_obbligatorio',                 'E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO'),
            ('vendite.fn_aggiungi_onere_commessa',                                'E_ONERE_ARTICOLO_MANCANTE'),
            ('vendite.fn_aggiungi_onere_commessa',                                'E_ONERE_IMPORTO_NON_VALIDO')
       ) a(funzione, codice)
       LEFT JOIN _punti v
              ON v.funzione = a.funzione AND v.codice = a.codice AND v.via = 'DIRETTO'
      WHERE v.canale IS DISTINCT FROM 'IN_CHIAMATA' OR v.chiave IS DISTINCT FROM 'campo'),
    NULL,
    '1. i 27 guard sanati il 21-09 e le 8 funzioni del 22-09 portano ancora il canale campo per i loro codici: nessun corpo riemesso da uno YAML stantio'
);

-- ============================================================
-- 2. ⛔ NESSUN RAMO CIECO
-- ============================================================
-- Un sito PRIMO_MOTIVO che non si lega a nessun codice non e' «a posto»: e' un
-- sito che la lettura non sa leggere. Stesso criterio del rubinetto (t.3).
SELECT is(
    (SELECT string_agg(funzione, ', ' ORDER BY funzione)
       FROM _punti
      WHERE via = 'PRIMO_MOTIVO' AND codice IS NULL
        AND funzione NOT LIKE 'pgtap_c2.%'),
    NULL,
    '2. ogni sito che solleva il primo motivo si lega ad almeno un codice: nessun ramo cieco'
);


-- ============================================================
-- 3..14. I casi costruiti, uno per proprieta'
-- ============================================================
SELECT is(
    (SELECT via || '/' || canale || '/' || chiave || '/' || n_chiamate || '/' || n_con_canale
       FROM _c2 WHERE codice = 'E_PGTAP_IN_CHIAMATA'),
    'DIRETTO/IN_CHIAMATA/campo/1/1',
    '3. la chiave campo nella chiamata: IN_CHIAMATA / campo'
);

SELECT is(
    (SELECT string_agg(codice || ':' || canale || '/' || chiave, ', ' ORDER BY codice)
       FROM _c2 WHERE codice IN ('E_PGTAP_PARAMETRO', 'E_PGTAP_ENTRAMBE')),
    'E_PGTAP_ENTRAMBE:IN_CHIAMATA/campo, E_PGTAP_PARAMETRO:IN_CHIAMATA/parametro',
    '4. la chiave parametro: IN_CHIAMATA / parametro — e campo vince su parametro quando ci sono entrambe, come nell''helper'
);

SELECT is(
    (SELECT canale || '/' || chiave FROM _c2 WHERE codice = 'E_PGTAP_VARIABILE'),
    'IN_VARIABILE/campo',
    '5. il context assegnato a una variabile del corpo: IN_VARIABILE — i «forse» del §3-bis si seguono'
);

SELECT is(
    (SELECT canale || '/' || coalesce(chiave, '-') || '/' || nome_in_chiave FROM _c2 WHERE codice = 'E_PGTAP_CHIAVE_NON_LETTA'),
    'CHIAVE_NON_LETTA/-/quantita',
    '6. la colonna come CHIAVE del context: CHIAVE_NON_LETTA, e nome_in_chiave dice quale (il difetto di meccanismo del §3-bis.4)'
);

SELECT is(
    (SELECT canale || '/' || coalesce(chiave, '-') || '/' || coalesce(nome_in_chiave, '-') FROM _c2 WHERE codice = 'E_PGTAP_NESSUNO'),
    'NESSUNO/-/-',
    '7. nessuna chiave e nessuna colonna: NESSUNO'
);

SELECT is(
    (SELECT string_agg(codice || ':' || via || '/' || canale, ', ' ORDER BY codice)
       FROM _c2 WHERE codice IN ('E_PGTAP_VAR_A', 'E_PGTAP_VAR_B')),
    'E_PGTAP_VAR_A:DIRETTO/IN_VARIABILE, E_PGTAP_VAR_B:DIRETTO/IN_VARIABILE',
    '8. il CODICE in variabile: la chiave c''e'' ma non e'' attribuibile — IN_VARIABILE, mai IN_CHIAMATA (un falso ok costa una promessa vuota non vista)'
);

SELECT is(
    (SELECT string_agg(codice || ':' || canale || '/' || chiave, ', ' ORDER BY codice)
       FROM _c2 WHERE funzione = 'pgtap_c2.fn_primo_motivo_p_campo'),
    'E_PGTAP_MOTIVO_CON:IN_CHIAMATA/campo, E_PGTAP_MOTIVO_SENZA:IN_CHIAMATA/campo',
    '9. primo motivo via helper con p_campo letterale: IN_CHIAMATA per TUTTI i codici della check (l''unione, pessimista)'
);

SELECT is(
    (SELECT string_agg(codice || ':' || canale || '/' || coalesce(chiave, '-') || '/' || check_funzioni, ', ' ORDER BY codice)
       FROM _c2 WHERE funzione = 'pgtap_c2.fn_primo_motivo_dal_motivo')
    || ' | ' ||
    (SELECT string_agg(codice || ':' || coalesce(motivo_chiave, '-') || ':' || n_motivi, ', ' ORDER BY codice)
       FROM _c2_check
      WHERE funzione = 'pgtap_c2.fn_primo_motivo_dal_motivo'),
    'E_PGTAP_MOTIVO_CON:IN_CHIAMATA/campo/fn_check_pgtap_canale, E_PGTAP_MOTIVO_SENZA:NESSUNO/-/fn_check_pgtap_canale'
    || ' | ' ||
    'E_PGTAP_MOTIVO_CON:campo:1, E_PGTAP_MOTIVO_SENZA:-:1',
    '10. primo motivo via helper SENZA p_campo: il canale viene dal MOTIVO della check, e la risalita condivisa lo dice (motivo_chiave)'
);

SELECT is(
    (SELECT string_agg(codice || ':' || via || '/' || canale || '/' || chiave, ', ' ORDER BY codice)
       FROM _c2 WHERE funzione = 'pgtap_c2.fn_primo_motivo_a_mano'),
    'E_PGTAP_MOTIVO_CON:PRIMO_MOTIVO/IN_CHIAMATA/campo, E_PGTAP_MOTIVO_SENZA:PRIMO_MOTIVO/IN_CHIAMATA/campo',
    '11. primo motivo A MANO (->> ''codice'', la coda del rubinetto) con la chiave nella chiamata: PRIMO_MOTIVO / IN_CHIAMATA'
);

SELECT is(
    (SELECT via || '/' || coalesce(canale, '-') FROM _c2 WHERE codice = 'E_PGTAP_NOMINATO'),
    'NOMINATO/-',
    '12. una funzione che NOMINA il codice senza sollevarlo: NOMINATO, canale NULL — «senza sito» e «nominato e mai sollevato» si distinguono'
);

SELECT is(
    (SELECT canale || '/' || n_chiamate || '/' || n_con_canale FROM _c2 WHERE codice = 'E_PGTAP_TRE'),
    'IN_CHIAMATA/3/2',
    '13. tre chiamate, due col campo: canale IN_CHIAMATA («almeno un punto», verso 1) e n_con_canale < n_chiamate (il verso 2 lo vede)'
);

SELECT is(
    (SELECT canale FROM _c2 WHERE codice = 'E_PGTAP_LIMITE'),
    'NESSUNO',
    '14. IL LIMITE: la chiave dentro un letterale jsonb non si vede — NESSUNO. Il punto cieco e'' scritto, non nascosto'
);

-- ⭐ Una stringa sola per i due siti: filtrata = il SOLO codice del filtro
--   (non l'unione della delegata), accodata = tutti. Il canale viene dal
--   motivo della delegata, come nel 10.
SELECT is(
    (SELECT string_agg(funzione || '>' || codice || ':' || canale, ', ' ORDER BY funzione, codice)
       FROM _c2
      WHERE funzione IN ('pgtap_c2.fn_delega_filtrata', 'pgtap_c2.fn_delega_accodata')
        AND via = 'PRIMO_MOTIVO'),
    'pgtap_c2.fn_delega_accodata>E_PGTAP_MOTIVO_CON:IN_CHIAMATA, '
    || 'pgtap_c2.fn_delega_accodata>E_PGTAP_MOTIVO_SENZA:NESSUNO, '
    || 'pgtap_c2.fn_delega_filtrata>E_PGTAP_MOTIVO_CON:IN_CHIAMATA',
    '15. LA DELEGA: una check che restituisce i motivi di un''altra ne eredita i codici — tutti se li accoda, i soli del filtro se li filtra (->> ''codice'' = ...). Prima: ramo cieco'
);

-- ⛔ Il gemello negativo, ed e' quello che il rubinetto aveva visto: contare
--   i motivi di un'altra check non e' restituirli. Il sito eredita solo il
--   codice che la check emette da se', e NON entra nel perimetro dei
--   `valori` (la delegata li emette, la check che la conta no).
SELECT is(
    (SELECT string_agg(codice || ':' || check_emette_valori, ', ' ORDER BY codice)
       FROM _c2_check
      WHERE funzione = 'pgtap_c2.fn_consumo'),
    'E_PGTAP_CONTATO:false',
    '16. IL CONSUMO non e'' delega: una check che CONTA i motivi di un''altra emette il suo, non eredita codici ne'' `valori`'
);

DROP SCHEMA pgtap_c2 CASCADE;

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia dietro di se' nessuno schema e nessuna funzione di prova.
ROLLBACK;
