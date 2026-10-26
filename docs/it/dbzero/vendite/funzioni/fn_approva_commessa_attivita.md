{% include-markdown "it/dbzero/vendite/manual/fn_approva_commessa_attivita.md" %}
# ⚙️ Funzione `fn_approva_commessa_attivita`

```sql
CREATE FUNCTION fn_approva_commessa_attivita(p_commessa_id bigint, p_righe_ids bigint[], p_user text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_approva_commessa_attivita(p_commessa_id bigint, p_righe_ids bigint[] DEFAULT NULL::bigint[], p_user text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: approvazione righe commessa (BOZZA -> APPROVATA).
--   p_righe_ids NULL = tutte le righe NON_EMESSA della commessa.
--   Idempotente: salta le righe gia' APPROVATA. Ritorna il numero
--   di righe effettivamente approvate.
DECLARE
  v_approvate integer := 0;
BEGIN
  -- Guard: la commessa deve esistere.
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse WHERE id = p_commessa_id) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_approva_commessa_attivita',
      'E_COMMESSA_NON_TROVATA',
      jsonb_build_object('p_commessa_id', p_commessa_id),
      NULL::uuid,
      coalesce(p_commessa_id::text, 'NULL')
    );
  END IF;

  UPDATE vendite.commesse_attivita ca
     SET stato_approvazione = 'APPROVATA',
         user_update = COALESCE(p_user, CURRENT_USER)
   WHERE ca.commessa_id = p_commessa_id
     AND ca.stato_approvazione = 'BOZZA'
     AND ca.stato_emissione = 'NON_EMESSA'
     AND (p_righe_ids IS NULL OR ca.id = ANY(p_righe_ids));

  GET DIAGNOSTICS v_approvate = ROW_COUNT;
  RETURN v_approvate;
END
$function$

COMMENT ON FUNCTION vendite.fn_approva_commessa_attivita(p_commessa_id bigint, p_righe_ids bigint[], p_user text)
IS 'Approva righe commessa (stato_approvazione BOZZA->APPROVATA, solo NON_EMESSA). p_righe_ids NULL = tutte. Idempotente. Prerequisito di riga per emissione e per testata ->PRONTA_FATTURAZIONE. rev 2026-06-07.';
```

</div>

---
{% include-markdown "signature-core.md" %}
