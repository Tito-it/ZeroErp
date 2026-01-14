## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_dettaglio`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:  
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)      
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)     
> * [vendite.articoli_tipologie](/dbzero/vendite/tabelle/articoli_tipologie)    
> * [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi)    
> * [vendite.articoli_spesa](/dbzero/vendite/tabelle/articoli_spesa)    
> * [config.iva](/dbzero/config/tabelle/iva)    

---

### 🎯 Scopo Principale

(latest review 14-01-26)
La vista **`catalogo.vw_articoli_dettaglio`** espone i dati dell’articolo con le
anagrafiche di supporto (unita misura, tipologie, gruppi, spese e iva), evitando
join ripetitivi in applicazione.

Restituisce **una riga per articolo**.

---

### 🧱 Struttura logica della vista

La vista parte da `catalogo.articoli` e aggiunge:

* join a `catalogo.unita_misura` per codice/descrizione UoM;
* join a `vendite.articoli_tipologie` per tipologia articolo;
* join a `vendite.articoli_gruppi` per gruppo merceologico;
* join a `vendite.articoli_spesa` per voce di spesa;
* join a `config.iva` per dati IVA (codice/descrizione/aliquota).

---

### 📑 Campi esposti (principali)

| Colonna                                                        | Descrizione                            |
| -------------------------------------------------------------- | -------------------------------------- |
| `id`, `codice`, `descrizione`, `descrizione_breve`             | Identificativi e descrizioni articolo. |
| `uom_id` + `uom_codice`, `uom_descrizione`                     | Unita di misura base.                  |
| `tipo_voce_id` + `tipologia_codice`, `tipologia_descrizione`   | Tipologia articolo.                    |
| `gruppo_voce_id` + `gruppo_codice`, `gruppo_descrizione`       | Gruppo merceologico.                   |
| `spesa_id` + `spesa_codice`, `spesa_descrizione`               | Voce di spesa.                         |
| `iva_id` + `iva_codice`, `iva_descrizione`, `iva_aliquota_iva` | Dati IVA.                              |
| `attivo`, `storicizza`, `tx_id`                                | Stato e tracciamento.                  |
| `is_solo_componente`                                           | Articolo utilizzabile solo come componente. |

(Sono esposti anche i campi di audit e note di `catalogo.articoli`.)

---

### 🔍 Modalita' d'uso tipiche

```sql
SELECT *
FROM catalogo.vw_articoli_dettaglio
WHERE attivo IS TRUE
ORDER BY codice;
```

```sql
SELECT id, codice, descrizione, uom_codice, iva_aliquota_iva
FROM catalogo.vw_articoli_dettaglio
WHERE codice ILIKE 'ART%';
```

---

### ✅ Best practice e raccomandazioni

* Usare la vista per letture, reporting e API di consultazione.
* Per modifiche, aggiornare sempre le tabelle base (`catalogo.articoli` e relazioni).

---
{% include-markdown "signature-core.md" %}
