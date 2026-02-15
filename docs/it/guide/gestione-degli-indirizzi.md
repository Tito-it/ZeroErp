# 🌱 Guida alla Gestione degli Indirizzi
Questa guida illustra l’architettura, le scelte progettuali e i componenti coinvolti nella gestione degli indirizzi in Zero ERP.

> (latest review 15-02-26)
>
> 👀 **Vedi anche**
>
> * [`Guida Soggetti & Ruoli`](/guide/soggetti-e-ruoli-anagrafici)  
> **All'interno si trova l'appendice per le funzionalità indirizzo ruolo/soggetto** 

---
 
## 1. Principi Progettuali

1. **Unicità e non duplicazione**

   * Il dettaglio civico [`anagrafiche.indirizzi_dettaglio`](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) è unico: vincolo `UNIQUE(via_norm, civico_norm, interno, piano, palazzina)` impedisce duplicati.

2. **Centralizzazione dei dati geografici**

   * Stati, regioni, province, comuni, CAP, toponomastica e stradario risiedono nello schema **`config`**, con le chiavi esterne in **`anagrafiche`**.

3. **Storicizzazione trasparente**

   * Tutte le modifiche a `config.stradario` e `anagrafiche.indirizzi` sono salvate in **`storico.*`** con snapshot JSONB, tipi operazione (A/U/D) e transazione **tx_id**, tramite la trigger-function generica [`script.trgfn_storico_generic()`](/dbzero/script/funzioni/trgfn_storico_generic).


4. **Fallback storico/originario**

   * Le helper [`script.fn_get_snapshot_as_of()`](/dbzero/script/funzioni/fn_get_snapshot_as_of) e [`script.fn_get_record_id_as_of()`](/dbzero/script/funzioni/fn_get_record_id_as_of) permettono di leggere il JSONB di un record “as of” una data, utile per audit e rendicontazione.

5. **Supporto indirizzi “liberi”**

   * In importazioni o migrazioni, [`anagrafiche.indirizzi`](/dbzero/anagrafiche/tabelle/indirizzi) accetta `indirizzo_libero` senza FK, con check constraint che evita mix errati di campi.

---

## 2. Schema Tabellare

### 2.1. Configurazione Geografica (`config`)

* **[config.stati](/dbzero/config/tabelle/stati)** : Stati con `iso_code2`, `iso_code3`.
* **[config.regioni](/dbzero/config/tabelle/regioni)**, **[config.province](/dbzero/config/tabelle/province)**, **[config.comuni](/dbzero/config/tabelle/comuni)**: gerarchia geografica.
* **[config.codici_postali](/dbzero/config/tabelle/codici_postali)**: CAP per comune.
* **[config.toponomastica](/dbzero/config/tabelle/toponomastica)**: tipologie di toponimo (via, strada, etc.).
* **[config.stradario_generale](/dbzero/config/tabelle/stradario_generale)**: anagrafica delle vie (toponomastica + nome.).
* **[config.stradario](/dbzero/config/tabelle/stradario)**: stradario per via di un luogo (comune + stradario_generale).
* **[config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)**: classi di indirizzo(residenza, posta, etc.).

### 2.2. Dettaglio Civico e Associazione (`anagrafiche`)

* **[anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio)**: via_norm, civico_norm, interno, piano, palazzina, geoloc.
* **[anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)**: associa il **ruolo** (`soggetto_ruolo_id`) a indirizzo normalizzato (`indirizzi_dettaglio_id`) o libero (`indirizzo_libero`, `comune_id`, ecc.).

### 2.3. Storico (`storico`)

* **[storico.stradario](/dbzero/storico/tabelle/stradario)**, **[storico.indirizzi](/dbzero/storico/tabelle/indirizzi)**, **[storico.indirizzi_dettaglio](/dbzero/storico/tabelle/indirizzi_dettaglio)**: snapshot JSONB con periodi di validità e tx_id.

---

## 3. Funzioni e Trigger Coinvolti

