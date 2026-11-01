## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_base`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[anagrafiche.vw_indirizzi_resolved_ruolo](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo)  
> [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto)  
> [anagrafiche.vw_indirizzi_resolved_all](/dbzero/anagrafiche/views/vw_indirizzi_resolved_all)  
> [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)  
>
Approfondimenti tabelle:
>
[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)  
> [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)  
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)  
> [config.comuni](/dbzero/config/tabelle/comuni)  
> [config.codici_postali](/dbzero/config/tabelle/codici_postali)  
> [config.province](/dbzero/config/tabelle/province)  
> [config.regioni](/dbzero/config/tabelle/regioni)  
> [config.stati](/dbzero/config/tabelle/stati)  

---
### 🎯 Scopo Principale

(latest review 25-03-26)
La vista **`anagrafiche.vw_indirizzi_resolved_base`** è il **layer comune** per la risoluzione degli indirizzi, e unifica in un solo output:

* indirizzi **per ruolo** (`anagrafiche.indirizzi`),
* indirizzi **per soggetto** (`anagrafiche.indirizzi_soggetti`).

La vista:

* centralizza la logica di **composizione dell’indirizzo human‑readable** (`indirizzo_display`),
* espone **campi strutturati** territoriali e internazionali,
* elimina duplicazioni tra le viste “resolved” specialistiche.

È la **sorgente unica** usata dalle viste:

* `vw_indirizzi_resolved_ruolo`
* `vw_indirizzi_resolved_soggetto`
* `vw_indirizzi_resolved_all`

---

### Struttura logica della vista

La vista è costruita come:

* **UNION ALL** tra indirizzi ruolo e indirizzi soggetto,
* join su `config.tipi_indirizzi`,
* join su `vw_indirizzi_dettaglio` e `script.vw_indirizzo_completo` per completare i dati normalizzati,
* arricchimento con **geodata** (stato, regione, provincia, comune, CAP).

---

### Semantica di `scope`

| scope      | Origine                          | Significato                              |
| ---------- | -------------------------------- | ---------------------------------------- |
| `RUOLO`    | `anagrafiche.indirizzi`          | Indirizzo associato a un soggetto/ruolo. |
| `SOGGETTO` | `anagrafiche.indirizzi_soggetti` | Indirizzo anagrafico del soggetto.       |

---

### 📑 Campi esposti (principali)

| Colonna                      | Tipo                   | Descrizione                               |
| ---------------------------- | ---------------------- | ----------------------------------------- |
| `scope`                      | `text`                 | Ambito: `RUOLO` o `SOGGETTO`.             |
| `indirizzo_id`               | `bigint`               | PK della tabella di origine.              |
| `soggetto_id`                | `uuid`                 | Soggetto proprietario dell’indirizzo.     |
| `soggetto_ruolo_id`          | `bigint`               | Valorizzato solo se scope=RUOLO.          |
| `istanza_utility_id`         | `bigint`               | ID istanza utility (`anagrafiche.istanze_utilities.id`). Valorizzato solo se scope=RUOLO e indirizzo specifico per istanza. NULL per scope=SOGGETTO e per indirizzi generici. |
| `tipo_indirizzo_id`          | `integer`              | Tipo indirizzo (ID tecnico).              |
| `tipo_indirizzo_codice`      | `varchar`              | Codice del tipo indirizzo (display, `ti.codice`); il codice interno è `tipo_indirizzo_codice_interno`. |
| `tipo_indirizzo_descrizione` | `text`                 | Descrizione del tipo indirizzo.           |
| `is_normalizzato`            | `boolean`              | TRUE se basato su `indirizzi_dettaglio`.  |
| `indirizzo_dettaglio_id`     | `bigint`               | FK al dettaglio civico.                   |
| `indirizzo_display`          | `text`                 | Indirizzo human‑readable pronto per UI.   |
| `indirizzo_libero`           | `text`                 | Indirizzo libero (se non normalizzato).   |
| `comune_id`                  | `integer`              | Comune risolto.                           |
| `comune_descrizione`         | `text`                 | Nome comune.                              |
| `provincia_id`               | `integer`              | Provincia risolta.                        |
| `provincia_sigla`            | `text`                 | Sigla provincia.                          |
| `provincia_descrizione`      | `text`                 | Descrizione provincia.                    |
| `regione_id`                 | `integer`              | Regione risolta.                          |
| `regione_descrizione`        | `text`                 | Nome regione.                             |
| `stato_id`                   | `integer`              | Stato risolto.                            |
| `stato_iso2`                 | `text`                 | Codice ISO2 stato.                        |
| `stato_descrizione`          | `text`                 | Nome stato.                               |
| `codice_postale_id`          | `integer`              | ID del codice postale (se presente).      |
| `cap`                        | `text`                 | CAP/codice postale (se disponibile).      |
| `cap_codice`                 | `text`                 | Codice postale da tabella CAP.            |
| `geoloc`                     | `geometry(Point,4326)` | Geoloc risolta.                           |
| `locality`                   | `text`                 | Località (uso internazionale).            |
| `administrative_area`        | `text`                 | Area amministrativa (uso internazionale). |
| `sublocality`                | `text`                 | Sublocalità (uso internazionale).         |
| `postal_code`                | `text`                 | Codice postale libero della forma estera (facoltativo). Fino al 18-10-2026 si chiamava `postal_box`. |

(Sono esposti anche campi di audit e dettagli civico/stradario per completezza.)

---

### Modalità d’uso tipiche

```sql
-- Lista completa di indirizzi, con scope e formattazione standard
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_base
WHERE soggetto_id = :soggetto_id;
```

```sql
-- Solo indirizzi normalizzati
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_base
WHERE is_normalizzato = TRUE;
```

---

### Best practice e raccomandazioni

* Non utilizzare questa vista per DML: usare sempre le tabelle base.
* Usarla come sorgente unica per funzioni di lettura/risoluzione.
* Preferire le viste derivate quando serve filtrare per scope.

---

{% include-markdown "signature-core.md" %}
