{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_set_parent_istanza.md" %}
# ⚙️ Funzione `trgfn_clienti_set_parent_istanza`

```sql
CREATE FUNCTION trgfn_clienti_set_parent_istanza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_parent_istanza_id anagrafiche.istanze_utilities.parent_istanza_id%TYPE;
    v_is_annullato      boolean;
    v_fittizia          anagrafiche.istanze_utilities.fittizia%TYPE;
BEGIN
-- ============================================================
-- Scopo: la catena delle istanze, cioe' parent_istanza_id
--   sull'istanza del cliente.
--   * con PDP: il predecessore e' il cliente precedente sullo
--     stesso PDP;
--   * senza PDP, su un'istanza fittizia (rev 2026-10-14, C-9 di
--     brief-db-cliente-manuale-uno-per-soggetto-e-utility): il
--     predecessore e' l'ultimo cliente con la stessa chiave
--     soggetto + utility + azienda;
--   * senza PDP su un'istanza vera: non si tocca niente.
--   Esclusi: clienti AN e clienti senza data_attivazione.
-- ============================================================

    -- 0) Senza data_attivazione -> niente catena.
    IF NEW.data_attivazione IS NULL THEN
        UPDATE anagrafiche.istanze_utilities iu
           SET parent_istanza_id = NULL
         WHERE iu.id = NEW.istanza_utility_id;
        RETURN NEW;
    END IF;

    -- 1) Annullato -> fuori dalla catena.
    SELECT (sc.codice_interno = 'AN')
      INTO v_is_annullato
      FROM config.stati_cliente sc
     WHERE sc.id = NEW.stato_cliente_id;

    IF COALESCE(v_is_annullato, false) THEN
        UPDATE anagrafiche.istanze_utilities iu
           SET parent_istanza_id = NULL
         WHERE iu.id = NEW.istanza_utility_id;
        RETURN NEW;
    END IF;

    -- 2) Senza PDP: la catena delle fittizie (C-9).
    IF NEW.pdp_id IS NULL THEN
        SELECT iu.fittizia
          INTO v_fittizia
          FROM anagrafiche.istanze_utilities iu
         WHERE iu.id = NEW.istanza_utility_id;

        -- Istanza vera senza PDP: la catena non ha un perno.
        IF NOT COALESCE(v_fittizia, false) THEN
            RETURN NEW;
        END IF;

        -- Ruolo e utility li ha gia' scritti dal BA
        -- trgfn_clienti_sync_utility_from_ba (BEFORE, viene
        -- prima per nome). L'azienda per l'installazione.
        SELECT k.istanza_utility_id
          INTO v_parent_istanza_id
          FROM anagrafiche.fn_clienti_stessa_chiave(
                   NEW.soggetto_ruolo_id,
                   NEW.utility_id,
                   script.fn_get_ba_emittente_sr_id_installazione(NEW.billing_account_id)) k
         WHERE k.istanza_utility_id <> NEW.istanza_utility_id
           AND k.data_attivazione <= NEW.data_attivazione
         ORDER BY k.data_attivazione DESC, k.cliente_id DESC
         LIMIT 1;

        UPDATE anagrafiche.istanze_utilities iu
           SET parent_istanza_id = v_parent_istanza_id
         WHERE iu.id = NEW.istanza_utility_id
           AND iu.parent_istanza_id IS DISTINCT FROM v_parent_istanza_id;

        RETURN NEW;
    END IF;

    -- 3) Con PDP: il cliente precedente sullo stesso PDP
    --    (data_attivazione <= la mia, la piu' recente).
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

    -- Nessun precedente: prima istanza del PDP -> NULL.
    UPDATE anagrafiche.istanze_utilities iu
       SET parent_istanza_id = v_parent_istanza_id
     WHERE iu.id = NEW.istanza_utility_id;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_set_parent_istanza()
IS 'Calcola parent_istanza_id dell''istanza del cliente (la catena). Con PDP: il cliente precedente sullo stesso PDP. Senza PDP su un''istanza fittizia (rev 2026-10-14, C-9): l''ultimo cliente con la stessa chiave soggetto + utility + azienda, da anagrafiche.fn_clienti_stessa_chiave. Senza PDP su un''istanza vera: nessun cambio. Esclusi i clienti AN e quelli senza data_attivazione. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility; per il ramo PDP: brief-db-catena-istanze-pdp.';
```

</div>

---
{% include-markdown "signature-core.md" %}
