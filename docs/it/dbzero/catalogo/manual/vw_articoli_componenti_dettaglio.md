## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_dettaglio`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)      
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)     

---

### 🎯 Scopo Principale

(latest review 14-01-26)
La vista **`catalogo.vw_articoli_componenti_dettaglio`** espone i legami
prodotto–componente e arricchisce la riga con codice/descrizione di prodotto
e componente.

Restituisce **una riga per legame componente**.

---

### Struttura logica della vista

La vista parte da `catalogo.articoli_componenti` e aggiunge:

* join a `catalogo.articoli` per il **prodotto**;
* join a `catalogo.articoli` per il **componente**.

---

### 📑 Campi esposti (principali)

| Colonna                                       | Descrizione                |
| --------------------------------------------- | -------------------------- |
| `id`, `prodotto_id`, `componente_id`          | Identificativi del legame. |
| `prodotto_codice`, `prodotto_descrizione`     | Dati articolo prodotto.    |
| `componente_codice`, `componente_descrizione` | Dati articolo componente.  |
| `coeff_qta`, `partecipa_qta`, `obbligatorio`  | Parametri del legame.      |
| `valid_from`, `valid_to`                      | Validita temporale.        |
| `attivo`, `storicizza`, `tx_id`               | Stato e tracciamento.      |

(Sono esposti anche i campi di audit e note di `catalogo.articoli_componenti`.)

---

### Modalita' d'uso tipiche

```sql
SELECT *
FROM catalogo.vw_articoli_componenti_dettaglio
WHERE prodotto_id = :articolo_id
ORDER BY valid_from;
```

---

### Best practice e raccomandazioni

* Usare la vista per consultazione e composizione distinta base.
* Per modifiche, aggiornare sempre `catalogo.articoli_componenti`.

---
{% include-markdown "signature-core.md" %}
