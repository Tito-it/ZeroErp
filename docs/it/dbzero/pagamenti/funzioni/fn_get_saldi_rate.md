{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldi_rate.md" %}
# ⚙️ Funzione `fn_get_saldi_rate`

```sql
CREATE FUNCTION fn_get_saldi_rate(p_scadenza_ids bigint[], p_escludi_contabile_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldi_rate(p_scadenza_ids bigint[], p_escludi_contabile_riga_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(scadenza_id bigint, saldo numeric, in_lavorazione numeric, incassato numeric, has_movimenti boolean)
 LANGUAGE sql
 STABLE
AS $function$
-- Scopo: il nucleo set-based dei saldi delle rate, con l'IMPUTAZIONE
--        derivata dei movimenti e delle righe senza rata (Q-A/γ).
-- Regole: array obbligatorio; si leggono TUTTE le rate dei documenti
--         coinvolti (il piano intero) e si restituiscono le chieste;
--         FIFO per data_scadenza fino a capienza, l'ultima assorbe;
--         il verso e' quello del documento; nessuna scrittura.
WITH
-- 1) i documenti delle rate chieste
docs AS (
    SELECT DISTINCT s.fattura_id
      FROM vendite.fatture_scadenze s
     WHERE s.id = ANY (p_scadenza_ids)
),
-- 2) TUTTE le rate di quei documenti, in ordine di imputazione
rate AS (
    SELECT s.id, s.fattura_id, s.importo,
           row_number() OVER (PARTITION BY s.fattura_id
                              ORDER BY s.data_scadenza, s.numero_rata, s.id) AS rn,
           count(*)     OVER (PARTITION BY s.fattura_id)                    AS n_rate,
           sign(sum(s.importo) OVER (PARTITION BY s.fattura_id))             AS segno
      FROM vendite.fatture_scadenze s
     WHERE s.fattura_id IN (SELECT d.fattura_id FROM docs d)
),
-- 3) cio' che e' REGISTRATO: per rata (scadenza_id) e senza rata (NULL)
mov AS (
    SELECT m.fattura_id, m.scadenza_id,
           SUM(m.importo) AS movimenti,
           SUM(m.importo) FILTER (
               WHERE c.id IS NOT NULL
                 AND c.is_fondo_fattura IS FALSE
                 AND c.is_compensazione IS FALSE) AS incassato,
           count(*) AS n
      FROM pagamenti.vendite_movimenti m
      LEFT JOIN pagamenti.centri_riscossione c ON c.id = m.centro_riscossione_id
     WHERE m.attivo IS TRUE
       AND m.fattura_id IN (SELECT d.fattura_id FROM docs d)
       AND (p_escludi_contabile_riga_id IS NULL
            OR m.contabile_riga_id IS DISTINCT FROM p_escludi_contabile_riga_id)
     GROUP BY m.fattura_id, m.scadenza_id
),
-- 4) cio' che e' DICHIARATO: righe postabili sotto testata non finale
lav AS (
    SELECT cr.fattura_id, cr.scadenza_id,
           SUM(cr.importo) AS in_lavorazione
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
      JOIN pagamenti.vendite_contabili co             ON co.id = cr.contabile_id
      JOIN pagamenti.vendite_contabili_stati cs       ON cs.id = co.stato_id
     WHERE cr.attivo IS TRUE
       AND st.is_postabile IS TRUE
       AND cs.is_final IS NOT TRUE
       AND cr.fattura_id IN (SELECT d.fattura_id FROM docs d)
       AND (p_escludi_contabile_riga_id IS NULL
            OR cr.id <> p_escludi_contabile_riga_id)
     GROUP BY cr.fattura_id, cr.scadenza_id
),
-- 5) la base per rata: diretti, non-imputato del documento (in unita'
--    positive, col verso del documento), capienza del primo stadio
base AS (
    SELECT r.id, r.fattura_id, r.importo, r.rn, r.n_rate, r.segno,
           COALESCE(mr.movimenti, 0)                AS mov_diretti,
           COALESCE(mr.incassato, 0)                AS inc_diretti,
           (mr.n IS NOT NULL)                       AS ha_diretti,
           COALESCE(lr.in_lavorazione, 0)           AS lav_diretta,
           COALESCE(md.movimenti, 0)                AS u_mov_raw,
           COALESCE(md.incassato, 0)                AS u_inc_raw,
           r.segno * COALESCE(md.movimenti, 0)      AS u_mov,
           r.segno * COALESCE(ld.in_lavorazione, 0) AS u_lav,
           GREATEST(r.segno * (r.importo - COALESCE(mr.movimenti, 0)), 0) AS cap1
      FROM rate r
      LEFT JOIN mov mr ON mr.scadenza_id = r.id
      LEFT JOIN lav lr ON lr.scadenza_id = r.id
      LEFT JOIN mov md ON md.fattura_id = r.fattura_id AND md.scadenza_id IS NULL
      LEFT JOIN lav ld ON ld.fattura_id = r.fattura_id AND ld.scadenza_id IS NULL
),
-- 6) primo stadio: i movimenti senza rata, FIFO fino a capienza
st1 AS (
    SELECT b.*,
           COALESCE(sum(b.cap1) OVER (PARTITION BY b.fattura_id ORDER BY b.rn
                                      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS cap1_prima
      FROM base b
),
st1b AS (
    SELECT s.*,
           CASE
               -- verso contrario al documento: tutto sulla prima, resta visibile
               WHEN s.u_mov < 0     THEN CASE WHEN s.rn = 1 THEN s.u_mov ELSE 0 END
               -- l'ultima assorbe l'eccedenza: Σ rate = documento
               WHEN s.rn = s.n_rate THEN GREATEST(s.u_mov - s.cap1_prima, 0)
               ELSE LEAST(GREATEST(s.u_mov - s.cap1_prima, 0), s.cap1)
           END AS take1
      FROM st1 s
),
-- 7) secondo stadio: le righe senza rata, sullo spazio che resta
st2 AS (
    SELECT s.*,
           s.segno * s.take1 AS imputato_mov,
           GREATEST(s.segno * (s.importo - s.mov_diretti - s.segno * s.take1 - s.lav_diretta), 0) AS cap2
      FROM st1b s
),
st2b AS (
    SELECT s.*,
           COALESCE(sum(s.cap2) OVER (PARTITION BY s.fattura_id ORDER BY s.rn
                                      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS cap2_prima
      FROM st2 s
),
st2c AS (
    SELECT s.*,
           CASE
               WHEN s.u_lav < 0     THEN CASE WHEN s.rn = 1 THEN s.u_lav ELSE 0 END
               WHEN s.rn = s.n_rate THEN GREATEST(s.u_lav - s.cap2_prima, 0)
               ELSE LEAST(GREATEST(s.u_lav - s.cap2_prima, 0), s.cap2)
           END AS take2
      FROM st2b s
)
SELECT s.id                                                       AS scadenza_id,
       s.importo - s.mov_diretti - s.imputato_mov                 AS saldo,
       s.lav_diretta + s.segno * s.take2                          AS in_lavorazione,
       s.inc_diretti
         + CASE WHEN s.u_mov_raw <> 0
                THEN round(s.imputato_mov * s.u_inc_raw / s.u_mov_raw, 6)
                ELSE 0 END                                        AS incassato,
       (s.ha_diretti OR s.imputato_mov <> 0)                      AS has_movimenti
  FROM st2c s
 WHERE s.id = ANY (p_scadenza_ids);
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldi_rate(p_scadenza_ids bigint[], p_escludi_contabile_riga_id bigint)
IS 'IL NUCLEO dei saldi delle rate: la formula scritta UNA volta in forma set-based, per N rate. `saldo` = importo della rata meno i movimenti attivi che la NOMINANO meno la quota IMPUTATA dei movimenti del documento senza rata; `in_lavorazione` = righe contabili attive, postabili, sotto distinta non finale, dirette piu'' la quota imputata di quelle senza rata; `incassato` = cassa vera (centro presente, non fondo fattura ne'' compensazione), diretta piu'' la quota imputata in proporzione; `has_movimenti` = movimenti diretti o quota imputata diversa da zero. ⭐ rev 2 del 2026-09-17 — L''IMPUTAZIONE DERIVATA (Q-A/γ, decisione di Tid): i movimenti e le righe SENZA rata di un documento si attribuiscono alle sue rate in ordine di data_scadenza (poi numero_rata, id) fino alla capienza di ciascuna, e l''ultima assorbe l''eccedenza — cosi'' Σ saldi delle rate = saldo del documento SEMPRE, per costruzione; il verso e'' quello del documento (sign della somma delle rate: su una nota di credito le rate sono negative, la capienza e'' in valore assoluto — la forma di D14-c), e un non-imputato di verso contrario va tutto sulla prima rata, dove resta visibile come MOVIMENTO_CONTRARIO. Nessuno scrive niente: e'' D2 («lo stato della rata e'' derivato, mai scritto») fino in fondo. E'' la risposta al PUNTO CIECO della rata: il fondo fattura scrive la propria riga sul documento sorgente senza rata, D16 ammette la riga manuale «fattura si'', rata no», e prima di questa rev una fattura a rata unica pagata cosi'' aveva saldo_fattura 0 e saldo_rata 100 — e la rata della nota di credito (P-5) avrebbe contato il credito riportato due volte. ⚠️ Per imputare servono TUTTE le rate del documento: il nucleo legge il piano intero dei documenti delle rate chieste e restituisce le chieste. p_scadenza_ids e'' OBBLIGATORIO (`= ANY` nudo, indicizzabile in ogni forma; NULL = zero righe: per tutte le rate c''e'' vw_saldi_rate). p_escludi_contabile_riga_id toglie la riga che sta scrivendo, diretta o senza rata. ⭐ TRE PORTE, UNA FORMULA: fn_get_saldo_rata (caso a un elemento, con guard ed E_RATA_NON_TROVATA), vw_saldi_rate (tutte le rate), la chiamata con l''array della pagina dal backend. ⚠️ STABLE e LANGUAGE sql: non solleva mai, INVOKER (somma cio'' che chi legge vede). Brief: brief-db-distinta-ricerca-rate §4-bis.4 e §4-bis.6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
