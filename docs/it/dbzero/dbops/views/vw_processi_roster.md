{% include-markdown "it/dbzero/dbops/manual/vw_processi_roster.md" %}
# 🔍 View `vw_processi_roster`

> 📝 **Descrizione**
>
> Per ogni processo automatico vivo (ritiro non raggiunto, script.fn_e_obsoleto), con quale IDENTITA' lavora ciascuna azienda: la terna (auth_user_id, username, identita_id) piu' l'emittente. Le cinque condizioni sono tutte necessarie (legame attivo, identita' attiva, ruolo OPERATORE, utente Django attivo, emittente attivo): spegnerne una basta a fermare il processo, ed e' la stessa terna che script.fn_riattiva_utente_tecnico riaccende tutta insieme. L'utente Django si legge da script.fn_get_auth_user_stato e non da un JOIN diretto: una vista si risolve alla CREATE, e le tabelle di django le crea manage.py migrate, non Liquibase. La leggono l'accodamento della chiusura per scadenza e il backend.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_roster AS
SELECT p.codice AS processo_codice,
    p.classe,
    p.canale,
    idg.auth_user_id,
    au.username,
    idg.id AS identita_id,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_codice,
    ef.soggetto_ruolo_id AS emittente_soggetto_ruolo_id
   FROM (((((dbops.processi p
     JOIN dbops.processi_identita pi ON (((pi.processo_id = p.id) AND pi.attivo)))
     JOIN anagrafiche.identita_digitali idg ON (((idg.auth_user_id = pi.auth_user_id) AND idg.attivo AND (idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo))))
     JOIN LATERAL script.fn_get_auth_user_stato(pi.auth_user_id) au(username, is_active) ON (au.is_active))
     JOIN config.user_emittenti_fiscali uef ON ((uef.auth_user_id = pi.auth_user_id)))
     JOIN anagrafiche.emittenti_fiscali ef ON (((ef.id = uef.emittente_fiscale_id) AND ef.attivo)))
  WHERE (NOT script.fn_e_obsoleto(p.obsoleto_dal))
  ORDER BY p.codice, ef.codice, idg.auth_user_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
