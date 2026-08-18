## 📘 Documentazione Concettuale – Funzione Trigger `anagrafiche.trgfn_billing_account_guard_albero_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)

---
### 🎯 Scopo Principale
(latest review 18-08-26)

Fa scattare il controllo dell'albero omogeneo quando qualcuno **imposta o cambia
il genitore** di un billing account.

---

### Contesto di Esecuzione

* **Tipo**: trigger `AFTER INSERT OR UPDATE OF parent_account_id`
* **Fascia**: `z95`

---

### Perche' `AFTER` e perche' `z95`, contro la convenzione

La convenzione di casa vuole i controlli in fascia `a10`, cioe' **prima** della
scrittura. Qui non si puo', e la ragione e' concreta.

**L'emittente di un billing account non esiste finche' non esiste la sua riga di
assegnazione** — e quella riga la crea un altro trigger, subito **dopo**
l'inserimento. Un controllo che girasse prima leggerebbe il **gestore globale**
al posto dell'emittente vero, e rifiuterebbe ogni albero creato da un operatore
il cui emittente non e' quello predefinito.

L'alternativa sarebbe replicare qui la logica che assegna l'emittente: cioe'
avere **due** risolutori. Che e' esattamente cio' che il progetto evita, perche'
il giorno in cui divergono il controllo dichiara sano un albero che la
fatturazione spacca.

Il nome in fascia `z95` serve a farlo scattare **dopo** il trigger di
assegnazione: a parita' di momento, i trigger girano in ordine alfabetico.

---

### Impatto e Vantaggi

* il trigger e' sottile: contiene solo il *quando*. Il *cosa* sta nella funzione
  di controllo, condivisa con l'altro trigger.
