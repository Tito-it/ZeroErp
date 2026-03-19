## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili_righe`** contiene il dettaglio delle
righe importate/gestite nella testata contabile vendite, con stato di lavorazione
e riferimenti di abbinamento (fattura, billing account).

---

### Campi chiave (semantica)

* `contabile_id`: FK alla testata `pagamenti.vendite_contabili`.
* `riferimento_ente`: riferimento esterno del flusso (CRO/TRN/UID operazione).
* `importo`: importo riga (vincolo `<> 0`).
* `fattura_id`: fattura eventualmente abbinata.
* `billing_account_id`: billing account eventualmente abbinato.
* `stato_id`: stato di lavorazione riga.
* `motivo_sospeso`: dettaglio diagnostico in caso di sospensione.

---

### Regole principali

* La riga appartiene sempre a una testata (`contabile_id` obbligatorio).
* `stato_id` usa il lookup `pagamenti.vendite_contabili_righe_stati`.
* `importo` non puo` essere zero.
* Centro riscossione/ente di provenienza sono definiti in testata, non in riga.

---

### Esempio d’uso

```sql
SELECT r.id, r.contabile_id, r.importo, r.stato_id, r.fattura_id
FROM pagamenti.vendite_contabili_righe r
WHERE r.attivo IS TRUE
ORDER BY r.id DESC
LIMIT 50;
```

---

{% include-markdown "signature-core.md" %}
