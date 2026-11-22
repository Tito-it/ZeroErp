## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_titolo_iva_ambito`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo di cui giudica l'ambito
> * [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) — le righe di ambito
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_ambiti_guard) — chi la chiama dalle righe
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_ambito) — chi la chiama dal titolo

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_titolo_iva_ambito` elenca i motivi per cui l'ambito di un titolo IVA non sta in piedi. Non
solleva e non scrive: restituisce un elenco vuoto se l'ambito è coerente, altrimenti i motivi in ordine, e chi
solleva prende il primo.

---

### ⭐ Una funzione, perché i guard sono due

La regola serve da due parti: quando si scrive una riga di ambito, e quando cambia il titolo (si allarga una data,
si riattiva, si cambia tipo, titolare o emittente) senza che le righe di ambito siano toccate. Un controllo scritto
solo sulle righe sarebbe cieco nel secondo caso, che è il più comune: prolungare un titolo è un gesto normale.

I due guard la chiamano invece di riscriverla: la regola sta in un posto solo, e i due non possono divergere.

---

### I due motivi

1. **Righe di ambito su un titolo che vale per tutto** (`E_TITOLO_IVA_AMBITO_NON_AMMESSO`): il titolo direbbe due
   cose opposte, e chi calcola l'IVA ne leggerebbe una sola. Se c'è questo, l'altro non si guarda.
2. **Il pareggio** (`E_TITOLO_IVA_AMBITO_SOVRAPPOSTO`): un altro titolo attivo e ristretto dello stesso soggetto,
   verso lo stesso emittente, dello stesso tipo, in un periodo che si tocca, che copre lo stesso oggetto allo
   stesso livello. Si guarda solo se il titolo è attivo e ristretto. Il rifiuto nomina il tipo del titolo e la
   merce, e fra più conflitti sceglie sempre lo stesso.

---

### ⚠️ Che cosa è un pareggio, e che cosa si risolve da sé

| Due titoli, stesso soggetto, emittente e tipo, periodi che si toccano | Esito |
| --- | --- |
| entrambi valgono per tutto | rifiutato dal vincolo di esclusione della tabella dei titoli |
| uno per tutto, uno su un articolo | vince il più specifico |
| uno su un articolo, uno sulla sua categoria | vince l'articolo |
| entrambi sullo stesso oggetto, allo stesso livello | rifiutato da questa funzione |

Solo l'ultimo è un pareggio: due titoli indistinguibili per specificità, fra cui non c'è niente da scegliere. Una
scelta fatta sull'ordine degli identificativi sarebbe un'ambiguità del modello, non una regola. Livelli diversi
invece non si bloccano: è la configurazione più normale.

Per i titoli totali basta il vincolo di esclusione, più forte di un guard; questa funzione copre la metà che un
vincolo non raggiunge, perché la chiave passa da una tabella figlia.

---

### Gira coi permessi di chi chiama

Il confronto è fra titoli verso lo stesso emittente, quindi visibili alle stesse condizioni: chi vede un titolo vede
anche quello con cui fa pareggio. Non c'è il conflitto invisibile che renderebbe cieco il controllo.

Un titolo che non esiste dà un elenco vuoto: la funzione elenca motivi, non giudica l'esistenza.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — la riga su un titolo totale, il pareggio sullo stesso
  articolo, i livelli diversi che passano, il periodo del titolo allargato che crea il pareggio.

---

{% include-markdown "signature-core.md" %}
