# 🔍 View `vw_lotti_chiusi_con_gruppi_in_errore`

> 📝 **Descrizione**
>
> PRESIDIO, e deve restare VUOTO. Elenca una contraddizione: un lotto chiuso COMPLETATO che contiene documenti dichiarati in ERRORE. Sono due affermazioni che non possono stare insieme — o il giro e' andato bene, o quei documenti non erano suoi. ⭐ Nasce dalla decisione del 2026-09-06 di non sollevare piu' quando falliscono TUTTE le commesse di un giro: senza l'eccezione lo stato finale del lotto lo decide chi guarda fatture in errore e segnalazioni critiche, e con tutte le commesse fallite le fatture NON NASCONO — la salvezza dipende solo dalle segnalazioni critiche scritte da un altro pezzo, cioe' e' INDIRETTA. ⭐ Rev 2026-09-07: legge vendite.fatturazione_lotti_esiti, quindi vede anche i lotti SENZA perimetro (i giri di massa), che prima erano fuori portata perche' l'esito viveva sulle righe del perimetro. Brief: brief-db-esito-gruppo-lotto §15.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_chiusi_con_gruppi_in_errore
WITH (security_invoker=true) AS
SELECT l.id AS lotto_id,
    l.codice AS lotto_codice,
    l.stato_lotto,
    l.competenza_mese,
    l.emittente_soggetto_ruolo_id,
    count(*) AS gruppi_in_errore,
    min(e.errore_quando) AS primo_errore,
    max(e.errore_quando) AS ultimo_errore,
    array_agg(DISTINCT e.errore_codice) FILTER (WHERE (e.errore_codice IS NOT NULL)) AS codici_errore
   FROM (vendite.fatturazione_lotti l
     JOIN vendite.fatturazione_lotti_esiti e ON ((e.lotto_id = l.id)))
  WHERE ((e.stato_esecuzione = 'ERRORE'::text) AND (l.stato_lotto = 'COMPLETATO'::text))
  GROUP BY l.id, l.codice, l.stato_lotto, l.competenza_mese, l.emittente_soggetto_ruolo_id;
```


---
{% include-markdown "signature-core.md" %}
