## 📘 Documentazione Concettuale – Funzione `ui.fn_lista_da_codice`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — il catalogo delle liste
>
> Approfondimento funzioni:
>
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — legge da qui la lista, i due contrassegni dell'azienda e la soglia
> * [ui.fn_lista_colonne_ricerca_full](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full) — legge da qui la lista della ricerca libera
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — liste attive e spente

---

### 🎯 Scopo Principale

La funzione restituisce la riga di una lista configurabile dato il suo codice, se la lista esiste ed
è accesa; altrimenti rifiuta con `E_UI_LISTA_NON_TROVATA`. È la sede unica della regola «lista
assente o spenta»: la configurazione della schermata, la ricerca libera del database e la soglia
della ricerca del backend passano tutte da qui.

---

### Assente e spenta sono la stessa risposta

Una lista che non esiste e una lista spenta danno lo stesso rifiuto, col codice nella frase: per chi
apre una schermata le due cose non si distinguono, e una lista spenta non deve rispondere con la
sua configurazione.

---

### Restituisce la riga intera

Il risultato ha la forma della tabella: chi la chiama prende i campi che gli servono (l'`id`, i due
contrassegni dell'azienda, la soglia della ricerca). Si legge come una tabella da cui scegliere le
colonne; chiamata come valore singolo, restituisce la riga in un campo solo.

---

### ⚠️ Che cosa oggi non copre

* **Due letture per codice nel backend non passano da qui.** Il repository della configurazione
  (l'`id` di una lista accesa) e il cancello del perimetro emittente (i due contrassegni) rileggono
  la tabella con la stessa condizione, scritta a mano: sono due copie della regola, che qui ha la
  sua sede. Rispondono «niente» invece di rifiutare, e la funzione non ha una forma che lo faccia.
* **Il codice si confronta così com'è**: maiuscole, minuscole e spazi contano, e un codice `NULL` dà
  il rifiuto con un codice vuoto nella frase.

---

### Codici errore

* `E_UI_LISTA_NON_TROVATA` — nessuna lista accesa con quel codice.

---

### Test

* `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` — la funzione esiste ed è STABLE; su liste
  costruite risponde la soglia dichiarata e quella di default; lista inesistente e lista spenta
  rifiutate, e lo stesso rifiuto arriva dalla configurazione e dalla ricerca libera.

---

### Note di migrazione

* 2026-09-25 — nasce, e prende il posto delle due copie della lettura per codice nella configurazione
  della schermata e nella ricerca libera.

---

{% include-markdown "signature-core.md" %}
