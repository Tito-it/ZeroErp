## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_commessa(...)`

> 👀 **Vedi anche**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse)
> [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> [vendite.transizioni_stati_commessa](/dbzero/vendite/tabelle/transizioni_stati_commessa)
> [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)
> [vendite.fn_approva_commessa_attivita](/dbzero/vendite/funzioni/fn_approva_commessa_attivita)

---
### 🎯 Scopo Principale
(rev 2026-06-07)
`vendite.fn_cambia_stato_commessa(p_commessa_id, p_nuovo_stato, p_user)` è l'**entrypoint
sanzionato (DB-first)** per cambiare lo stato di una commessa: risolve il codice stato in id,
esegue l'`UPDATE` e ritorna lo stato da/a.

La validazione del grafo (matrice) e il guard di dominio
(`→ PRONTA_FATTURAZIONE` richiede righe approvate) **non** vivono in questa funzione: sono
enforced dal trigger `vendite.trgfn_commesse_guard_transizione`, che scatta sull'`UPDATE`.
La funzione quindi **non ri-valida la matrice** (niente logica duplicata) — se la transizione
è illegale, il trigger solleva e l'errore si propaga.

Tipico chiamante: l'handler `vendita.push_preventivo`, che la invoca con `'PRONTA_FATTURAZIONE'`
**dopo** aver approvato le righe via `fn_approva_commessa_attivita`.

---

### Regole principali

* La transizione è validata dal trigger guard contro `vendite.transizioni_stati_commessa`.
* Parametri ID validati esplicitamente (`p_commessa_id` NULL o ≤ 0 rifiutato).
* La commessa deve esistere; lo stato destinazione deve esistere ed essere `attivo`.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_commessa_id` | `vendite.commesse.id%TYPE` | ID della commessa. Obbligatorio, > 0. |
| `p_nuovo_stato` | `vendite.stati_commessa.codice_interno%TYPE` | Codice stato destinazione (es. `'PRONTA_FATTURAZIONE'`). |
| `p_user` | `vendite.commesse.user_update%TYPE` | Utente che esegue la transizione (default `CURRENT_USER`). |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `commessa_id` | bigint | ID della commessa |
| `stato_da` | varchar | Codice stato prima della transizione |
| `stato_a` | varchar | Codice stato dopo la transizione |

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | `p_commessa_id` NULL o ≤ 0 |
| `E_COMMESSA_NON_TROVATA` | Commessa inesistente |
| `E_STATO_SCONOSCIUTO` | Codice stato destinazione non trovato/non attivo |
| `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` | (dal trigger) Transizione non in matrice |
| `E_COMMESSA_NESSUNA_RIGA_APPROVATA` | (dal trigger) → `PRONTA_FATTURAZIONE` senza righe approvate |

---

### Esempio d'uso

```sql
-- Percorso push: prima approva le righe, poi porta la testata a emittibile
SELECT vendite.fn_approva_commessa_attivita(42);
SELECT * FROM vendite.fn_cambia_stato_commessa(42, 'PRONTA_FATTURAZIONE', 'operatore1');
```

---

{% include-markdown "signature-core.md" %}
