{% include-markdown "it/dbzero/dbops/manual/vw_credenziali_da_sanare.md" %}
# 🔍 View `vw_credenziali_da_sanare`

> 📝 **Descrizione**
>
> Presidio ZERO delle credenziali. NESSUNA_VESTE: la credenziale non ha alcuna veste, nemmeno spenta (anagrafiche.vw_accessi_altri.nessun_accesso: una regola sola); una credenziale con sole vesti spente e' una persona disattivata e non entra. PERSONA_E_SISTEMA: vesti di persona e di macchina sulla stessa credenziale (script.fn_veste_di_sistema), che il guard trgfn_identita_digitali_guard_natura_credenziale rifiuta: escono le righe scritte prima del guard e quelle di una gara fra transazioni. NESSUNA_VESTE si sana dando una veste alla credenziale o cancellandola (spegnerla in Django non basta: resta una credenziale senza veste); PERSONA_E_SISTEMA separando le due nature su due credenziali.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_credenziali_da_sanare
WITH (security_invoker=true) AS
SELECT a.auth_user_id,
    a.username,
    'NESSUNA_VESTE'::text AS motivo
   FROM anagrafiche.vw_accessi_altri a
  WHERE a.nessun_accesso
UNION ALL
 SELECT m.auth_user_id,
    au.username,
    'PERSONA_E_SISTEMA'::text AS motivo
   FROM (( SELECT idg.auth_user_id
           FROM anagrafiche.identita_digitali idg
          GROUP BY idg.auth_user_id
         HAVING (bool_or(script.fn_veste_di_sistema(idg.ruolo_applicativo, idg.tecnica)) AND bool_or((NOT script.fn_veste_di_sistema(idg.ruolo_applicativo, idg.tecnica))))) m
     LEFT JOIN LATERAL script.fn_get_auth_user_stato(m.auth_user_id) au(username, is_active) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
