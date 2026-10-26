{% include-markdown "it/dbzero/documenti/manual/fn_template_esito_risoluzione.md" %}
# ⚙️ Funzione `fn_template_esito_risoluzione`

```sql
CREATE FUNCTION fn_template_esito_risoluzione(p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint, p_sorgente_tipo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_template_esito_risoluzione(p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint, p_sorgente_tipo_id bigint)
 RETURNS TABLE(esito text, template_documento_id bigint, template_versione_id bigint, modelli_stampabili integer)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN ((x.n_propri > 0) AND (x.def_proprio IS NOT NULL)) THEN 'EMITTENTE'::text
             WHEN (x.n_propri > 0) THEN 'SENZA_PREDEFINITO'::text
             WHEN (x.def_standard IS NOT NULL) THEN 'STANDARD'::text
             ELSE 'NON_RISOLTO'::text
         END AS "case",
         CASE
             WHEN (x.n_propri > 0) THEN x.def_proprio
             ELSE x.def_standard
         END AS def_standard,
         CASE
             WHEN (x.n_propri > 0) THEN x.ver_proprio
             ELSE x.ver_standard
         END AS ver_standard,
     x.n_propri
    FROM ( SELECT (count(DISTINCT s.template_documento_id) FILTER (WHERE (NOT s.standard)))::integer AS n_propri,
             max(s.template_documento_id) FILTER (WHERE ((NOT s.standard) AND s.is_default)) AS def_proprio,
             max(s.template_versione_id) FILTER (WHERE ((NOT s.standard) AND s.is_default)) AS ver_proprio,
             max(s.template_documento_id) FILTER (WHERE (s.standard AND s.is_default)) AS def_standard,
             max(s.template_versione_id) FILTER (WHERE (s.standard AND s.is_default)) AS ver_standard
            FROM documenti.vw_template_versioni_stampabili s
           WHERE ((s.tipo_documento_output_id = fn_template_esito_risoluzione.p_tipo_documento_output_id) AND (s.sorgente_tipo_id = fn_template_esito_risoluzione.p_sorgente_tipo_id) AND ((s.emittente_fiscale_id = fn_template_esito_risoluzione.p_emittente_fiscale_id) OR s.standard))) x;
END

COMMENT ON FUNCTION documenti.fn_template_esito_risoluzione(p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint, p_sorgente_tipo_id bigint)
IS 'L''esito della risoluzione a due livelli per (emittente, tipo, sorgente), sui modelli che possono stampare (vw_template_versioni_stampabili) (2026-10-21, brief-db-modelli-documento-standard §10.3 K-5; strada B di §4.1 Q-2): EMITTENTE (il suo predefinito stampabile), SENZA_PREDEFINITO (ha modelli suoi stampabili, nessuno predefinito: lo standard non entra), STANDARD (il predefinito standard stampabile), NON_RISOLTO. Con modello, versione e numero dei modelli suoi stampabili. Sempre una riga. Sede unica della regola: la leggono fn_risolvi_template_applicabile e vw_template_risoluzione_emittente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
