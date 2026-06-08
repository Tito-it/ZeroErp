## 📘 Documentazione Concettuale – Funzione `vendite.fn_approva_commessa_attivita(...)`

> 👀 **Vedi anche**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.fn_cambia_stato_commessa](/dbzero/vendite/funzioni/fn_cambia_stato_commessa)
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(rev 2026-06-07)
`vendite.fn_approva_commessa_attivita(p_commessa_id, p_righe_ids, p_user)` porta le righe
`commesse_attivita` da `stato_approvazione = 'BOZZA'` a `'APPROVATA'`.

È il **prerequisito di riga per l'emissione**: `fn_emit_attivita_fatturabili_da_commessa`
emette solo righe `APPROVATA`, e il guard transizione `→ PRONTA_FATTURAZIONE`
(`trgfn_commesse_guard_transizione`) richiede almeno una riga `APPROVATA` + `NON_EMESSA`.

Tipico chiamante: l'handler `vendita.push_preventivo`, **prima** di
`fn_cambia_stato_commessa(..., 'PRONTA_FATTURAZIONE')`. Il preventivo accettato è
l'autorizzazione: le righe nate dal push vengono confermate senza ulteriore intervento.

---

### Regole principali

* Approva solo righe in `stato_approvazione = 'BOZZA'` **e** `stato_emissione = 'NON_EMESSA'`.
* `p_righe_ids` **opzionale**: `NULL` = tutte le righe `NON_EMESSA` della commessa; altrimenti
  solo le righe il cui `id` è nell'array.
* **Idempotente**: le righe già `APPROVATA` non rientrano nel `WHERE` → seconda invocazione
  ritorna 0.
* La commessa deve esistere.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_commessa_id` | `vendite.commesse.id%TYPE` | ID della commessa. Obbligatorio. |
| `p_righe_ids` | `bigint[]` | ID righe da approvare. Default `NULL` = tutte le `NON_EMESSA`. |
| `p_user` | `vendite.commesse_attivita.user_update%TYPE` | Utente (default `CURRENT_USER`). |

---

### 📦 Output

| Tipo | Descrizione |
|------|-------------|
| `integer` | Numero di righe effettivamente portate ad `APPROVATA` |

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_NON_TROVATA` | Commessa inesistente |

---

### Esempio d'uso

```sql
-- Approva tutte le righe non emesse della commessa
SELECT vendite.fn_approva_commessa_attivita(42);

-- Approva solo righe specifiche
SELECT vendite.fn_approva_commessa_attivita(42, ARRAY[1001, 1002]::bigint[], 'operatore1');
```

---

{% include-markdown "signature-core.md" %}