| **Oggetto**                                                                                                           | **Tipo**         | **Descrizione**                                          |
| --------------------------------------------------------------------------------------------------------------------- | ---------------- | -------------------------------------------------------- |
| [script.fn_get_parameter_full(...)](/dbzero/script/funzioni/fn_get_parameter_full)                                    | helper           | Parametri e override (tenant, user, session, funzione)   |
| [script.fn_get_default_by_param(...)](/dbzero/script/funzioni/fn_get_default_by_param)                                | helper           | Default generico da lookup table + parametro             |
| [script.fn_get_snapshot_as_of(...)](/dbzero/script/funzioni/fn_get_snapshot_as_of)                                    | helper           | JSONB snapshot “as of” data                              |
| [script.fn_get_record_id_as_of(...)](/dbzero/script/funzioni/fn_get_record_id_as_of)                                  | helper           | ID record “as of” data, solo storico                     |
| [script.fn_generate_codice(tipo)](/dbzero/script/funzioni/fn_generate_codice)                                         | helper           | Genera codici progressivi da `sistema_codici`            |
| [script.trgfn_storico_generic()](/dbzero/script/funzioni/trgfn_storico_generic)                                       | trigger function | Storicizzazione generica con JSONB snapshot              |
| [script.trgfn_sync_stato_iso2()](/dbzero/script/funzioni/trgfn_sync_stato_iso2)                                       | trigger function | Sincronizza `stato_iso2` da `config.stati`               |
| [script.trgfn_generate_codice_generic()](/dbzero/script/funzioni/trgfn_generate_codice_generic)                       | trigger function | Generica per `codice_<entità>`, usa `fn_generate_codice` |
| [anagrafiche.trgfn_indirizzi_dettaglio_normalize()](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) | trigger function | Normalizza `via_norm`, `civico_norm`                     |

---

## 4. Flusso di Vita di un Indirizzo

1. **Inserimento**: normalizzazione via trigger su `indirizzi_dettaglio` o inserimento di `indirizzo_libero`.
2. **Associazione**: `anagrafiche.indirizzi` collega il ruolo (`soggetto_ruolo_id`) a riga di dettaglio o a indirizzo libero; `anagrafiche.indirizzi_soggetti` copre il layer identitario del soggetto.
3. **Storicizzazione**: `trgfn_storico_generic('indirizzi_id')` registra snapshot.
4. **Lettura storica**: `fn_get_snapshot_as_of()`/`fn_get_record_id_as_of()` ricostruiscono lo stato di un record a una data.

---

## 5. Importazioni e Indirizzi Liberi

* Durante migrazioni di massa, si popola `indirizzo_libero` senza forzare FK a `indirizzi_dettaglio`.
* Check constraints assicurano che non si mischino dati normalizzati e liberi.
* Il flag `storicizza` (booleano) permette di disabilitare temporaneamente la storicizzazione per carichi massivi.

---

## 6. Riclassificazione Vie (Caso A/B)

Questa sezione descrive una **policy unica** per gestire variazioni di vie/comuni mantenendo coerenza dei dati e storicizzazione completa.

### ✅ Policy operativa unica

Per tutte le casistiche (rinomina parziale, rinomina totale, fusione vie, variazioni comuni) si adotta la stessa logica:

1. **Creare il nuovo riferimento in configurazione**
   * Vie: nuova riga in `config.stradario_generale` e relativo record in `config.stradario`.
   * Comuni: nuovo riferimento in `config.comuni` (o aggiornamento coerente con le regole di dominio).
2. **Allineare gli indirizzi coinvolti**
   * Aggiornare **solo** le righe di `anagrafiche.indirizzi_dettaglio` interessate, puntandole al nuovo riferimento.
3. **Rinormalizzare**
   * I trigger di normalizzazione aggiornano `via_norm` e `indirizzo_normalizzato`.
4. **Storico garantito**
   * Le modifiche sono tracciate in `storico.stradario` e in `storico.indirizzi_dettaglio` (e, se rilevante, nello storico dei comuni).

