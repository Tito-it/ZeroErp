{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_su_pgagent.md" %}
# 🔍 View `vw_processi_dominio_su_pgagent`

> 📝 **Descrizione**
>
> Processi DOMINIO vivi (ritiro non raggiunto, script.fn_e_obsoleto) che ESEGUONO dentro pgAgent. DEVE restare VUOTA. Li' un processo non ha identita', quindi nessun perimetro emittente, e un fallimento non arriva a nessuno: la traccia sta in pgagent.pga_joblog, che l'applicazione non vede. Che un job pgAgent SVEGLI un processo di dominio resta lecito: un job che chiama dbops.fn_accoda_lavoro non tocca nessun documento, e il lavoro vero resta tracciato nella coda; il canale di quel processo e' CODA_AUTOMATICA. Non e' un CHECK su dbops.processi: il registro e' catalogo, e un CHECK trasformerebbe un errore di configurazione di una riga in un migrate rotto.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_su_pgagent AS
SELECT codice AS processo_codice,
    descrizione,
    canale,
    'esegue dentro pgAgent: senza identita'', e un fallimento non arriva a nessuno. Va spostato su CODA_AUTOMATICA, con il job pgAgent che lo ACCODA invece di eseguirlo'::text AS motivo
   FROM dbops.processi p
  WHERE ((classe = 'DOMINIO'::text) AND (NOT script.fn_e_obsoleto(obsoleto_dal)) AND (canale = 'PGAGENT'::text));
```

</div>


---
{% include-markdown "signature-core.md" %}
