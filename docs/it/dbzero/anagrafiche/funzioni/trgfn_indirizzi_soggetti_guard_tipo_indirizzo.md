# ⚙️ Funzione `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`

```sql
CREATE FUNCTION trgfn_indirizzi_soggetti_guard_tipo_indirizzo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_soggetto_dettaglio_id config.tipi_soggetto_dettaglio.id%TYPE;
  v_has_matrix                 boolean;
  v_today                      date := current_date;
BEGIN
  -- Gestione DELETE: nessun controllo
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  -- Se mancano i riferimenti chiave, non faccio nulla
  IF NEW.soggetto_id IS NULL OR NEW.tipo_indirizzo_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Recupero tipo_soggetto_dettaglio dal soggetto
  SELECT s.tipo_soggetto_dettaglio_id
    INTO v_tipo_soggetto_dettaglio_id
    FROM anagrafiche.soggetti s
   WHERE s.id = NEW.soggetto_id;

  -- Se non ho tipo_soggetto_dettaglio non applico vincoli (fallback permissivo)
  IF v_tipo_soggetto_dettaglio_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Verifico se ESISTE almeno una riga di matrice per questo tipo_soggetto_dettaglio
  SELECT EXISTS (
    SELECT 1
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = v_tipo_soggetto_dettaglio_id
  ) INTO v_has_matrix;

  -- Caso A: nessuna matrice definita → indirizzi liberi
  IF NOT v_has_matrix THEN
    RETURN NEW;
  END IF;

  -- Caso B: matrice definita → accetto solo tipi previsti, attivi e validi
  IF NOT EXISTS (
    SELECT 1
      FROM config.tipi_soggetto_dettaglio_tipi_indirizzo m
     WHERE m.tipo_soggetto_dettaglio_id = v_tipo_soggetto_dettaglio_id
       AND m.tipo_indirizzo_id          = NEW.tipo_indirizzo_id
       AND m.attivo                     = TRUE
       AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
       AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_indirizzi_soggetti_guard_tipo_indirizzo',
      'E_TIPO_INDIRIZZO_NON_PERMESSO',
      jsonb_build_object(
        'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
        'tipo_soggetto_dettaglio_id', v_tipo_soggetto_dettaglio_id,
        'soggetto_id', NEW.soggetto_id
      ),
      NEW.tx_id,
      NEW.tipo_indirizzo_id::text,
      v_tipo_soggetto_dettaglio_id::text,
      NEW.soggetto_id::text
    );
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
