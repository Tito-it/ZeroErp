{% include-markdown "it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md" %}
# 🔍 View `risorse_umane_auth_user`

```sql
CREATE OR REPLACE VIEW anagrafiche.risorse_umane_auth_user AS
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
