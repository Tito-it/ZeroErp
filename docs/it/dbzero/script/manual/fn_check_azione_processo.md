## 📘 Documentazione Concettuale – Funzione `script.fn_check_azione_processo()`

> 👀 **Vedi anche**
>
> **La catena, scritta una volta:** [script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni)

---

### 🎯 Scopo Principale
(riscritta il 04-10-2026, brief-db-permessi-tetto-area)

Risponde **sì o no**: questo utente può eseguire questa azione di processo?
È la domanda che fanno il backend e i verbi di scrittura (attraverso
[fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione)).

Non contiene la regola: legge la riga dell'azione da
[fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni),
dove sono spiegati la catena e il **tetto d'area** (un'azione abilitata da un
override o da un profilo resta negata se l'area dell'operatore non arriva al
minimo dell'azione). Un codice d'azione mancante vale «no».

{% include-markdown "signature-core.md" %}
