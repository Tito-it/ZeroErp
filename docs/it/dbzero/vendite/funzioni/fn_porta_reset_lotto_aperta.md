{% include-markdown "it/dbzero/vendite/manual/fn_porta_reset_lotto_aperta.md" %}
# ⚙️ Funzione `fn_porta_reset_lotto_aperta`

```sql
CREATE FUNCTION fn_porta_reset_lotto_aperta(p_tabella regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_porta_reset_lotto_aperta(p_tabella regclass)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se la porta del reset del lotto e' aperta per la scrittura
    --   su p_tabella (in un trigger: TG_RELID). Due condizioni in AND (D-V1):
    --   la GUC zeroerp.maintenance_reset_lotto_draft accesa, e chi scrive e'
    --   il proprietario della tabella (script.fn_is_proprietario_tabella).
    --   La GUC la accende solo vendite.fn_cleanup_fatture_by_ids, primitiva
    --   riservata, e la spegne prima di uscire: la porta e' aperta solo
    --   mentre la pulizia lavora, dentro i verbi DEFINER del reset.
    -- ⚠️ INVOKER, ed e' portante: fn_is_proprietario_tabella guarda
    --   current_user, cioe' chi scrive davvero.
    -- ⚠️ La GUC e' un interruttore, non l'id di una riga (D-W a): la porta
    --   la tiene il proprietario dentro una primitiva chiusa.
    SELECT COALESCE(lower(current_setting('zeroerp.maintenance_reset_lotto_draft', true)), '')
               IN ('on', 'true', '1')
           AND script.fn_is_proprietario_tabella(p_tabella)
$function$

COMMENT ON FUNCTION vendite.fn_porta_reset_lotto_aperta(p_tabella regclass)
IS 'La porta del reset del lotto: vera se la GUC zeroerp.maintenance_reset_lotto_draft e'' accesa (on, true, 1) e chi scrive e'' il proprietario della tabella (script.fn_is_proprietario_tabella). La leggono le sette funzioni di trigger che il reset attraversa (attivita fatturabili, commesse, satelliti della fattura, stato del lotto, log). La GUC la accende e la spegne vendite.fn_cleanup_fatture_by_ids, riservata al proprietario: per l''app la porta e'' sempre chiusa. INVOKER: deve vedere chi scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
