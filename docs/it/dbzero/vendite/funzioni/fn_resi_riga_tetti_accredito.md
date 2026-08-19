{% include-markdown "it/dbzero/vendite/manual/fn_resi_riga_tetti_accredito.md" %}
# ⚙️ Funzione `fn_resi_riga_tetti_accredito`

```sql
CREATE FUNCTION fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
 RETURNS TABLE(accredito_dovuto numeric, qta_riga_fattura numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
-- Scopo: i due tetti dell'accredito, letti SOPRA la RLS.
--   - accredito_dovuto: quanti pezzi (in unita' di MERCE, cioe'
--     unita' padre) il conto della merce dichiara accreditabili
--     per questa riga di reso. Lo consuma la madre, che verifica
--     l'uguaglianza di D-NC-6;
--   - qta_riga_fattura: quanti pezzi ha fatturato la riga di
--     fattura che si sta rettificando. Lo consuma il guard del
--     ponte, come tetto del DOCUMENTO.
-- ⚠️ SECURITY DEFINER perche' i chiamanti sono un guard e una
--   madre: sotto RLS una riga fuori perimetro si legge come «non
--   c'e'», e un tetto letto zero smette di dire la verita'. Il
--   search_path e' fissato perche' una SECURITY DEFINER senza e'
--   dirottabile.
-- ⚠️ Zero e non NULL sull'assenza: e' il valore fail-closed. Una
--   riga fuori dalla coda ha accredito dovuto 0, e qualunque
--   quantita' positiva lo supera.
SELECT
    COALESCE((SELECT sum(q.accredito_dovuto)
                FROM vendite.vw_resi_da_accreditare q
               WHERE q.resi_riga_id = p_resi_riga_id), 0)::numeric,
    COALESCE((SELECT fr.qta
                FROM vendite.fatture_righe fr
               WHERE fr.id = p_fattura_riga_id), 0)::numeric;
$function$

COMMENT ON FUNCTION vendite.fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
IS 'I due tetti dell''accredito di una riga di reso, letti SOPRA la RLS: l''accredito dovuto secondo il conto della merce (in unita'' PADRE, da vendite.vw_resi_da_accreditare) e la quantita'' della riga di fattura che si sta rettificando (in unita'' di riga). ⚠️ SECURITY DEFINER perche'' i consumatori sono un guard e una funzione madre: sotto RLS una riga fuori perimetro si legge come «non c''e''», e un tetto letto zero smette di dire la verita''. E'' il difetto gia'' visto in trgfn_resi_righe_guard_origine_coerente. search_path fissato: una SECURITY DEFINER senza e'' dirottabile. Restituisce 0 sull''assenza, che e'' il valore fail-closed. ⭐ Le due misure sono in UNITA'' DIVERSE e vanno consumate da due presidi diversi: su un articolo composito tre righe di documento valgono UNA unita'' di merce (vw_af_merce_per_riga calcola quantita_padre = max(quantita/coeff_qta), non la somma). brief-design-note-credito-resi D-NC-10. rev 2026-08-18.';
```

---
{% include-markdown "signature-core.md" %}
