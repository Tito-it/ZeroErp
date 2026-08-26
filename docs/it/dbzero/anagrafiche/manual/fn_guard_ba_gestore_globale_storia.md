## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_ba_gestore_globale_storia`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
[anagrafiche.fn_guard_albero_ba_gestore_globale](/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Impedisce di cambiare **l'emittente generale dell'installazione** quando ci sono
clienti, agganciati a lui per difetto, che hanno già una storia.

---

### Perché ha un raggio diverso da tutti gli altri controlli

Gli altri riguardano **un** cliente. Questo riguarda **tutti quelli che non
hanno un aggancio proprio**.

L'emittente generale è quello su cui ricade chiunque non sia stato agganciato
esplicitamente. Cambiarlo non è una configurazione: è **ri-attribuire
retroattivamente l'emittente di tutto ciò che quei clienti hanno prodotto**. Una
riga sola, un numero arbitrario di documenti.

---

### Come risponde, e perché non li visita tutti

La domanda è *«esiste della storia?»*, e la risposta non cambia dopo il primo
cliente che ne ha. Quindi ne cerca **uno** — il primo, con un ordine
deterministico — e lascia a lui comporre il messaggio.

⭐ Il vantaggio non è la velocità: è che l'errore **nomina un cliente vero**
invece di dire «da qualche parte». Chi lo legge sa dove guardare.

⚠️ L'ordine esplicito non è pedanteria: senza, sarebbe il caso a decidere quale
cliente compare nell'errore, e lo stesso rifiuto racconterebbe due storie
diverse a due tentativi consecutivi.

---

### ⚠️ In pratica questo cancello chiude quasi sempre

Ed è corretto. Su un'installazione che ha già fatturato, spostare l'emittente
generale non è un'impostazione da rivedere: è una riscrittura della storia.

Se serve davvero un secondo emittente, la strada è agganciare **esplicitamente**
i clienti che devono passare — e per quelli con documenti già emessi vale la
regola di sempre: non si spostano, si apre una fornitura nuova.

---

### Il fratello che sorveglia la stessa riga

Lo stesso movimento è già presidiato per un'altra ragione: l'**omogeneità
dell'albero** dei clienti. Le due funzioni si assomigliano molto e rispondono a
due domande diverse — *«l'albero può diventare misto?»* e *«c'è storia da
proteggere?»* — sulla stessa riga di configurazione.

---

### Impatto e Vantaggi

* il caso con il raggio più largo del dominio non è lasciato scoperto;
* il messaggio è quello del controllo sul singolo cliente: **una
  implementazione, due superfici** — e nessuna frase da tenere allineata a mano.
