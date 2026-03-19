## 📘 Documentazione Concettuale – Tabella `pagamenti.compensazioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.compensazioni`** rappresenta la testata del processo
che genera movimenti di compensazione tra documenti del cliente.

---

### Campi chiave (semantica)

* `id`: identificativo compensazione.
* `data_esecuzione`: timestamp esecuzione processo.
* `meta`: metadati operativi.

---

### Regole principali

* Una compensazione puo` generare piu` movimenti.
* La compensazione e` collegata alla testata contabile tramite
  `pagamenti.vendite_contabili.compensazione_id`.
* I movimenti vengono generati in fase di posting contabile.

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.compensazioni
ORDER BY data_esecuzione DESC;
```

---

{% include-markdown "signature-core.md" %}
