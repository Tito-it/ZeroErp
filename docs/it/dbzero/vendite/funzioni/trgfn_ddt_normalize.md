{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_normalize.md" %}
# ⚙️ Funzione `trgfn_ddt_normalize`

```sql
CREATE FUNCTION trgfn_ddt_normalize()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo: normalizzazione DDT su INSERT/UPDATE.
  --   1. anno/data se numero presente (INSERT).
  --   2. eredita billing/utility/valuta/emittente dall'ordine
  --      sorgente (ORDINE_VENDITA, lookup per codice_interno) su
  --      INSERT se non gia' valorizzati.
  --   3. fallback emittente da billing_account (standalone).
  --   2-bis. (rev 2026-10-09) utility e destinatario seguono il BA
  --      quando il chiamante non li dice (INSERT e cambio di BA).
  -- =========================================================

  -- 1. anno/data
  IF TG_OP = 'INSERT' AND (NEW.numero IS NOT NULL AND btrim(NEW.numero) <> '') THEN
    IF NEW.anno IS NULL OR NEW.anno = 0 THEN
      NEW.anno := EXTRACT(YEAR FROM script.fn_data_operativa())::smallint;
    END IF;
    IF NEW.data IS NULL THEN
      NEW.data := script.fn_data_operativa();
    END IF;
  END IF;

  -- 2. eredita billing/utility/valuta/emittente da ordine sorgente
  IF TG_OP = 'INSERT'
     AND NEW.sorgente_tipo_id IS NOT NULL
     AND NEW.sorgente_uid IS NOT NULL
     AND (NEW.billing_account_id IS NULL
          OR NEW.utility_id IS NULL
          OR NEW.valuta_id IS NULL
          OR NEW.emittente_fiscale_id IS NULL)
  THEN
    IF EXISTS (
      SELECT 1 FROM config.sorgenti
      WHERE id = NEW.sorgente_tipo_id AND codice_interno = 'ORDINE_VENDITA'
    ) THEN
      SELECT
        COALESCE(NEW.billing_account_id, o.billing_account_id),
        COALESCE(NEW.utility_id, ba.utility_id),
        COALESCE(NEW.valuta_id, o.valuta_id),
        COALESCE(NEW.emittente_fiscale_id, o.emittente_fiscale_id)
      INTO
        NEW.billing_account_id,
        NEW.utility_id,
        NEW.valuta_id,
        NEW.emittente_fiscale_id
      FROM vendite.ordini o
      LEFT JOIN anagrafiche.billing_account ba
        ON ba.id = o.billing_account_id
      WHERE o.uid = NEW.sorgente_uid
      LIMIT 1;
    END IF;
  END IF;

  -- 2-bis. utility e destinatario seguono il billing account (rev
  --   2026-10-09, brief-db-esecutivi-ba-coppia, D-4 e D-5): col BA sono
  --   COPIE di cio' che il BA dice, e la FK fk_ddt_ba_cliente rifiuta un
  --   valore diverso. Qui si scrivono solo quando il chiamante non le dice:
  --   * su INSERT, se sono NULL (il DDT standalone col BA: prima nasceva
  --     senza utility);
  --   * su UPDATE, se il BA cambia (in bozza: fuori lo blocca
  --     trg_ddt_a05_lock_fuori_bozza_upd) e il chiamante non ha toccato la
  --     colonna. Un BA tolto toglie la utility (CHECK «tutti e due o
  --     nessuno») e lascia il destinatario, che senza BA e' libero.
  IF NEW.billing_account_id IS NOT NULL
     AND (NEW.utility_id IS NULL OR NEW.destinatario_soggetto_ruolo_id IS NULL
          OR (TG_OP = 'UPDATE'
              AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id))
  THEN
    SELECT
      CASE WHEN NEW.utility_id IS NULL
                OR (TG_OP = 'UPDATE'
                    AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id
                    AND NEW.utility_id IS NOT DISTINCT FROM OLD.utility_id)
           THEN ba.utility_id ELSE NEW.utility_id END,
      CASE WHEN NEW.destinatario_soggetto_ruolo_id IS NULL
                OR (TG_OP = 'UPDATE'
                    AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id
                    AND NEW.destinatario_soggetto_ruolo_id IS NOT DISTINCT FROM OLD.destinatario_soggetto_ruolo_id)
           THEN ba.soggetto_ruolo_id ELSE NEW.destinatario_soggetto_ruolo_id END
      INTO NEW.utility_id, NEW.destinatario_soggetto_ruolo_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = NEW.billing_account_id;
  ELSIF TG_OP = 'UPDATE'
        AND NEW.billing_account_id IS NULL
        AND OLD.billing_account_id IS NOT NULL
        AND NEW.utility_id IS NOT DISTINCT FROM OLD.utility_id THEN
    NEW.utility_id := NULL;
  END IF;

  -- 3. fallback standalone: emittente da billing_account (convenzione PK).
  IF TG_OP = 'INSERT'
     AND NEW.emittente_fiscale_id IS NULL
     AND NEW.billing_account_id IS NOT NULL
  THEN
    NEW.emittente_fiscale_id :=
      anagrafiche.fn_get_emittente_fiscale_pk(NEW.billing_account_id);
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_normalize()
IS 'Normalize DDT: anno/data; eredita billing/utility/valuta/emittente da ordine sorgente (ORDINE_VENDITA, per codice_interno) su INSERT; fallback emittente da billing_account (fn_get_emittente_fiscale_pk). rev 2026-07-10 (§15 emittente). rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): punto 2-bis, utility e destinatario sono copie del billing account e li scrive il BA quando il chiamante non li dice — su INSERT se NULL (il DDT standalone col BA nasceva senza utility), su UPDATE se il BA cambia e la colonna non e'' stata toccata; un BA tolto toglie la utility. Un valore esplicito diverso lo rifiuta la FK fk_ddt_ba_cliente.';
```

---
{% include-markdown "signature-core.md" %}
