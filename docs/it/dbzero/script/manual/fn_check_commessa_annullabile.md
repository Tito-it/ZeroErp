## 📘 Documentazione Concettuale – Funzione `script.fn_check_commessa_annullabile()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
>
Approfondimento funzioni:
> • [vendite.trgfn_commesse_guard_transizione](/dbzero/vendite/funzioni/trgfn_commesse_guard_transizione)
> • [script.fn_check_commessa_chiudibile](/dbzero/script/funzioni/fn_check_commessa_chiudibile)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — funzione rev 2026-07-24)

Elenca i motivi che impediscono di **annullare** una commessa. Motivo unico: esistono righe
con `stato_emissione = 'EMESSA'`.

---

### ⭐ Il criterio è deliberatamente restrittivo

`EMESSA` significa **«uscita verso una fattura»**, non «fatturata in via definitiva». La
differenza conta, perché il reset di un lotto cancella le fatture ma **non riporta indietro**
`stato_emissione`.

Si sarebbe potuto usare un criterio più fine — «esiste una fattura viva» — e sarebbe stato più
permissivo. È stato scelto il più restrittivo perché `ANNULLATA` è **terminale e
irreversibile**: sbagliare in senso permissivo qui non si corregge più.

⚠️ Conseguenza pratica: una commessa le cui fatture sono state tutte cancellate da un reset
**resta non annullabile**. Non è un difetto, è la scelta — ma è la domanda che arriva
dall'assistenza, e la risposta è questa.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE` (558) | Almeno una riga `stato_emissione = 'EMESSA'` |
| `E_PARAMETRO_INVALIDO` | `commessa_id` nullo o non positivo |

Indice usato: `ix_commesse_attivita_commessa_stati`.

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
