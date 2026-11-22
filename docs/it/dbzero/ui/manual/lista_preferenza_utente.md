## 📘 Documentazione Concettuale – Tabella `ui.lista_preferenza_utente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista personalizzata
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — il preset di base e la sua data del contenuto
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — i codici che la preferenza cita
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — le misure «righe per pagina» ammesse
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — la gemella delle dashboard
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — legge la preferenza chiave per chiave
> * [ui.trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot) — scrive lo snapshot dal preset di base, a ogni salvataggio e a ogni «Ignora»
> * [ui.fn_preset_aggiornato](/dbzero/ui/funzioni/fn_preset_aggiornato) — le chiavi del banner
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — la forma della configurazione e la misura di pagina, alla scrittura
> * [ui.fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione) — la regola di forma
> * [ui.fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista) — l'ordinamento di partenza, che la preferenza non porta
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — la personalizzazione dell'operatore

---

### 🎯 Scopo Principale

`ui.lista_preferenza_utente` conserva la personalizzazione di una lista fatta da un utente: le
colonne e le righe per pagina che ha scelto. Una riga per coppia (utente, lista); ciò che l'utente
non ha scelto segue lo standard.

---

### ⭐ Una chiave assente vuol dire «come lo standard»

`configurazione` porta solo le chiavi che l'utente ha scelto, fra `colonne` e
`pagina_dimensione`. Il resolver le legge una per una: una chiave presente prevale sul preset, una
chiave assente viene dal preset di base o dal catalogo. Così un cambio del preset arriva anche a chi
ha personalizzato altro.

⛔ L'ordinamento e i filtri non si salvano. Il clic sull'intestazione di una colonna vale per la
sessione, e la lista riparte dall'ordinamento del preset
([fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista)); i filtri di partenza sono
dell'interfaccia di ogni lista.

Chi salva rimanda solo le chiavi che il resolver dice di origine `preferenza`, più quella appena
toccata: rimandare la configurazione risolta per intero trasformerebbe in «scelta» una copia del
preset, e la congelerebbe. Una preferenza senza chiavi non si salva: si cancella, e l'utente torna
allo standard. Le due regole le applica il servizio, non il database.

Le colonne sono citate per **codice**, non per id: una colonna spenta o tolta dal catalogo sparisce
dalla lista risolta senza errore.

---

### Lo snapshot del preset di base e il banner «preset aggiornato»

Al salvataggio il servizio scrive in `preset_base_id` il preset di base che il resolver gli ha dato
(`preset_base`). Lo snapshot `preset_base_contenuto_aggiornato_il` lo scrive il database: il
trigger [trgfn_preferenza_preset_base_snapshot](/dbzero/ui/funzioni/trgfn_preferenza_preset_base_snapshot)
copia la data del contenuto del preset, una per chiave (`{chiave: data}`), a ogni scrittura che
nomina la base o lo snapshot, e il valore mandato dal servizio non conta. Se poi il preset cambia
una chiave che la preferenza imposta, il resolver la mette in `preset_aggiornato_chiavi` e accende
`preset_aggiornato`: il frontend propone di vedere le novità. Una chiave che la preferenza non
imposta la segue già dal preset, e non accende niente.

«Non mostrarmelo più» è una scrittura che nomina `preset_base_id`, anche con lo stesso valore: lo
snapshot si riallinea e il banner si spegne, finché il preset non cambia di nuovo. Se la base
salvata non è più la base di oggi (spenta, cancellata o scavalcata), il resolver non accende
`preset_aggiornato` ma `preset_base_cambiato`, che propone il riallineamento. Il preset cancellato
porta `preset_base_id` a nessuno (`ON DELETE SET NULL`) e lo snapshot torna vuoto.

---

### Che cosa il database controlla

