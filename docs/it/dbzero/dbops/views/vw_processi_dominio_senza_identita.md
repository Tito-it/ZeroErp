{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_identita.md" %}
# 🔍 View `vw_processi_dominio_senza_identita`

> 📝 **Descrizione**
>
> Disaccordi fra il flag anagrafiche.identita_digitali.tecnica e il registro dbops.processi_identita, nei DUE sensi, piu' i processi DOMINIO headless ancora senza utente tecnico. DEVE restare VUOTA. ⛔ Esclusi i processi su canale CODA: sono accodati da un operatore e girano con lo scope catturato all'enqueue — un utente tecnico li' cancellerebbe il nome di chi ha chiesto il lavoro. ⭐ Il terzo verso (identita' col flag che nessun processo rivendica) protegge dal caso peggiore: marcare tecnica=true sull'identita' di una PERSONA per farla sparire dai conteggi. Brief: brief-db-processi-automatici-identita-e-perimetro §8.

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_identita AS
SELECT p.codice AS processo_codice,
    p.canale,
    NULL::integer AS auth_user_id,
    'processo DOMINIO headless senza utente tecnico'::text AS motivo
   FROM dbops.processi p
  WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text])) AND (NOT (EXISTS ( SELECT 1
           FROM dbops.processi_identita pi
          WHERE ((pi.processo_id = p.id) AND pi.attivo)))))
UNION ALL
 SELECT p.codice AS processo_codice,
    p.canale,
    pi.auth_user_id,
    'utente tecnico senza identita'' OPERATORE con flag tecnica'::text AS motivo
   FROM (dbops.processi p
     JOIN dbops.processi_identita pi ON (((pi.processo_id = p.id) AND pi.attivo)))
  WHERE (NOT (EXISTS ( SELECT 1
           FROM anagrafiche.identita_digitali idg
          WHERE ((idg.auth_user_id = pi.auth_user_id) AND idg.attivo AND idg.tecnica AND (idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)))))
UNION ALL
 SELECT NULL::text AS processo_codice,
    NULL::text AS canale,
    idg.auth_user_id,
    'identita'' con flag tecnica non rivendicata da nessun processo'::text AS motivo
   FROM anagrafiche.identita_digitali idg
  WHERE (idg.tecnica AND idg.attivo AND (NOT (EXISTS ( SELECT 1
           FROM dbops.processi_identita pi
          WHERE ((pi.auth_user_id = idg.auth_user_id) AND pi.attivo)))));
```


---
{% include-markdown "signature-core.md" %}
