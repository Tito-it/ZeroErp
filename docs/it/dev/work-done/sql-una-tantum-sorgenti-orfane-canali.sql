-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum — gli orfani di sorgente su dbdev (S-6 / D-12 di Tid, 2026-11-06)
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto 0, giro 0.2.
--
-- Che cosa: dal giro 0.2 il presidio degli orfani (dbops.vw_sorgenti_orfane) copre
-- ogni tabella con la provenienza. Su dbdev, il 2026-11-06 dopo l'apply, vede 387
-- righe, TUTTE in vendite.documenti_fatturazione_canali (TESTUALE, livello
-- DOCUMENTO): PREVENTIVO 352, DDT_VENDITA 16, CONTRATTO 14, ORDINE_VENDITA 5.
-- Sono canali di fatturazione di documenti cancellati (V-5: il canale nasce
-- all'INSERT della bozza e non si toglie al DELETE). Dati di test: si cancellano.
--
-- Perche' si possono cancellare senza altro:
--   · nessuna FK punta a vendite.documenti_fatturazione_canali;
--   · nessun lettore fuori dalla funzione che lo scrive (§6.4); il registro si
--     ritira comunque nel lotto T (D-10);
--   · sul DELETE gira solo lo storico (trgfn_storico_generic): la cancellazione
--     resta tracciata in storico.documenti_fatturazione_canali.
--
-- Come: in UNA transazione. Si cancellano SOLO le righe che il presidio indica
-- (per id, dalla vista), poi si verifica che il presidio sia vuoto: se resta
-- qualcosa lo script si ferma e non scrive niente. Idempotente: rilanciato a
-- presidio vuoto cancella zero righe.
-- Chi: Tid, come zeroerp_owner (db/internal.env). Solo sviluppo.
--
-- Uso:
--   set -a; . db/internal.env; set +a
--   psql -v ON_ERROR_STOP=1 -f docs/it/dev/work-done/sql-una-tantum-sorgenti-orfane-canali.sql
-- ------------------------------------------------------------

BEGIN;

-- 1. Che cosa c'e', prima
SELECT o.tabella, o.livello, o.sorgente_codice_interno, count(*) AS orfani
  FROM dbops.vw_sorgenti_orfane o
 GROUP BY 1, 2, 3
 ORDER BY 1, 3;

-- 2. Le righe da cancellare: solo quelle del registro dei canali che il presidio indica
CREATE TEMP TABLE _orfani_canali ON COMMIT DROP AS
SELECT o.riga_id AS id
  FROM dbops.vw_sorgenti_orfane o
 WHERE o.tabella = 'vendite.documenti_fatturazione_canali'::regclass;

DELETE FROM vendite.documenti_fatturazione_canali c
 USING _orfani_canali x
 WHERE c.id = x.id;

-- 3. Il presidio dev'essere vuoto: altrimenti si annulla tutto
DO $verifica$
DECLARE
    v_restano bigint;
BEGIN
    SELECT count(*) INTO v_restano FROM dbops.vw_sorgenti_orfane;
    IF v_restano > 0 THEN
        RAISE EXCEPTION 'Restano % orfani fuori dal registro dei canali: niente e'' stato cancellato. Guardare dbops.vw_sorgenti_orfane.', v_restano;
    END IF;
    RAISE NOTICE 'Presidio degli orfani vuoto.';
END
$verifica$;

COMMIT;
