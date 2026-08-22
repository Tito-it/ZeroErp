## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_movimenti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso/rimborso
collegati alle fatture, con indicazione della **provenienza** (centro riscossione)
 e dei parametri utili al calcolo interessi e alla contabilizzazione.

---

### Campi chiave (semantica)

* `fattura_id`: fattura collegata (obbligatoria; derivata da riga contabile se presente).
* `billing_account_id`: intestatario (obbligatorio; derivato da riga contabile se presente).
* `centro_riscossione_id`: origine incasso (banca/posta/cassa/compensazione).
* `contabile_riga_id`: riga contabile di riferimento (se presente).
* `scadenza_id`: la **rata** a cui il movimento e' imputato, copiata dalla riga.
* `contabile_id`: testata contabile (derivata da `contabile_riga_id` quando valorizzata).
* `data_effettiva`, `data_registrazione`, `data_valuta`, `data_contabile`: date movimento.
* `data_per_calcolo_interessi`: data riferimento per interessi.
* `data_contabilizzazione`: data invio/registrazione in contabilita.
* `escluso_da_interessi`: esclude il movimento dal calcolo interessi.
* `importo`: valore (positivo o negativo).

---

### Regole principali

* I movimenti rappresentano il risultato di posting contabile.
* Le compensazioni sono tracciate sulla testata contabile (`vendite_contabili.compensazione_id`),
  non direttamente sul movimento.
* I movimenti possono essere esclusi dal calcolo interessi.
* Se `contabile_riga_id` e` valorizzato, `contabile_id`, `fattura_id`,
  `billing_account_id` e `scadenza_id` devono essere coerenti con la riga
  (guard applicativa): sono **quattro** riferimenti dal 2026-08-22, erano tre.

> ⭐ **Perche' la rata sta anche qui, se c'e' gia' sulla riga.** Perche' il
> **movimento e' il fatto**, e i fatti si leggono da soli: chi somma gli incassi
> di una rata deve poterlo fare **senza passare dalla riga** — che puo' essere
> disattivata, spostata, o vivere sotto una distinta annullata.
>
> ⚠️ E non e' una seconda sorgente di verita': il valore **non lo scrive il
> chiamante**, lo copia il trigger di mirror. Chi ne passa uno diverso da quello
> della riga viene rifiutato, esattamente come per gli altri tre.
* `contabile_riga_id` e` univoco quando presente (1 movimento ↔ 1 riga contabile).

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_movimenti
WHERE fattura_id = 123;
```

---

{% include-markdown "signature-core.md" %}
