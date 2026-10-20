{% include-markdown "it/dbzero/dbops/manual/vw_processi_dominio_su_pgagent.md" %}
# 🔍 View `vw_processi_dominio_su_pgagent`

> 📝 **Descrizione**
>
> Processi di classe DOMINIO che ESEGUONO dentro pgAgent. DEVE arrivare a VUOTA. ⛔ Li' un processo non ha identita' — quindi nessun perimetro emittente — e un fallimento non arriva a nessuno: la traccia sta in pgagent.pga_joblog, che nessuno guarda e che l'applicazione non vede. ⭐ L'argomento e' sperimentale: apply_storicizza_weekly e' morto ogni settimana per SEI MESI e lo si e' scoperto per caso (R-12). ⚠️ Che un job pgAgent SVEGLI un processo di dominio resta lecito e non e' una scappatoia: un job che chiama dbops.fn_accoda_lavoro non tocca nessun documento — se muore non ha fatto danni, e il lavoro vero resta tracciato nella coda. Il registro descrive il PROCESSO, non chi suona la sveglia: percio' il canale diventa CODA_AUTOMATICA. ⛔ Non e' un CHECK su dbops.processi, e per due ragioni: oggi fallirebbe il migrate (la riga c'e' ancora), e il registro e' catalogo — un CHECK trasformerebbe un errore di configurazione in un migrate rotto, cioe' in un problema di tutti invece che di quella riga. Decisione: brief-db-processi-automatici-identita-e-perimetro, sezione 12.12.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_su_pgagent AS
SELECT codice AS processo_codice,
    descrizione,
    canale,
    'esegue dentro pgAgent: senza identita'', e un fallimento non arriva a nessuno. Va spostato su CODA_AUTOMATICA, con il job pgAgent che lo ACCODA invece di eseguirlo'::text AS motivo
   FROM dbops.processi p
  WHERE ((classe = 'DOMINIO'::text) AND attivo AND (obsoleto_dal IS NULL) AND (canale = 'PGAGENT'::text));
```

</div>


---
{% include-markdown "signature-core.md" %}
