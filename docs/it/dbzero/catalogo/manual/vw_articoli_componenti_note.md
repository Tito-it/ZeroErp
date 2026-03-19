## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_note`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:  
>
[catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti)    
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)     
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> [config.note_stili](/dbzero/config/tabelle/note_stili)    
> [config.lingue](/dbzero/config/tabelle/lingue)    

---
### 🎯 Scopo Principale
(latest review 14-01-26)
La vista **`catalogo.vw_articoli_componenti_note`** fornisce una lettura delle
note legate ai componenti articolo, includendo i riferimenti a prodotto,
componente, stile e lingua.

Restituisce **una riga per nota**.

---

### Struttura logica della vista

La vista parte da `catalogo.note_articoli_componenti` e aggiunge:

* join a `catalogo.articoli_componenti` per il legame prodotto–componente;
* join a `catalogo.articoli` per codice/descrizione prodotto e componente;
* join a `config.note_stili` per dati stile nota;
* join a `config.lingue` per dati lingua.

---

### 📑 Campi esposti (principali)

| Colonna                                                     | Descrizione                |
| ----------------------------------------------------------- | -------------------------- |
| `articolo_componente_id`, `prodotto_id`, `componente_id`    | Identificativi del legame. |
| `prodotto_codice`, `prodotto_descrizione`                   | Dati articolo prodotto.    |
| `componente_codice`, `componente_descrizione`               | Dati articolo componente.  |
| `nota_id`, `nota_anchor_tipo`, `nota_posizione`, `nota_seq` | Posizionamento nota.       |
| `nota_testo`, `nota_testo_md`                               | Contenuto nota.            |
| `stile_id`, `stile_codice`, `stile_descrizione`             | Stile applicato.           |
| `lingua_id`, `lingua_codice_iso`, `lingua_descrizione`      | Lingua della nota.         |

(Sono esposti anche i campi di audit della nota.)

---

### Modalita' d'uso tipiche

```sql
SELECT *
FROM catalogo.vw_articoli_componenti_note
WHERE prodotto_id = :articolo_id
ORDER BY nota_posizione, nota_seq;
```

---

### Best practice e raccomandazioni

* Usare la vista per consultazione e rendering note componenti.
* Per modifiche, operare su `catalogo.note_articoli_componenti`.

---
{% include-markdown "signature-core.md" %}
