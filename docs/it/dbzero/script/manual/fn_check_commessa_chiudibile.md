## 📘 Documentazione Concettuale – Funzione `script.fn_check_commessa_chiudibile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
Approfondimento funzioni:
> • [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)
> • [script.fn_check_commessa_pronta_fatturazione](/dbzero/script/funzioni/fn_check_commessa_pronta_fatturazione)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-07-24)

Elenca i motivi che impediscono di **chiudere** una commessa. Motivo unico: esistono righe
`stato_approvazione = 'APPROVATA'` **e** `stato_emissione = 'NON_EMESSA'`.

Sono esattamente le righe che `fn_list_commesse_emittibili` avrebbe raccolto: **chiudere
sopra di esse le perde**, e `CHIUSA` è irreversibile. Lavoro approvato che nessuno fatturerà
più.

---

### ⭐ È il guard speculare di quello d'ingresso

| Verso | Chi | Regola |
|---|---|---|
| **ingresso** → `PRONTA_FATTURAZIONE` | `fn_check_commessa_pronta_fatturazione` | *deve* esserci almeno una riga pronta |
| **uscita** → `CHIUSA` | questa | **non deve** restarne nessuna |

La stessa condizione, letta nei due versi: è ciò che rende sicuro l'arco
`IN_ESECUZIONE → CHIUSA`.

⚠️ La congiunzione è su **due assi distinti**: `stato_approvazione` e `stato_emissione` sono
colonne separate con CHECK separati, non due valori dello stesso stato. Una riga approvata e
già emessa non blocca; una non approvata nemmeno.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_CHIUSURA_CON_RIGHE_PENDENTI` (559) | Almeno una riga `APPROVATA` + `NON_EMESSA` |
| `E_PARAMETRO_INVALIDO` | `commessa_id` nullo o non positivo |

---

### Il pattern `fn_check_*` — vale per tutte e cinque

**Funzione pura**: `STABLE`, nessuna scrittura, **nessun raise di dominio**. Ritorna `[]` se
l'azione è permessa, altrimenti un array JSONB ordinato di
`{codice, reason, reason_key, dettaglio}`.

L'ordine è quello di **gravità**: chi solleva prende il **primo**.

⭐ **Sorgente unica per due consumatori diversi.** La stessa funzione è letta da:

* il **guard di transizione**, che solleva il codice del primo motivo;
* `fn_available_actions_*`, che espone l'azione come `disabled` con i suoi `reasons`.

È ciò che rende impossibile la divergenza classica fra UI e database — il bottone acceso su
un'azione che il DB rifiuta. Non è disciplina, è struttura: c'è un solo posto da cambiare.

`reason_key` è la chiave i18n per il frontend; `dettaglio` porta il conteggio, così il
messaggio può dire *quanti*.

⚠️ **Il guard sui parametri è l'unica eccezione alla purezza**: `id` nullo o `<= 0` solleva
`E_PARAMETRO_INVALIDO`. È un errore di programmazione, non una condizione di dominio, e va
detto invece di essere normalizzato in silenzio.

---

{% include-markdown "signature-core.md" %}
