## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_soggetto`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)    
> [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti)   
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)    
>
Approfondimenti viste:
>
[anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)    

---
### 🎯 Scopo Principale
(latest review 20-12-25)
La vista **`anagrafiche.vw_indirizzi_resolved_soggetto`** fornisce una rappresentazione **normalizzata e pronta all’uso** degli indirizzi **associati direttamente a un soggetto**, indipendentemente dai suoi ruoli.

Questa vista è pensata per gestire:

* indirizzi **anagrafici di base** (residenza, domicilio fiscale, corrispondenza);
* indirizzi **trasversali ai ruoli**, riutilizzabili in più contesti applicativi;
* indirizzi **liberi o internazionali**, non necessariamente normalizzati su stradario.

Gli obiettivi principali sono:

* Centralizzare la logica di **risoluzione indirizzo soggetto** in un unico oggetto SQL.
* Esporre un **output coerente** con quello degli indirizzi di ruolo (`vw_indirizzi_resolved_ruolo`).
* Fornire una **API SQL stabile** per UI, API REST e servizi di dominio.

La vista è **read-only** e rappresenta il **layer canonico di lettura** per gli indirizzi diretti del soggetto.

---

### Collegamenti principali

* **Tabelle sorgenti**:

  * `anagrafiche.indirizzi_soggetti`
  * `anagrafiche.soggetti`
  * `config.tipi_indirizzi`

* **Viste di supporto**:

  * `anagrafiche.vw_indirizzi_dettaglio` – per indirizzi normalizzati
  * `script.vw_indirizzo_completo` – per arricchimento geografico (comune, CAP, provincia)

* **Viste correlate**:

  * `anagrafiche.vw_indirizzi_resolved_ruolo`
  * `anagrafiche.vw_indirizzi_resolved_all`

---

### Struttura logica della vista

La vista parte dalla tabella `anagrafiche.indirizzi_soggetti` e applica:

* join su `config.tipi_indirizzi` per identificare e descrivere il tipo indirizzo;
* left join su `vw_indirizzi_dettaglio` se l’indirizzo è normalizzato;
* left join su `script.vw_indirizzo_completo` per arricchire i dati geografici anche per indirizzi liberi;
* costruzione di un campo `indirizzo_display` coerente e utilizzabile direttamente.

Il risultato è un record **"resolved"**, semanticamente completo e coerente con lo standard Zero ERP.

---

### 📑 Campi esposti (principali)

| Colonna                  | Tipo                   | Descrizione                                                |
| ------------------------ | ---------------------- | ---------------------------------------------------------- |
| `scope`                  | `text`                 | Costante `’SOGGETTO’`, identifica l’ambito dell’indirizzo. |
| `indirizzo_id`           | `bigint`               | PK della tabella `anagrafiche.indirizzi_soggetti`.         |
| `soggetto_id`            | `uuid`                 | Identificativo del soggetto.                               |
| `soggetto_ruolo_id`      | `bigint`               | Sempre NULL per questa vista.                              |
| `tipo_indirizzo_id`      | `integer`              | Tipo indirizzo.                                            |
| `tipo_indirizzo_codice`  | `varchar`              | Codice del tipo indirizzo (display, `ti.codice`), non il codice interno. |
| `tipo_indirizzo_codice_interno` | `varchar`       | Codice interno del tipo (`ti.codice_interno`, immutabile): la chiave per confronti e logica. Dal 2026-11-01, come la base. |
| `is_normalizzato`        | `boolean`              | TRUE se l’indirizzo è basato su `indirizzi_dettaglio`.     |
| `indirizzo_dettaglio_id` | `bigint`               | FK al dettaglio civico, se presente.                       |
| `indirizzo_display`      | `text`                 | Stringa pronta per UI/documenti.                           |
| `comune_descrizione`     | `text`                 | Comune (se disponibile).                                   |
| `cap`                    | `text`                 | Codice postale.                                            |
| `provincia`              | `text`                 | Sigla provincia.                                           |
| `geoloc`                 | `geometry(Point,4326)` | Geolocalizzazione risolta.                                 |

(La vista espone anche campi di audit e componenti internazionali.)

---

### Modalità d’uso tipiche

**1. Elenco indirizzi di un soggetto**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_soggetto
WHERE soggetto_id = :soggetto_id
ORDER BY tipo_indirizzo_codice;
```

**2. Recupero indirizzo per tipo (es. residenza)**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_soggetto
WHERE soggetto_id = :soggetto_id
  AND tipo_indirizzo_id = :tipo_indirizzo_id;
```

**3. Uso come fallback rispetto agli indirizzi di ruolo**

Questa vista è tipicamente utilizzata come **secondo livello di lookup**, quando un indirizzo non è definito a livello di ruolo.

---

### Best practice e raccomandazioni

* Utilizzare questa vista per leggere indirizzi **anagrafici generali** del soggetto.
* Non duplicare indirizzi di ruolo in questa tabella: il loro ambito corretto è `anagrafiche.indirizzi`.
* In caso di ambiguità tra indirizzi soggetto e ruolo, delegare la risoluzione alle funzioni applicative (`fn_get_indirizzo_resolved`).
* Considerare la vista come **contratto stabile** per API e servizi.

---

{% include-markdown "signature-core.md" %}