Per la riclassificazione e' prevista la procedura `maintenance.proc_bump_indirizzi_dettaglio(...)`, che abilita la manutenzione e forza la rinormalizzazione degli indirizzi collegati.

### Esempi applicativi

* **Rinomina totale via**: nuova via + riallineamento di tutti i civici collegati al vecchio `stradario_id`.
* **Rinomina parziale via**: nuova via + riallineamento solo dei civici del tratto interessato.
* **Fusione vie**: riallineamento dei civici su un unico `stradario_id`.

### 🧩 Nota su manutenzione toponomastica

La correzione di un toponimo non avviene modificando la riga in uso:  
si crea una **nuova** voce in `config.toponomastica`, si riallineano i record di `config.stradario_generale` interessati e si lascia che la normalizzazione aggiorni `indirizzo_normalizzato`.

### ⚠️ Manutenzione straordinaria (riclassificazione controllata)

Le seguenti procedure sono riservate a **manutenzione straordinaria** e vanno usate solo in contesti controllati:

* [`maintenance.proc_bump_toponomastica`](/dbzero/maintenance/funzioni/proc_bump_toponomastica) — correzione toponimo con riallineamento automatico di `stradario_generale`.
* **[`maintenance.proc_bump_indirizzi_dettaglio`](/dbzero/maintenance/funzioni/proc_bump_indirizzi_dettaglio)** — riallineamento degli indirizzi civici dopo riclassificazione.

---

*Questa guida copre l’intero ciclo di vita e le componenti software per la gestione degli indirizzi in Zero ERP: dalla tabella geografica di base, al dettaglio civico, fino alle funzioni di audit e storicizzazione.*

### 7. Diagramma ER
```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%  
erDiagram
    stati              ||--o{ regioni             : has
    regioni            ||--o{ province            : has
    province           ||--o{ comuni              : has
    comuni             ||--o{ codici_postali      : has

    toponomastica      ||--o{ stradario_generale  : has
    stradario_generale ||--o{ stradario           : has

    stradario          ||--o{ indirizzi_dettaglio : uses
    indirizzi_dettaglio||--o{ indirizzi           : assigned_to

    comuni             ||--o{ indirizzi           : uses
    codici_postali     ||--o{ indirizzi           : uses
    stati              ||--o{ indirizzi           : uses

    indirizzi          ||--o{ storico_indirizzi   : history
    stradario          ||--o{ storico_stradario    : history
```

---
## 8. Appendice – Indirizzi per Ruolo e per Soggetto

Questa appendice descrive la separazione tra indirizzi **per ruolo** e **per soggetto**, le motivazioni e gli oggetti tecnici introdotti per la consultazione coerente.

### 8.1. Motivazioni e funzionamento

* **Indirizzi per ruolo (`anagrafiche.indirizzi`)**
  - Rappresentano indirizzi operativi legati a un ruolo (cliente, fornitore, gestore, ecc.).
  - Sono usati per documenti, processi e flussi specifici di ruolo.

* **Indirizzi per soggetto (`anagrafiche.indirizzi_soggetti`)**
  - Rappresentano indirizzi identitari del soggetto (es. residenza, sede legale primaria).
  - Sono indipendenti dai ruoli e possono essere usati come fallback.

* **Policy di risoluzione (master/fallback)**
  - **Master**: indirizzo del ruolo (`anagrafiche.indirizzi`).
  - **Fallback**: indirizzo del soggetto (`anagrafiche.indirizzi_soggetti`) solo quando il layer ruolo non risolve il tipo richiesto.
  - Nei processi critici, se mancano entrambi, il comportamento atteso è fail-closed (errore bloccante).

* **Regole di coerenza (indirizzi liberi)**
  - La modalità normalizzata è sempre preferibile.
  - Gli indirizzi liberi sono ammessi solo quando `indirizzo_dettaglio_id` è `NULL`,
    con obbligo di `indirizzo_libero`, `stato_id` e una struttura minima:
    **(comune + CAP)** oppure **(locality + postal_box)** con almeno uno tra
    `administrative_area` e `sublocality`.

### 8.2. Viste “resolved”

