## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_movimenti`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.compensazioni](/dbzero/pagamenti/tabelle/compensazioni)  
>
---

### 🎯 Scopo Principale

La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso/rimborso
collegati alle fatture, con indicazione della **provenienza** (centro riscossione)
 e dei parametri utili al calcolo interessi e alla contabilizzazione.

---

### 🧱 Campi chiave (semantica)

* `fattura_id`: fattura collegata.
* `billing_account_id`: intestatario.
* `centro_riscossione_id`: origine incasso (banca/posta/cassa/compensazione).
* `contabile_riga_id`: riga contabile di riferimento (se presente).
* `contabile_id`: testata contabile (derivata da `contabile_riga_id` quando valorizzata).
* `compensazione_id`: testata processo compensazione (se movimento da compensazione).
* `data_effettiva`, `data_registrazione`, `data_valuta`, `data_contabile`: date movimento.
* `data_per_calcolo_interessi`: data riferimento per interessi.
* `data_contabilizzazione`: data invio/registrazione in contabilita.
* `escluso_da_interessi`: esclude il movimento dal calcolo interessi.
* `importo`: valore (positivo o negativo).

---

### ✅ Regole principali

* Un movimento puo` essere collegato a una fattura o usato per compensazioni.
* I movimenti possono essere esclusi dal calcolo interessi.
* Se `contabile_riga_id` e` valorizzato, `contabile_id` deve essere coerente
  con la testata della riga (guard applicativa).
* `contabile_riga_id` e` univoco quando presente (1 movimento ↔ 1 riga contabile).

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_movimenti
WHERE fattura_id = 123;
```

---

{% include-markdown "signature-core.md" %}
