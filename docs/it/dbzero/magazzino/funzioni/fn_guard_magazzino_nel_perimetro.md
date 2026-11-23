{% include-markdown "it/dbzero/magazzino/manual/fn_guard_magazzino_nel_perimetro.md" %}
# ⚙️ Funzione `fn_guard_magazzino_nel_perimetro`

```sql
CREATE FUNCTION fn_guard_magazzino_nel_perimetro(p_magazzino_id bigint, p_auth_user_id integer, p_porta text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_guard_magazzino_nel_perimetro(p_magazzino_id bigint, p_auth_user_id integer, p_porta text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Scopo: il magazzino c'e' ed e' nel perimetro di chi agisce
    --   (il predicato della policy), altrimenti
    --   E_MAG_MAGAZZINO_NON_TROVATO senza dire quale dei due.
    IF NOT EXISTS (SELECT 1
                     FROM magazzino.magazzini mg
                    WHERE mg.id = p_magazzino_id
                      AND script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id, mg.id)) THEN
        PERFORM script.fn_log_and_raise_error(
            'magazzino', p_porta, 'E_MAG_MAGAZZINO_NON_TROVATO',
            jsonb_build_object('magazzino_id', p_magazzino_id),
            NULL::uuid,
            COALESCE(p_magazzino_id::text, '(nessuno)'));
    END IF;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_guard_magazzino_nel_perimetro(p_magazzino_id bigint, p_auth_user_id integer, p_porta text)
IS 'Guard: il magazzino esiste ed e'' nel perimetro dell''utente (script.fn_scope_ef_whitelist_via_magazzino, il predicato della policy), altrimenti E_MAG_MAGAZZINO_NON_TROVATO, senza dire se non esiste o non e'' suo. p_porta e'' la funzione che rifiuta: il log e'' suo. Serve ai verbi SECURITY DEFINER che fanno nascere qualcosa dentro un magazzino (un''ubicazione, la testata di un documento interno), dove la RLS non filtra. Non controlla il permesso: lo ha gia'' controllato il verbo. INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
