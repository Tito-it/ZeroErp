{% include-markdown "it/dbzero/script/manual/fn_scope_note_magazzino_ef_whitelist.md" %}
# ⚙️ Funzione `fn_scope_note_magazzino_ef_whitelist`

```sql
CREATE FUNCTION fn_scope_note_magazzino_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_magazzino_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: smistare la nota verso l'adattatore della sua famiglia.
    --   Serve al PADRE partizionato magazzino.note, che non eredita le
    --   policy delle partizioni. Nelle partizioni _riga target_id e' la
    --   TESTATA: lo scope passa da li'.
    -- ⛔ L'ELSE false e' la riga che conta: un target_tipo nuovo e non
    --   gestito rende quelle note INVISIBILI dal padre, non visibili a
    --   tutti. Presidiato dal pgTAP di P-12 contro chk_note_target_tipo.
    SELECT CASE p_target_tipo
        WHEN 'ASSET'              THEN script.fn_scope_ef_whitelist_via_asset(p_auth_user_id, p_target_id)
        WHEN 'EVENTO_ASSET'       THEN script.fn_scope_ef_whitelist_via_evento_asset(p_auth_user_id, p_target_id)
        WHEN 'INVENTARIO'         THEN script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id, p_target_id)
        WHEN 'INVENTARIO_RIGA'    THEN script.fn_scope_ef_whitelist_via_inventario(p_auth_user_id, p_target_id)
        WHEN 'MOVIMENTO'          THEN script.fn_scope_ef_whitelist_via_movimento(p_auth_user_id, p_target_id)
        WHEN 'RETTIFICA'          THEN script.fn_scope_ef_whitelist_via_rettifica(p_auth_user_id, p_target_id)
        WHEN 'RETTIFICA_RIGA'     THEN script.fn_scope_ef_whitelist_via_rettifica(p_auth_user_id, p_target_id)
        WHEN 'TRASFERIMENTO'      THEN script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id, p_target_id)
        WHEN 'TRASFERIMENTO_RIGA' THEN script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id, p_target_id)
        ELSE false
    END;
$function$

COMMENT ON FUNCTION script.fn_scope_note_magazzino_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato magazzino.note: sceglie l''adattatore dalla famiglia (target_tipo) e passa target_id, che nelle partizioni _riga e'' la testata. ELSE false: un target_tipo nuovo e non gestito rende quelle note invisibili, non pubbliche — e'' la riga che conta, presidiata dal pgTAP di P-12 contro chk_note_target_tipo. Stampo: fn_scope_note_ef_whitelist (vendite). Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.10.';
```

</div>

---
{% include-markdown "signature-core.md" %}
