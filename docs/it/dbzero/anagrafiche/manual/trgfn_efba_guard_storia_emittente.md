## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_efba_guard_storia_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/manual/fn_guard_ba_cambio_emittente)
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

È il cancello sull'unica tabella che decide **a quale emittente appartiene un
cliente**: sorveglia tutti i modi in cui quel legame può cambiare, e li blocca
se il cliente ha già una storia.

---

### ⚠️ Il movimento che si dimentica è la **cancellazione**

Sembra che «spostare un cliente da un emittente all'altro» sia una modifica. Non
lo è: il gestionale non ha nessuna modifica su quel legame. Lo spostamento si fa
in due tempi:

1. **si cancella** l'aggancio all'emittente A — e da quel momento il cliente
   ricade sull'emittente generale dell'installazione, che è **già** un cambio;
2. **si crea** l'aggancio all'emittente B.

⇒ Un controllo che guardasse solo la creazione lascerebbe passare tutto, perché
**il danno lo fa il primo passo**.

---

### I casi che sorveglia

| Movimento | Prima | Dopo |
|---|---|---|
| si crea un aggancio | l'emittente generale | quello scelto |
| si cambia l'aggancio | il precedente | il nuovo |
| si sposta l'aggancio su un altro cliente | si controllano **entrambi** | |
| si cancella l'aggancio | quello che c'era | l'emittente generale |
| si tocca l'**emittente generale** | — | riguarda **tutti** i clienti non agganciati |

L'ultimo caso è quello con il raggio più largo: una riga sola può ri-attribuire
retroattivamente l'emittente di un numero arbitrario di documenti.

---

### Due trappole tecniche che valgono per chiunque scriva un controllo così

**La prima**: quando si cancella un aggancio, per sapere «dove ricadrà il
cliente» **non si può chiedere al risolutore**. In quel momento la riga che si
sta cancellando c'è ancora, quindi il risolutore risponderebbe proprio quella:
«prima» e «dopo» coinciderebbero, e il controllo non scatterebbe mai.

**La seconda**: un controllo che sorveglia anche le cancellazioni deve
restituire la riga *vecchia*. Restituire «niente» **annulla la cancellazione in
silenzio** — che è la differenza fra un cancello che blocca dicendolo e uno che
fa sparire il gesto senza errori.

---

### Convive con il fratello, e non si sovrappongono

Sulla stessa tabella c'è già un controllo che sorveglia **l'omogeneità
dell'albero** dei clienti: padre e figli devono stare sullo stesso emittente.

Sono complementari, e le due frasi si leggono bene una accanto all'altra:

* l'uno dice **«l'albero non può diventare misto»**;
* l'altro dice **«la storia non si sposta»**.

---

### Impatto e Vantaggi

* la regola vale per ogni percorso che tocca quella tabella, non solo per quello
  previsto dal gestionale oggi;
* la decisione non vive qui: questo è solo l'aggancio, e delega a chi la sa —
  una implementazione, cinque movimenti.
