## 📘 Documentazione Concettuale – Funzione `dbops.fn_col_exists`

> 👀 **Vedi anche**
>
> • [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Dice se una colonna esiste: `EXISTS` su `information_schema.columns`, tre parametri, ritorna
`boolean`.

⭐ È una funzione di tre righe che sostiene tutte le **automazioni**. Il runner
`fn_run_automations_lock_columns` la usa per aggiungere al trigger solo le colonne che esistono
davvero sulla tabella target: senza, una riga di configurazione che nomina una colonna
inesistente farebbe fallire il DDL generato invece di essere ignorata.

⚠️ Legge `information_schema`, quindi vede solo ciò su cui l'utente corrente ha privilegi: un
`false` può significare «non c'è» oppure «non la vedo».

---

{% include-markdown "signature-core.md" %}
