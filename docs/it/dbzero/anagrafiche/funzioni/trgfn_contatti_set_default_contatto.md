{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_contatti_set_default_contatto.md" %}
# ⚙️ Funzione `trgfn_contatti_set_default_contatto`

```sql
CREATE FUNCTION trgfn_contatti_set_default_contatto()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_entra   boolean;
    v_chiesto boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il predefinito della riga di contesto (soggetto, ruolo,
    --   istanza): il primo contatto che entra nel contesto, o
    --   quello che lo chiede.
    --
    -- Regole:
    --   - entra nel contesto chi nasce o cambia soggetto, ruolo
    --     o istanza;
    --   - chiede il segno chi lo passa a true (all'INSERT, o da
    --     false a true); un segno portato da un altro contesto
    --     non e' una richiesta;
    --   1. chi chiede il segno lo toglie agli altri del contesto;
    --   2. chi entra senza chiederlo e' predefinito se il
    --      contesto non ne ha uno;
    --   3. default_context = il livello del predefinito, NULL
    --      sugli altri;
    --   4. il predefinito del soggetto e' anche
    --      soggetti.default_contatto_id.
    --   Il segno tolto lo giudica trgfn_contatti_guard_predefinito.
    -- =========================================================
    v_entra := TG_OP = 'INSERT'
            OR (OLD.soggetto_id, OLD.soggetto_ruolo_id, OLD.istanza_utility_id)
               IS DISTINCT FROM
               (NEW.soggetto_id, NEW.soggetto_ruolo_id, NEW.istanza_utility_id);
    v_chiesto := NEW.is_default AND (TG_OP = 'INSERT' OR NOT OLD.is_default);

    IF v_chiesto THEN
        -- 1) Il segno passa a questa riga.
        UPDATE anagrafiche.contatti c
           SET is_default = false
         WHERE c.soggetto_id = NEW.soggetto_id
           AND c.soggetto_ruolo_id  IS NOT DISTINCT FROM NEW.soggetto_ruolo_id
           AND c.istanza_utility_id IS NOT DISTINCT FROM NEW.istanza_utility_id
           AND c.is_default
           AND c.id <> NEW.id;
    ELSIF v_entra THEN
        -- 2) Chi entra senza chiederlo: predefinito se il contesto non ne ha.
        NEW.is_default := NOT EXISTS (
            SELECT 1
              FROM anagrafiche.contatti c
             WHERE c.soggetto_id = NEW.soggetto_id
               AND c.soggetto_ruolo_id  IS NOT DISTINCT FROM NEW.soggetto_ruolo_id
               AND c.istanza_utility_id IS NOT DISTINCT FROM NEW.istanza_utility_id
               AND c.is_default
               AND c.id <> NEW.id);
    END IF;

    -- 3) L'etichetta del livello.
    NEW.default_context := CASE
        WHEN NOT NEW.is_default               THEN NULL
        WHEN NEW.istanza_utility_id IS NOT NULL THEN 'istanza'
        WHEN NEW.soggetto_ruolo_id  IS NOT NULL THEN 'ruolo'
        ELSE 'soggetto'
    END;

    -- 4) Il predefinito del soggetto, quando lo diventa.
    IF NEW.is_default
       AND NEW.soggetto_ruolo_id IS NULL
       AND NEW.istanza_utility_id IS NULL
       AND (v_entra OR NOT OLD.is_default)
    THEN
        UPDATE anagrafiche.soggetti s
           SET default_contatto_id = NEW.id
         WHERE s.id = NEW.soggetto_id
           AND s.default_contatto_id IS DISTINCT FROM NEW.id;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_contatti_set_default_contatto()
IS 'Trigger BEFORE INSERT OR UPDATE su anagrafiche.contatti (fase a20): il predefinito della riga di contesto (soggetto, ruolo, istanza). Chi chiede il segno (is_default a true all''INSERT, o da false a true) lo toglie agli altri del contesto; chi entra nel contesto (nasce, o cambia soggetto, ruolo o istanza) senza chiederlo e'' predefinito se il contesto non ne ha uno. Un segno portato da un altro contesto non e'' una richiesta. default_context e'' il livello del predefinito (soggetto|ruolo|istanza), NULL sugli altri. Il predefinito del soggetto e'' anche soggetti.default_contatto_id, scritto quando lo diventa. Il segno tolto e il predefinito cancellato li giudica anagrafiche.trgfn_contatti_guard_predefinito; l''unicita'' la scrive l''indice uq_contatti_predefinito_contesto. La regola sta nella nota _contatto-predefinito.';
```

</div>

---
{% include-markdown "signature-core.md" %}
