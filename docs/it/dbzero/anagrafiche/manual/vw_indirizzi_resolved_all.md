## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_indirizzi_resolved_all`

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**
>
Approfondimenti viste:
>
[anagrafiche.vw_indirizzi_resolved_ruolo](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo)    
> [anagrafiche.vw_indirizzi_resolved_soggetto](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto)   
> [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)   
>
Approfondimenti tabelle:
>
[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)   
> [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti)   
> [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)   

---
### 🎯 Scopo Principale
(latest review 20-12-25)
La vista **`anagrafiche.vw_indirizzi_resolved_all`** rappresenta il **punto unico e canonico di lettura** degli indirizzi in Zero ERP.

Legge **`anagrafiche.vw_indirizzi_resolved_base`** senza filtro di scope, quindi riporta insieme:

* gli indirizzi legati direttamente al soggetto (`scope = 'SOGGETTO'`, come `vw_indirizzi_resolved_soggetto`);
* gli indirizzi legati a un soggetto/ruolo (`scope = 'RUOLO'`, come `vw_indirizzi_resolved_ruolo`).

Le tre viste derivate hanno le **stesse colonne della base**, nello stesso ordine: una colonna nuova della base si aggiunge anche a loro (presidio `db/pgtap/anagrafiche/test-vw-indirizzi-resolved-derivate-codice-interno-v1.sql`).

L’obiettivo è fornire un **formato di output uniforme** che consenta:

* Query applicative semplici (“dammi tutti gli indirizzi di un soggetto”) senza conoscere il modello interno.
* Implementazione robusta di funzioni di dominio (resolver) che possono applicare:

  * priorità (ruolo → soggetto o viceversa),
  * fallback basati su matrici configurabili,
  * strategie di default per documenti (fatture/DDT/contratti).
* Riduzione drastica della duplicazione di join e di logiche di formatting nel codice SQL e nel backend.

La vista è **read-only** dal punto di vista logico: tutte le modifiche avvengono sulle tabelle base.

---

### Scelte progettuali e motivazioni

**Perché una vista unificata?**

1. **Contratto stabile verso l’applicazione**

   * API/UI possono interrogare un solo oggetto senza dover conoscere dove risiede l’indirizzo (soggetto o ruolo).

2. **Separazione dei livelli**

   * “Storage” su tabelle (`indirizzi`, `indirizzi_soggetti`)
   * “Presentation/Read model” su viste (`vw_indirizzi_resolved_*`)

3. **Supporto completo a indirizzi normalizzati e liberi**

   * `indirizzo_dettaglio_id` → join su `vw_indirizzi_dettaglio`
   * `indirizzo_libero` + campi internazionali → display coerente

4. **Facilita l’evoluzione**

   * In futuro si possono aggiungere:

     * gestione multi-indirizzo per tipo,
     * ranking/priorità,
     * filtri tenant/istanza,
     * formattazioni avanzate
       senza cambiare il contratto applicativo.

---

### Struttura logica della vista

La vista è la proiezione della base, colonna per colonna:

```sql
SELECT scope, source, indirizzo_id, …, tipo_indirizzo_codice_interno
FROM anagrafiche.vw_indirizzi_resolved_base;
```

Il corpo esatto è nella [pagina della vista](/dbzero/anagrafiche/views/vw_indirizzi_resolved_all). La UNION ALL fra i due layer (`anagrafiche.indirizzi` e `anagrafiche.indirizzi_soggetti`) sta nella base: lì i record arrivano da tabelle diverse, e la provenienza resta in `scope` e negli ID.

---

### Semantica di `scope`

La colonna `scope` permette di distinguere chiaramente:

| scope      | Origine                          | Significato                                                 |
| ---------- | -------------------------------- | ----------------------------------------------------------- |
| `SOGGETTO` | `anagrafiche.indirizzi_soggetti` | Indirizzo anagrafico generale del soggetto                  |
| `RUOLO`    | `anagrafiche.indirizzi`          | Indirizzo specifico per un ruolo (cliente, fornitore, ecc.) |

Questa distinzione è fondamentale per:

* risoluzione indirizzi con priorità (es. documenti di vendita → ruolo)
* audit/debug (“da dove arriva questo indirizzo?”)
* API che espongono l’origine del dato

