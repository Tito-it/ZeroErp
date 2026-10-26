{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_guard_onere_natura.md" %}
# ⚙️ Funzione `trgfn_articoli_guard_onere_natura`

```sql
CREATE FUNCTION trgfn_articoli_guard_onere_natura()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_guard_onere_natura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_destinazione  config.nature_vendita.destinazione_tipo%TYPE;
    v_natura        config.nature_vendita.descrizione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un articolo-onere (causale_onere_id valorizzato) non e'
    --   merce: la sua natura non ha destinazione ORDINE_VENDITA.
    --   BEFORE INSERT OR UPDATE OF natura_vendita_id, causale_onere_id
    --   su catalogo.articoli. Un UPDATE che non cambia nessuna
    --   delle due colonne non si rigiudica.
    -- rev 2026-10-19 (20261019-98, brief-db-grammatica-unica-
    --   documenti lotto 2b): la destinazione e' il codice della
    --   sorgente, ORDINE_VENDITA (era ORDINE).
    -- =========================================================
    IF NEW.causale_onere_id IS NULL THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'UPDATE'
       AND NEW.natura_vendita_id IS NOT DISTINCT FROM OLD.natura_vendita_id
       AND NEW.causale_onere_id  IS NOT DISTINCT FROM OLD.causale_onere_id THEN
        RETURN NEW;
    END IF;

    SELECT nv.destinazione_tipo, COALESCE(nv.descrizione, nv.codice)
      INTO v_destinazione, v_natura
      FROM config.nature_vendita nv
     WHERE nv.id = NEW.natura_vendita_id;

    -- Natura assente: parla la FK.
    IF v_destinazione = 'ORDINE_VENDITA' THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', TG_NAME::text, 'E_ARTICOLO_ONERE_NATURA_MERCE',
            jsonb_build_object(
                'campo',             'natura_vendita_id',
                'articolo_id',       NEW.id,
                'causale_onere_id',  NEW.causale_onere_id,
                'natura_vendita_id', NEW.natura_vendita_id,
                'destinazione_tipo', v_destinazione),
            NEW.tx_id,
            NEW.codice,
            v_natura);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_guard_onere_natura()
IS 'Guard BEFORE INSERT OR UPDATE OF natura_vendita_id, causale_onere_id su catalogo.articoli: un articolo-onere (causale_onere_id valorizzato) non e'' merce, la sua natura non ha destinazione_tipo ORDINE (E_ARTICOLO_ONERE_NATURA_MERCE, campo natura_vendita_id). Senza, un onere creato senza dire la natura prendeva il DEFAULT (MERCE): un addebito trattato come bene da evadere in ordine e in bolla, e come cessione di beni. La regola legge la destinazione dal vocabolario (config.nature_vendita), come le viste di smistamento: segue la natura se cambia destinazione. Un UPDATE che non cambia le due colonne non rigiudica. Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-9). ⭐ rev 2026-10-19 (20261019-98, brief-db-grammatica-unica-documenti lotto 2b): la destinazione della merce e'' ORDINE_VENDITA, il codice della sorgente (era ORDINE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
