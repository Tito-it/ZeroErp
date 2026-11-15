{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_set_categoria_cliente_snapshot.md" %}
# ⚙️ Funzione `trgfn_contratti_set_categoria_cliente_snapshot`

```sql
CREATE FUNCTION trgfn_contratti_set_categoria_cliente_snapshot()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: alla nascita del contratto, la categoria del cliente dal
--   billing account, se chi crea non la passa.
-- ⛔ Il congelamento fuori bozza NON sta qui: lo fa il lock della
--   testata (trg_contratti_a05_lock_fuori_bozza_upd,
--   E_DOC_CONDIZIONI_FUORI_BOZZA). Il ramo UPDATE che lo ripeteva
--   (E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE) e' ritirato il
--   2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro
--   6c-bis): non parlava mai, il lock arriva prima.
DECLARE
    v_categoria_id anagrafiche.billing_account.categoria_cliente_id%TYPE;
BEGIN
    IF NEW.categoria_cliente_id_snapshot IS NULL THEN
        SELECT ba.categoria_cliente_id
          INTO v_categoria_id
          FROM anagrafiche.billing_account ba
         WHERE ba.id = NEW.billing_account_id;

        NEW.categoria_cliente_id_snapshot := v_categoria_id;
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()
IS 'Trigger BEFORE INSERT su vendite.contratti: categoria_cliente_id_snapshot dal billing account, se chi crea non la passa. Il congelamento fuori bozza lo fa il lock della testata (trg_contratti_a05_lock_fuori_bozza_upd, E_DOC_CONDIZIONI_FUORI_BOZZA): in bozza la categoria si cambia, per esempio per una riclassificazione del billing account mentre il contratto si prepara.';
```

</div>

---
{% include-markdown "signature-core.md" %}
