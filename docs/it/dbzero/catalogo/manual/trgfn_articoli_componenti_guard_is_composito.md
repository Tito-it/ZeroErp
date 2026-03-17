## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_componenti_guard_is_composito`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle**     
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)    
>

🎯 Scopo Principale

(latest review 15-01-26)
La funzione **`catalogo.trgfn_articoli_componenti_guard_is_composito`** impedisce
di usare come **prodotto** un articolo con `is_composito = false`.
Serve a garantire che la distinta base sia definita solo per articoli realmente compositi.

---

### Logica applicata

* Il trigger scatta **BEFORE INSERT OR UPDATE OF prodotto_id** su `catalogo.articoli_componenti`.
* Legge `catalogo.articoli.is_composito` dell’articolo referenziato da `prodotto_id`.
* Se `is_composito = false` → blocca con `script.fn_log_and_raise_error(...)`.

---

### Comportamento atteso

* **Consentito**: usare come prodotto un articolo con `is_composito = true`.
* **Bloccato**: usare come prodotto un articolo con `is_composito = false`.
* **Nessun effetto**: se `prodotto_id` è `NULL` (non previsto in pratica).

---

### Esempio

```sql
-- Articolo non composito
UPDATE catalogo.articoli
SET is_composito = false
WHERE codice = 'SEDIA';

-- Tentativo di usare SEDIA come prodotto in distinta base: bloccato
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valid_from)
VALUES (:id_sedia, :id_vite_m6, 4, CURRENT_DATE);
```

---

### Best practice e raccomandazioni

* Definire `is_composito = true` per gli articoli che devono avere una distinta base.
* Tenere allineati i dati anagrafici e la distinta base per evitare incoerenze.

---
{% include-markdown "signature-core.md" %}