---

### 📑 Campi esposti (principali)

La vista espone un set uniforme di campi, coerente con le due viste sottostanti.

| Colonna                      | Tipo                   | Descrizione                                     |
| ---------------------------- | ---------------------- | ----------------------------------------------- |
| `scope`                      | `text`                 | Ambito: `SOGGETTO` o `RUOLO`.                   |
| `indirizzo_id`               | `bigint`               | PK della tabella di origine (varia per scope).  |
| `soggetto_id`                | `uuid`                 | Soggetto proprietario dell’indirizzo.           |
| `soggetto_ruolo_id`          | `bigint`               | Valorizzato solo se scope=RUOLO.                |
| `tipo_indirizzo_id`          | `integer`              | Tipo indirizzo.                                 |
| `tipo_indirizzo_codice`      | `varchar`              | Codice del tipo indirizzo (display, `ti.codice`), non il codice interno. |
| `tipo_indirizzo_codice_interno` | `varchar`          | Codice interno del tipo (`ti.codice_interno`, immutabile): la chiave per confronti e logica. Dal 2026-11-01, come la base. |
| `tipo_indirizzo_descrizione` | `text`                 | Descrizione del tipo indirizzo.                 |
| `is_normalizzato`            | `boolean`              | TRUE se `indirizzo_dettaglio_id` è valorizzato. |
| `indirizzo_dettaglio_id`     | `bigint`               | FK al dettaglio civico se normalizzato.         |
| `indirizzo_display`          | `text`                 | Stringa pronta per UI/documenti.                |
| `comune_id`                  | `integer`              | Comune (da dettaglio o da dati liberi).         |
| `comune_descrizione`         | `text`                 | Comune (se disponibile).                        |
| `cap`                        | `text`                 | CAP/codice postale (se disponibile).            |
| `provincia`                  | `text`                 | Provincia (se disponibile).                     |
| `geoloc`                     | `geometry(Point,4326)` | Geoloc risolta.                                 |

Sono esposti anche i campi tecnici/audit (tx_id, data/user insert/update) e i componenti internazionali.

---

### Modalità d’uso tipiche

**1) Elenco completo indirizzi di un soggetto**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_all
WHERE soggetto_id = :soggetto_id
ORDER BY scope, tipo_indirizzo_codice;
```

**2) Elenco indirizzi “solo ruolo” (utile per documenti)**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_all
WHERE soggetto_ruolo_id = :soggetto_ruolo_id
ORDER BY tipo_indirizzo_codice;
```

**3) Query per tipo indirizzo (senza sapere se soggetto o ruolo)**

```sql
SELECT *
FROM anagrafiche.vw_indirizzi_resolved_all
WHERE soggetto_id = :soggetto_id
  AND tipo_indirizzo_id = :tipo_indirizzo_id;
```

**4) Base per funzioni di dominio “resolver”**

Questa vista è progettata per diventare la sorgente primaria di:

* `fn_list_indirizzi(...)` – lista parametrica
* `fn_get_indirizzo_resolved(...)` – risoluzione singola con fallback e priorità

---

### Performance e indicizzazioni consigliate

Le prestazioni dipendono dalle tabelle sottostanti; si raccomandano:

* `anagrafiche.indirizzi`: indice su `(soggetto_ruolo_id, tipo_indirizzo_id)`
* `anagrafiche.indirizzi_soggetti`: indice su `(soggetto_id, tipo_indirizzo_id)`
* `anagrafiche.indirizzi_dettaglio`: indice su `stradario_id` + unique su combinazione civico

Per la vista “all” non si creano indici (a meno di materializzazione).

---

### Best practice e raccomandazioni

* Usare questa vista come **entry point unico** per qualunque lettura indirizzi in applicazione.
* Non “bypassare” direttamente le tabelle nelle query applicative: si perde uniformità e si duplicano logiche.
* Per selezionare un solo indirizzo in modo deterministico, usare una funzione resolver (evita ambiguità in caso futuro di multi-indirizzo).
* Mantenere la vista coerente e stabile nel tempo: aggiungere colonne è ok, cambiare semantica no.

---

{% include-markdown "signature-core.md" %}
