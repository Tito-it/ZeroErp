{% include-markdown "it/dbzero/documenti/manual/fn_template_motivo_non_stampabile.md" %}
# ⚙️ Funzione `fn_template_motivo_non_stampabile`

```sql
CREATE FUNCTION fn_template_motivo_non_stampabile(p_template_documento_id bigint, p_template_versione_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_template_motivo_non_stampabile(p_template_documento_id bigint, p_template_versione_id bigint DEFAULT NULL::bigint)
 RETURNS text
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN (t.id IS NULL) THEN 'MODELLO_INESISTENTE'::text
             WHEN (NOT t.attivo) THEN 'MODELLO_SPENTO'::text
             WHEN (s.template_versione_id IS NULL) THEN 'NESSUNA_VERSIONE_VALIDA'::text
             WHEN ((fn_template_motivo_non_stampabile.p_template_versione_id IS NOT NULL) AND (s.template_versione_id <> fn_template_motivo_non_stampabile.p_template_versione_id)) THEN 'VERSIONE_NON_IN_USO'::text
             ELSE NULL::text
         END AS "case"
    FROM ((( SELECT 1 AS "?column?") base
      LEFT JOIN documenti.template_documenti t ON ((t.id = fn_template_motivo_non_stampabile.p_template_documento_id)))
      LEFT JOIN documenti.vw_template_versioni_stampabili s ON ((s.template_documento_id = t.id)));
END

COMMENT ON FUNCTION documenti.fn_template_motivo_non_stampabile(p_template_documento_id bigint, p_template_versione_id bigint)
IS 'Il modello oggi puo'' stampare, e con la versione indicata? NULL se si; altrimenti il motivo, nell''ordine: MODELLO_INESISTENTE, MODELLO_SPENTO (il modello e'' disattivato), NESSUNA_VERSIONE_VALIDA (nessuna versione fuori bozza, attiva e valida alla data operativa), VERSIONE_NON_IN_USO (solo con p_template_versione_id: il modello stampa, ma con un''altra versione). «Puo'' stampare» e'' documenti.vw_template_versioni_stampabili, letta e non ricopiata. Sede unica della regola: la leggono documenti.fn_risolvi_template_applicabile (il modello indicato, prima del render) e documenti.trgfn_documenti_generati_check_coerenza (la nascita della stampa).';
```

</div>

---
{% include-markdown "signature-core.md" %}
