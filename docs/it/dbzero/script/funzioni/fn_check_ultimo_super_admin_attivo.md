{% include-markdown "it/dbzero/script/manual/fn_check_ultimo_super_admin_attivo.md" %}
# ⚙️ Funzione `fn_check_ultimo_super_admin_attivo`

```sql
CREATE FUNCTION fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Predicato per-utente: true sse togliere a p_auth_user_id la
    --   sua garanzia di SUPER_ADMIN lascerebbe il sistema senza
    --   nessun SUPER_ADMIN SENZA SCADENZA (lockout, subito o col
    --   calendario).
    --
    -- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile, decisione di
    --   Tid): «SUPER_ADMIN» qui vuol dire SENZA SCADENZA, cioe'
    --   script.fn_identita_super_admin_senza_scadenza: utilizzabile
    --   oggi, nessuna data di fine su veste e rapporto, credenziale
    --   non bloccata. E' la stessa domanda di
    --   fn_check_almeno_un_super_admin_attivo, e le due funzioni la
    --   leggono dallo stesso building block: prima ognuna aveva il
    --   suo blocco di filtri, e non coincidevano (questa guardava la
    --   finestra, l'altra no).
    --   Un amministratore che ha GIA' una data di fine non e' «senza
    --   scadenza»: spegnerlo non riduce la garanzia, e qui risponde
    --   false (il drawer lo lascia spegnere).
    -- =========================================================
    SELECT
            p_auth_user_id IS NOT NULL
        AND EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali id
             WHERE id.auth_user_id = p_auth_user_id
               AND script.fn_identita_super_admin_senza_scadenza(id.id)
        )
        AND NOT EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali id
             WHERE id.auth_user_id <> p_auth_user_id
               AND script.fn_identita_super_admin_senza_scadenza(id.id)
        );
$function$

COMMENT ON FUNCTION script.fn_check_ultimo_super_admin_attivo(p_auth_user_id integer)
IS 'Predicato per-utente: true sse questo auth_user e'' l''unico SUPER_ADMIN SENZA SCADENZA del sistema, cioe'' togliergli la garanzia (spegnerlo, dargli una data di fine sulla veste o sul rapporto, bloccarne la credenziale, togliergli il profilo) lascerebbe il sistema senza amministratori, subito o col calendario. «Senza scadenza» = script.fn_identita_super_admin_senza_scadenza (utilizzabile oggi, nessuna data di fine su veste e rapporto, credenziale non bloccata): la stessa regola di fn_check_almeno_un_super_admin_attivo, dallo stesso building block. Un amministratore che ha gia'' una data di fine risponde false: spegnerlo non riduce la garanzia. Usato per le capability can_disable / can_demote_super_admin del drawer Operatore. Rev 2026-10-07 (brief-db-veste-utilizzabile): prima «attivo e raggiungibile» era un blocco di filtri ricopiato due volte, con la finestra della veste e senza il rapporto; ora e'' il building block, con la garanzia sulla data di fine decisa da Tid.';
```

</div>

---
{% include-markdown "signature-core.md" %}
