## 📘 Documentazione Concettuale – Funzione `script.fn_get_note`

> 👀 **Vedi anche**
>
**Approfondimento Tabelle**
> 
• [`config.note_stili`](/dbzero/config/tabelle/note_stili)   
> • [`config.lingue`](/dbzero/config/tabelle/lingue)    
>
**Approfondimento Funzioni**
> • [`script.fn_get_note`](/dbzero/script/funzioni/fn_get_note)   
>
**Esempi di uso**
> • [`vendite.fn_get_vendite_note`](/dbzero/vendite/funzioni/fn_get_vendite_note)    
> • [`acquisti.fn_get_acquisti_note`](/dbzero/acquisti/funzioni/fn_get_acquisti_note)    

---
### 🎯 Scopo Principale
(latest review 14-01-26)
`script.fn_get_note` e' una funzione generica che **normalizza la lettura delle note** da una tabella `*.note` partizionata.  
Restituisce sempre lo stesso set di colonne con **stile** e **lingua** risolti da `config.note_stili` e `config.lingue`.

---

### Parametri

| Parametro         | Tipo       | Descrizione                                            |
| ----------------- | ---------- | ------------------------------------------------------ |
| `p_note_table`    | `regclass` | Tabella note sorgente (es. `'vendite.note'::regclass`) |
| `_target_tipo`    | `text`     | Tipo target (normalizzato a `UPPER`)                   |
| `_target_id`      | `bigint`   | ID testata                                             |
| `_target_riga_id` | `bigint`   | ID riga (opzionale)                                    |
| `_include_doc`    | `boolean`  | Include note con `anchor_tipo = 'DOCUMENTO'`           |
| `_include_righe`  | `boolean`  | Include note con `anchor_tipo = 'RIGA'`                |
| `_only_visible`   | `boolean`  | Se `true`, filtra `visibile = true`                    |

---

### Logica di estrazione

1. Seleziona le note dalla tabella passata in `p_note_table`.
2. Join su `config.note_stili` per ottenere il codice stile.
3. Left join su `config.lingue` per ottenere il codice lingua.
4. Filtra per `target_tipo`, `target_id`, e (se presente) `target_riga_id`.
5. Applica i filtri su `anchor_tipo` e `visibile`.
6. Ordina per **DOCUMENTO** prima di **RIGA**, poi per `posizione`, `seq`, `id`.

---

### Output (campi principali)

* `target_tipo`, `target_id`, `target_riga_id`
* `anchor_tipo`, `posizione`, `seq`
* `testo`, `testo_md`
* `stile`, `lingua`
* `visibile`, `solo_stampa`
* `meta`, `data_insert`, `user_insert`, `data_update`, `user_update`

---

### Esempi d’uso

**1) Note documento (solo visibili)**

```sql
SELECT *
FROM script.fn_get_note(
  'vendite.note'::regclass,
  'FATTURA',
  :fattura_id,
  NULL,
  true,
  false,
  true
);
```

**2) Note riga (incluse anche non visibili)**

```sql
SELECT *
FROM script.fn_get_note(
  'vendite.note'::regclass,
  'FATTURA',
  :fattura_id,
  :riga_id,
  false,
  true,
  false
);
```

**3) Note documento + righe insieme**

> Ultima revisione: 2026-10-25 (brief-db-grammatica-unica-documenti, lotto 3): `_target_tipo` è il codice di `config.tipi_entita` (`ORDINE_VENDITA`, non più `ORDINE`).

```sql
SELECT *
FROM script.fn_get_note(
  'vendite.note'::regclass,
  'ORDINE_VENDITA',
  :ordine_id,
  :riga_id,
  true,
  true,
  true
);
```

---

### Best practice

* Passa sempre `p_note_table` come `regclass` per evitare SQL injection e garantire la risoluzione corretta della tabella.
* Usa `_include_doc` / `_include_righe` per controllare con precisione l’ambito delle note.
* Imposta `_only_visible = true` nei contesti di stampa e UI.

---

{% include-markdown "signature-core.md" %}