{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_efba.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_efba`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: il billing account e' visibile all'utente? Un BA ha UN emittente,
    --   ma quale lo dice script.fn_get_ba_emittente_sr_id, che non e' un fatto
    --   della riga: legame esplicito, altrimenti l'emittente dell'utente in
    --   sessione, altrimenti quello di default. Per questo non e' un modo di
    --   fn_resolve_emittente_fiscale_id (la domanda di FATTO).
    -- ⭐ Rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): la stessa composizione
    --   delle policy (20261018-50), in convenzione SOGGETTO_RUOLO: il perimetro
    --   (fn_get_emittenti_scope_sr_ids) e l'emittente del BA interrogati con
    --   fn_scope_ef_perimetro. Prima era plpgsql con la stessa logica scritta
    --   a mano: NULL = tutti, '{}' = nessuno, BA senza emittente = false.
    --   Stesse risposte; utente NULL -> perimetro '{}' -> false.
    SELECT script.fn_scope_ef_perimetro(
        script.fn_get_emittenti_scope_sr_ids(p_auth_user_id),
        script.fn_get_ba_emittente_sr_id(p_billing_account_id))
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_efba(p_auth_user_id integer, p_billing_account_id bigint)
IS '⭐ rev 2026-10-18 (20261018-49, D-3b-2 ondata 2): l''emittente dal risolutore DEFINER (via_efba: dalla composizione delle policy, in convenzione soggetto_ruolo); una strada sola, nessuna policy del padre per chiamata. Stesse risposte. Adapter via_efba dello scope EF_WHITELIST per billing_account: true se il BA e'' raggiungibile (mapping efba specifico-o-default) da almeno uno degli emittenti nello scope dell''operatore. Riusa fn_get_emittenti_scope_sr_ids ∩ fn_check_ba_visible_for_emittenti. Utente NULL -> false (rev 2026-10-04, Q-1: era true, come la canonica); super admin -> true; nessuna identita'' OPERATORE, whitelist vuota (P-2a) o emittente attivo fuori scope -> false. Nota perf: lo scope e'' query-constant (valutato una volta per auth_user_id); il costo per-riga e'' il lookup efba. Brief: brief-db-esclusioni-implicite Q-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
