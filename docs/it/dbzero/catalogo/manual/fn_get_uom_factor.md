## 📘 Documentazione Concettuale – Funzione `catalogo.fn_get_uom_factor`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle**   
> • [`catalogo.articoli_uom_operativa`](/dbzero/catalogo/tabelle/articoli_uom_operativa)     
> • [`catalogo.unita_misura_conversioni`](/dbzero/catalogo/tabelle/unita_misura_conversioni)     
>
**Approfondimento Funzioni**   
> • [`catalogo.fn_get_uom_base`](/dbzero/catalogo/funzioni/fn_get_uom_base)  

---
### 🎯 Scopo Principale
(latest review 13-01-26)
La funzione **`catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)`** ritorna il **fattore di conversione** dalla UoM richiesta alla **UoM base** dell’articolo.

Supporta un **fallback globale**: se la conversione articolo-specifica non e' presente, usa le conversioni definite in `catalogo.unita_misura_conversioni`.

---

### Logica di calcolo

1. **UoM base articolo**  
   Legge `catalogo.articoli.uom_id` (tramite `catalogo.fn_get_uom_base`).
2. **UoM uguale alla base**  
   Se `p_uom_id = uom_base` → ritorna `1`.
3. **Conversione articolo-specifica**  
   Cerca in `catalogo.articoli_uom_operativa` una riga attiva e valida.
4. **Fallback globale diretto**  
   Cerca in `catalogo.unita_misura_conversioni` `uom_from = p_uom_id` e `uom_to = uom_base`.
5. **Fallback globale inverso**  
   Se trova solo `uom_from = uom_base` e `uom_to = p_uom_id`, ritorna `1/fattore`.
6. **Se non trovato**  
   Ritorna `NULL`.

---

### Esempi d’uso

**1) Caso articolo-specifico**

```sql
SELECT catalogo.fn_get_uom_factor(:articolo_id, :uom_scatola_id);
```

Se l’articolo ha una UoM operativa “scatola” con `factor_to_base = 6`, ritorna `6`.

**2) Caso fallback globale**

```sql
SELECT catalogo.fn_get_uom_factor(:articolo_id, :uom_mj_id);
```

Se l’articolo non ha una conversione specifica per `MJ`, la funzione usa la conversione globale (es. `SMC -> MJ`).

---

### Best practice

* Definisci conversioni **globali** solo per UoM standard, non per confezioni specifiche.
* Usa `articoli_uom_operativa` per conversioni **legate al prodotto** (es. pezzi per scatola).
* Gestisci il caso `NULL` a livello applicativo/trigger quando la conversione non e' disponibile.

---

{% include-markdown "signature-core.md" %}

