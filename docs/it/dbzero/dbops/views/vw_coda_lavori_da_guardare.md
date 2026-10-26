{% include-markdown "it/dbzero/dbops/manual/vw_coda_lavori_da_guardare.md" %}
# 🔍 View `vw_coda_lavori_da_guardare`

> 📝 **Descrizione**
>
> I lavori di coda che chiedono un occhio: falliti (ERRORE), presi e mai chiusi (IN_CORSO da oltre un'ora: il worker e' morto a meta'), o mai presi (PENDING da oltre un'ora: ⛔ il worker non sta girando). DEVE restare VUOTA. ⭐ Esiste PRIMA della migrazione dei processi di dominio dalla coda, e non dopo: l'argomento per lasciare pgAgent e' che pgAgent non racconta i suoi fallimenti — apply_storicizza_weekly e' morto ogni settimana per sei mesi e lo si e' scoperto per caso (R-12). ⛔ Ma la coda senza questa vista non era meglio: 4 lavori in ERRORE e nessuno a nominarli. Spostarci il lavoro prima avrebbe TRASFERITO il silenzio invece di toglierlo. ⚠️ Il terzo motivo e' il piu' importante e il meno visibile: un worker spento non produce errori, produce ASSENZA. ⚠️ Le soglie di un'ora non vengono da una misura ma dal fatto che il drenatore gira di continuo: una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi. ⛔ Fuori ANNULLATO (deciso da qualcuno) e archiviato (gia' guardato): un presidio che elenca cio' che qualcuno ha gia' visto smette di essere una lista di cose da fare.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_coda_lavori_da_guardare AS
SELECT id,
    uid,
    job_type,
    stato,
    tentativi,
    max_tentativi,
        CASE
            WHEN (stato = 'ERRORE'::text) THEN 'fallito: tentativi esauriti'::text
            WHEN (stato = 'IN_CORSO'::text) THEN 'preso e mai chiuso: il worker e'' morto a meta'''::text
            ELSE 'mai preso: il worker non sta girando'::text
        END AS motivo,
    (now() - COALESCE(claimed_at, run_after, data_insert)) AS da_quanto,
    ultimo_errore,
    scope,
    data_insert
   FROM dbops.coda_lavori c
  WHERE ((NOT archiviato) AND ((stato = 'ERRORE'::text) OR ((stato = 'IN_CORSO'::text) AND (claimed_at < (now() - '01:00:00'::interval))) OR ((stato = 'PENDING'::text) AND (COALESCE(run_after, data_insert) < (now() - '01:00:00'::interval)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
