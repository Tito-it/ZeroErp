## 📘 Documentazione Concettuale – Tabella `catalogo.note`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle**
> • [`catalogo.articoli`](/dbzero/catalogo/tabelle/articoli)  
> • [`catalogo.articoli_componenti`](/dbzero/catalogo/tabelle/articoli_componenti)  
> • [`config.note_stili`](/dbzero/config/tabelle/note_stili)  
> • [`config.lingue`](/dbzero/config/tabelle/lingue)  

---

### 🎯 Scopo Principale

(last review 13-01-26)
`catalogo.note` centralizza le **note testuali** associate agli oggetti del catalogo, con **tabella partizionata** per tipo di target. Supporta note su:

* **Articoli** (`target_tipo = 'ARTICOLI'`)
* **Articoli componenti** (`target_tipo = 'ARTICOLI_COMPONENTI'`)

---

### Relazioni

| Tipo | Tabella ↔ Campo                                  | Descrizione                                  |
| ---- | ------------------------------------------------ | -------------------------------------------- |
| FK → | `config.note_stili(id)` ← `id_stile`             | Stile della nota                             |
| FK → | `config.lingue(id)` ← `id_lingua`                | Lingua della nota                            |
| FK → | `catalogo.articoli(id)` ← `target_id`            | Target nota (partizione ARTICOLI)            |
| FK → | `catalogo.articoli_componenti(id)` ← `target_id` | Target nota (partizione ARTICOLI_COMPONENTI) |

---

### Struttura logica (campi chiave)

* **Identità**: `id BIGINT` + `target_tipo` (**PK composita**)
* **Target**: `target_tipo`, `target_id`, `target_riga_id` (opzionale per ancoraggio “RIGA”)
* **Posizionamento**: `anchor_tipo`, `posizione`, `seq`
* **Contenuto**: `testo`, `testo_md`
* **Stile/Lingua**: `id_stile`, `id_lingua`
* **Flag**: `visibile`, `solo_stampa`
* **Tecnico**: `meta`, `data_insert`, `user_insert`, `data_update`, `user_update`

---

### 🚦 Vincoli & Regole

* **Partizionamento**: `LIST (target_tipo)`
* **Valori ammessi**: `target_tipo IN ('ARTICOLI','ARTICOLI_COMPONENTI')`
* **Anchor**: `anchor_tipo IN ('DOCUMENTO','RIGA')`
* **Posizione**: `posizione IN ('HEADER','FOOTER','SEZIONE','BEFORE','AFTER')`
* **Sequenza**: `seq >= 0`

---

### Partizioni

* `catalogo.note_articoli` → `target_tipo = 'ARTICOLI'`
* `catalogo.note_articoli_componenti` → `target_tipo = 'ARTICOLI_COMPONENTI'`

---

### Query tipiche

**1) Note per articolo**

```sql
SELECT n.*
FROM catalogo.note n
WHERE n.target_tipo = 'ARTICOLI'
  AND n.target_id = :articolo_id
ORDER BY n.anchor_tipo, n.posizione, n.seq;
```

**2) Note per componente**

```sql
SELECT n.*
FROM catalogo.note n
WHERE n.target_tipo = 'ARTICOLI_COMPONENTI'
  AND n.target_id = :articolo_componente_id
ORDER BY n.anchor_tipo, n.posizione, n.seq;
```

---

{% include-markdown "signature-core.md" %}

