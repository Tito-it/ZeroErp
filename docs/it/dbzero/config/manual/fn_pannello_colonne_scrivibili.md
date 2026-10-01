## 📘 Documentazione Concettuale – Funzione `config.fn_pannello_colonne_scrivibili()`

> 👀 **Vedi anche**
>
> **Chi la usa:** [config.fn_pannello_scrivi](/dbzero/config/funzioni/fn_pannello_scrivi) — il verbo del pannello · il form del pannello, lato backend
>
> **La lista che legge:** [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili)

---

### 🎯 Scopo Principale
(scritta il 27-09-2026)

Dice **quali colonne** di una tabella si possono compilare dal pannello
«Gestione tabelle», nell'ordine in cui stanno nella tabella.

Due parti del programma fanno la stessa domanda:

* il **form** del pannello, per sapere quali campi mostrare;
* il **verbo** che salva, per sapere quali campi accettare.

Fino al 27-09-2026 ciascuna aveva un suo elenco, e se i due elenchi si fossero
separati il form avrebbe offerto un campo che il salvataggio rifiuta. Adesso
rispondono tutte e due da qui.

---

### Cosa resta fuori

Le colonne che il database compila da solo, per ogni riga:

* `id`;
* le colonne di audit (chi e quando ha inserito o modificato);
* `tx_id`, `storicizza`, `uid`;
* le colonne calcolate e quelle numerate in automatico senza eccezioni.

---

### Una tabella che il pannello non gestisce

Se la tabella non è nel pannello, o non esiste, la risposta è vuota (`NULL`),
senza errore. A rifiutare il salvataggio è il verbo, con il suo codice.

Presidio: `db/pgtap/config/test-fn-pannello-colonne-scrivibili-v1.sql`.

{% include-markdown "signature-core.md" %}
