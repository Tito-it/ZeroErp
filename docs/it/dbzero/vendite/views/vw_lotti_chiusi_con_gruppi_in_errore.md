# 🔍 View `vw_lotti_chiusi_con_gruppi_in_errore`

> 📝 **Descrizione**
>
> PRESIDIO. Elenca una contraddizione: un lotto chiuso COMPLETATO che contiene documenti dichiarati in ERRORE. Sono due affermazioni che non possono stare insieme — o il giro e' andato bene, o quei documenti non erano suoi. DEVE RESTARE VUOTA. ⭐ Nasce dalla decisione del 2026-09-06 di non sollevare piu' quando falliscono TUTTE le commesse di un giro: senza l'eccezione lo stato finale del lotto lo decide il verdetto `fermo`, e con tutte le commesse fallite le fatture NON NASCONO. Il 2026-09-12 e' successo davvero (LTF-0010972: un rilancio ha scritto COMPLETATO con due documenti in ERRORE, perche' il verdetto del runner non contava ancora gli esiti). ⭐ Rev 2026-09-07: legge vendite.fatturazione_lotti_esiti, quindi vede anche i lotti SENZA perimetro (i giri di massa). ⭐ Rev 2026-09-23 — LE DUE PORTE. (1) La transizione verso COMPLETATO su un lotto fermo e' rifiutata dal database (trg_fatturazione_lotti_a10_guard_completato_upd). (2) Resta aperta quella dell'ESITO: un documento marcato ERRORE su un lotto GIA' COMPLETATO produce la stessa contraddizione senza toccare stato_lotto — ed e' cio' che questa vista continua a sorvegliare. ⭐ Rev 2026-09-23 — L'INVARIANTE TORNA VUOTA, E IL PREGRESSO E' CHIUSO. Dal 2026-09-07 era «nessuna riga non dichiarata»: sei lotti annullati prima di quel giorno portavano stato_lotto = COMPLETATO scritto dal vecchio annullo, con un gruppo in ERRORE. Decisione di Tid del 2026-09-23: un lotto annullato e' VUOTO — l'annullo chiude i suoi esiti come chiude fatture e task run (fn_annulla_lotto_da_draft, rev 2026-09-23), e i lotti gia' annullati sono stati allineati allo stesso modo. Quei lotti non compaiono piu' perche' non hanno piu' documenti in ERRORE, non perche' un filtro li nasconda: la vista NON esclude gli annullati, e non deve. ⚠️ La falsificazione di stato_lotto su undici lotti (brief-db-esito-gruppo-lotto §25) resta un fatto e non e' stata corretta (decisione del 07-09): l'elenco si chiede allo storico. Lettore a catalogo: dbops.vw_lotti_chiusi_con_errori_da_guardare. Brief: brief-db-esito-gruppo-lotto §15, §24, §25; brief-db-annullamento-chiude-la-vita §9.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

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

</div>


---
{% include-markdown "signature-core.md" %}
