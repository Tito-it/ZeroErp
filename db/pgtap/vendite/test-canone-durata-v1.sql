-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il canone «dalla durata del periodo», fonte CANONE/DURATA (changeSet
--       20261029-31 … -33, brief-db-contratto-righe-periodiche-in-commessa §6.9,
--       Lotto 2). Decisione G-9 di Tid (2026-10-28): CANONE/MANUALE esce; la
--       durata conta la quantita' dal calendario nell'unita' dell'articolo, quindi
--       si ammette solo se l'unita' si conta dal calendario (GIORNO | MESE).
--       Decisioni di Tid del 2026-10-29: la durata solo su QUOTA_FISSA, SERVIZI e
--       SERVIZIO_RICORRENTE; IMPOSTA non e' un canone (20261029-34); F-8: dove la
--       durata c'e', per il canone si propone lei, prima e di default (20261029-35).
--
-- ⭐ TUTTO COSTRUITO: articoli dal builder (dbops.fn_pgtap_crea_articolo), con
--   l'unita' che il caso vuole. La regola si legge dalla sede unica del
--   perimetro, vendite.fn_articolo_erogazioni, e dal predicato del guard,
--   script.fn_check_riga_erogazione (senza documento: il motivo della utility
--   tace, parla solo il perimetro).
--
-- Indice test (1..12):
--   Il vocabolario
--    1) CANONE ha due fonti: FISSA (default) e DURATA; CANONE/MANUALE non c'e' piu'
--    2) la durata, mai di default nel seed, su QUOTA_FISSA, SERVIZI e SERVIZIO_RICORRENTE
--    3) GG si conta a GIORNO, MESE a MESE; le ore (HH) no
--   Il perimetro dell'articolo
--    4) servizio ricorrente a pezzi: niente durata
--    5) lo stesso a giorni: la durata c'e', ed e' lei il default (F-8)
--    6) …e a mesi
--    7) un kit a giorni: solo FISSA (I-D6), niente durata
--   Il guard e la quantita'
--    8) CANONE/DURATA su un articolo a pezzi: E_RIGA_EROGAZIONE_FUORI_PERIMETRO / fonte_quantita_attesa
--    9) CANONE/DURATA su un articolo a giorni: ammessa
--   10) la durata non porta la quantita' sulla riga (script.fn_fonte_porta_quantita)
--   L'ordine e le tipologie
--   11) a giorni la durata viene prima della FISSA nell'ordine (F-8)
--   12) IMPOSTA non ammette il canone; ONERE_SISTEMA il canone si', la durata no
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- Scopo: le combinazioni di un articolo come testo ordinato, «EROG/FONTE[*]».
CREATE OR REPLACE FUNCTION pg_temp.combo(p_articolo uuid)
RETURNS text LANGUAGE sql STABLE AS $fx$
    SELECT string_agg(e.tipo_erogazione || '/' || e.fonte_quantita_attesa
                      || CASE WHEN e.e_default THEN '*' ELSE '' END,
                      ' ' ORDER BY e.tipo_erogazione, e.fonte_quantita_attesa)
      FROM vendite.fn_articolo_erogazioni(p_articolo) e;
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.uom(p_codice text)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
    SELECT u.id FROM catalogo.unita_misura u WHERE u.codice = p_codice;
$fx$;

-- ============================================================
-- Fixture COSTRUITA: servizi ricorrenti (natura SERVIZIO_RICORRENTE:
-- CANONE/FISSA*, CANONE/DURATA, CONSUMO/MANUALE) a pezzi, a giorni, a mesi; un kit a giorni.
-- ============================================================
CREATE TEMP TABLE tmp_dur_art AS
SELECT v.sigla, dbops.fn_pgtap_crea_articolo('PGTAP-DUR-' || v.sigla,
           p_uom_id            => CASE v.sigla WHEN 'PZ' THEN NULL
                                               WHEN 'KG' THEN pg_temp.uom('GG')
                                               ELSE pg_temp.uom(v.sigla) END,
           p_is_composito      => v.sigla = 'KG',
           p_natura_vendita_id => (SELECT n.id FROM config.nature_vendita n
                                    WHERE n.codice_interno = 'SERVIZIO_RICORRENTE')) AS id
  FROM (VALUES ('PZ'), ('GG'), ('MESE'), ('KG')) AS v(sigla);

CREATE OR REPLACE FUNCTION pg_temp.art(p_sigla text)
RETURNS uuid LANGUAGE sql STABLE AS $fx$
    SELECT id FROM tmp_dur_art WHERE sigla = p_sigla;
$fx$;

-- ============================================================
-- 1-3) Il vocabolario
-- ============================================================
SELECT is(
    (SELECT string_agg(f.fonte_quantita_attesa || CASE WHEN f.e_default THEN '*' ELSE '' END,
                       ' ' ORDER BY f.fonte_quantita_attesa)
       FROM config.erogazioni_fonti f WHERE f.tipo_erogazione = 'CANONE'),
    'DURATA FISSA*',
    '1) CANONE ha due fonti, FISSA di default e DURATA; CANONE/MANUALE ritirata (G-9)');

