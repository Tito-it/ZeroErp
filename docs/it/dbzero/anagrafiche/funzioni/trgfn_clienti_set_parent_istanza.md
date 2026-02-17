{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_set_parent_istanza.md" %}
# ⚙️ Funzione `trgfn_clienti_set_parent_istanza`

```sql
CREATE FUNCTION trgfn_clienti_set_parent_istanza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_parent_istanza_id bigint;
    v_is_annullato      boolean;
BEGIN

-- ============================================================
-- Funzione: anagrafiche.trgfn_clienti_set_parent_istanza()
-- Scopo:
--   - per ogni cliente valido, calcola la parent_istanza_id
--     sulla tabella anagrafiche.istanze_utilities
--   - la catena è per PDP (stesso pdp_id)
--   - esclude:
--       * stati cliente con codice_interno = 'AN'
--       * clienti senza data_attivazione
--   - la prima istanza per PDP non ha parent_istanza_id (NULL)
-- ============================================================


    ------------------------------------------------------------------
    -- 0) Se non c'è PDP o non c'è data_attivazione → niente catena
    ------------------------------------------------------------------
    IF NEW.pdp_id IS NULL
       OR NEW.data_attivazione IS NULL
    THEN
        UPDATE anagrafiche.istanze_utilities iu
        SET parent_istanza_id = NULL
        WHERE iu.id = NEW.istanza_utility_id;

        RETURN NEW;
    END IF;

    ------------------------------------------------------------------
    -- 1) Verifica se lo stato_cliente è 'AN' (annullato)
    ------------------------------------------------------------------
    SELECT (sc.codice_interno = 'AN')
    INTO v_is_annullato
    FROM config.stati_cliente sc
    WHERE sc.id = NEW.stato_cliente_id;

    IF COALESCE(v_is_annullato, false) THEN
        -- I clienti annullati sono esclusi dalla catena
        UPDATE anagrafiche.istanze_utilities iu
        SET parent_istanza_id = NULL
        WHERE iu.id = NEW.istanza_utility_id;

        RETURN NEW;
    END IF;

    ------------------------------------------------------------------
    -- 2) Ricerca dell'istanza precedente sullo stesso PDP
    --    Criteri:
    --      - stesso pdp_id
    --      - istanza diversa da quella corrente
    --      - data_attivazione NON NULL
    --      - stato_cliente.codice_interno <> 'AN'
    --      - data_attivazione <= NEW.data_attivazione
    --    Ordinamento:
    --      - data_attivazione desc, id desc → prende la più recente
    ------------------------------------------------------------------
    SELECT c_prev.istanza_utility_id
    INTO v_parent_istanza_id
    FROM anagrafiche.clienti c_prev
    JOIN config.stati_cliente sc_prev
      ON sc_prev.id = c_prev.stato_cliente_id
    WHERE c_prev.pdp_id = NEW.pdp_id
      AND c_prev.istanza_utility_id <> NEW.istanza_utility_id
      AND c_prev.data_attivazione IS NOT NULL
      AND sc_prev.codice_interno <> 'AN'
      AND c_prev.data_attivazione <= NEW.data_attivazione
    ORDER BY c_prev.data_attivazione DESC,
             c_prev.id DESC
    LIMIT 1;

    ------------------------------------------------------------------
    -- 3) Aggiorna parent_istanza_id sull'istanza corrente
    --    - se non trova nulla → prima istanza per quel PDP → NULL
    --    - altrimenti collega alla precedente
    ------------------------------------------------------------------
    UPDATE anagrafiche.istanze_utilities iu
    SET parent_istanza_id = v_parent_istanza_id
    WHERE iu.id = NEW.istanza_utility_id;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()
IS 'Calcola e imposta parent_istanza_id per anagrafiche.istanze_utilities
      in base alla catena di clienti per lo stesso PDP,
      escludendo clienti annullati (stato_cliente.codice_interno = ''AN'')
      e clienti senza data_attivazione.';
```

---
{% include-markdown "signature-core.md" %}
