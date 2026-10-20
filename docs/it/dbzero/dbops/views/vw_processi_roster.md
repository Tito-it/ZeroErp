{% include-markdown "it/dbzero/dbops/manual/vw_processi_roster.md" %}
# 🔍 View `vw_processi_roster`

> 📝 **Descrizione**
>
> Per ogni processo automatico, con quale IDENTITA' lavora ciascuna azienda: la terna (auth_user_id, username, identita_id) piu' l'emittente. ⭐ Il fatto esisteva gia' ma viveva in una stringa SQL dentro Python (processi_repository.roster_processo): serviva solo al produttore della fatturazione. Da quando anche il DB deve accodare — il job pgAgent della chiusura scadenze — riscriverlo sarebbe stata una SECONDA scrittura dello stesso fatto. ⚠️ Le cinque condizioni sono tutte necessarie (legame attivo, identita' attiva, ruolo OPERATORE, utente Django attivo, emittente attivo): spegnerne uno basta a fermare il processo, quindi guardarne uno solo basta a sbagliare — e' la stessa terna che script.fn_riattiva_utente_tecnico riaccende tutta insieme. ⚠️ La condizione sull'utente Django passa da script.fn_get_auth_user_stato e non da un JOIN diretto: una vista si risolve alla CREATE e le tabelle di django le crea manage.py migrate, non Liquibase. ⚠️ Al backend: roster_processo puo' diventare un SELECT su questa vista. Finche' restano due copie, sono due copie.

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
  WHERE (p.attivo AND (p.obsoleto_dal IS NULL))
  ORDER BY p.codice, ef.codice, idg.auth_user_id;
```

</div>


---
{% include-markdown "signature-core.md" %}
