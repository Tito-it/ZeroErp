## 📘 Documentazione Concettuale – Funzione `vendite.fn_group_attivita_fatturabili`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [vendite.articolo_regole_fatturazione](/dbzero/vendite/tabelle/articolo_regole_fatturazione)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.fn_group_attivita_fatturabili()`** costruisce la
**chiave di aggregazione riga** a partire da una riga di `attivita_fatturabili`.

---

### ✅ Regole principali

* `dest_billing_account_id` usa il BA reale (mai il parent).
* `uom_id` deriva da attivita (fallback su articolo).
* `iva_id` deriva dall’articolo.
* Regole di aggregazione/arrotondamento da `vendite.articolo_regole_fatturazione`
  (fallback ai valori standard se assenti).
* Se l’intervallo `competenza_dal/competenza_al` e` significativo (diverso da
  `data_attivita` o con range > 0), viene incluso nella chiave di aggregazione.

---

### ✅ Output

Ritorna un **jsonb** con:

* chiave riga (`articolo_id`, `dest_billing_account_id`, `uom_id`, `prezzo_unitario`, `iva_id`)
  + `competenza_dal/competenza_al` quando rilevanti
* regole (`visibilita_componenti`, `calcolo_qta_padre`, `arrotondamenti`)

---

### 🧪 Esempio

```sql
SELECT vendite.fn_group_attivita_fatturabili(12345);
```

**Nota pratica**

* Se `competenza_dal = competenza_al = data_attivita` → l’intervallo **non** entra in chiave.
* Se `competenza_dal <> competenza_al` **oppure** diverso da `data_attivita` → intervallo **incluso**.

---

{% include-markdown "signature-core.md" %}