* **La forma di `configurazione`**, alla nascita e a ogni modifica che la cambia: il guard
  [trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma), con la regola di
  [fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione). Un oggetto con
  le sole chiavi `colonne` e `pagina_dimensione`, nessuna a null; `colonne` un elenco di voci con le
  sole chiavi `codice`, `ordine`, `larghezza`, `visibile`, `fissata`. Solo il codice è obbligatorio,
  e un campo che manca prende il default della colonna; nessun campo è null. Il codice è di una
  colonna della lista, anche spenta, e non si ripete; ordine e larghezza sono interi positivi,
  visibilità e fissaggio vero o falso. La configurazione vuota è ammessa: segue il preset in tutto.
* `pagina_dimensione`, se c'è, è un intero del catalogo
  [misure_pagina](/dbzero/ui/tabelle/misure_pagina), giudicato dallo stesso guard. Una preferenza
  salvata con una misura poi uscita dal catalogo non rompe la lettura: la lista risponde lo standard.
* **Ciò che esce dal catalogo esce anche dalla preferenza.** Tolta una misura dal catalogo, la chiave
  `pagina_dimensione` esce dalle preferenze che la citano
  ([trgfn_misure_pagina_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_misure_pagina_ritira_dalle_preferenze));
  cancellata una colonna, la sua voce esce dalle preferenze della lista
  ([trgfn_voce_ritira_dalle_preferenze](/dbzero/ui/funzioni/trgfn_voce_ritira_dalle_preferenze)), e se
  era l'unica la chiave `colonne` esce e segue il preset. Così una preferenza non resta mai con un
  valore che il guard rifiuterebbe al salvataggio successivo.
* Una scrittura che riscrive la configurazione uguale (chiudere il banner, riallinearsi alla base)
  passa senza giudizio.
* Una riga scritta senza passare dal guard non rende la lista inapribile: il resolver salta le voci
  che non riconosce e dà il default ai campi che non legge.
* Una preferenza per utente e lista (`uq_ui_lista_preferenza_utente_user_lista`).
* Il preset di base è un preset **della stessa lista**: un vincolo composto lega la base alla lista
  della riga, e il preset di un'altra lista è rifiutato. Cancellato il preset, la preferenza resta, senza
  base e senza snapshot: le scelte dell'utente non si perdono, e ciò che non ha scelto viene dal nuovo
  preset di base.
* L'utente cancellato porta via le sue preferenze; la FK verso `django.auth_user` si aggiunge in
  coda all'installazione, perché la tabella la crea Django dopo Liquibase.

La preferenza è uno stato dell'utente, non un'entità con un ciclo di vita: non ha `attivo`, e le
FK verso lista e preset sono in eccezione alla regola ATTIVO, così una lista o un preset scelti da
qualcuno si spengono lo stesso. La preferenza di una lista spenta resta, e torna a valere se la
lista si riaccende.

Le date: `data_insert` ha il default, `data_update` la scrive il database a ogni INSERT e UPDATE
([trgfn_preferenza_data_update](/dbzero/ui/funzioni/trgfn_preferenza_data_update)); il valore mandato da
chi scrive non conta. **Senza audit, per scelta:** la preferenza è un dato personale, scritto solo
dall'utente della riga e spesso, e non ha `user_insert` né `user_update`.

---

### ⚠️ Che cosa oggi non copre

* **Una colonna spenta resta nella preferenza, finché la persona non salva.** Spegnere una colonna
  non la toglie dalla preferenza, e la lettura la salta; ma il salvataggio successivo rimanda le
  colonne che la lettura ha dato, senza quella spenta, e la voce si perde. Se la colonna si riaccende
  prima, la scelta torna a valere; dopo, la colonna rientra come nuova. Il database ritira la voce
  solo alla cancellazione.

---

### Codici errore

* `E_UI_CONFIGURAZIONE_FORMA` — la configurazione non ha la forma ammessa; il messaggio dice la
  chiave e il motivo.
