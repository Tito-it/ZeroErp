## 📘 Documentazione Concettuale – Tabella `pratiche.pratiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il tipo della pratica
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — l'edizione di workflow che la pratica tiene per sempre
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — gli step istanziati della pratica
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — la storia della pratica
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) · [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche) · [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche) — stato, priorità e canale d'origine
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il cliente a grana fine
>
> Approfondimento funzioni:
>
> * [pratiche.fn_lista_pratiche_per_contesto](/dbzero/pratiche/funzioni/fn_lista_pratiche_per_contesto) — la lettura per contesto anagrafico
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — genera una pratica figlia da un flusso
> * [pratiche.trgfn_pratiche_default_definizione](/dbzero/pratiche/funzioni/trgfn_pratiche_default_definizione) · [pratiche.trgfn_pratiche_guard_pin_immutabile](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_pin_immutabile) — il pin dell'edizione
> * [pratiche.trgfn_pratiche_guard_contesto](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_contesto) — la coerenza del contesto anagrafico
> * [pratiche.trgfn_pratiche_guard_chiusura_flussi](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_chiusura_flussi) — quando una pratica si può chiudere
>
> Guide:
>
> * [Gestione pratiche](/guide/gestione-pratiche) — il modulo, dal punto di vista di chi lo usa

---

### 🎯 Scopo Principale

La tabella `pratiche.pratiche` è l'entità principale del modulo pratiche: una pratica operativa col suo
ciclo di vita, il tipo, lo stato, la priorità, l'assegnazione, il contesto anagrafico e la genealogia.

---

### Il tipo e l'edizione di workflow

* Il **tipo di prestazione** determina gli step di template disponibili.
* ⭐ **La pratica pinna l'edizione di workflow alla nascita** (`definizione_id`) e la tiene per sempre:
  `pratiche.trgfn_pratiche_default_definizione` la risolve all'inserimento (l'edizione pubblicata
  dell'emittente, altrimenti il preset), `pratiche.trgfn_pratiche_guard_pin_immutabile` ne impedisce
  la modifica. Le modifiche successive alle definizioni non cambiano il percorso delle pratiche in
  volo.
* La FK verso l'edizione è composita con il tipo di prestazione: un'edizione di un altro tipo non si
  può nemmeno scrivere.

---

### Lo stato

Gli stati sono `BOZZA`, `APERTA`, `SOSPESA`, `CHIUSA` e `ANNULLATA`, e le transizioni ammesse le
governa il catalogo delle transizioni. La chiusura è inoltre vincolata al lavoro rimasto: una pratica
non si chiude finché ha step obbligatori ancora percorribili e non completati, o flussi avviati e non
terminati; il ramo morto di un bivio non blocca. `data_apertura` si valorizza quando la pratica entra
in `APERTA`. La sospensione dell'intera pratica passa da `pratiche.sospensioni`.

---

### Il contesto anagrafico: di chi parla la pratica

Il contesto ha due rami, entrambi appesi al soggetto (`soggetto_id`):

* **il ruolo** (`soggetto_ruolo_id`): la pratica parla di un soggetto in un suo ruolo;
* **l'istanza** (`istanza_utility_id`): la pratica parla di una fornitura, indipendentemente dal ruolo
  (un prospect senza ruolo cliente è ammesso).

Con il soggetto vuoto la pratica è interna. Le combinazioni danno le lenti canoniche (ruolo, istanza,
soggetto, interna), che `pratiche.fn_lista_pratiche_per_contesto` legge; la coerenza fra soggetto,
ruolo, istanza e billing account la garantisce `pratiche.trgfn_pratiche_guard_contesto`.

**Il cliente a grana fine** è `billing_account_id`: un ruolo cliente ha un billing account per ogni
coppia istanza/utility, e il solo ruolo non dice di quale fornitura parla la pratica. Per gli altri
ruoli (fornitori, vettori…) il ruolo basta.

* Il billing account resta vuoto per le pratiche di fornitori e altri ruoli, per le pratiche interne e
  per quelle nate prima dell'istanza (l'allaccio che nasce da una pratica).
* Con un billing account serve l'istanza (`chk_pratiche_ba_con_istanza`), e il billing account deve
  essere di quell'istanza (FK composita) e del ruolo della pratica (guard del contesto).
* La pratica nata da un preventivo prende il billing account del preventivo; quella generata da un
  flusso lo copia dalla madre.

---

### L'assegnazione

La risorsa umana e l'unità organizzativa dicono chi lavora la pratica. Sono ortogonali al contesto: una
pratica interna è un contesto vuoto con un'assegnazione. Ogni cambio di assegnazione lascia la sua
riga nel giornale.

---

### La genealogia fra pratiche

`pratica_padre_id` e `flusso_origine_id` collegano una pratica generata alla pratica e al flusso che
l'hanno generata; li valorizza `pratiche.fn_genera_pratica_da_flusso`. Se la madre o il flusso
d'origine spariscono, il collegamento si svuota e la figlia resta.

⛔ **Un flusso non genera due figlie dello stesso tipo.** Un indice unico parziale su (flusso d'origine,
tipo di prestazione) impedisce il doppio figlio della generazione.

---

### Le altre colonne

* `emittente_fiscale_id` — l'identità fiscale che gestisce la pratica: è il perimetro di visibilità
  della riga (RLS per emittente).
* `canale_origine_id` — il canale esterno da cui è arrivata la richiesta; vuoto per una pratica creata
  internamente.
* `codice` — generato all'inserimento quando chi crea la pratica non lo fornisce.
* `data_scadenza` — la scadenza prevista.

Le colonne standard di audit, transazione e storico le arma il framework delle automazioni; la
tabella è storicizzata.

---

### Note di migrazione

* 2026-06-11 — `pratica_padre_id` e `flusso_origine_id` si valorizzano per le pratiche generate da un
  flusso.
* 2026-07-02 — arriva il pin dell'edizione di workflow, obbligatorio
  (brief-db-step-dominio-e-definizioni-versionate).
* 2026-10-08 — arriva `billing_account_id`, il cliente a grana fine (brief-db-istanza-nasce-col-ba).

---

{% include-markdown "signature-core.md" %}
