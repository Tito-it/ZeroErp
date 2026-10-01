## 📘 Documentazione Concettuale – Tabella `config.nomi_tentati_provenienze`

> 👀 **Vedi anche**
>
> **La madre:** [config.nomi_tentati](/dbzero/config/tabelle/nomi_tentati)
>
> **La gemella per le credenziali vere:** [config.credenziali_provenienze](/dbzero/config/tabelle/credenziali_provenienze)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Il **freno sulla provenienza** per un nome che non esiste: una riga per ogni
coppia *nome tentato + macchina da cui qualcuno ha sbagliato*. Funziona **come**
[config.credenziali_provenienze](/dbzero/config/tabelle/credenziali_provenienze):
stessa soglia, stessa durata, stessa frase, stessa scadenza di un giorno. Deve
essere così: se le due coppie frenassero in modo diverso, la differenza direbbe
se il nome esiste.

La regola del freno è scritta una volta sola,
[fn_login_freno_passo](/dbzero/script/funzioni/fn_login_freno_passo), e la usano
le due coppie.

---

### Storia

* 2026-09-25 — nasce (`20260925-56`), R-7. Brief:
  brief-db-blocco-login-per-credenziale §13.

{% include-markdown "signature-core.md" %}
