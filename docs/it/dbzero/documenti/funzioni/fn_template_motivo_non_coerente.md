{% include-markdown "it/dbzero/documenti/manual/fn_template_motivo_non_coerente.md" %}
# ⚙️ Funzione `fn_template_motivo_non_coerente`

```sql
CREATE FUNCTION fn_template_motivo_non_coerente(p_template_documento_id bigint, p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_template_motivo_non_coerente(p_template_documento_id bigint, p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint DEFAULT NULL::bigint)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (t.id IS NULL) THEN 'MODELLO_INESISTENTE'::text
             WHEN (t.sorgente_tipo_id IS DISTINCT FROM fn_template_motivo_non_coerente.p_sorgente_tipo_id) THEN 'SORGENTE'::text
             WHEN ((fn_template_motivo_non_coerente.p_tipo_documento_output_id IS NOT NULL) AND (t.tipo_documento_output_id IS DISTINCT FROM fn_template_motivo_non_coerente.p_tipo_documento_output_id)) THEN 'TIPO'::text
             WHEN ((t.standard IS NOT TRUE) AND (t.emittente_fiscale_id IS DISTINCT FROM fn_template_motivo_non_coerente.p_emittente_fiscale_id)) THEN 'EMITTENTE'::text
             ELSE NULL::text
         END AS "case"
    FROM (( SELECT 1 AS "?column?") base
      LEFT JOIN documenti.template_documenti t ON ((t.id = fn_template_motivo_non_coerente.p_template_documento_id)));
END

COMMENT ON FUNCTION documenti.fn_template_motivo_non_coerente(p_template_documento_id bigint, p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
IS 'Il modello va bene per il documento? (2026-10-21, brief-db-modelli-documento-standard §10.3 K-4). NULL se si; altrimenti il motivo, nell''ordine: MODELLO_INESISTENTE, SORGENTE, TIPO (solo se il tipo e'' indicato), EMITTENTE (un modello di un altro emittente che non e'' standard). Sede unica della regola: la leggono trgfn_documenti_generati_check_coerenza (regole 2-4) e fn_risolvi_template_applicabile (il modello indicato, prima del render).';
```

</div>

---
{% include-markdown "signature-core.md" %}
