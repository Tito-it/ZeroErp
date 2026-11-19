## 📘 Documentazione Concettuale – Funzione `ui.fn_resolve_lista_config`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista, la soglia di ricerca, le dichiarazioni sull'emittente
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — il catalogo delle colonne
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — i preset fra cui si sceglie la base
> * [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna) — le colonne del preset di base
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — la preferenza dell'utente
> * [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso) — i permessi di colonna
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — le misure «righe per pagina»
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la riga della lista dal codice
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili dell'utente, con la loro priorità
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello di ogni colonna per l'utente
> * [ui.fn_misura_pagina_ammessa](/dbzero/ui/funzioni/fn_misura_pagina_ammessa) — una misura è del catalogo?
> * [ui.fn_misura_pagina_default](/dbzero/ui/funzioni/fn_misura_pagina_default) — la misura di default `PAGINA`
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la gemella delle dashboard
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — la cascata vista dall'amministratore

---

### 🎯 Scopo Principale

`ui.fn_resolve_lista_config` risponde come si presenta una lista a un utente: quali colonne, in
che ordine e con che permessi, l'ordinamento, i filtri e le righe per pagina, e da dove viene
ciascuna di queste scelte. È l'unica sede della cascata preferenza → preset → catalogo; il backend
la chiama a ogni apertura di lista e passa il risultato al frontend.

---

### La lista e i profili dell'utente

La riga della lista la legge [fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice): una
lista che non c'è o è spenta dà `E_UI_LISTA_NON_TROVATA`. Dalla stessa riga vengono la soglia della
ricerca libera e le due dichiarazioni sull'emittente (se la lista sa dire l'emittente di ogni riga,
e se ha un perimetro di emittente), che il risultato ripete così come sono.

I profili dell'utente li dà
[fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili)
per la veste della sessione ([fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente)); senza una
veste valida, per tutte le vesti dell'utente. Ogni profilo ha una priorità: ad hoc, poi reparto,
poi portale.

---

### ⭐ La cascata è per chiave

Le quattro chiavi (`colonne`, `ordinamento`, `filtri`, `pagina_dimensione`) si risolvono ognuna per
conto suo, dal primo di questi livelli che la contiene:

1. **la preferenza dell'utente**, se ha quella chiave (una chiave null vale come assente);
2. **il preset di base**;
3. **il catalogo**: tutte le colonne accese, visibili, con l'identificatore fissato; nessun
   ordinamento, nessun filtro, la misura di default `PAGINA`.

Il preset di base si cerca sempre, anche quando c'è una preferenza: dà le chiavi che la
preferenza non ha. È un preset di default e acceso della lista, scelto così:

* il preset di ruolo del profilo con la priorità migliore fra quelli che hanno un preset di
  default per la lista;
* se quel preset non ha colonne accese, o non c'è, il preset dell'azienda passata dal chiamante
  (solo se il chiamante ne passa una);
* se nemmeno quello ha colonne accese, o non c'è, il preset di sistema.

Un preset conta come base solo se ha almeno una colonna accesa, e una volta scelto dà tutte e
quattro le chiavi.

```mermaid
flowchart TD
    P[Preferenza: la chiave c'è?] -->|sì| PR[valore della preferenza]
    P -->|no| B{Preset di base trovato?}
    B -->|sì| BV[valore del preset di base]
    B -->|no| C[valore del catalogo]
    subgraph Scelta del preset di base
      R[ruolo, profilo più prioritario] -->|senza colonne accese| E[azienda del chiamante]
      E -->|senza colonne accese| S[sistema]
    end
```

---

### Le righe per pagina e lo standard

Per `pagina_dimensione` vale solo una misura del catalogo. Lo **standard** è la misura del preset
di base se è nel catalogo, altrimenti il default `PAGINA`. Risponde la misura della preferenza se
è nel catalogo, altrimenti lo standard. Il risultato porta anche lo standard da solo, perché il
frontend lo mostra come «come lo standard (N)». La misura che risponde non è mai vuota.

---

### L'origine di ogni chiave

Per ognuna delle quattro chiavi il risultato dice da dove viene: `preferenza`, l'ambito del preset
di base (`ruolo`, `emittente_fiscale`, `sistema`) o `catalogo`. Il frontend, al salvataggio,
rimanda solo le chiavi di origine `preferenza` più quella toccata: così salvare una chiave non
congela le altre. Una misura della preferenza fuori catalogo non ha origine `preferenza`, e quindi
non si rimanda.

---

### Le colonne nuove del catalogo

Sulle colonne risolte, da qualunque livello vengano, il resolver aggiunge in coda le colonne
accese del catalogo che mancano, **nascoste**, dopo tutte le altre. Il contatore `colonne_nuove`
dice quante sono, contate **dopo** il filtro dei permessi: annuncia solo colonne che l'utente può
davvero trovare nel pannello.

---

### Normalizzazione e permessi di colonna

