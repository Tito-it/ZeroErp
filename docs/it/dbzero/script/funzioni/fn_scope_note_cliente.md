# ⚙️ Funzione `fn_scope_note_cliente`

```sql
CREATE FUNCTION fn_scope_note_cliente(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_cliente(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- ⚠️ Due famiglie soltanto, ed e' l'unione ESATTA di cio' che
    --   le partizioni gia' concedono: `note_fatture` ha la veste
    --   ba_ownership, `note_ordini` la cliente_ownership. Le altre
    --   cinque non hanno vesti cliente, quindi il padre non deve
    --   inventarne — aprirebbe piu' delle partizioni.
    SELECT CASE p_target_tipo
        WHEN 'FATTURA' THEN script.fn_scope_ba_ownership_via_fattura(p_identita_id, p_target_id)
        WHEN 'ORDINE'  THEN script.fn_scope_cliente_ownership_via_ordine(p_identita_id, p_target_id)
        ELSE false
    END;
$function$

COMMENT ON FUNCTION script.fn_scope_note_cliente(p_identita_id bigint, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore per il padre vendite.note, veste CLIENTE_PORTALE. ⚠️ Copre solo FATTURA e ORDINE: e'' l''unione esatta delle vesti cliente che le partizioni gia'' concedono. Le altre cinque famiglie non ne hanno, e il padre non deve inventarne — aprirebbe piu'' delle partizioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
