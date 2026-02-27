# ⚙️ Funzione `fn_list_attivita_sorgenti_abilitate`

```sql
CREATE FUNCTION fn_list_attivita_sorgenti_abilitate(p_utility_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_attivita_sorgenti_abilitate(p_utility_id integer DEFAULT NULL::integer)
 RETURNS TABLE(sorgente_tipo_id bigint, branch_code character varying, abilitata boolean, acquisizione_mode character varying, block_scope character varying, priorita smallint, meta jsonb)
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le sorgenti abilitate del dominio attivita
  --   con ordinamento centralizzato a DB.
  --
  -- Regole:
  --   - considera solo record policy attivi e abilitati
  --   - ordinamento: priorita, id
  --   - p_utility_id mantenuto per compatibilita` interfaccia
  --     (al momento non applica filtri dedicati)
  -- =========================================================
  IF p_utility_id IS NOT NULL AND p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_attivita_sorgenti_abilitate', 'E_GENERICO',
      jsonb_build_object(
        'scope', 'ATTIVITA_FATTURABILI',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail', 'utility_id non valido', 'utility_id', p_utility_id)
      ),
      NULL::uuid,
      'utility_id non valido'
    );
  END IF;

  RETURN QUERY
  SELECT
    p.sorgente_tipo_id,
    p.branch_code,
    p.abilitata,
    p.acquisizione_mode,
    p.block_scope,
    p.priorita,
    p.meta
  FROM vendite.attivita_fatturabili_sorgenti_branch_policy p
  WHERE p.abilitata IS TRUE
    AND p.attivo IS TRUE
  ORDER BY p.priorita, p.id;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_attivita_sorgenti_abilitate(p_utility_id integer)
IS 'Elenca policy sorgenti abilitate per pipeline attivita (attivo=true, abilitata=true) ordinate per priorita.';
```

---
{% include-markdown "signature-core.md" %}
