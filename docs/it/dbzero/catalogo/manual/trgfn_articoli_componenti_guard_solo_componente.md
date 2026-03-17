## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_componenti_guard_solo_componente`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle**    
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)    
>
**Approfondimento Trigger/Funzioni**    
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)  

---

### 🎯 Scopo Principale

(latest review 14-01-26)
La funzione **`catalogo.trgfn_articoli_componenti_guard_solo_componente`** impedisce
di usare come **prodotto** un articolo marcato `is_solo_componente = true`.
Serve a garantire che articoli “solo componente” non vengano messi come
`prodotto_id` in `catalogo.articoli_componenti`.

---

### Logica applicata

* Il trigger scatta **BEFORE INSERT OR UPDATE OF prodotto_id** su `catalogo.articoli_componenti`.
* Legge `catalogo.articoli.is_solo_componente` dell’articolo referenziato da `prodotto_id`.
* Se `is_solo_componente = true` → blocca con `script.fn_log_and_raise_error(...)`.

---

### Comportamento atteso

* **Consentito**: usare un articolo normale come prodotto.
* **Bloccato**: usare un articolo con `is_solo_componente = true` come prodotto.
* **Nessun effetto**: se `prodotto_id` è `NULL` (non previsto in pratica).

---

### Esempio

```sql
-- Articolo solo componente
UPDATE catalogo.articoli
SET is_solo_componente = true
WHERE codice = 'VITE_M6';

-- Tentativo di usare VITE_M6 come prodotto: bloccato
INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valid_from)
VALUES (:id_vite_m6, :id_sedile, 1, CURRENT_DATE);
```

---

### Best practice e raccomandazioni

* Usare `is_solo_componente` per classificare articoli “solo componente”.
* Per evitare incoerenze, applicare la regola anche **in fase di aggiornamento** dei dati anagrafici.

---
{% include-markdown "signature-core.md" %}
