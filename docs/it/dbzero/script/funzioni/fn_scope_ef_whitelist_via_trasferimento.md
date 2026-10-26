{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_trasferimento.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_trasferimento`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'utente vede l'emittente della chiave (trasferimento)? La
    --   domanda su UN emittente, per chi non sta in una policy (verbi, guard,
    --   backend): la regola e' della canonica, l'emittente del risolutore.
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l'emittente si chiede a
    --   script.fn_resolve_emittente_fiscale_id('trasferimento', ...), DEFINER, invece di
    --   leggerlo sotto la RLS del padre: una strada sola, e nessuna policy del
    --   padre rieseguita a ogni chiamata. Stesse risposte. Le policy non passano
    --   piu' di qui (20261018-50).
    SELECT script.fn_check_user_emittente_scope(
        p_auth_user_id,
        script.fn_resolve_emittente_fiscale_id('trasferimento', p_trasferimento_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_trasferimento(p_auth_user_id integer, p_trasferimento_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adattatore di scope per un trasferimento via il magazzino di ORIGINE (magazzino_id_from): una risalita basta perche'' trgfn_trasferimenti_guard_stesso_emittente garantisce che la destinazione sia dello stesso emittente (M-6). Chiave di trasferimenti_righe e delle note note_trasferimento e note_trasferimento_riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