Ogni colonna risolta che non è accesa nel catalogo della lista si scarta. Sulle altre:

* una colonna identificatore o azione è sempre visibile, e un identificatore è sempre fissato;
* il livello dell'utente lo dà [fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello),
  la stessa sede che usa la ricerca libera: `BLOCCATO` toglie la colonna, `LETTURA` la rende non
  esportabile, `TUTTO` la lascia com'è;
* tipo, etichetta i18n, esportabilità e la priorità di ritiro si leggono sempre freschi dal
  catalogo, mai dalla preferenza o dal preset.

Ordine, larghezza, visibilità e fissaggio vengono dal livello che ha dato le colonne.

---

### Il flag «preset aggiornato»

Se la preferenza ha un preset di base e uno snapshot, il resolver legge la data del contenuto
**di quel preset** e accende `preset_aggiornato` quando è più recente dello snapshot e l'utente
non ha premuto «ignora» dopo quell'ultimo cambio. Senza preferenza, senza base o senza snapshot il
flag è spento.

---

### ⚠️ Che cosa oggi non copre

* **Il ruolo dopo il primo.** Fra i preset di ruolo guarda solo quello del profilo più
  prioritario: se non ha colonne accese passa all'azienda, anche se un profilo successivo ha un
  preset di ruolo completo.
* **La parità di priorità.** Senza una veste valida due profili possono avere la stessa priorità
  (due portali), e la scelta del preset di ruolo fra i due non è determinata.
* **Un preset senza colonne dà le altre chiavi.** Se nessun preset ha colonne accese, le colonne
  vengono dal catalogo, ma ordinamento, filtri e misura vengono dal preset dell'ultimo livello
  cercato, se lì un preset di default c'è, e l'origine di quelle chiavi dice quell'ambito.
* **Ordinamento e filtri non filtrati.** Passano così come sono, dalla preferenza o dal preset:
  possono nominare colonne spente, non ordinabili, non filtrabili o bloccate per l'utente.
* **La forma della preferenza.** Una voce di colonna con un ordine o una larghezza non interi
  ferma la funzione con un errore di conversione, e la lista non si apre per quell'utente; una voce
  senza visibilità esce con la visibilità vuota; un codice ripetuto esce due volte. Una preferenza
  di colonne i cui codici sono tutti spariti lascia visibili solo identificatore e azioni.
* **Il preset di base non è nel risultato.** Il backend lo ricalcola da sé per salvarlo nella
  preferenza, con una cascata che non scarta i preset senza colonne accese: la base salvata può
  essere diversa da quella usata qui.
* **Il flag guarda il preset salvato, non quello vero.** Si calcola sul preset scritto nella
  preferenza anche se è spento o non è più la base, e su tutto il contenuto del preset anche
  quando la preferenza segue già il preset per le chiavi cambiate.
* **La regola del 2.** La lettura del preset (colonne, ordinamento, filtri, misura) è scritta tre
  volte, una per ambito; la cascata e il flag sono ricopiati in
  [fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) e nel backend.

---

### Codici errore

* `E_UI_LISTA_NON_TROVATA` — lista inesistente o spenta (dal building block della lista).
* `E_UI_MISURA_PAGINA_DEFAULT_MANCANTE` — il catalogo delle misure non ha il default `PAGINA`.

---

### Test

* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — lista inesistente, catalogo, preset di sistema e
  di profilo, preferenza, colonna sensibile con e senza grant, identificatore normalizzato, colonna
  nuova, priorità dei profili, veste, priorità di ritiro.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — la cascata per chiave,
  l'origine, la misura standard, la lista senza preset.
* `db/pgtap/ui/test-fn-resolve-lista-config-contatore-colonne-nuove-v1.sql` — il contatore dopo il
  filtro dei permessi.
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — il flag.
* `db/pgtap/ui/test-misure-pagina-v1.sql` — la misura sempre del catalogo.
* `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql`,
  `db/pgtap/ui/test-lista-definizione-multi-emittente-v1.sql`,
  `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` — le proprietà della lista nel
  risultato.
* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — la stessa regola di livello della
  ricerca libera.
* `db/pgtap/ui/test-lista-contratti-seed.sql` — una lista del seed risolta.

---

### Note di migrazione

* 2026-09-23 — veste e livello di colonna passano a due building block condivisi con la ricerca
  libera.
* 2026-09-25 — la riga della lista dal building block; nel risultato la soglia della ricerca.
* 2026-09-30 — la misura di pagina dal catalogo delle misure: prima un 25 scritto nella funzione,
  e senza preferenza né preset poteva uscire vuota.
* 2026-11-01 — la cascata diventa per chiave; nel risultato l'origine e la misura standard. Prima
  si sceglieva un livello solo, il primo con le colonne, e se ne prendevano tutte e quattro le
  chiavi.
* 2026-11-08 — il flag legge la data del contenuto del preset, non più l'audit.

---

{% include-markdown "signature-core.md" %}
