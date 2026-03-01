{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_normalize.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_normalize`

```sql
CREATE FUNCTION trgfn_billing_account_guard_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()
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
  -- (Riservato per future normalizzazioni)

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

  -- 2.1) Se c'e parent, valido_dal e' obbligatorio
  IF NEW.parent_account_id IS NOT NULL AND NEW.valido_dal IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', TG_NAME, 'E_VALORE_MANCANTE',
      jsonb_build_object('codice', NEW.codice, 'column', 'valido_dal'),
      NULL::uuid, 'valido_dal'
    );
  END IF;

  -- 2.2) Coerenza CF parent/child quando c'e parent
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

  -- 2.3) Coerenza date validita
  IF NEW.valido_al IS NOT NULL THEN
    IF NEW.valido_dal IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_VALORE_MANCANTE',
        jsonb_build_object('codice', NEW.codice, 'column', 'valido_al_requires_valido_dal'),
        NULL::uuid, 'valido_al'
      );
    ELSIF NEW.valido_al < NEW.valido_dal THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_DATA_FINE_NON_MAGGIORE_DI_INIZIO',
        jsonb_build_object('valido_dal', NEW.valido_dal, 'valido_al', NEW.valido_al),
        NULL::uuid, NEW.valido_al::text, NEW.valido_dal::text
      );
    END IF;
  END IF;

  -- 2.4) Guard dissociazione parent: blocca la rimozione di parent_account_id
  --      quando esistono attivita_fatturabili non ancora fatturate sul BA figlio.
  --      Questo previene la corruzione della catena di fatturazione:
  --        fatture.billing_account_id (padre) → fatture_righe.dest_billing_account_id (figlio)
  IF TG_OP = 'UPDATE'
     AND OLD.parent_account_id IS NOT NULL
     AND NEW.parent_account_id IS NULL
  THEN
    IF EXISTS (
      SELECT 1
        FROM vendite.attivita_fatturabili af
       WHERE af.billing_account_id = NEW.id
         AND af.fatturato IS FALSE
    ) THEN
      PERFORM script.fn_log_and_raise_error(
        'database', TG_NAME, 'E_DISSOCIAZIONE_PARENT_CON_ATTIVITA',
        jsonb_build_object(
          'billing_account_id', NEW.id,
          'codice', NEW.codice,
          'ex_parent_account_id', OLD.parent_account_id,
          'detail', 'Impossibile rimuovere parent_account_id: esistono attivita non fatturate collegate a questo billing account'
        ),
        NULL::uuid,
        NEW.id::text, OLD.parent_account_id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_normalize()
IS 'Guard/normalize: valida parent e date; normalizza codice se presente.
Include guard dissociazione parent: blocca la rimozione di parent_account_id
quando esistono attivita_fatturabili non fatturate sul BA figlio.';
```

---
{% include-markdown "signature-core.md" %}
