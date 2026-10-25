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

* **Articoli** (`target_tipo = 'ARTICOLO'`)
* **Articoli componenti** (`target_tipo = 'ARTICOLO_COMPONENTE'`)

> Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3): i codici sono quelli di
> `config.tipi_entita`, al singolare (fino al 2026-10-25 `ARTICOLI` e `ARTICOLI_COMPONENTI`); `target_tipo` è
> `varchar(50)` con la FK `fk_cat_note_target_tipo` al posto del CHECK. Segue l'altra metà della FK composta:
> `catalogo.articoli(_componenti).note_target_tipo`.

---

### Relazioni

| Tipo | Tabella ↔ Campo                                  | Descrizione                                  |
| ---- | ------------------------------------------------ | -------------------------------------------- |
| FK → | `config.note_stili(id)` ← `id_stile`             | Stile della nota                             |
| FK → | `config.lingue(id)` ← `id_lingua`                | Lingua della nota                            |
| FK → | `catalogo.articoli(id)` ← `target_id`            | Target nota (partizione ARTICOLO)            |
| FK → | `catalogo.articoli_componenti(id)` ← `target_id` | Target nota (partizione ARTICOLO_COMPONENTE) |

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
* **Valori ammessi**: i codici di `config.tipi_entita`, per FK (`fk_cat_note_target_tipo`); in pratica le due partizioni
* **Anchor**: `anchor_tipo IN ('DOCUMENTO','RIGA')`
* **Posizione**: `posizione IN ('HEADER','FOOTER','SEZIONE','BEFORE','AFTER')`
* **Sequenza**: `seq >= 0`

---

### Partizioni

* `catalogo.note_articoli` → `target_tipo = 'ARTICOLO'`
* `catalogo.note_articoli_componenti` → `target_tipo = 'ARTICOLO_COMPONENTE'`

---

### Query tipiche

**1) Note per articolo**

```sql
SELECT n.*
FROM catalogo.note n
WHERE n.target_tipo = 'ARTICOLO'
  AND n.target_id = :articolo_id
ORDER BY n.anchor_tipo, n.posizione, n.seq;
```

**2) Note per componente**

```sql
SELECT n.*
FROM catalogo.note n
WHERE n.target_tipo = 'ARTICOLO_COMPONENTE'
  AND n.target_id = :articolo_componente_id
ORDER BY n.anchor_tipo, n.posizione, n.seq;
```

---

{% include-markdown "signature-core.md" %}

