# ⚙️ Funzione `fn_scope_note_ef_whitelist`

```sql
CREATE FUNCTION fn_scope_note_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: smistare la nota verso l'adattatore della sua
    --   famiglia. Serve al PADRE partizionato vendite.note, che
    --   non eredita le policy delle partizioni.
    -- ⛔ L'ELSE false e' la riga che conta: un target_tipo nuovo e
    --   non gestito rende quelle note INVISIBILI dal padre, non
    --   visibili a tutti. Presidiato dal pgTAP della slice.
    SELECT CASE p_target_tipo
        WHEN 'PREVENTIVO' THEN script.fn_scope_ef_whitelist_via_preventivo(p_auth_user_id, p_target_id)
        WHEN 'ORDINE'     THEN script.fn_scope_ef_whitelist_via_ordine(p_auth_user_id, p_target_id)
        WHEN 'DDT'        THEN script.fn_scope_ef_whitelist_via_ddt(p_auth_user_id, p_target_id)
        WHEN 'CONTRATTO'  THEN script.fn_scope_ef_whitelist_via_contratto(p_auth_user_id, p_target_id)
        WHEN 'FATTURA'    THEN script.fn_scope_ef_whitelist_via_fattura(p_auth_user_id, p_target_id)
        WHEN 'OFFERTA'    THEN script.fn_scope_ef_whitelist_via_offerta(p_auth_user_id, p_target_id)
        WHEN 'ATTIVITAFT' THEN script.fn_scope_ef_whitelist_via_attivita_fatturabile(p_auth_user_id, p_target_id)
        ELSE false
    END;
$function$

COMMENT ON FUNCTION script.fn_scope_note_ef_whitelist(p_auth_user_id integer, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato vendite.note, veste OPERATORE: instrada su target_tipo verso l''adattatore della famiglia. Esiste perche'' le policy delle PARTIZIONI non risalgono al padre — provato il 2026-09-09: col padre armato e senza policy propria, risponde zero. ⛔ ELSE false: un target_tipo non gestito rende quelle note invisibili dal padre, non visibili a tutti; presidiato dal pgTAP della slice, che confronta i rami col CHECK. Brief §6.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
