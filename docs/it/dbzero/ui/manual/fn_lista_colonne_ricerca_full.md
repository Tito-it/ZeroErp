## 📘 Documentazione Concettuale – Funzione `ui.fn_lista_colonne_ricerca_full`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — `ricercabile_full` e il campo sorgente
>
> Approfondimento funzioni:
>
> * [ui.fn_lista_da_codice](/dbzero/ui/funzioni/fn_lista_da_codice) — la lista dal codice, e il rifiuto se manca
> * [ui.fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello di ogni colonna per l'utente
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — la ricerca libera

---

### 🎯 Scopo Principale

La funzione dice in quali colonne di una lista l'utente della sessione può fare la ricerca libera, e
per ciascuna quale campo della vista interrogare. Il backend la legge a ogni ricerca: un
`ricercabile_full` cambiato dalla pagina tecnica vale subito, e una colonna che l'utente non vede
non entra mai nella ricerca.

---

### Quali colonne

Tutte quelle che rispettano insieme quattro condizioni:

* la colonna è accesa;
* `ricercabile_full` è acceso: è la scelta, fatta nel catalogo, di cercarci dentro;
* ha un campo sorgente, senza il quale non c'è niente da interrogare;
* il suo livello per l'utente non è `BLOCCATO`. `LETTURA` entra: spegne l'export, non la vista.

Il livello viene da [fn_lista_colonne_livello](/dbzero/ui/funzioni/fn_lista_colonne_livello), la
stessa sede da cui lo legge la configurazione della schermata: le due risposte coincidono per
costruzione. L'ordine è quello di partenza delle colonne, poi il codice.

---

### Utente e veste vengono dalla sessione

Non si passano: l'utente è quello del contesto di sessione, la veste quella di
[fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente), come li imposta l'autenticazione. Senza
utente in sessione (un comando, un job) nessun permesso si applica: le colonne sensibili escono, le
altre restano.

La configurazione della schermata invece riceve l'utente come argomento. Che i due coincidano lo
verifica il backend, che rifiuta la chiamata se il contesto di sessione è vuoto o di un altro utente
(`E_UI_CHIAMATA_NON_VALIDA`).

---

### ⚠️ Che cosa oggi non copre

* **Il campo sorgente non è sempre un campo della vista.** Su una lista senza vista non è verificato
  da niente; su un'azione non è verificato; un nome della lineage dei documenti è ammesso senza stare
  nella vista. La funzione lo restituisce comunque, e la ricerca interroga un campo che può non
  esserci.
* **Un utente di sessione che non è un numero** fa fallire la lettura con l'errore grezzo del cast,
  mentre la veste sbagliata ripiega in silenzio.
* **Il filtro sul campo sorgente accetta ancora anche la stringa vuota**, che il vincolo della
  colonna rifiuta da prima: è innocuo, e ripete il vincolo.

---

### Codici errore

* `E_UI_LISTA_NON_TROVATA` — lista assente o spenta, da `fn_lista_da_codice`.

---

### Test

* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — le quattro condizioni una per una, i due
  permessi in conflitto, `LETTURA` che entra, la stessa decisione del risolutore, la veste dalla
  sessione, l'utente assente, la lista inesistente.
* `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` — il rifiuto della lista inesistente arriva da
  `fn_lista_da_codice`.

---

### Note di migrazione

* 2026-09-23 — nasce, su richiesta del team backend, con i due building block del livello e della
  veste.
* 2026-09-25 — la lista dal codice la legge `fn_lista_da_codice`.

---

{% include-markdown "signature-core.md" %}
