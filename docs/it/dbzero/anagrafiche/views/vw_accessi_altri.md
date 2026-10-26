{% include-markdown "it/dbzero/anagrafiche/manual/vw_accessi_altri.md" %}
# 🔍 View `vw_accessi_altri`

> 📝 **Descrizione**
>
> Il tab «Altri accessi» dell'area Accessi: una riga per credenziale di categoria ALTRO (script.fn_categoria_accesso), cioe' le persone senza veste operatore (portale clienti e fornitori, shop) e le credenziali senza alcuna veste (nessun_accesso, da script.fn_credenziale_ha_vesti: la regola unica, la stessa che rifiuta l'eliminazione in script.fn_check_credenziale_eliminabile). vesti = una voce per veste, anche spenta, con lo stato di script.fn_stato_veste e il soggetto collegato (cliente_ids e' un ARRAY: un soggetto_ruolo puo' avere piu' clienti; fornitore_id e' unico). vesti_elenco e stato_accesso (il migliore fra le vesti, NESSUNO senza vesti) servono a filtrare. Secondo fattore da fn_get_totp_device (solo lo stato) e fn_totp_obbligatorio; blocco da config.credenziali. Le credenziali vengono da script.fn_credenziali (una vista non nomina django.*). security_invoker: attraversa anagrafiche.clienti, che ha la RLS. Brief: brief-db-be-fe-area-accessi (R-DB-A2), brief-db-elimina-credenziale-senza-veste (D-1).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_accessi_altri
WITH (security_invoker=true) AS
SELECT c.auth_user_id,
    c.username,
    c.email,
    c.nome,
    c.cognome,
    COALESCE(NULLIF(concat_ws(' '::text, c.nome, c.cognome), ''::text), c.username) AS nome_visualizzato,
    COALESCE(v.vesti, '[]'::jsonb) AS vesti,
    v.vesti_elenco,
    v.soggetti_elenco,
    (NOT script.fn_credenziale_ha_vesti(c.auth_user_id)) AS nessun_accesso,
    COALESCE(v.stato_accesso, 'NESSUNO'::text) AS stato_accesso,
    c.is_active,
    totp.stato AS secondo_fattore_stato,
    tob.obbligatorio AS secondo_fattore_obbligatorio,
    (cr.bloccata_at IS NOT NULL) AS bloccata,
    cr.bloccata_at AS bloccata_dal,
    cr.motivo_blocco,
    c.last_login AS ultimo_accesso
   FROM ((((script.fn_credenziali() c(auth_user_id, username, email, nome, cognome, is_active, last_login)
     LEFT JOIN LATERAL ( SELECT count(*) AS n_vesti,
            jsonb_agg(jsonb_build_object('identita_id', idg.id, 'ruolo_applicativo', idg.ruolo_applicativo, 'stato', sv.stato, 'attivo', idg.attivo, 'valido_dal', idg.valido_dal, 'valido_al', idg.valido_al, 'invito_inviato_at', idg.invito_inviato_at, 'token_scade_at', sv.token_scade_at, 'soggetto_id', s.id, 'soggetto_ruolo_id', idg.soggetto_ruolo_id, 'soggetto', s.ragione_sociale_completa, 'cliente_ids', ( SELECT COALESCE(jsonb_agg(cl.id ORDER BY cl.id), '[]'::jsonb) AS "coalesce"
                   FROM anagrafiche.clienti cl
                  WHERE (cl.soggetto_ruolo_id = idg.soggetto_ruolo_id)), 'fornitore_id', ( SELECT fo.id
                   FROM anagrafiche.fornitori fo
                  WHERE (fo.soggetto_ruolo_id = idg.soggetto_ruolo_id))) ORDER BY idg.ruolo_applicativo, idg.id) AS vesti,
            string_agg(DISTINCT (idg.ruolo_applicativo)::text, ', '::text ORDER BY (idg.ruolo_applicativo)::text) AS vesti_elenco,
            string_agg(DISTINCT s.ragione_sociale_completa, ', '::text ORDER BY s.ragione_sociale_completa) AS soggetti_elenco,
                CASE
                    WHEN bool_or((sv.stato = 'ATTIVO'::text)) THEN 'ATTIVO'::text
                    WHEN bool_or((sv.stato = 'PENDING'::text)) THEN 'PENDING'::text
                    WHEN bool_or((sv.stato = 'NON_SPEDITO'::text)) THEN 'NON_SPEDITO'::text
                    ELSE 'DISATTIVO'::text
                END AS stato_accesso
           FROM (((anagrafiche.identita_digitali idg
             JOIN LATERAL script.fn_stato_veste(idg.id) sv(stato, token_scade_at) ON (true))
             JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = idg.soggetto_ruolo_id)))
             JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
          WHERE (idg.auth_user_id = c.auth_user_id)
         HAVING (count(*) > 0)) v ON (true))
     LEFT JOIN config.credenziali cr ON ((cr.auth_user_id = c.auth_user_id)))
     CROSS JOIN LATERAL script.fn_get_totp_device(c.auth_user_id) totp(stato, secret_encrypted, ultimo_passo_usato, recovery_rimasti))
     CROSS JOIN LATERAL script.fn_totp_obbligatorio(c.auth_user_id) tob(obbligatorio, motivo))
  WHERE (script.fn_categoria_accesso(c.auth_user_id) = 'ALTRO'::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
