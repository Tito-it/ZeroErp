{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_guard_emittente_ba.md" %}
# ⚙️ Funzione `trgfn_contratti_guard_emittente_ba`

```sql
CREATE FUNCTION trgfn_contratti_guard_emittente_ba()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_guard_emittente_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ef_atteso_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
  -- Risolve l'emittente atteso per il BA del contratto.
  -- fn_get_emittente_fiscale_pk solleva E_EMITTENTE_DEFAULT_MISSING
  -- se il BA non ha mapping EF (configurazione errata, non
  -- scenario atteso in produzione).
  v_ef_atteso_id := anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);

  -- Guard: l'emittente del contratto deve corrispondere a quello del BA.
  IF NEW.emittente_fiscale_id IS DISTINCT FROM v_ef_atteso_id THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_contratti_guard_emittente_ba',
      'E_CONTRATTO_EMITTENTE_BA_INCOERENTE',
      jsonb_build_object(
        'billing_account_id',   NEW.billing_account_id,
        'emittente_fiscale_id', NEW.emittente_fiscale_id,
        'emittente_atteso_id',  v_ef_atteso_id,
        'numero_contratto',     NEW.numero
      ),
      NULL::uuid,
      concat('ba=', NEW.billing_account_id,
             ', ef=', NEW.emittente_fiscale_id,
             ', ef_atteso=', v_ef_atteso_id)
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_guard_emittente_ba()
IS 'Guard BEFORE INSERT/UPDATE: verifica che contratti.emittente_fiscale_id coincida con anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id). Solleva E_CONTRATTO_EMITTENTE_BA_INCOERENTE se incoerente. Fires dopo trgfn_contratti_default_emittente (firing order alphabetico).';
```

---
{% include-markdown "signature-core.md" %}
