{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione_da_guardare.md" %}
# 🔍 View `vw_processi_programmazione_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i processi automatici la cui sveglia e la cui ultima corsa non tornano. DEVE restare VUOTA. ⭐ E' il panorama (dbops.vw_processi_programmazione) proiettato sulla colonna `da_guardare`, NON un secondo criterio: ripetere qui un NOT IN sugli stati sarebbe la seconda enumerazione dello stesso vocabolario, e la seconda diverge — il giorno in cui uno stato nuovo entra, qualcuno dovrebbe ricordarsi di venire a decidere da che parte cade. ⛔ Il panorama non puo' stare al suo posto: elenca anche i sani (12 righe OK al 2026-09-06), e un presidio che mostra il verde insegna a leggere il verde come debito, cioe' a ignorare l'avviso. ⚠️ Restano FUORI di proposito FUORI_PORTATA e SU_RICHIESTA, che non sono guasti per ragioni opposte: il primo e' un limite di vista del database (i COMMAND li sveglia systemd, e chi li presidia e' il backend da deploy/sveglie.json), il secondo e' la natura del processo (un CODA lo sveglia una persona: una cadenza da confrontare non esiste). ⭐ Lo stato che vale piu' di tutti e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non lo sa. E' la firma di R-12 — un lavoro che muore prima di riuscire a raccontarlo. ⭐ LE DUE DATE DEL GIORNALE SONO DUE, rev 2026-09-07: il verdetto poggia su `giornale_ultima_corsa_pgagent` (le sole corse scritte dal percorso DB), e `giornale_ultima_corsa` sta accanto perche' la DIFFERENZA fra le due e' informazione — se la seconda e' avanti e la prima indietro, qualcuno ha registrato sotto questo codice senza essere pgAgent. Brief §9.5-bis. ⚠️ UNA CAUSA NON ACCERTATA, e non e' una condizione di riapertura: fra il 21-02-2026 e il 05-09-2026 apply_storicizza_weekly e' girato ogni settimana senza lasciare una riga, e la corsa forzata del 2026-09-07 e' andata VERDE — quindi il difetto non era nel job, era nel verbale, ma perche' sei mesi e mezzo di corse riuscite non abbiano scritto niente resta senza risposta. Da qui non si accerta: lo storico degli esiti dello scheduler sta in pgagent.*, che zeroerp_app non legge. ⇒ La prossima volta che questo giornale tace, si comincia da li'. ⭐ LA CAUSA, rev 2026-10-09 (brief-db-presidio-processi-testo-per-causa §3 B.1): colonna `causa` in coda, proiettata dal panorama come lo stato. Due stati hanno due cause con rimedi diversi (MUTO: TIMER_FERMO o SERVIZIO_GIU; MAI_PARTITO: TIMER_NON_INSTALLATO o JOB_MAI_PARTITO), e la causa sceglie il testo per chi agisce (dbops.presidi.colonna_variante = 'causa'). Qui non e' mai NULL: nel panorama da_guardare E' «la riga ha una causa».

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
