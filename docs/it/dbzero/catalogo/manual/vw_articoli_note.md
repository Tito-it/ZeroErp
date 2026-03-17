## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_note`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli)    
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)     
> [config.note_stili](/dbzero/config/tabelle/note_stili)    
> [config.lingue](/dbzero/config/tabelle/lingue)    

---

### 🎯 Scopo Principale

(latest review 14-01-26)
La vista **`catalogo.vw_articoli_note`** fornisce una lettura immediata delle
note legate agli articoli, arricchite con stile e lingua.

Restituisce **una riga per nota**.

---

### Struttura logica della vista

La vista parte da `catalogo.note_articoli` e aggiunge:

* join a `catalogo.articoli` per codice/descrizione articolo;
* join a `config.note_stili` per dati stile nota;
* join a `config.lingue` per dati lingua.

---

### 📑 Campi esposti (principali)

| Colonna                                                     | Descrizione          |
| ----------------------------------------------------------- | -------------------- |
| `articolo_id`, `articolo_codice`, `articolo_descrizione`    | Dati articolo.       |
| `nota_id`, `nota_anchor_tipo`, `nota_posizione`, `nota_seq` | Posizionamento nota. |
| `nota_testo`, `nota_testo_md`                               | Contenuto nota.      |
| `stile_id`, `stile_codice`, `stile_descrizione`             | Stile applicato.     |
| `lingua_id`, `lingua_codice_iso`, `lingua_descrizione`      | Lingua della nota.   |

(Sono esposti anche i campi di audit della nota.)

---

### Modalita' d'uso tipiche

```sql
SELECT *
FROM catalogo.vw_articoli_note
WHERE articolo_id = :articolo_id
ORDER BY nota_posizione, nota_seq;
```

---

### Best practice e raccomandazioni

* Usare la vista per consultazione e rendering note.
* Per modifiche, operare su `catalogo.note_articoli`.

---
{% include-markdown "signature-core.md" %}
