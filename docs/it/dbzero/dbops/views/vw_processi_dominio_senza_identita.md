{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_senza_identita.md" %}
# 🔍 View `vw_processi_dominio_senza_identita`

> 📝 **Descrizione**
>
> Processi DOMINIO che non possono dire CHI agisce, guardati in tre versi: processo vivo (ritiro non raggiunto, script.fn_e_obsoleto) senza utente tecnico, utente tecnico senza identita' OPERATORE col flag tecnica, identita' col flag che nessun processo rivendica. DEVE restare VUOTA. Canali: PGAGENT, COMMAND e CODA_AUTOMATICA: un lavoro accodato da una macchina non ha un'identita' prestata da nessuno. I processi CODA restano esclusi: l'identita' la porta l'operatore che accoda, e dargliene una tecnica cancellerebbe il suo nome.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_identita AS
SELECT p.codice AS processo_codice,
    p.canale,
    NULL::integer AS auth_user_id,
    'processo DOMINIO headless senza utente tecnico'::text AS motivo
   FROM dbops.processi p
  WHERE ((p.classe = 'DOMINIO'::text) AND (NOT script.fn_e_obsoleto(p.obsoleto_dal)) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text, 'CODA_AUTOMATICA'::text])) AND (NOT (EXISTS ( SELECT 1
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

</div>


---
{% include-markdown "signature-core.md" %}
