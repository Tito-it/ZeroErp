{% include-markdown "it/dbzero/vendite/manual/fn_resi_riga_tetti_accredito.md" %}
# ⚙️ Funzione `fn_resi_riga_tetti_accredito`

```sql
CREATE FUNCTION fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
 RETURNS TABLE(accredito_dovuto numeric, qta_riga_fattura numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
 SET plan_cache_mode TO 'force_generic_plan'
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
-- ⭐ rev 2026-09-21 (D14 giro 2, D3): la coda si legge PER
--   DOCUMENTO — fn_resi_da_accreditare col seme del DDT della
--   riga resa — e non piu' dalla vista, che e' la coda di TUTTI
--   e qui veniva pagata a ogni riga scritta sul ponte. Dentro
--   questa DEFINER la funzione (INVOKER) gira come l'owner: sopra
--   la RLS, com'era la vista. COALESCE a '{}' se la riga non
--   c'e': un array NULL sarebbe «tutta la coda».
SELECT
    COALESCE((SELECT sum(q.accredito_dovuto)
                FROM vendite.fn_resi_da_accreditare(
                         COALESCE((SELECT ARRAY[dr.ddt_id]
                                     FROM vendite.resi_righe rr
                                     JOIN vendite.ddt_righe dr ON dr.id = rr.ddt_riga_id
                                    WHERE rr.id = p_resi_riga_id),
                                  '{}'::bigint[]),
                         NULL::bigint[]) q
               WHERE q.resi_riga_id = p_resi_riga_id), 0)::numeric,
    COALESCE((SELECT fr.qta
                FROM vendite.fatture_righe fr
               WHERE fr.id = p_fattura_riga_id), 0)::numeric;
$function$

COMMENT ON FUNCTION vendite.fn_resi_riga_tetti_accredito(p_resi_riga_id bigint, p_fattura_riga_id bigint)
IS 'I due tetti dell''accredito di una riga di reso, letti SOPRA la RLS: l''accredito dovuto secondo il conto della merce (in unita'' PADRE) e la quantita'' della riga di fattura che si sta rettificando (in unita'' di riga). ⭐ rev 2026-09-21 (D14 giro 2, D3): il primo tetto si legge PER DOCUMENTO da vendite.fn_resi_da_accreditare(ARRAY[ddt della riga resa], NULL) — la coda di quel DDT — e non piu'' da vw_resi_da_accreditare intera, che questo guard pagava a ogni riga scritta sul ponte; stesso numero (la vista e'' la proiezione della funzione). ⚠️ SECURITY DEFINER perche'' i consumatori sono un guard (trgfn_resi_accrediti_guard) e una funzione madre: sotto RLS una riga fuori perimetro si legge come «non c''e''», e un tetto letto zero smette di dire la verita''. Dentro la DEFINER la funzione INVOKER a valle gira come l''owner, sopra la RLS. search_path fissato: una SECURITY DEFINER senza e'' dirottabile (i corpi BEGIN ATOMIC a valle hanno i nomi gia'' risolti). Restituisce 0 sull''assenza, che e'' il valore fail-closed; su una riga inesistente il seme e'' ''{}'' (zero righe, non «tutta la coda»). ⭐ Le due misure sono in UNITA'' DIVERSE e vanno consumate da due presidi diversi: su un articolo composito tre righe di documento valgono UNA unita'' di merce (vw_af_merce_per_riga calcola quantita_padre = max(quantita/coeff_qta), non la somma). brief-design-note-credito-resi D-NC-10. rev 2026-08-18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
