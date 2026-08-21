## 📘 Documentazione Concettuale – Tabella `pagamenti.compensazioni`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
> 🔴 **Dal cantiere incassi questa tabella cambia nome e mestiere (D15, 2026-08-21).**
> Diventa **`pagamenti.sistemazioni`**: non più la sola compensazione, ma il
> **registro delle decisioni** su un saldo in eccesso — `RIPORTO` su una fattura
> futura, `RIMBORSO` con bonifico, `COMPENSAZIONE` fra documenti. Chiamare
> «compensazione» un bonifico di rimborso sarebbe falso.
>
> La descrizione qui sotto resta valida **per l'oggetto di oggi**. Piano: slice 4
> di `docs/it/dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md`.
> ⛔ **Non ancora applicato.**

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

* Una compensazione può generare più movimenti.
* La compensazione è collegata alla testata contabile tramite
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
