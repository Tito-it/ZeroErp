{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_ruoli_guard_indirizzi_required.md" %}
# ⚙️ Funzione `trgfn_soggetti_ruoli_guard_indirizzi_required`

```sql
CREATE FUNCTION trgfn_soggetti_ruoli_guard_indirizzi_required()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_matrix boolean;
  v_today      date := script.fn_data_operativa();
  v_missing    record;
  v_ruolo_nome config.tipi_ruoli.descrizione%TYPE;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  IF NEW.tipo_ruolo_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Se non esiste alcuna riga matrice per quel ruolo -> libero
  SELECT EXISTS (
    SELECT 1
      FROM config.tipi_ruolo_tipi_indirizzo m
     WHERE m.tipo_ruolo_id = NEW.tipo_ruolo_id
  ) INTO v_has_matrix;

  IF NOT v_has_matrix THEN
    RETURN NEW;
  END IF;

  -- Cerca un obbligatorio mancante (considerando fallback)
  SELECT m.tipo_indirizzo_id,
         m.fallback_tipo_indirizzo_id
    INTO v_missing
    FROM config.tipi_ruolo_tipi_indirizzo m
   WHERE m.tipo_ruolo_id = NEW.tipo_ruolo_id
     AND m.obbligatorio = TRUE
     AND m.attivo = TRUE
     AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
     AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
     AND NOT EXISTS (
       SELECT 1
         FROM anagrafiche.indirizzi i
        WHERE i.soggetto_ruolo_id = NEW.id
          AND (
            i.tipo_indirizzo_id = m.tipo_indirizzo_id
            OR (m.fallback_tipo_indirizzo_id IS NOT NULL AND i.tipo_indirizzo_id = m.fallback_tipo_indirizzo_id)
          )
     )
   LIMIT 1;

  IF FOUND THEN
    SELECT tr.descrizione INTO v_ruolo_nome
      FROM config.tipi_ruoli tr
     WHERE tr.id = NEW.tipo_ruolo_id;

    -- Valori per descrizione, nell'ordine della frase: il
    -- ruolo, poi il tipo richiesto col suo ripiego. Gli id
    -- stanno nel contesto.
    PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_soggetti_ruoli_guard_indirizzi_required',
      'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
      jsonb_build_object(
        'soggetto_ruolo_id', NEW.id,
        'tipo_ruolo_id', NEW.tipo_ruolo_id,
        'tipo_indirizzo_id_required', v_missing.tipo_indirizzo_id,
        'fallback_tipo_indirizzo_id', v_missing.fallback_tipo_indirizzo_id
      ),
      NEW.tx_id,
      COALESCE(v_ruolo_nome, NEW.tipo_ruolo_id::text),
      COALESCE(anagrafiche.fn_nomi_tipo_indirizzo_richiesto(
                   v_missing.tipo_indirizzo_id,
                   v_missing.fallback_tipo_indirizzo_id),
               v_missing.tipo_indirizzo_id::text)
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()
IS 'Constraint trigger DEFERRABLE su anagrafiche.soggetti_ruoli: il ruolo deve avere, fra i suoi indirizzi (anagrafiche.indirizzi), ogni tipo che config.tipi_ruolo_tipi_indirizzo dichiara obbligatorio per il suo tipo di ruolo, attivo e valido il giorno di script.fn_data_operativa(), oppure il ripiego della riga (fallback_tipo_indirizzo_id). Tipo di ruolo NULL o senza nessuna riga di matrice: libero. Al primo obbligatorio mancante E_INDIRIZZO_OBBLIGATORIO_MANCANTE, coi valori della frase nell''ordine tipo di ruolo e tipo richiesto col ripiego, per descrizione (anagrafiche.fn_nomi_tipo_indirizzo_richiesto); gli id nel contesto. Il requisito non guarda la natura del soggetto. ⛔ Da NON confondere con anagrafiche.trgfn_soggetti_guard_indirizzi_required, il gemello del layer SOGGETTO, che legge la matrice della natura e ha un codice suo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
