## 📘 Documentazione Concettuale – Tabella `pratiche.workflow_definizioni`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — l'identità di cui l'edizione è una variante
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — i passi dell'edizione
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — le pratiche legate all'edizione
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — l'emittente di un'edizione propria
>
> Approfondimento viste:
>
> * [pratiche.vw_definizioni_drift](/dbzero/pratiche/views/vw_definizioni_drift) — le edizioni il cui preset d'origine è andato avanti
>
> Approfondimento funzioni:
>
> * [pratiche.fn_risolvi_definizione](/dbzero/pratiche/funzioni/fn_risolvi_definizione) — quale edizione vale per un tipo e un emittente
> * [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) · [pratiche.fn_nuova_versione_definizione](/dbzero/pratiche/funzioni/fn_nuova_versione_definizione) · [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — i verbi del ciclo di vita
> * [pratiche.fn_copia_definizione](/dbzero/pratiche/funzioni/fn_copia_definizione) — il motore di copia dei verbi
> * [pratiche.trgfn_workflow_definizioni_guard](/dbzero/pratiche/funzioni/trgfn_workflow_definizioni_guard) — transizioni e testata immutabile
> * [pratiche.trgfn_tipi_prestazione_bootstrap_definizione](/dbzero/pratiche/funzioni/trgfn_tipi_prestazione_bootstrap_definizione) — il preset che nasce col tipo
> * [pratiche.trgfn_pratiche_default_definizione](/dbzero/pratiche/funzioni/trgfn_pratiche_default_definizione) · [pratiche.trgfn_template_flussi_default_definizione](/dbzero/pratiche/funzioni/trgfn_template_flussi_default_definizione) — l'edizione risolta alla nascita di pratica e passo
> * [pratiche.fn_check_definizione_struttura_bloccata](/dbzero/pratiche/funzioni/fn_check_definizione_struttura_bloccata) · [pratiche.fn_check_definizione_congelata](/dbzero/pratiche/funzioni/fn_check_definizione_congelata) — i due predicati dell'immutabilità

---

### 🎯 Scopo Principale

La tabella `pratiche.workflow_definizioni` contiene le edizioni versionate delle definizioni di
workflow: una riga è un'edizione del workflow di un tipo di prestazione per uno scope.

* `emittente_fiscale_id` vuoto: il **preset**, che vale per ogni emittente senza un'edizione propria;
* `emittente_fiscale_id` valorizzato: l'edizione propria di una società, il **fork**.

Il tipo di prestazione resta l'identità di reporting; le edizioni sono varianti e versioni del suo
workflow. Due società possono avere workflow diversi senza clonare il tipo, e una pratica aperta non
vede cambiare la sua roadmap quando cambia la definizione.

---

### Il ciclo di vita

* `BOZZA` — modificabile. Al più una bozza per scope: una sola edizione in lavorazione alla volta.
* `PUBBLICATA` — istanziabile, una sola per scope. La testata (tipo, emittente, versione, origine) non
  cambia più.
* `RITIRATA` — non più istanziabile; le pratiche già legate continuano sulla loro edizione.

Le transizioni ammesse sono solo `BOZZA` → `PUBBLICATA` e `PUBBLICATA` → `RITIRATA`.

---

### ⭐ La pratica fissa la sua edizione alla nascita

Ogni pratica risolve la propria edizione quando nasce (`pratiche.definizione_id`) e la tiene per
sempre. Ogni nuovo tipo di prestazione nasce col suo preset in versione 1 già pubblicato: la
risoluzione trova sempre un'edizione per un tipo appena creato.

---

### L'immutabilità della struttura

Per i fork emessi la struttura dei passi è protetta, con due assi:

* un fork pubblicato o ritirato non si modifica: ha pratiche legate alla sua versione;
* solo un fork pubblicato non si cancella: un ritirato resta cancellabile, per smantellare le edizioni
  storiche col percorso «ritira, poi cancella».

Il preset e le bozze restano modificabili. I guard dei passi e dei loro figli leggono i due predicati
`fn_check_definizione_struttura_bloccata` e `fn_check_definizione_congelata`.

---

### Le colonne che non si capiscono dal nome

* `versione` — progressivo per scope (tipo, emittente), positivo.
* `preset_origine_id` — da quale edizione è nato il fork; se quell'edizione viene cancellata, il
  riferimento si svuota.
* `versione_origine` — la versione del preset d'origine al momento del fork: con `preset_origine_id`
  dice se il preset è andato avanti dopo il fork (`pratiche.vw_definizioni_drift`).

---

### I vincoli

* Una versione è unica per (tipo, emittente), e il preset è uno scope come gli altri: due valori vuoti
  di emittente valgono come uguali. Lo stesso vale per i due indici parziali che ammettono al più una
  bozza e al più una pubblicata per scope; quello delle pubblicate è anche l'arbitro del conflitto con
  cui il trigger di nascita del tipo crea il preset.
* La coppia (id, tipo) è unica perché passi e pratiche la referenziano insieme: un figlio non può
  puntare a un'edizione di un altro tipo, per costruzione e senza trigger.
* ⭐ La cancellazione del tipo cancella le sue edizioni: l'edizione è un metadato del tipo e senza tipo
  non ha senso. La protezione vera è transitiva: passi e pratiche referenziano l'edizione senza
  cascata, quindi un tipo con figli vivi non si cancella comunque.
* Tipo ed emittente devono essere attivi.

---

### Codici errore

* `E_DEFINIZIONE_TRANSIZIONE_NON_AMMESSA` — un cambio di stato fuori dalle due transizioni ammesse.
* `E_DEFINIZIONE_PUBBLICATA_IMMUTABILE` — una modifica della testata fuori dalla bozza.

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — preset alla nascita del tipo, risoluzione alla nascita
  di passo e pratica, una sola pubblicata per scope, il vincolo composito (id, tipo).
* `pratiche/test-workflow-definizioni-fase1` — flusso coerente con l'edizione, edizione della pratica
  immutabile, generazione verso un'edizione senza il passo.
* `pratiche/test-workflow-definizioni-fase2` e `-fase2b` — fork, nuova versione, pubblicazione e
  immutabilità della struttura.
* `pratiche/test-definizione-bozza-unica` e `pratiche/test-definizione-ritirata-edit-freeze` — la bozza
  unica per scope e la ritirata bloccata ma cancellabile.

---

### Note di migrazione

* 2026-07-02 — nasce col modello «edizioni + fork»: prima le definizioni erano globali e le pratiche non
  fissavano nessuna edizione (brief-db-step-dominio-e-definizioni-versionate).
* 2026-07-04 — al più una bozza per scope, e la ritirata bloccata alla modifica ma cancellabile
  (brief-db-accesso-write-editing-bozza).

---

{% include-markdown "signature-core.md" %}
