## 📘 Documentazione Concettuale – Funzione `script.fn_login_freno_passo()`

> 👀 **Vedi anche**
>
> **Chi la usa:** [fn_registra_tentativo_login](/dbzero/script/funzioni/fn_registra_tentativo_login)
>
> **La gemella per l'attesa:** [fn_login_attesa_secondi](/dbzero/script/funzioni/fn_login_attesa_secondi)

---

### 🎯 Scopo Principale
(scritta il 25-09-2026)

Dice come cambia il **freno su una macchina** dopo un accesso sbagliato:

* se il freno di prima era già finito, il conto **riparte da uno**;
* altrimenti il conto cresce di uno;
* alla soglia (`login_max_tentativi_falliti`) la macchina è frenata per
  `login_blocco_minuti` da adesso. Un errore mentre il freno è in corso lo
  **rinnova**.

Riceve tutto come argomenti, anche l'istante, e non legge niente. La usano le due
coppie che frenano — credenziale + macchina e nome inesistente + macchina — perché
una regola scritta due volte prima o poi risponde in due modi, e qui la
differenza direbbe a chi prova se il nome esiste.

---

### Storia

* 2026-09-25 — nasce (`20260925-59`), estratta dalla registrazione per R-7.

{% include-markdown "signature-core.md" %}
