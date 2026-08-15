{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_emittente_ba.md" %}
# ⚙️ Funzione `trgfn_resi_guard_emittente_ba`

```sql
CREATE FUNCTION trgfn_resi_guard_emittente_ba()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_emittente_ba()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ef_atteso_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
  -- Skip: nessun BA su cui ancorare la coerenza.
  IF NEW.billing_account_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Emittente atteso per il BA del reso.
  v_ef_atteso_id := anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);

  IF NEW.emittente_fiscale_id IS DISTINCT FROM v_ef_atteso_id THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_resi_guard_emittente_ba',
      'E_RESO_EMITTENTE_BA_INCOERENTE',
      jsonb_build_object(
          'campo', 'emittente_fiscale_id',
        'billing_account_id',   NEW.billing_account_id,
        'emittente_fiscale_id', NEW.emittente_fiscale_id,
        'emittente_atteso_id',  v_ef_atteso_id,
        'numero_reso',          NEW.numero
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

COMMENT ON FUNCTION vendite.trgfn_resi_guard_emittente_ba()
IS 'Guard coerenza emittente<->BA su vendite.resi (E_RESO_EMITTENTE_BA_INCOERENTE). Mirror trgfn_ddt_guard_emittente_ba; firing z10 dopo il normalize. rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
