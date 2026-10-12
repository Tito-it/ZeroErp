## 📘 Documentazione Concettuale – Funzione `vendite.fn_rendi_commessa_emittibile`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_approva_commessa_attivita](/dbzero/vendite/funzioni/fn_approva_commessa_attivita) — l'approvazione  
> • [vendite.fn_cambia_stato_commessa](/dbzero/vendite/funzioni/fn_cambia_stato_commessa) — il cambio di stato  

---

### 🎯 Scopo Principale
(2026-10-12, brief-db-annullo-a-valle-riapre-a-monte, D-10)

Dopo un invio in commessa, rende la commessa **emittibile**: approva le righe di
**questo** invio e porta la commessa a `PRONTA_FATTURAZIONE`. Prima lo faceva il
backend in due passi; ora il backend chiama questa funzione.

---

### Le righe da approvare (`p_righe_ids`)

| Valore | Significato |
| --- | --- |
| `NULL` | nessun filtro: tutte le righe in bozza non emesse della commessa |
| vuoto | nessuna riga di questo invio è atterrata: niente da approvare, ma la commessa va comunque a `PRONTA_FATTURAZIONE` |
| pieno | le sole righe dell'invio: le righe in bozza di altri invii non si toccano |

⭐ **Perché una funzione madre e non un trigger**: «le righe di questo invio» le
conosce solo chi orchestra l'invio.

---

### Lo stato

* Già `PRONTA_FATTURAZIONE`: il cambio non si tenta (la matrice non ammette lo
  stesso stato in partenza e in arrivo).
* `CHIUSA` o `ANNULLATA`: il cambio si tenta e la matrice rifiuta. Non si invia
  in una commessa chiusa.

---

### Note operative

* `SECURITY INVOKER`, come le due funzioni che compone. La transazione la sceglie
  il chiamante: tutto o niente nell'invio singolo, una commessa alla volta nel
  batch.
* Ritorna le righe approvate.
* Test: `db/pgtap/vendite/test-annullo-commessa-v1.sql` (test 4).

---

{% include-markdown "signature-core.md" %}
