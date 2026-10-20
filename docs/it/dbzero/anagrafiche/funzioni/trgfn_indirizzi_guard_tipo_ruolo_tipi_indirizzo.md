{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo.md" %}
# ⚙️ Funzione `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo`

```sql
CREATE FUNCTION trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
v_tipo_ruolo_id  anagrafiche.soggetti_ruoli.tipo_ruolo_id%TYPE;
v_has_matrix     boolean;
v_today          date := script.fn_data_operativa();
BEGIN
-- Gestione DELETE: nessun controllo
IF TG_OP = 'DELETE' THEN
        RETURN OLD;
END IF;

-- Se mancano i riferimenti chiave, non faccio nulla
IF NEW.soggetto_ruolo_id IS NULL
OR NEW.tipo_indirizzo_id IS NULL THEN
        RETURN NEW;
END IF;

-- Recupero tipo_ruolo dal soggetto_ruolo
SELECT sr.tipo_ruolo_id
INTO v_tipo_ruolo_id
FROM anagrafiche.soggetti_ruoli sr
WHERE sr.id = NEW.soggetto_ruolo_id;


-- Verifico se ESISTE almeno una riga di matrice per questo tipo_ruolo
SELECT EXISTS (
        SELECT 1
        FROM config.tipi_ruolo_tipi_indirizzo m
        WHERE m.tipo_ruolo_id = v_tipo_ruolo_id
) INTO v_has_matrix;

-- Caso A: nessuna matrice definita → indirizzi liberi
IF NOT v_has_matrix THEN
        RETURN NEW;
END IF;

-- Caso B: matrice definita → accetto solo tipi previsti, attivi e validi
IF NOT EXISTS (
        SELECT 1
        FROM config.tipi_ruolo_tipi_indirizzo m
        WHERE m.tipo_ruolo_id      = v_tipo_ruolo_id
        AND m.tipo_indirizzo_id  = NEW.tipo_indirizzo_id
        AND m.attivo             = TRUE
        AND (m.valido_dal IS NULL OR m.valido_dal <= v_today)
        AND (m.valido_al  IS NULL OR m.valido_al  >= v_today)
) THEN
        -- In alternativa qui puoi integrare dbops.fn_log_and_raise_error(...)
        PERFORM script.fn_log_and_raise_error(
     'database',
     'trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo',
     'E_TIPO_INDIRIZZO_NON_PERMESSO',
     jsonb_build_object(
            'campo',             'tipo_indirizzo_id',
            'tipo_indirizzo_id', NEW.tipo_indirizzo_id,
            'tipo_ruolo_id',     v_tipo_ruolo_id,
            'soggetto_ruolo_id', NEW.soggetto_ruolo_id), 
      new.tx_id,
     NEW.tipo_indirizzo_id::text ,         
       v_tipo_ruolo_id::text, NEW.soggetto_ruolo_id::text);         

END IF;

RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()
IS 'Trigger function per validare coerenza tra anagrafiche.indirizzi e config.tipi_ruolo_tipi_indirizzo.
Verifica che il tipo_indirizzo sia ammesso per il tipo_ruolo del soggetto_ruolo associato.
Se non esiste alcuna riga di matrice per il tipo_ruolo, tutti i tipi sono ammessi.
Altrimenti, solo i tipi attivi e validi sono permessi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
