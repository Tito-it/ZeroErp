{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_ba_coerenza.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_ba_coerenza`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_ba_coerenza()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_iu_id anagrafiche.billing_account.istanza_utility_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Validare coerenza tra billing_account e istanza_utility
  --   sulle righe attivita_fatturabili.
  --
  -- Regole:
  --   - se billing_account_id e` valorizzato, deve esistere
  --   - istanza_utility_id deve coincidere con quella del BA
  --   - variadic su fn_log_and_raise_error sempre testuali
  --
  -- 🔴 REV 2026-09-10 — TOLTA l'uscita anticipata.
  --   Il corpo apriva con:
  --       IF NEW.commessa_attivita_id IS NOT NULL THEN RETURN NEW;
  --   motivata cosi': «righe da commessa: coerenza garantita a
  --   monte dal push (fn_get_or_create_commessa)». Ma
  --   `commessa_attivita_id` e` NOT NULL: quell'uscita valeva per
  --   OGNI riga che sopravvive, e il guard non validava mai
  --   niente. Un presidio che sembra esserci e non c'e`.
  --   ⛔ E «garantita a monte» e` una convenzione, non una
  --   garanzia: un guard esiste per il giorno in cui qualcuno
  --   scrive da un'altra parte.
  -- =========================================================

  IF NEW.billing_account_id IS NOT NULL THEN
    SELECT b.istanza_utility_id
      INTO v_iu_id
      FROM anagrafiche.billing_account b
     WHERE b.id = NEW.billing_account_id;

    IF NOT FOUND THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'attivita_fatturabili',
        'E_PARAMETRI_TABELLA',
        jsonb_build_object(
          'context','validazione billing_account_id',
          'billing_account_id', NEW.billing_account_id
        ),
        NULL::uuid,
        'billing_account', NEW.billing_account_id::text
      );
    END IF;

    IF NEW.istanza_utility_id IS DISTINCT FROM v_iu_id THEN
      PERFORM script.fn_log_and_raise_error(
        'database',
        'attivita_fatturabili',
        'E_COERENZA_ID',
        jsonb_build_object(
          'context','validazione istanza_utility_id',
          'istanza_utility_id', NEW.istanza_utility_id,
          'billing_account_id', NEW.billing_account_id,
          'istanza_utility_attesa', v_iu_id
        ),
        NULL::uuid,
        'istanza_utility_id', COALESCE(NEW.istanza_utility_id::text, 'NULL'),
        'billing_account', NEW.billing_account_id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()
IS 'Guard BEFORE INSERT OR UPDATE su vendite.attivita_fatturabili: la riga e il suo billing account devono nominare la stessa istanza di utility. 🔴 Dal 2026-09-10 valida DAVVERO: prima usciva su commessa_attivita_id IS NOT NULL, che essendo la colonna NOT NULL valeva per ogni riga sopravvissuta — un presidio che sembrava esserci e non c''era. Brief: brief-db-perimetro-emittente-righe-documento.md §11.13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
