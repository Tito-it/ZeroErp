{% include-markdown "it/dbzero/dbops/manual/fn_sessione_del_migratore.md" %}
# ⚙️ Funzione `fn_sessione_del_migratore`

```sql
CREATE FUNCTION fn_sessione_del_migratore()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sessione_del_migratore()
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se la sessione e' di chi amministra il database
    --   (il migratore o un superuser), letto dal ruolo di LOGIN.
    -- ⛔ session_user: dentro una DEFINER current_user e' il
    --    proprietario. Fail-closed: la domanda sul ruolo risponde
    --    false, mai NULL.
    SELECT dbops.fn_ruolo_del_migratore(session_user::text);
$function$

COMMENT ON FUNCTION dbops.fn_sessione_del_migratore()
IS 'La sessione e'' di chi amministra il database? true se il ruolo di LOGIN (session_user) e'' un ruolo del migratore secondo dbops.fn_ruolo_del_migratore: membro del proprietario dello schema dbops, in ogni ambiente, o superuser. session_user e non current_user perche'' dentro una SECURITY DEFINER current_user e'' il proprietario; limite dichiarato: un SET ROLE non cambia session_user. Fail-closed, non solleva: rifiuta il chiamante. La chiamano dbops.fn_sync_functions_owner (RAISE nudo, canale di log protetto), script.fn_blocca_credenziale, script.fn_totp_disabilita_device (lo sblocco del secondo fattore dal server), script.fn_porta_manutenzione_aperta (le porte di manutenzione) e script.trgfn_seed_primo_impianto (chi scrive una tabella del seed di primo impianto). INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
