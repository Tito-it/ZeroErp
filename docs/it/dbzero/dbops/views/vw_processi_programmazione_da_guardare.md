{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione_da_guardare.md" %}
# 🔍 View `vw_processi_programmazione_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i processi automatici la cui sveglia e la cui ultima corsa non tornano. DEVE restare VUOTA. E' il panorama (dbops.vw_processi_programmazione) proiettato sulla colonna da_guardare (causa non NULL), NON un secondo criterio: ripetere qui un NOT IN sugli stati sarebbe la seconda enumerazione dello stesso vocabolario, e la seconda diverge. Il panorama non puo' stare al suo posto: elenca anche i sani, e un presidio che mostra il verde insegna a leggere il verde come debito. Restano fuori, con causa NULL, OK, IN_ATTESA (mai girato, prima corsa futura), SPENTO (sveglia spenta su questa installazione), FUORI_PORTATA (i COMMAND senza contratto: li sveglia systemd, e chi li presidia e' il backend da deploy/sveglie.json) e SU_RICHIESTA (un CODA lo sveglia una persona: una cadenza da confrontare non esiste). Lo stato che vale piu' di tutti e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non ha la corsa di pgAgent: un lavoro che muore prima di riuscire a raccontarlo. Il verdetto poggia su giornale_ultima_corsa_pgagent (le sole corse scritte dal percorso DB), e giornale_ultima_corsa sta accanto perche' la DIFFERENZA fra le due e' informazione: se la seconda e' avanti e la prima indietro, qualcuno ha registrato sotto questo codice senza essere pgAgent. Quando il giornale tace su un job che pgAgent dice girato, la storia degli esiti dello scheduler sta in pgagent.*, che zeroerp_app non legge: si comincia da li'. La colonna causa, proiettata dal panorama come lo stato, distingue i rimedi dove uno stato ne ha due (MUTO: TIMER_FERMO o SERVIZIO_GIU; MAI_PARTITO: TIMER_NON_INSTALLATO o JOB_MAI_PARTITO) e sceglie il testo per chi agisce (dbops.presidi.colonna_variante = 'causa'); qui non e' mai NULL.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_programmazione_da_guardare AS
SELECT processo_codice,
    stato,
    classe,
    canale,
    jobname_pgagent,
    job_abilitato,
    pgagent_ultima_corsa,
    giornale_ultima_corsa_pgagent,
    giornale_ultima_corsa,
    ultimo_esito,
    prossima_corsa,
    causa
   FROM dbops.vw_processi_programmazione v
  WHERE da_guardare
  ORDER BY canale, processo_codice;
```

</div>


---
{% include-markdown "signature-core.md" %}
