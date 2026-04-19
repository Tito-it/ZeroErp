{% include-markdown "it/dbzero/script/manual/fn_check_almeno_un_super_admin_attivo.md" %}
# ⚙️ Funzione `fn_check_almeno_un_super_admin_attivo`

```sql
CREATE FUNCTION fn_check_almeno_un_super_admin_attivo()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_almeno_un_super_admin_attivo()
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Condizione di sicurezza: il sistema mantiene almeno un
    -- amministratore raggiungibile. Tre livelli AND obbligatori:
    --   1) profilo_accesso.codice = 'SUPER_ADMIN' (+ attivo)
    --   2) binding attivo verso quel profilo, di tipo AD_HOC
    --      (identita_digitale_id valorizzato)
    --   3) identita_digitali attiva
    -- Un unico EXISTS short-circuita: sufficiente trovare uno.
    SELECT EXISTS (
        SELECT 1
          FROM config.profili_accesso           pa
          JOIN config.profili_accesso_bindings  pab
            ON pab.profilo_accesso_id = pa.id
          JOIN anagrafiche.identita_digitali    id
            ON id.id = pab.identita_digitale_id
         WHERE pa.codice = 'SUPER_ADMIN'
           AND pa.attivo = true
           AND pab.attivo = true
           AND id.attivo  = true
    );
$function$

COMMENT ON FUNCTION script.fn_check_almeno_un_super_admin_attivo()
IS 'Ritorna true se esiste almeno un''identita attiva con binding attivo verso un profilo SUPER_ADMIN. Usato dai guard anti-lockout su profili_accesso_bindings e identita_digitali. STABLE, fail-closed nessun raise.';
```

---
{% include-markdown "signature-core.md" %}
