{% include-markdown "it/dbzero/dbops/manual/vw_fatture_stampa_coda_da_guardare.md" %}
# 🔍 View `vw_fatture_stampa_coda_da_guardare`

> 📝 **Descrizione**
>
> PRESIDIO: le stampe in coda che chiedono un occhio — fallite (ERRORE), prese e mai chiuse (IN_CORSO da oltre un'ora: il worker e' morto a meta' e il reaper non e' passato), o mai prese (PENDING da oltre un'ora: ⛔ il drenatore della stampa non sta girando). DEVE restare VUOTA. E' la gemella di dbops.vw_coda_lavori_da_guardare, nata il 2026-09-11 perche' delle due code gemelle una sola aveva il presidio. ⭐ data_update e' l'ultima transizione di stato: l'audit trigger lo porta a now() a ogni scrittura, e sulle righe vive l'unica scrittura del drenatore e' una transizione (archiviato vale solo sugli stati terminali) — il reaper lo legge gia' cosi'. ⚠️ Non e' un vincolo: una scrittura non di stato su una riga viva azzererebbe l'orologio, e il presidio tacerebbe un'ora in piu' (non suonerebbe a vuoto). ⚠️ Un'ora non deriva dalla cadenza di due minuti: una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi. ⚠️ Niente ANNULLATO: la stampa non ce l'ha. Fuori archiviato (gia' guardato). ⛔ Perimetro DEFINER a catalogo: la tabella ha la RLS e la vista e' security_invoker — una persona legge col suo perimetro, il digest conta da proprietario e riporta il numero. Brief: brief-db-quattro-processi-senza-presidio §4.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_fatture_stampa_coda_da_guardare
WITH (security_invoker=true) AS
SELECT id,
    sorgente_tipo_id,
    sorgente_id,
    sorgente_uid,
    lotto_id,
    stato,
    tentativi,
        CASE
            WHEN (stato = 'ERRORE'::text) THEN 'fallito: tentativi esauriti'::text
            WHEN (stato = 'IN_CORSO'::text) THEN 'preso e mai chiuso: il worker e'' morto a meta'''::text
            ELSE 'mai preso: il drenatore della stampa non sta girando'::text
        END AS motivo,
    (now() - data_update) AS da_quanto,
    ultimo_errore,
    documento_id,
    data_insert,
    data_update
   FROM vendite.fatture_stampa_coda c
  WHERE ((NOT archiviato) AND ((stato = 'ERRORE'::text) OR ((stato = 'IN_CORSO'::text) AND (data_update < (now() - '01:00:00'::interval))) OR ((stato = 'PENDING'::text) AND (data_update < (now() - '01:00:00'::interval)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
