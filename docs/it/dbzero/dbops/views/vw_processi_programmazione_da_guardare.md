{% include-markdown "it/dbzero/dbops/manual/vw_processi_programmazione_da_guardare.md" %}
# 🔍 View `vw_processi_programmazione_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: i processi automatici la cui sveglia e la cui ultima corsa non tornano. DEVE restare VUOTA. ⭐ E' il panorama (dbops.vw_processi_programmazione) proiettato sulla colonna `da_guardare`, NON un secondo criterio: ripetere qui un NOT IN sugli stati sarebbe la seconda enumerazione dello stesso vocabolario, e la seconda diverge — il giorno in cui uno stato nuovo entra, qualcuno dovrebbe ricordarsi di venire a decidere da che parte cade. ⛔ Il panorama non puo' stare al suo posto: elenca anche i sani (12 righe OK al 2026-09-06), e un presidio che mostra il verde insegna a leggere il verde come debito, cioe' a ignorare l'avviso. ⚠️ Restano FUORI di proposito FUORI_PORTATA e SU_RICHIESTA, che non sono guasti per ragioni opposte: il primo e' un limite di vista del database (i COMMAND li sveglia systemd, e chi li presidia e' il backend da deploy/sveglie.json), il secondo e' la natura del processo (un CODA lo sveglia una persona: una cadenza da confrontare non esiste). ⭐ Lo stato che vale piu' di tutti e' GIRA_E_NON_REGISTRA: pgAgent dice che il job e' girato, il giornale non lo sa. E' la firma di R-12 — un lavoro che muore prima di riuscire a raccontarlo. 🔴 FATTO DATATO 2026-09-06, e va tolto da qui quando sara' rientrato: questa vista NASCE con due righe. chiusura_scadenze_daily ha avuto il wrapper alle 00:39, dopo la corsa delle 00:05, e alla prossima registra. apply_storicizza_weekly no: il suo wrapper esiste dal 2025-08-08, il giornale si ferma al 2026-02-21 e pgAgent dice che ha girato il 2026-09-05 — sei mesi e mezzo di corse senza traccia. Brief: brief-db-sveglia-dei-processi §8.1.

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_programmazione_da_guardare AS
SELECT processo_codice,
    stato,
    classe,
    canale,
    jobname_pgagent,
    job_abilitato,
    pgagent_ultima_corsa,
    giornale_ultima_corsa,
    ultimo_esito,
    prossima_corsa
   FROM dbops.vw_processi_programmazione v
  WHERE da_guardare
  ORDER BY canale, processo_codice;
```


---
{% include-markdown "signature-core.md" %}
