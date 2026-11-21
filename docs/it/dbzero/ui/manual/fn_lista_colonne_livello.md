## 📘 Documentazione Concettuale – Funzione `ui.fn_lista_colonne_livello`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna) — le colonne e il loro `sensibile`
> * [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso) — i permessi per profilo
>
> Approfondimento funzioni:
>
> * [script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) — i profili dell'utente sotto una veste, con la priorità
> * [ui.fn_veste_corrente](/dbzero/ui/funzioni/fn_veste_corrente) — la veste della sessione, che i chiamanti passano qui
> * [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config) — primo lettore: quali colonne mostrare
> * [ui.fn_lista_colonne_ricerca_full](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full) — secondo lettore: in quali colonne cercare
>
> Guide:
>
> * [Configurazione delle liste](/guide/configurazione-liste) — chi vede cosa

---

### 🎯 Scopo Principale

La funzione calcola, per ogni colonna accesa di una lista, il livello con cui un utente la vede
sotto una veste: `TUTTO`, `LETTURA` o `BLOCCATO`. È la sede unica della regola dei permessi di
colonna, letta dalla configurazione della schermata e dalla ricerca libera: due calcoli separati
prima o poi darebbero due risposte, e la ricerca troverebbe righe per il valore di una colonna che
la lista non mostra.

---

### La regola

1. I permessi si cercano fra i profili d'accesso che si applicano all'utente sotto la veste data.
2. Se più profili danno un permesso sulla stessa colonna, vince il più specifico (AD_HOC, poi
   REPARTO, poi PORTALE); a parità il più restrittivo.
3. Senza permesso, una colonna sensibile è `BLOCCATO` e le altre `TUTTO`.

⭐ **Senza veste il ripiego non allarga mai.** Con la veste `NULL` (i due chiamanti la passano quando
la variabile di sessione manca o non è una veste) la regola si applica sotto **ciascuna** veste
utilizzabile dell'utente ([fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile)),
e per ogni colonna vale il livello **più restrittivo** fra le vesti. Un permesso AD_HOC `TUTTO`
dell'identità di portale non scavalca più un REPARTO `BLOCCATO` dell'operatore, né il ripiego
`BLOCCATO` di una colonna sensibile sotto una veste che non ha permessi: anche quella veste conta,
perché saltarla allargherebbe.

Senza utente, o con un utente senza vesti né profili, non vale nessun permesso e restano i livelli
di ripiego: le colonne sensibili sono bloccate.

L'azienda non entra: i permessi di colonna sono per profilo d'accesso.

---

### Una riga per ogni colonna accesa, anche bloccata

Il filtro lo fa chi legge, perché ognuno ne fa una cosa diversa: la configurazione della schermata
toglie le colonne bloccate e spegne l'export su quelle in `LETTURA`, la ricerca libera toglie le
bloccate. Il risolutore dei profili si chiama una volta, qualunque sia il numero delle colonne.

---

### ⚠️ Che cosa oggi non copre

* **La lista non si verifica**: un `id` inesistente o di una lista spenta dà le colonne che trova, o
  nessuna. La funzione è un mattone: la lista la verificano i chiamanti, con `fn_lista_da_codice`.

---

### Codici errore

Nessuno: la funzione non rifiuta.

---

### Test

* `db/pgtap/ui/test-fn-lista-colonne-ricerca-full-v1.sql` — attraverso la ricerca libera: colonna
  sensibile con e senza permesso, `BLOCCATO`, `LETTURA`, il più specifico che batte il più
  restrittivo, la veste letta dalla sessione, l'utente assente; la stessa decisione del risolutore
  della configurazione.

* `db/pgtap/ui/test-ui-catalogo-liste-v1.sql` — la chiama direttamente: un operatore con una
  seconda veste di portale e un permesso `TUTTO` su quella; con la veste `NULL` la colonna sensibile
  resta `BLOCCATO`, sotto la veste del permesso è `TUTTO`.

---

### Note di migrazione

* 2026-09-23 — nasce dai passi del risolutore della configurazione che calcolavano il livello, quando
  la ricerca libera è diventata il secondo lettore.
* 2026-11-21 — con la veste `NULL` vale il livello più restrittivo fra le vesti utilizzabili
  dell'utente, non più il profilo più specifico fra tutte.

---

{% include-markdown "signature-core.md" %}