Le viste resolved centralizzano la composizione dell’indirizzo human‑readable e i campi territoriali:

* [`anagrafiche.vw_indirizzi_resolved_base`](/dbzero/anagrafiche/views/vw_indirizzi_resolved_base)
* [`anagrafiche.vw_indirizzi_resolved_ruolo`](/dbzero/anagrafiche/views/vw_indirizzi_resolved_ruolo)
* [`anagrafiche.vw_indirizzi_resolved_soggetto`](/dbzero/anagrafiche/views/vw_indirizzi_resolved_soggetto)
* [`anagrafiche.vw_indirizzi_resolved_all`](/dbzero/anagrafiche/views/vw_indirizzi_resolved_all)
* [`anagrafiche.vw_indirizzi_dettaglio`](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio)

Nota:
* Le viste resolved espongono anche la provenienza (`source`: `RUOLO` / `SOGGETTO`) come campo derivato utile per audit/debug.

### 8.3. Funzioni di lettura

* [`script.fn_get_indirizzi_by_ruolo`](/dbzero/script/funzioni/fn_get_indirizzi_by_ruolo)
* [`script.fn_get_indirizzo`](/dbzero/script/funzioni/fn_get_indirizzo)
* [`script.fn_get_indirizzi_by_soggetto`](/dbzero/script/funzioni/fn_get_indirizzi_by_soggetto)
* [`script.fn_get_indirizzo_by_soggetto`](/dbzero/script/funzioni/fn_get_indirizzo_by_soggetto)

### 8.4. Diagramma logico (ruolo vs soggetto)

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    soggetti        ||--o{ indirizzi_soggetti : has
    soggetti        ||--o{ soggetti_ruoli : has
    soggetti_ruoli  ||--o{ indirizzi : has

    indirizzi_dettaglio ||--o{ indirizzi : normalized_by
    indirizzi_dettaglio ||--o{ indirizzi_soggetti : normalized_by

    indirizzi           ||--o{ vw_indirizzi_resolved_ruolo : resolved
    indirizzi_soggetti  ||--o{ vw_indirizzi_resolved_soggetto : resolved
    vw_indirizzi_resolved_ruolo ||--o{ vw_indirizzi_resolved_all : union
    vw_indirizzi_resolved_soggetto ||--o{ vw_indirizzi_resolved_all : union
```

### 8.5. Validazione pgTAP (stato punto 2.4)

Il punto **2.4 - Doppio layer indirizzi (ruolo/soggetto)** e' validato da:

* `db/pgtap/anagrafiche/test-indirizzi-fallback.sql`

Copertura attuale (14 assert):

1. Presenza Gestore di test.
2. Presenza tipi indirizzo minimi (`RES`, `SEDELEG`).
3. Upsert idempotente di `indirizzi_dettaglio`.
4. Pre-condizione: assenza indirizzi ruolo `RES/SEDELEG/SEDEOP`.
5. Guard: blocco inserimento `RES` su Gestore.
6. Verifica post-guard: nessun `RES` inserito.
7. Inserimento `SEDELEG` su ruolo riuscito.
8. Fallback `fn_get_indirizzo(..., 'SEDEOP') -> SEDELEG`.
9. Coerenza `fn_get_indirizzi_by_ruolo` con `vw_indirizzi_resolved_base` (`scope='RUOLO'`).
10. Presenza `SEDELEG` in `fn_get_indirizzi_by_ruolo`.
11. Coerenza `fn_get_indirizzi_by_soggetto` con `vw_indirizzi_resolved_base` (`scope='SOGGETTO'`).
12. Dominio `source` valido in `vw_indirizzi_resolved_all` (`RUOLO`/`SOGGETTO`).
13. `SEDELEG` di ruolo in `vw_indirizzi_resolved_all` con `source='RUOLO'`.
14. Coerenza cardinalita: `vw_indirizzi_resolved_all = vw_indirizzi_resolved_ruolo + vw_indirizzi_resolved_soggetto`.

---
{% include-markdown "signature-core.md" %}
