# 📘 Documentazione tecnica – Struttura degli schemi in Zero ERP

Questa guida descrive la struttura logica degli schemi utilizzati nel progetto **Zero ERP**, con lo scopo di standardizzare, organizzare e semplificare lo sviluppo collaborativo e la manutenzione del sistema.

---

## 🧱 Schemi principali

### 1. `anagrafiche`
Contiene tutte le tabelle legate all'anagrafica soggetti (persone fisiche e giuridiche).

- Esempi: `soggetti`, `indirizzi`, `contatti`
- Usa identificatori UUID e naming coerente

### 2. `config`
Contiene tabelle di configurazione parametrica e lookup.

- Esempi: `stati`, `nazioni`, `contatti_ruoli`
- Normalizzazione forte, spesso referenziate da altri schemi

### 3. `script`
Contiene tutta la logica applicativa: viste e funzioni **legate direttamente ai processi funzionali** del sistema ERP.

- Esempi: `vw_clienti_attivi`, `fn_calcolo_fattura()`
- Contiene anche funzioni come `fn_get_stradario_by_indirizzo()` o `fn_get_stradario()`

#### 📌 Esempio funzione `fn_get_stradario`

```sql
-- FUNCTION: script.fn_get_stradario(p_comune_id INT DEFAULT NULL, p_indirizzo TEXT DEFAULT '')
-- Restituisce lo stradario filtrato per comune, oppure libera ricerca su tutto il territorio
-- DROP FUNCTION IF EXISTS script.fn_get_stradario(INT, TEXT);
```

Questa funzione accetta:
- `comune_id`: se presente, filtra le vie del solo comune
- `indirizzo`: testo per ricerca parziale (opzionale)

> Se `comune_id IS NOT NULL`, esegue una ricerca **specifica per comune**.
> Altrimenti esegue una ricerca **generale** su tutte le vie italiane.

### 4. `dbops`
Contiene funzioni e viste **tecniche** di supporto, analisi e manutenzione del database.

- Naming storico: inizialmente `devops`, poi trasformato in `dbops` per rappresentare meglio lo scopo
- Esempi: `vw_function_list`, `fn_foreign_keys_info(text)`, `vw_fk_senza_indice`
- Nessuna logica applicativa, solo strumenti per DBA e manutentori

#### 📌 Esempio funzione `fn_foreign_keys_info`
```sql
-- FUNCTION: dbops.fn_foreign_keys_info(text)
-- DROP FUNCTION IF EXISTS dbops.fn_foreign_keys_info(text);
```

### 5. `storico`
Contiene tutte le tabelle che hanno necessità di mantenere uno **storico temporale delle modifiche**.

- Esempi: `soggetti_storico`, `contratti_storico`
- Usato per audit, confronto tra versioni, report su dati passati

---

## 📏 Convenzioni di naming

| Oggetto         | Convenzione                             | Esempio                          |
|----------------|-----------------------------------------|----------------------------------|
| Schema         | minuscolo, singolare                    | `anagrafiche`, `config`, `dbops` |
| Tabella        | plurale                                 | `soggetti`, `fatture`            |
| Colonna ID     | `id` (UUID) /SERIAL                     | 'id'                             |
| FK             | `nome_campo_id`                         | `contatto_ruolo_id`,`soggetto_id`|
| Vista          | prefisso `vw_`                          | `vw_clienti_attivi`              |
| Funzione       | prefisso `fn_`, nomi descrittivi        | `fn_calcolo_totale()`            |
| View tecnica   | in `dbops`, senza prefissi extra        | `vw_function_list`               |

> ℹ️ Nota: inizialmente la funzione `foreign_keys_info()` non rispettava il prefisso `fn_`. Ora è correttamente rinominata `fn_foreign_keys_info()`.

---

## 🧪 Strumenti DB integrati in `dbops`

| Nome vista/funzione         | Scopo                                                      |
|-----------------------------|-------------------------------------------------------------|
| `vw_function_list`          | Elenco di tutte le funzioni in `dbops` e `script`          |
| `vw_catalogo_oggetti`       | Elenco oggetti tecnici nello schema `dbops`                |
| `vw_fk_senza_indice`        | FK senza indice esplicito per validazione e tuning         |
| `fn_foreign_keys_info(text)`| Analisi FK in entrata/uscita da una tabella                |

---

## 🔄 Evoluzioni future

- Possibile separazione in moduli: `fatturazione`, `contratti`, `clienti`, `magazzino`
- Integrazione con API REST e dashboard interattive (es. Vue/PrimeVue)
- Gestione versionamento schema tramite CI/CD
- Espansione dello schema `storico` per audit e verifica temporale

---

> 🧠 *“Struttura chiara = manutenzione felice.”*  
> Zero ERP cresce punta a: Documenta, nomina bene, condividi meglio.
