## 📘 Documentazione Concettuale – Funzione `pratiche.fn_crea_pratica`

> 👀 **Vedi anche**
>
> Tabelle:
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
>
> Funzioni:
> [vendite.fn_genera_pratica_da_preventivo](/dbzero/vendite/funzioni/fn_genera_pratica_da_preventivo) (consumer)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> WIP:
> [Analisi e piano di fix — gestione transazioni backend](/dev/work-in-progress/analisi-fix-transazioni) (Classe A)

### 🎯 Scopo Principale

(latest review 08-07-2026)

La funzione **`pratiche.fn_crea_pratica`** è il **building block condiviso** per
la creazione di una pratica. La creazione è identica per ogni sorgente
(preventivo, ordine, futuri domini): risolve lo stato iniziale `APERTA` e la
priorità di default `NORMALE`, poi esegue l'`INSERT`.

Ogni **funzione madre di dominio** la chiama e vi aggiunge la sola parte
specifica (risoluzione contesto + link della propria sorgente). Così
l'atomicità di ogni dominio si ottiene **senza duplicare** la logica di
creazione pratica: si scrive una volta, si riusa.

---

### Firma

```sql
pratiche.fn_crea_pratica(
    p_emittente_fiscale_id pratiche.pratiche.emittente_fiscale_id%TYPE,
    p_tipo_prestazione_id  pratiche.pratiche.tipo_prestazione_id%TYPE,
    p_soggetto_id          pratiche.pratiche.soggetto_id%TYPE DEFAULT NULL,
    p_soggetto_ruolo_id    pratiche.pratiche.soggetto_ruolo_id%TYPE DEFAULT NULL,
    p_istanza_utility_id   pratiche.pratiche.istanza_utility_id%TYPE DEFAULT NULL,
    p_priorita_id          pratiche.pratiche.priorita_id%TYPE DEFAULT NULL,
    p_descrizione          pratiche.pratiche.descrizione%TYPE DEFAULT NULL,
    p_meta                 jsonb DEFAULT '{}'::jsonb
) RETURNS pratiche.pratiche.id%TYPE
```

### Guard di dominio (già trigger, applicati all'INSERT)

I guard sulla pratica **non** sono replicati nella funzione: sono trigger su
`pratiche.pratiche` e scattano all'INSERT — coerenza contesto
(`trgfn_pratiche_guard_contesto`), scope emittente, pin definizione
(`trgfn_pratiche_default_definizione`), parent attivi (emittente / tipo / stato
/ priorità / soggetto / UO / canale), audit, tx_id, gen_codice, giornale.

> ⚠️ **Guard pre/post-attivazione NON incluso.** Il controllo «tipo prestazione
> ammesso pre/post attivazione cliente» vive **solo** nel service Python
> (`pratiche_service.crea_pratica`, via `repo.ha_ba_attivo`): non esiste un
> trigger DB equivalente. Questa funzione **non** lo replica (nessuna
> regressione: non era in DB). I chiamanti che lo richiedono lo pre-verificano a
> monte.

### Note tecniche

* **`SECURITY INVOKER`**: RLS su `pratiche.pratiche` valutata come dal Python.
* Stato/priorità di default risolti per `codice_interno` (`APERTA`, `NORMALE`);
  se non configurati ⇒ **`E_CONFIG_MANCANTE`**.
