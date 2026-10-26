# ⚙️ Funzione `trgfn_efba_guard_clienti_chiave`

```sql
CREATE FUNCTION trgfn_efba_guard_clienti_chiave()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_clienti_chiave()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_id anagrafiche.emittenti_fiscali_billing_account.billing_account_id%TYPE;
BEGIN
  -- Un collegamento spostato da un BA a un altro: i clienti
  -- di entrambi; se uno dei due lati e' la riga di default,
  -- anche il raggio N.
  IF TG_OP = 'UPDATE'
     AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
      PERFORM anagrafiche.fn_guard_clienti_chiave_unica_di(OLD.billing_account_id, NULL);
      PERFORM anagrafiche.fn_guard_clienti_chiave_unica_di(NEW.billing_account_id, NULL);
      IF OLD.billing_account_id IS NULL OR NEW.billing_account_id IS NULL THEN
          PERFORM anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale();
      END IF;
      RETURN NULL;
  END IF;

  IF TG_OP = 'DELETE' THEN
      v_ba_id := OLD.billing_account_id;
  ELSE
      v_ba_id := NEW.billing_account_id;
  END IF;

  IF v_ba_id IS NOT NULL THEN
      -- Movimenti 1-3: collegamento di un BA creato, cambiato
      -- o tolto.
      PERFORM anagrafiche.fn_guard_clienti_chiave_unica_di(v_ba_id, NULL);
      RETURN NULL;
  END IF;

  -- Movimento 4: la riga senza BA e' l'azienda predefinita.
  PERFORM anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale();
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_clienti_chiave()
IS 'Constraint trigger function (AFTER INSERT OR UPDATE OR DELETE DEFERRABLE INITIALLY DEFERRED su anagrafiche.emittenti_fiscali_billing_account): l''azienda di un BA e'' nella chiave del cliente manuale. Per un collegamento creato, cambiato o tolto controlla i clienti del BA (anagrafiche.fn_guard_clienti_chiave_unica_di); per la riga di default il raggio N (anagrafiche.fn_guard_clienti_chiave_unica_gestore_globale). E_CLIENTE_STESSA_CHIAVE. Tassonomia di anagrafiche.trgfn_efba_guard_istanza_emittente. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
