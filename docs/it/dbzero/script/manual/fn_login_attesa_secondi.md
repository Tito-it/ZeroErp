## 📘 Documentazione Concettuale – Funzione `script.fn_login_attesa_secondi()`

> 👀 **Vedi anche**
>
> **Il modello:** [config.credenziali](/dbzero/config/tabelle/credenziali)
>
> **I numeri:** [fn_login_parametri](/dbzero/script/funzioni/fn_login_parametri)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Calcola **quanti secondi** deve aspettare il prossimo tentativo di una credenziale
che ha sbagliato tante volte di fila:

* sotto il tetto: **zero**;
* al tetto: l'attesa **base**;
* ogni errore in più: il **doppio**, fino all'attesa **massima**.

Con i valori di partenza (tetto 20, base 2 secondi, massimo 60): al ventesimo
errore 2 secondi, poi 4, 8, 16, 32, e da lì sempre 60. La credenziale **non si
chiude mai**: rallenta.

Riceve i numeri come argomenti e non legge niente: la usano sia il controllo
prima della password sia la registrazione dopo, e devono dare la stessa risposta.

---

### Storia

* 2026-09-25 — nasce (`20260925-05`).

{% include-markdown "signature-core.md" %}
