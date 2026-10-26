{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_righe_componenti_guard_pending.md" %}
# ⚙️ Funzione `trgfn_ddt_righe_componenti_guard_pending`

```sql
CREATE FUNCTION trgfn_ddt_righe_componenti_guard_pending()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_righe_componenti_guard_pending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Scopo:
    --   Quando un componente BoM CASO A ha stato_approvazione_prezzo =
    --   'PENDING' (richiesta L3 out-of-policy in attesa di esito),
    --   bloccare modifiche ai campi struttura.
    --
    -- Allowlist modificabile in PENDING:
    --   stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
    --   meta, data_update, user_update (audit automatico).
    --
    -- Denylist (tutti gli altri campi struttura):
    --   riga_ddt_id, articolo_componente_id, componente_id,
    --   coeff_qta_snapshot, quantita, uom_operativa_id,
    --   factor_to_base, qta_operativa, prezzo_unitario, iva_id,
    --   origine_prezzo, ordine, attivo.

    IF OLD.stato_approvazione_prezzo IS DISTINCT FROM
       'PENDING'::config.stato_approvazione_prezzo
    THEN
        RETURN NEW;
    END IF;

    IF NEW.riga_ddt_id                IS DISTINCT FROM OLD.riga_ddt_id
    OR NEW.articolo_componente_id     IS DISTINCT FROM OLD.articolo_componente_id
    OR NEW.componente_id              IS DISTINCT FROM OLD.componente_id
    OR NEW.coeff_qta_snapshot         IS DISTINCT FROM OLD.coeff_qta_snapshot
    OR NEW.quantita                   IS DISTINCT FROM OLD.quantita
    OR NEW.uom_operativa_id           IS DISTINCT FROM OLD.uom_operativa_id
    OR NEW.factor_to_base             IS DISTINCT FROM OLD.factor_to_base
    OR NEW.qta_operativa              IS DISTINCT FROM OLD.qta_operativa
    OR NEW.prezzo_unitario            IS DISTINCT FROM OLD.prezzo_unitario
    OR NEW.iva_id                     IS DISTINCT FROM OLD.iva_id
    OR NEW.origine_prezzo             IS DISTINCT FROM OLD.origine_prezzo
    OR NEW.ordine                     IS DISTINCT FROM OLD.ordine
    OR NEW.attivo                     IS DISTINCT FROM OLD.attivo
    THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_COMPONENTE_PREZZO_PENDENTE',
            jsonb_build_object(
                'componente_id', OLD.id,
                'riga_ddt_id',   OLD.riga_ddt_id,
                'hint', 'Attendi esito approvazione (APPROVED/REJECTED) '
                     || 'prima di modificare il componente.'
            ),
            NULL::uuid,
            OLD.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_righe_componenti_guard_pending()
IS 'BEFORE UPDATE guard L3 su ddt_righe_componenti: blocca modifiche ai campi struttura quando stato_approvazione_prezzo=PENDING. Pattern simmetrico a trgfn_preventivi_righe_componenti_guard_pending. Raise E_COMPONENTE_PREZZO_PENDENTE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
