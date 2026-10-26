{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_indirizzi_required.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_indirizzi_required`

```sql
CREATE FUNCTION trgfn_soggetti_guard_indirizzi_required()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_matrix boolean;
  v_today      date := script.fn_data_operativa();
  v_missing    record;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  -- se non ho il tipo, non applico vincoli (fallback permissivo)
  IF NEW.tipo_soggetto_dettaglio_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Se non esiste alcuna riga matrice per quel tipo -> libero
  SELECT EXISTS (
    SELECT 1
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = NEW.tipo_soggetto_dettaglio_id
  ) INTO v_has_matrix;

  IF NOT v_has_matrix THEN
    RETURN NEW;
  END IF;

  -- Cerca un obbligatorio mancante (considerando fallback)
  SELECT m.tipo_indirizzo_id,
         m.fallback_tipo_indirizzo_id
    INTO v_missing
    FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
   WHERE m.tipo_soggetto_dettaglio_id = NEW.tipo_soggetto_dettaglio_id
     AND m.obbligatorio = TRUE
     AND m.attivo = TRUE
     AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
     AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
     AND NOT EXISTS (
       SELECT 1
         FROM anagrafiche.indirizzi_soggetti i
        WHERE i.soggetto_id = NEW.id
          AND (
            i.tipo_indirizzo_id = m.tipo_indirizzo_id
            OR (m.fallback_tipo_indirizzo_id IS NOT NULL AND i.tipo_indirizzo_id = m.fallback_tipo_indirizzo_id)
          )
     )
   LIMIT 1;

  IF FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_soggetti_guard_indirizzi_required',
      'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
      jsonb_build_object(
        'soggetto_id', NEW.id,
        'tipo_soggetto_dettaglio_id', NEW.tipo_soggetto_dettaglio_id,
        'tipo_indirizzo_id_required', v_missing.tipo_indirizzo_id,
        'fallback_tipo_indirizzo_id', v_missing.fallback_tipo_indirizzo_id
      ),
      NEW.tx_id,
      NEW.id::text,
       ' tipo soggetto dettaglio ',  NEW.tipo_soggetto_dettaglio_id::text,
      v_missing.tipo_indirizzo_id::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()
IS 'Constraint trigger DEFERRABLE: per soggetti verifica presenza indirizzi obbligatori da config.tipi_soggetto_dettaglio_tipi_indirizzo. Se matrice assente -> libero.';
```

</div>

---
{% include-markdown "signature-core.md" %}
