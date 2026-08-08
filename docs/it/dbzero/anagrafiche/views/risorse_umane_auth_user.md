{% include-markdown "it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md" %}
# 🔍 View `risorse_umane_auth_user`

> 📝 **Descrizione**
>
> Vista compat post-cutover §13.3 (security_invoker=true). Fase 7 (29-04-2026): rimossa colonna calcolata ruolo_sistema (CASE inline su attivo/ruolo_applicativo/finestra/binding SA) e relativa subquery sa, sblocca DROP TYPE config.ruolo_sistema. Body ridotto a proiezione liscia su identita_digitali (filtro ruolo_applicativo=OPERATORE) + LEFT JOIN risorse_umane via soggetto_ruolo_id.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW anagrafiche.risorse_umane_auth_user
WITH (security_invoker=true) AS
SELECT id.id,
    ru.id AS risorsa_umana_id,
    id.auth_user_id,
    id.attivo,
    id.meta,
    id.data_insert,
    id.user_insert,
    id.data_update,
    id.user_update,
    id.storicizza,
    id.tx_id,
    id.tentativi_falliti,
    id.bloccato_fino_a,
    id.deve_cambiare_password,
    id.invito_inviato_at,
    id.totp_obbligatorio
   FROM (anagrafiche.identita_digitali id
     LEFT JOIN anagrafiche.risorse_umane ru ON ((ru.soggetto_ruolo_id = id.soggetto_ruolo_id)))
  WHERE (id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo);
```


---
{% include-markdown "signature-core.md" %}
