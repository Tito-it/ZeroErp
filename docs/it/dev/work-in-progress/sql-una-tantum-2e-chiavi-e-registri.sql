-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- SQL una tantum per Zero ERP — NON e' un changeSet
--
-- Sotto-giri 2c-2e (brief-db-grammatica-unica-documenti §13): i DATI di dbdev che
-- i changeSet 20261020-32 ... -98 non toccano, perche' sono dati dell'installazione e
-- non catalogo (L2e-1 di Tid, 2026-10-20: solo dbdev; dev.smoke e' un utente di dbdev).
--
-- QUANDO: subito DOPO l'apply di 20261020-32 ... -98, prima di lavorare con push,
--   commesse e registri. Da zero (CI, scratch) non serve: le chiavi e i registri
--   nascono gia' nella forma nuova.
-- COME:  set -a; . db/internal.env; set +a
--        psql -X -v ON_ERROR_STOP=1 -f <questo file>
--
-- COSA FA (per criterio, non per id; rilanciato non trova piu' niente):
--   1) le chiavi del push (vendite.commesse_attivita.segment_key) prendono il codice
--      della sorgente come prefisso (G-8): PREV -> PREVENTIVO, ORD -> ORDINE_VENDITA,
--      DDT -> DDT_VENDITA, CONTR -> CONTRATTO, CONS -> ATTIVITA_CONSUMI. MAN resta (le
--      righe a mano non hanno un documento). Il resto della chiave (:R:, :M:, #CMP:,
--      #RET:) resta com'e'; segment_base e' generata e segue da sola;
--   2) le copie della chiave nel meta delle attivita' fatturabili (meta->>'segment_key'),
--      con la stessa regola: nessuno le usa per ritrovare una riga, ma nei dati non
--      restano due grammatiche;
--   3) i registri nati dal provisioning prendono il codice nuovo (L2c-1):
--      <codice della famiglia>-<id dell'emittente> al posto delle tre prime lettere. Lo
--      standard della FATTURA si riconosce solo dal codice: senza questo passo il
--      provisioning ne creerebbe un secondo.
--
-- ⚠️ I TRIGGER: un UPDATE di commesse_attivita fa scattare guard di riga senza lista di
--   colonne (listino, proiezione dello stato del preventivo, storico), anche su righe
--   gia' fatturate; la conversione sul posto (ALTER TYPE ... USING) e' impedita dalla
--   colonna generata segment_base. Si spengono i trigger UTENTE delle due tabelle solo
--   dentro questa transazione (DISABLE TRIGGER USER: lo puo' fare il proprietario) e si
--   riaccendono prima del COMMIT. Nessuna riga di storico per un cambio tecnico di
--   nome: e' voluto. I registri non ne hanno bisogno (nessun guard nomina codice).
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE una_tantum_mappa (vecchio text PRIMARY KEY, nuovo text NOT NULL) ON COMMIT DROP;
INSERT INTO una_tantum_mappa VALUES
    ('PREV',  'PREVENTIVO'),
    ('ORD',   'ORDINE_VENDITA'),
    ('DDT',   'DDT_VENDITA'),
    ('CONTR', 'CONTRATTO'),
    ('CONS',  'ATTIVITA_CONSUMI');

CREATE TEMP TABLE una_tantum_riepilogo (passo text, righe bigint) ON COMMIT DROP;

-- ---------------------------------------------------------------- 1) le chiavi
ALTER TABLE vendite.commesse_attivita DISABLE TRIGGER USER;

WITH c AS (
    UPDATE vendite.commesse_attivita ca
       SET segment_key = m.nuovo || substr(ca.segment_key, length(m.vecchio) + 1)
      FROM una_tantum_mappa m
     WHERE split_part(ca.segment_key, ':', 1) = m.vecchio
    RETURNING 1)
INSERT INTO una_tantum_riepilogo SELECT '1) chiavi di commesse_attivita', count(*) FROM c;

ALTER TABLE vendite.commesse_attivita ENABLE TRIGGER USER;

-- ---------------------------------------------------------------- 2) le copie nel meta
ALTER TABLE vendite.attivita_fatturabili DISABLE TRIGGER USER;

WITH c AS (
    UPDATE vendite.attivita_fatturabili af
       SET meta = jsonb_set(af.meta, '{segment_key}',
                            to_jsonb(m.nuovo || substr(af.meta ->> 'segment_key', length(m.vecchio) + 1)))
      FROM una_tantum_mappa m
     WHERE split_part(af.meta ->> 'segment_key', ':', 1) = m.vecchio
    RETURNING 1)
INSERT INTO una_tantum_riepilogo SELECT '2) copie nel meta delle attivita fatturabili', count(*) FROM c;

ALTER TABLE vendite.attivita_fatturabili ENABLE TRIGGER USER;

-- ---------------------------------------------------------------- 3) i registri provvisionati
WITH c AS (
    UPDATE vendite.registri_fatturazione r
       SET codice = vendite.fn_codice_registro_provisionato(r.famiglia_documento, r.emittente_soggetto_ruolo_id)
     WHERE r.codice = left(r.famiglia_documento, 3) || '-' || r.emittente_soggetto_ruolo_id::text
       AND r.codice <> vendite.fn_codice_registro_provisionato(r.famiglia_documento, r.emittente_soggetto_ruolo_id)
    RETURNING 1)
INSERT INTO una_tantum_riepilogo SELECT '3) codici dei registri provvisionati', count(*) FROM c;

\echo 'Riepilogo:'
SELECT * FROM una_tantum_riepilogo ORDER BY passo;

\echo 'Controllo: prefissi rimasti nelle chiavi (deve esserci solo il codice delle sorgenti e MAN):'
SELECT split_part(segment_key, ':', 1) AS prefisso, count(*)
  FROM vendite.commesse_attivita GROUP BY 1 ORDER BY 1;

COMMIT;
