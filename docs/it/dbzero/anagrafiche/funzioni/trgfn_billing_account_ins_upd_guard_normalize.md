{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_ins_upd_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_billing_account_ins_upd_guard_normalize`

```sql
CREATE FUNCTION trgfn_billing_account_ins_upd_guard_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_ins_upd_guard_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
    DECLARE
      v_cf_child  text;
      v_cf_parent text;
    BEGIN
      ------------------------------------------------------------------
      -- 1) NORMALIZE (pulizie/derive)
      ------------------------------------------------------------------
      -- Generazione codice se assente
      IF NEW.codice IS NULL OR btrim(NEW.codice) = '' THEN
        NEW.codice := script.fn_generate_codice('billing_account');
      ELSE
        NEW.codice := btrim(NEW.codice);
      END IF;

      -- (Esempi di altre normalizzazioni eventuali)
      -- NEW.note := nullif(btrim(NEW.note), '');

      ------------------------------------------------------------------
      -- 2) GUARD (validazioni di business con errori)
      ------------------------------------------------------------------
      -- 2.0) Parent: vieta self-reference
      IF NEW.parent_account_id IS NOT NULL AND NEW.parent_account_id = NEW.id THEN
        PERFORM script.fn_log_and_raise_error(
          'database', TG_NAME, 'E_PARENT_SELF',
          jsonb_build_object('codice', NEW.codice, 'parent_account_id', NEW.parent_account_id),
          NULL::uuid, NEW.parent_account_id::text
        );
      END IF;

      -- 2.1) Se c'è parent, valid_from è obbligatorio
      IF NEW.parent_account_id IS NOT NULL AND NEW.valid_from IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
          'database', TG_NAME, 'E_VALORE_MANCANTE',
          jsonb_build_object('codice', NEW.codice, 'column', 'valid_from'),
          NULL::uuid, 'valid_from'
        );
      END IF;

      -- 2.2) Coerenza CF parent/child quando c'è parent
      IF NEW.parent_account_id IS NOT NULL THEN
        SELECT s.id_fiscale_univoco_cf_piva
          INTO v_cf_child
          FROM anagrafiche.istanze_utilities iu
          JOIN anagrafiche.soggetti s ON s.id = iu.soggetto_id
        WHERE iu.id = NEW.istanza_utility_id;

        SELECT s2.id_fiscale_univoco_cf_piva
          INTO v_cf_parent
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.istanze_utilities iu2 ON iu2.id = ba.istanza_utility_id
          JOIN anagrafiche.soggetti s2 ON s2.id = iu2.soggetto_id
        WHERE ba.id = NEW.parent_account_id;

        IF v_cf_child IS DISTINCT FROM v_cf_parent THEN
          PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_ID_FISCALI_DIVERSI',
            jsonb_build_object(
              'codice', NEW.codice,
              'parent_account_id', NEW.parent_account_id,
              'id_fiscale_univoco_cf_piva', v_cf_child,
              'parent_id_fiscale_univoco_cf_piva', v_cf_parent
            ),
            NULL::uuid,
            NEW.parent_account_id::text, v_cf_child, v_cf_parent
          );
        END IF;
      END IF;

      -- 2.3) Coerenza date validità
      IF NEW.valid_to IS NOT NULL THEN
        IF NEW.valid_from IS NULL THEN
          PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_VALORE_MANCANTE',
            jsonb_build_object('codice', NEW.codice, 'column', 'valid_to_requires_valid_from'),
            NULL::uuid, 'valid_to'
          );
        ELSIF NEW.valid_to <= NEW.valid_from THEN
          PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_DATA_FINE_NON_MAGGIORE_DI_INIZIO',
            jsonb_build_object('valid_from', NEW.valid_from, 'valid_to', NEW.valid_to),
            NULL::uuid, NEW.valid_to::text, NEW.valid_from::text
          );
        END IF;
      END IF;

      
      RETURN NEW;
    END;
    $function$
```

---
{% include-markdown "signature-core.md" %}
