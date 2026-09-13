## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_dettaglio`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:  
>
[catalogo.articoli](/dbzero/catalogo/tabelle/articoli)      
> [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)     
> [vendite.articoli_tipologie](/dbzero/vendite/tabelle/articoli_tipologie)    
> [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi)    
> [vendite.articoli_spesa](/dbzero/vendite/tabelle/articoli_spesa)    
> [config.iva](/dbzero/config/tabelle/iva)    
> [config.nature_vendita](/dbzero/config/tabelle/nature_vendita)    

---
### 🎯 Scopo Principale
(latest review 14-01-26)
La vista **`catalogo.vw_articoli_dettaglio`** espone i dati dell’articolo con le
anagrafiche di supporto (unita misura, tipologie, gruppi, spese, iva e natura di
vendita), evitando join ripetitivi in applicazione.

Restituisce **una riga per articolo**.

---

### Struttura logica della vista

La vista parte da `catalogo.articoli` e aggiunge:

* join a `catalogo.unita_misura` per codice/descrizione UoM;
* join a `vendite.articoli_tipologie` per tipologia articolo;
* join a `vendite.articoli_gruppi` per gruppo merceologico;
* join a `vendite.articoli_spesa` per voce di spesa;
* join a `config.iva` per dati IVA (codice/descrizione/aliquota);
* join a `config.nature_vendita` per la natura di vendita (codice_interno/descrizione/destinazione_tipo).

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
| `natura_vendita_id` + `natura_vendita_codice_interno`, `natura_vendita_descrizione`, `natura_vendita_destinazione_tipo` | Natura di vendita: instradamento split post-accettazione (`destinazione_tipo` = ORDINE/COMMESSA/CONTRATTO). |
| `attivo`, `storicizza`, `tx_id`                                | Stato e tracciamento.                  |
| `is_solo_componente`                                           | Articolo utilizzabile solo come componente. |

(Sono esposti anche i campi di audit e note di `catalogo.articoli`.)

---

### Modalita' d'uso tipiche

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

### Best practice e raccomandazioni

* Usare la vista per letture, reporting e API di consultazione.
* Per modifiche, aggiornare sempre le tabelle base (`catalogo.articoli` e relazioni).

### 🔄 rev 2026-09-13 — da dove arriva l'articolo

Cinque colonne in coda (`20260913-19`): `modo_approvvigionamento_id`, la sua
decodifica — `modo_approvvigionamento_codice_interno` per la logica e
`modo_approvvigionamento_descrizione` a video, sulla forma di
`natura_vendita_*` — più `gestito_a_magazzino` e `lead_time_giorni`. La
decodifica **non** si chiama `_codice`: il valore viene dalla chiave immutabile,
e il nome deve dirlo ([linee guida SQL §6c](/linee-guida-sql)).

⚠️ La vista le espone, ma il backend della lista e del drawer articolo elenca
le colonne **per nome**: finché non le aggiunge, a video non arrivano. Per
questo le tre colonne della lista articoli sono seminate spente. Brief:
`brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezioni 5.2 e 5.5.

---
{% include-markdown "signature-core.md" %}
