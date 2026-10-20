{% include-markdown "it/dbzero/anagrafiche/manual/vw_accessi_sistema.md" %}
# 🔍 View `vw_accessi_sistema`

> 📝 **Descrizione**
>
> Il tab «Di sistema» dell'area Accessi, sola lettura (A-6): una riga per credenziale di categoria SISTEMA (script.fn_categoria_accesso), cioe' gli utenti tecnici dei processi automatici e le credenziali API_CLIENT. tipo = PROCESSO (una veste con tecnica; vince se ci sono entrambe) o API_CLIENT. Processo collegato da dbops.processi_identita (al piu' uno), emittente da config.user_emittenti_fiscali (al piu' uno), blocco da config.credenziali. Niente secondo fattore: su una macchina non ha senso. Il FE apre il drawer del processo da processo_id. Brief: brief-db-be-fe-area-accessi (R-DB-A2-bis).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_accessi_sistema
WITH (security_invoker=true) AS
SELECT c.auth_user_id,
    c.username,
        CASE
            WHEN v.e_processo THEN 'PROCESSO'::text
            ELSE 'API_CLIENT'::text
        END AS tipo,
    v.vesti_elenco,
    v.identita_attiva,
    pr.id AS processo_id,
    pr.codice AS processo_codice,
    pr.descrizione AS processo_descrizione,
    pr.attivo AS processo_attivo,
    pi.attivo AS legame_processo_attivo,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_codice,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    c.is_active,
    (cr.bloccata_at IS NOT NULL) AS bloccata,
    cr.bloccata_at AS bloccata_dal,
    cr.motivo_blocco,
    c.last_login AS ultimo_accesso
   FROM ((((((((script.fn_credenziali() c(auth_user_id, username, email, nome, cognome, is_active, last_login)
     JOIN LATERAL ( SELECT bool_or(idg.tecnica) AS e_processo,
            bool_or(idg.attivo) AS identita_attiva,
            string_agg(DISTINCT (idg.ruolo_applicativo)::text, ', '::text ORDER BY (idg.ruolo_applicativo)::text) AS vesti_elenco
           FROM anagrafiche.identita_digitali idg
          WHERE (idg.auth_user_id = c.auth_user_id)) v ON (true))
     LEFT JOIN dbops.processi_identita pi ON ((pi.auth_user_id = c.auth_user_id)))
     LEFT JOIN dbops.processi pr ON ((pr.id = pi.processo_id)))
     LEFT JOIN config.user_emittenti_fiscali uef ON ((uef.auth_user_id = c.auth_user_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = uef.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.credenziali cr ON ((cr.auth_user_id = c.auth_user_id)))
  WHERE (script.fn_categoria_accesso(c.auth_user_id) = 'SISTEMA'::text);
```

</div>


---
{% include-markdown "signature-core.md" %}