SELECT is(
    (SELECT string_agg(x.chi, ' ' ORDER BY x.chi) FROM (
        SELECT 'T:' || lt.codice || CASE WHEN t.e_default THEN '*' ELSE '' END AS chi
          FROM config.listini_tipologie_erogazioni t
          JOIN config.listini_tipologie lt ON lt.id = t.tipologia_id
         WHERE t.tipo_erogazione = 'CANONE' AND t.fonte_quantita_attesa = 'DURATA'
        UNION ALL
        SELECT 'N:' || nv.codice_interno || CASE WHEN n.e_default THEN '*' ELSE '' END
          FROM config.nature_vendita_erogazioni n
          JOIN config.nature_vendita nv ON nv.id = n.natura_vendita_id
         WHERE n.tipo_erogazione = 'CANONE' AND n.fonte_quantita_attesa = 'DURATA') x),
    'N:SERVIZIO_RICORRENTE T:QUOTA_FISSA T:SERVIZI',
    '2) la durata su QUOTA_FISSA, SERVIZI e SERVIZIO_RICORRENTE, mai di default nel seed (Tid, 2026-10-29)');

SELECT is(
    (SELECT string_agg(u.codice || '=' || coalesce(u.conta_dal_calendario, '-'), ' ' ORDER BY u.codice)
       FROM catalogo.unita_misura u WHERE u.codice IN ('GG', 'HH', 'MESE')),
    'GG=GIORNO HH=- MESE=MESE',
    '3) GG si conta a GIORNO, MESE a MESE; le ore no (il pacchetto di ore e'' un canone FISSA, G-10)');

-- ============================================================
-- 4-7) Il perimetro dell'articolo
-- ============================================================
SELECT is(pg_temp.combo(pg_temp.art('PZ')), 'CANONE/FISSA* CONSUMO/MANUALE',
    '4) servizio ricorrente a pezzi: niente durata');

SELECT is(pg_temp.combo(pg_temp.art('GG')), 'CANONE/DURATA* CANONE/FISSA CONSUMO/MANUALE',
    '5) lo stesso a giorni: la durata c''e'', ed e'' lei il default (F-8: il default della natura e'' un canone)');

SELECT is(pg_temp.combo(pg_temp.art('MESE')), 'CANONE/DURATA* CANONE/FISSA CONSUMO/MANUALE',
    '6) …e a mesi');

SELECT is(pg_temp.combo(pg_temp.art('KG')), 'CANONE/FISSA*',
    '7) un kit a giorni: solo FISSA (I-D6), niente durata');

-- ============================================================
-- 8-10) Il guard e la quantita'
-- ============================================================
-- Senza documento (id inesistente) la utility non c'e' e il motivo 1 tace.
SELECT is(
    (SELECT (m -> 0 ->> 'codice') || ' / ' || (m -> 0 -> 'dettaglio' ->> 'campo')
       FROM script.fn_check_riga_erogazione('CONTRATTO', -1, pg_temp.art('PZ'),
                'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'CANONE', 'DURATA') m),
    'E_RIGA_EROGAZIONE_FUORI_PERIMETRO / fonte_quantita_attesa',
    '8) CANONE/DURATA su un articolo a pezzi: fuori perimetro, col campo della fonte');

SELECT is(
    script.fn_check_riga_erogazione('CONTRATTO', -1, pg_temp.art('GG'),
        'AGGIUNTA'::vendite.tipo_eccezione_contratto, 'CANONE', 'DURATA'),
    '[]'::jsonb,
    '9) CANONE/DURATA su un articolo a giorni: ammessa');

SELECT is(script.fn_fonte_porta_quantita('DURATA'), false,
    '10) la durata non porta la quantita'' sulla riga: la conta il sistema dal calendario');

-- ============================================================
-- 11-12) L'ordine (F-8) e le tipologie che non sono un canone
-- ============================================================
SELECT is(
    (SELECT string_agg(e.fonte_quantita_attesa, ' ' ORDER BY e.ordine)
       FROM vendite.fn_articolo_erogazioni(pg_temp.art('GG')) e
      WHERE e.tipo_erogazione = 'CANONE'),
    'DURATA FISSA',
    '11) a giorni, per il canone la durata viene prima della FISSA: e'' la fonte che l''eredita'' e il form propongono');

SELECT is(
    (SELECT string_agg(lt.codice || ':' || coalesce(x.fonti, '-'), ' ' ORDER BY lt.codice)
       FROM config.listini_tipologie lt
       LEFT JOIN LATERAL (
            SELECT string_agg(t.fonte_quantita_attesa, ',' ORDER BY t.fonte_quantita_attesa) AS fonti
              FROM config.listini_tipologie_erogazioni t
             WHERE t.tipologia_id = lt.id AND t.tipo_erogazione = 'CANONE') x ON true
      WHERE lt.codice IN ('IMPOSTA', 'ONERE_SISTEMA')),
    'IMPOSTA:- ONERE_SISTEMA:FISSA',
    '12) IMPOSTA non e'' un canone; ONERE_SISTEMA il canone fisso si'', la durata no (Tid, 2026-10-29)');

SELECT * FROM finish();
ROLLBACK;
