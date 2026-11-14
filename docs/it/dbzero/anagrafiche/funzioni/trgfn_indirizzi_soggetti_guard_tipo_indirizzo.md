{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_soggetti_guard_tipo_indirizzo.md" %}
# ⚙️ Funzione `trgfn_indirizzi_soggetti_guard_tipo_indirizzo`

```sql
CREATE FUNCTION trgfn_indirizzi_soggetti_guard_tipo_indirizzo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_tipo_soggetto_dettaglio_id config.tipi_soggetto_dettaglio.id%TYPE;
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

  -- Il predicato e' quello che legge anche la regola del cambio di natura:
  -- natura NULL o senza matrice = indirizzi liberi; altrimenti la coppia
  -- deve essere in matrice, attiva e valida oggi.
  IF NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(
             v_tipo_soggetto_dettaglio_id, NEW.tipo_indirizzo_id,
             script.fn_data_operativa()) THEN
    -- Codice PROPRIO di questo layer, distinto da quello del guard sui
    -- RUOLI (trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo), che legge
    -- un'altra matrice: un messaggio plausibile e falso manda a cercare
    -- dove il problema non c'e'.
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_indirizzi_soggetti_guard_tipo_indirizzo',
      'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO',
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

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo()
IS 'Guard sugli indirizzi di SOGGETTO, quando si scrive un indirizzo: il tipo di indirizzo deve essere ammesso dalla natura di dettaglio del soggetto, col predicato di anagrafiche.fn_tipo_indirizzo_ammesso_per_natura (giorno: script.fn_data_operativa()); altrimenti E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO. Fallback permissivo quando il soggetto non ha una natura o quando per quella natura non esiste nessuna riga di matrice. Gli indirizzi gia'' scritti, al cambio di natura, li giudica anagrafiche.fn_check_cambio_natura_soggetto con lo stesso predicato. ⛔ Da NON confondere con anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo, che e'' il guard del layer RUOLO e legge un''altra matrice, con un codice d''errore suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
