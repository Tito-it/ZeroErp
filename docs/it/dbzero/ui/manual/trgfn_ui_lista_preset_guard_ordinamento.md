## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_ui_lista_preset_guard_ordinamento`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_preset](/dbzero/ui/tabelle/lista_preset) — la tabella su cui il guard è montato
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — i codici che l'ordinamento può citare
>
> Approfondimento funzioni:
>
> * [ui.fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista) — l'ordinamento risolto per l'utente
> * [ui.trgfn_ui_lista_preset_guard_pagina_dimensione](/dbzero/ui/funzioni/trgfn_ui_lista_preset_guard_pagina_dimensione) — l'altro guard del preset, sulla misura
>
> Guide:
>
> * [Configurazione liste](/guide/configurazione-liste) — l'ordinamento di partenza

---

### 🎯 Scopo Principale

`ui.trgfn_ui_lista_preset_guard_ordinamento` fa sì che l'ordinamento di partenza di un preset di lista
abbia la forma ammessa: un elenco di colonne della lista, ciascuna con la sua direzione. Rifiuta la
scrittura che non la rispetta.

---

### La forma dell'ordinamento

* Nessun ordinamento passa: il preset non dice da che colonna partire.
* Altrimenti è un elenco di voci, ognuna con due sole informazioni: la colonna e la direzione
  (crescente o decrescente).
* La colonna si cita col **codice** della colonna della lista, la stessa chiave con cui la citano le
  voci della composizione. Vale il codice di una colonna in qualsiasi stato, anche spenta: se torna,
  l'ordinamento torna con lei.
* La stessa colonna non compare due volte.

⛔ Il campo sorgente al posto del codice si rifiuta: nessuno lo traduce. Chi scrive l'ordinamento manda
il codice; il campo con cui il backend ordina lo legge poi
[fn_ordinamento_lista](/dbzero/ui/funzioni/fn_ordinamento_lista).

---

### ⭐ È la sola sede della forma

La preferenza dell'utente non porta l'ordinamento: il clic sull'intestazione di una colonna vale per la
sessione. L'unico ordinamento salvato è quello del preset, e la sua forma è scritta solo qui. Che
l'utente possa davvero ordinare per quella colonna (accesa, ordinabile, non bloccata per lui) lo decide
la lettura, non la scrittura.

Un UPDATE che non cambia né l'ordinamento né la lista passa senza giudizio: il seed riscrive le righe
uguali a ogni giro.

---

### Codici errore

* `E_UI_CONFIGURAZIONE_FORMA` — l'ordinamento non ha la forma ammessa; il campo è
  `ordinamento_default`, e il motivo è nel messaggio. È lo stesso codice del guard di forma delle
  preferenze.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — un campo sorgente al posto del codice, una
  direzione fuori dominio e una colonna ripetuta rifiutati; l'ordinamento riscritto uguale che passa.

---

### Note di migrazione

* 2026-11-21 — nasce. Prima l'ordinamento passava così com'era scritto, e nel seed usava due convenzioni
  (il codice della colonna o il campo sorgente): gli ordinamenti esistenti sono stati portati al codice,
  e le voci che non dicevano una colonna sola sono state tolte.

---

{% include-markdown "signature-core.md" %}
