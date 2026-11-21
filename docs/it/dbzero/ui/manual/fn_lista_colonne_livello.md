## 📘 Documentazione Concettuale – Funzione `ui.fn_lista_colonne_livello`

> **Ultimo aggiornamento**: 18 novembre 2026
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
   Senza veste, sotto tutte le vesti dell'utente.
2. Se più profili danno un permesso sulla stessa colonna, vince il più specifico (AD_HOC, poi
   REPARTO, poi PORTALE); a parità il più restrittivo.
3. Senza permesso, una colonna sensibile è `BLOCCATO` e le altre `TUTTO`.

Senza utente, o con un utente senza profili, non vale nessun permesso e restano i livelli di
ripiego: le colonne sensibili sono bloccate.

L'azienda non entra: i permessi di colonna sono per profilo d'accesso.

---

### Una riga per ogni colonna accesa, anche bloccata

Il filtro lo fa chi legge, perché ognuno ne fa una cosa diversa: la configurazione della schermata
toglie le colonne bloccate e spegne l'export su quelle in `LETTURA`, la ricerca libera toglie le
bloccate. Il risolutore dei profili si chiama una volta, qualunque sia il numero delle colonne.

---

### ⚠️ Che cosa oggi non copre

* **Senza veste la regola mescola le vesti.** Con la veste `NULL` i profili di tutte le identità
  dell'utente concorrono insieme, e il più specifico di un'identità batte il più restrittivo di
  un'altra: un AD_HOC `TUTTO` dell'identità di portale scavalca un REPARTO `BLOCCATO`
  dell'operatore. I due chiamanti passano `NULL` quando la variabile di sessione manca o non è una
  veste.
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

Nessun test chiama la funzione direttamente, né costruisce il caso della veste `NULL` con due
identità.

---

### Note di migrazione

* 2026-09-23 — nasce dai passi del risolutore della configurazione che calcolavano il livello, quando
  la ricerca libera è diventata il secondo lettore.

---

{% include-markdown "signature-core.md" %}
