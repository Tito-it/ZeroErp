{% include-markdown "it/dbzero/vendite/manual/fn_resolve_attivita_sorgente_branch_policy.md" %}
# ⚙️ Funzione `fn_resolve_attivita_sorgente_branch_policy`

```sql
CREATE FUNCTION fn_resolve_attivita_sorgente_branch_policy(p_sorgente_tipo_id bigint, p_require_abilitata boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_attivita_sorgente_branch_policy(p_sorgente_tipo_id bigint, p_require_abilitata boolean DEFAULT true)
 RETURNS TABLE(sorgente_tipo_id bigint, branch_code character varying, abilitata boolean, acquisizione_mode character varying, block_scope character varying, priorita smallint, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire la policy sorgente->branch per dominio
  --   ATTIVITA_FATTURABILI evitando mapping hardcoded in backend.
  --
  -- Regole:
  --   - p_sorgente_tipo_id obbligatorio (>0)
  --   - filtra sempre record attivi
  --   - se p_require_abilitata=true ritorna solo policy abilitate
  -- =========================================================
  IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_resolve_attivita_sorgente_branch_policy',
      'E_GENERICO',
      jsonb_build_object(
        'scope','ATTIVITA_FATTURABILI',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id',NULL,
        'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','sorgente_tipo_id obbligatorio',
          'sorgente_tipo_id',p_sorgente_tipo_id
        )
      ),
      NULL::uuid,
      'sorgente_tipo_id obbligatorio'
    );
  END IF;

  RETURN QUERY
  SELECT p.sorgente_tipo_id,
         p.branch_code,
         p.abilitata,
         p.acquisizione_mode,
         p.block_scope,
         p.priorita,
         p.meta
  FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
  WHERE p.sorgente_tipo_id = p_sorgente_tipo_id
    AND p.attivo IS TRUE
    AND (NOT p_require_abilitata OR p.abilitata IS TRUE)
  ORDER BY p.priorita, p.id
  LIMIT 1;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_resolve_attivita_sorgente_branch_policy',
      'E_GENERICO',
      jsonb_build_object(
        'scope','ATTIVITA_FATTURABILI',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id',NULL,
        'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','policy sorgente non trovata/non abilitata',
          'sorgente_tipo_id',p_sorgente_tipo_id,
          'require_abilitata',p_require_abilitata
        )
      ),
      NULL::uuid,
      'Policy sorgente attivita non trovata/non abilitata'
    );
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_resolve_attivita_sorgente_branch_policy(p_sorgente_tipo_id bigint, p_require_abilitata boolean)
IS 'Risoluzione centralizzata sorgente->branch/policy per pipeline attivita con filtro opzionale su abilitazione.';
```

---
{% include-markdown "signature-core.md" %}
