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
        CASE
            WHEN ((NOT id.attivo) OR (id.ruolo_applicativo = 'DISABILITATO'::config.ruolo_applicativo) OR ((id.valido_dal IS NOT NULL) AND (id.valido_dal > CURRENT_DATE)) OR ((id.valido_al IS NOT NULL) AND (id.valido_al < CURRENT_DATE))) THEN 'DISABILITATO'::config.ruolo_sistema
            WHEN (sa.identita_digitale_id IS NOT NULL) THEN 'ADMIN'::config.ruolo_sistema
            ELSE 'OPERATIVO'::config.ruolo_sistema
        END AS ruolo_sistema,
    id.storicizza,
    id.tx_id,
    id.tentativi_falliti,
    id.bloccato_fino_a,
    id.deve_cambiare_password,
    id.invito_inviato_at,
    id.totp_obbligatorio
   FROM ((anagrafiche.identita_digitali id
     LEFT JOIN anagrafiche.risorse_umane ru ON ((ru.soggetto_ruolo_id = id.soggetto_ruolo_id)))
     LEFT JOIN ( SELECT pab.identita_digitale_id
           FROM (config.profili_accesso_bindings pab
             JOIN config.profili_accesso pa ON ((pa.id = pab.profilo_accesso_id)))
          WHERE ((pab.attivo = true) AND (pa.attivo = true) AND (pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso) AND (pab.identita_digitale_id IS NOT NULL))) sa ON ((sa.identita_digitale_id = id.id)))
  WHERE (id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo);
```


---
{% include-markdown "signature-core.md" %}
