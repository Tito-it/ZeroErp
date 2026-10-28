{% include-markdown "it/dbzero/script/manual/fn_credenziale_ha_vesti.md" %}
# ⚙️ Funzione `fn_credenziale_ha_vesti`

```sql
CREATE FUNCTION fn_credenziale_ha_vesti(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_credenziale_ha_vesti(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM anagrafiche.identita_digitali idg
           WHERE (idg.auth_user_id = fn_credenziale_ha_vesti.p_auth_user_id))) AS "exists";
END

COMMENT ON FUNCTION script.fn_credenziale_ha_vesti(p_auth_user_id integer)
IS 'true se la credenziale (django.auth_user.id) ha almeno una veste in anagrafiche.identita_digitali, anche spenta. La regola UNICA di «credenziale senza veste»: la leggono anagrafiche.vw_accessi_altri (nessun_accesso, da cui il motivo NESSUNA_VESTE di dbops.vw_credenziali_da_sanare) e script.fn_check_credenziale_eliminabile (motivo CON_VESTI). Una credenziale con sole vesti spente ha vesti: e'' una persona disattivata (V-3). NULL in ingresso -> false. STABLE, SECURITY INVOKER, corpo BEGIN ATOMIC. Brief: brief-db-elimina-credenziale-senza-veste (D-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
