{% include-markdown "it/dbzero/script/manual/fn_has_identita_attiva.md" %}
# ⚙️ Funzione `fn_has_identita_attiva`

```sql
CREATE FUNCTION fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- La CREDENZIALE ha una veste di quel tipo UTILIZZABILE oggi? Fail-closed
    -- su NULL auth_user_id (EXISTS restituisce false).
    -- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): «utilizzabile» lo
    --   decide script.fn_veste_utilizzabile, non piu' una copia qui di
    --   attivo + finestra (che non guardava soggetto e rapporto).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
         WHERE id.auth_user_id = p_auth_user_id
           AND id.ruolo_applicativo = p_ruolo_applicativo
           AND script.fn_veste_utilizzabile(id.id)
    );
$function$

COMMENT ON FUNCTION script.fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Verifica se la credenziale (auth_user_id) ha una veste del ruolo_applicativo dato utilizzabile oggi, secondo script.fn_veste_utilizzabile. Helper DRY per le funzioni di risoluzione permessi/scope (§4.6.B.0 WIP multi-face-auth). LANGUAGE sql STABLE, fail-closed su NULL. Rev 2026-10-07 (brief-db-veste-utilizzabile): la regola non e'' piu'' ricopiata qui, la legge da script.fn_veste_utilizzabile (soggetto attivo e, per l''operatore umano, rapporto attivo e nelle sue date compresi).';
```

</div>

---
{% include-markdown "signature-core.md" %}
