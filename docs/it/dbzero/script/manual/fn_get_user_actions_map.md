## 📘 Documentazione Concettuale – Funzione `script.fn_get_user_actions_map()`

> 👀 **Vedi anche**
>
> **La catena, scritta una volta:** [script.fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni)

---

### 🎯 Scopo Principale
(riscritta il 04-10-2026, brief-db-permessi-tetto-area)

Restituisce, in una sola chiamata, tutte le azioni di processo **attive** di un
utente con la risposta sì/no: `{"genera_fatture_lotti": true, …}`. Alimenta
`/me/` → `azioni_abilitate` (via `fn_get_user_profile`) e la dashboard.

Non contiene la regola: aggrega
[fn_get_permessi_effettivi_azioni](/dbzero/script/funzioni/fn_get_permessi_effettivi_azioni),
la stessa che legge
[fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo):
mappa e controllo puntuale non possono dissentire. Utente mancante o ≤ 0 →
`E_ADMIN_VALIDAZIONE`.

{% include-markdown "signature-core.md" %}
