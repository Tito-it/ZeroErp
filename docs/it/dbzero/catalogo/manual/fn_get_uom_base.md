## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_base`

> 👀 **Vedi anche**
>
> **Approfondimento Tabelle**
> • [`catalogo.articoli`](/dbzero/catalogo/tabelle/articoli)  
> • [`catalogo.unita_misura`](/dbzero/catalogo/tabelle/unita_misura)  
>
> **Approfondimento Funzioni**
> • [`catalogo.fn_get_uom_factor`](/dbzero/catalogo/funzioni/fn_get_uom_factor)  

---

### 🎯 Scopo Principale

(latest updates 13-01-26)
La funzione **`catalogo.fn_get_uom_base(p_articolo_id)`** ritorna la **UoM base** dell’articolo, leggendo il campo `catalogo.articoli.uom_id`.

Se l’articolo non esiste o non ha UoM base, ritorna `NULL`.

---

### 🔁 Logica di calcolo

1. Cerca `catalogo.articoli.uom_id` per `p_articolo_id`.
2. Se trovato → ritorna l’ID della UoM base.
3. Se non trovato → ritorna `NULL`.

---

### 🔎 Esempi d’uso

**1) Recupero UoM base**

```sql
SELECT catalogo.fn_get_uom_base(:articolo_id);
```

**2) Uso con fallback applicativo**

```sql
WITH base AS (
  SELECT catalogo.fn_get_uom_base(:articolo_id) AS uom_base_id
)
SELECT CASE
  WHEN uom_base_id IS NULL THEN 'UoM base non definita'
  ELSE 'UoM base = ' || uom_base_id::text
END
FROM base;
```

**3) Recupero codice UoM base**

```sql
SELECT u.codice
FROM catalogo.articoli a
JOIN catalogo.unita_misura u ON u.id = catalogo.fn_get_uom_base(a.id)
WHERE a.id = :articolo_id;
```

**4) Articoli senza UoM base**

```sql
SELECT a.id, a.codice, a.descrizione
FROM catalogo.articoli a
WHERE catalogo.fn_get_uom_base(a.id) IS NULL;
```

---

### 🧭 Best practice

* Assicurati che `catalogo.articoli.uom_id` sia valorizzato per gli articoli gestiti in magazzino/fatturazione.
* Gestisci `NULL` a livello applicativo quando l’articolo non ha UoM base.

---

{% include-markdown "signature-core.md" %}