* `E_UI_MISURA_PAGINA_NON_AMMESSA` — `pagina_dimensione` non intera o fuori catalogo.
* Dal servizio, non dal database: `E_UI_PREFERENZA_VALIDAZIONE` (forma del payload, preferenza
  vuota), `E_UI_PREFERENZA_NON_TROVATA` («Ignora» senza una preferenza), `E_UI_LISTA_NON_TROVATA`.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — ogni forma rifiutata (le chiavi `filtri` e
  `ordinamento`, un campo a null, un codice di un'altra lista o ripetuto, un ordine scritto come
  stringa, un `visibile` non booleano, una radice che non è un oggetto), la configurazione vuota e la
  voce di una colonna spenta che passano, l'UPDATE che non cambia la configurazione su una riga
  malformata, il resolver che non cade su una riga scritta senza il guard.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — chiavi presenti e
  assenti; una chiave null rifiutata dal guard di forma.
* `db/pgtap/ui/test-fn-resolve-lista-config-preset-aggiornato-v1.sql` — snapshot, «Ignora» che
  riallinea, il cambio dopo che riaccende, base portata a nessuno.
* `db/pgtap/ui/test-fn-resolve-lista-config-cascata-per-chiave-v1.sql` — una preferenza di sole
  colonne non vede il banner quando cambia la misura del preset; lo vede, sulla chiave `colonne`,
  quando cambia la composizione.
* `db/pgtap/ui/test-fn-preset-di-base-v1.sql` — lo snapshot scritto dal database e non dal
  servizio; la base salvata diversa da quella di oggi (`preset_base_cambiato`).
* `db/pgtap/ui/test-fn-resolve-lista-config.sql` — la preferenza prevale sui preset.
* `db/pgtap/ui/test-misure-pagina-v1.sql` — la misura della preferenza nel catalogo.
* `db/pgtap/ui/test-ui-legami-preset-v1.sql` — il preset di base di un'altra lista rifiutato;
  cancellato il preset, la preferenza resta senza base.
* `db/pgtap/ui/test-ui-nell-ambito-v1.sql` — lo snapshot rinominato e per chiave, le FK in eccezione
  ATTIVO.

---

### Note di migrazione

* 2026-09-30 — la misura di pagina passa al catalogo delle misure, col guard sulla preferenza.
* 2026-11-01 — la preferenza vale chiave per chiave; le preferenze salvate prima, che copiavano
  ordinamento, filtri e misura del preset, sono state ripulite.
* 2026-11-08 — lo snapshot `preset_base_data_update` si rinomina
  `preset_base_contenuto_aggiornato_il` e confronta la data del contenuto del preset; le FK verso
  lista e preset entrano fra le eccezioni ATTIVO.
* 2026-11-20 — lo snapshot lo scrive il database, e il trigger `z90` che lo azzerava al cambio di
  base è tolto: azzerava anche lo snapshot nuovo portato dallo stesso salvataggio. Il resolver espone
  il preset di base da salvare (`preset_base`), e la copia della cascata nel servizio si ritira.
* 2026-11-20 — lo snapshot diventa per chiave (`{chiave: data}`, le righe esistenti portate a
  `max(snapshot, ignorato)` per ogni chiave, banner identico), e `preset_aggiornato_ignored_at` si
  ritira: «Ignora» è riscrivere `preset_base_id`.
* 2026-11-21 — `ordinamento` e `filtri` escono dalla configurazione e dallo snapshot: le preferenze
  esistenti le hanno perse. La forma della configurazione la giudica il database, col guard di forma
  che prende il posto di quello della sola misura; le righe esistenti sono state portate in forma
  (via chiavi e voci estranee, voci con un codice che non è della lista, ripetizioni, campi di tipo
  sbagliato).
* 2026-11-21 — il preset di base è legato alla lista della riga da un vincolo composto; le preferenze
  con la base di un'altra lista sono tornate senza base. Prima il resolver la trattava come una base che
  non è quella di oggi.
* 2026-11-21 — `data_update` la scrive il database, ed è sempre valorizzata: le righe senza hanno preso
  `data_insert`.
* 2026-11-22 — la colonna cancellata esce dalle preferenze della lista: prima la preferenza restava con
  il codice, e il guard di forma ne rifiutava ogni salvataggio.

---

{% include-markdown "signature-core.md" %}
