## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_ruolo`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)   
> [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)   
>
Approfondimenti viste:
>
[anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)  

---
### 🎯 Scopo Principale
(latest review 20‑12‑25)
La vista **`anagrafiche.vw_indirizzi_resolved_ruolo`** fornisce una rappresentazione **unificata, pronta all’uso e semanticamente ricca** degli indirizzi associati a uno **specifico ruolo di un soggetto** (es. cliente, fornitore, punto di fornitura).

Gli obiettivi principali sono:

* Centralizzare in un unico oggetto SQL la **risoluzione completa dell’indirizzo** (normalizzato o libero).
* Offrire un **formato di output stabile** per l’uso applicativo (API, documenti, report).
* Evitare la duplicazione di logica di join tra:

  * `anagrafiche.indirizzi`
  * `anagrafiche.indirizzi_dettaglio`
  * `config.tipi_indirizzi`
* Rendere trasparente la distinzione tra indirizzi:

  * **normalizzati** (con riferimento a stradario/civico),
  * **liberi / internazionali**.

La vista è **read‑only** e costituisce il **layer canonico di lettura** per gli indirizzi di ruolo.

---

### Collegamenti principali

* **Tabelle sorgenti**:

  * `anagrafiche.indirizzi`
  * `anagrafiche.soggetti_ruoli`
  * `config.tipi_indirizzi`

* **Viste di supporto**:

  * `anagrafiche.vw_indirizzi_dettaglio` – per indirizzi normalizzati
  * `script.vw_indirizzo_completo` – per arricchimento geografico (comune, CAP, provincia)

* **Viste derivate**:

  * `anagrafiche.vw_indirizzi_resolved_all`

---

### Struttura logica della vista

La vista parte dalla tabella `anagrafiche.indirizzi` (indirizzi per ruolo) e applica:

* join su `anagrafiche.soggetti_ruoli` per risalire al `soggetto_id`;
* join su `config.tipi_indirizzi` per arricchire il tipo indirizzo;
* left join su `vw_indirizzi_dettaglio` se l’indirizzo è normalizzato;
* left join su `script.vw_indirizzo_completo` per completare i dati geografici anche per indirizzi liberi.

Il risultato è un record **"resolved"**, pronto per il consumo applicativo.

---

### 📑 Campi esposti (principali)

| Colonna                  | Tipo                   | Descrizione                                             |
| ------------------------ | ---------------------- | ------------------------------------------------------- |
| `scope`                  | `text`                 | Costante `’RUOLO’`, identifica l’ambito dell’indirizzo. |
| `indirizzo_id`           | `bigint`               | PK della tabella `anagrafiche.indirizzi`.               |
| `soggetto_id`            | `uuid`                 | Soggetto a cui appartiene il ruolo.                     |
| `soggetto_ruolo_id`      | `bigint`               | Identificativo del ruolo.                               |
| `tipo_indirizzo_id`      | `integer`              | Tipo indirizzo (FK logica).                             |
| `tipo_indirizzo_codice`  | `varchar`              | Codice del tipo indirizzo (display, `ti.codice`), non il codice interno. |
| `tipo_indirizzo_codice_interno` | `varchar`       | Codice interno del tipo (`ti.codice_interno`, immutabile): la chiave per confronti e logica. Dal 2026-11-01, come la base. |
| `is_normalizzato`        | `boolean`              | TRUE se basato su `indirizzi_dettaglio`.                |
| `indirizzo_dettaglio_id` | `bigint`               | FK al dettaglio civico, se presente.                    |
| `indirizzo_display`      | `text`                 | Stringa pronta per UI/documenti.                        |
| `comune_descrizione`     | `text`                 | Nome comune (se disponibile).                           |
| `cap`                    | `text`                 | Codice postale.                                         |
| `provincia`              | `text`                 | Sigla provincia.                                        |
| `geoloc`                 | `geometry(Point,4326)` | Geolocalizzazione risolta.                              |

(Altri campi tecnici e di audit sono esposti per completezza.)

---

### Modalità d’uso tipiche

**1. Recupero indirizzi di un ruolo**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_ruolo
WHERE soggetto_ruolo_id = :soggetto_ruolo_id;
```

**2. Recupero indirizzo per tipo**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_ruolo
WHERE soggetto_ruolo_id = :soggetto_ruolo_id
  AND tipo_indirizzo_id = :tipo_indirizzo_id;
```

**3. Supporto a documenti (fatture, DDT, contratti)**

La colonna `indirizzo_display` è pensata per essere utilizzata direttamente nei documenti senza ulteriori formattazioni.

---

### Best practice e raccomandazioni

* Utilizzare questa vista come **unica fonte** per leggere indirizzi di ruolo.
* Non eseguire DML sulla vista: usare sempre `anagrafiche.indirizzi`.
* Per logiche di fallback o selezione avanzata, delegare alle funzioni applicative (`fn_get_indirizzo_resolved`).
* Considerare questa vista come **API SQL stabile** verso il mondo applicativo.

---

{% include-markdown "signature-core.md" %}
