**Relazione sulla Gestione degli Indirizzi e dello Stradario**

Questa relazione riassume le scelte di design, le tabelle e le funzioni implementate per la gestione degli indirizzi  , il catalogo stradario normalizzato, il legame con i **tipi_indirizzi** e **soggetti_ruoli**, e la storicizzazione dei dati. Sono inclusi esempi di utilizzo.

---

## 1. Stradario Normalizzato (config)

### 1.1. Tabelle principali
- **config.stradario_generale**: catalogo delle vie (es. `id=1, toponomastica_id=VIA, descrizione='ROMA', descrizione_breve='RM'`).
- **config.stradario**: associa ogni `via_id` a un `comune_id`, `codice_postale_id`, e una `geoloc` di via.

### 1.2. Funzione di lookup
- **script.fn_get_stradario(comune_id, partial_text)**: restituisce elenco di vie filtrate per comune e testo, con campi utili (via_id, codice_postale, geoloc, descrizione_completa).

---

## 2. Dettaglio Civico (anagrafiche.indirizzi_dettaglio)

### 2.1. Schema
```sql
CREATE TABLE anagrafiche.indirizzi_dettaglio (
  id SERIAL PRIMARY KEY,
  via_id INTEGER NOT NULL REFERENCES config.stradario(id),
  civico INTEGER,
  estensione_civico VARCHAR(10),
  palazzina VARCHAR(50),
  interno VARCHAR(10),
  piano VARCHAR(10),
  civic_geoloc geometry(Point,4326),
  altro TEXT,
  via_norm TEXT NOT NULL,
  civico_norm TEXT NOT NULL,
  CONSTRAINT uq_indirizzi_dettaglio_norm UNIQUE(via_norm, civico_norm, interno, piano, palazzina)
);
```
### 2.2. Normalizzazione
- Trigger/function (`dbops.fn_normalize_indirizzo` o trigger) che sfrutta `script.fn_get_stradario` per popolare `via_norm`, `civico_norm`, `civic_geoloc`, e identificare via_id.

### 2.3. Flusso di inserimento
1. **Ricerca**: utente digita "Via Roma 10" → chiamata a `script.fn_get_stradario`.
2. **Corrispondenza**: se esiste, si ottiene `via_id`, `geoloc`, `codice_postale`; altrimenti fallback.
3. **Insert** in `indirizzi_dettaglio`, scatenando la normalizzazione.

---

## 3. Indirizzi Contestualizzati (anagrafiche.indirizzi)

### 3.1. Schema
```sql
CREATE TABLE anagrafiche.indirizzi (
  id SERIAL PRIMARY KEY,
  soggetto_ruolo_id INTEGER NOT NULL REFERENCES anagrafiche.soggetti_ruoli,
  tipo_indirizzo_id INTEGER NOT NULL REFERENCES config.tipi_indirizzi,
  indirizzi_dettaglio_id INTEGER REFERENCES anagrafiche.indirizzi_dettaglio ON DELETE SET NULL,
  indirizzo_libero TEXT,
  comune_id INTEGER REFERENCES config.comuni ON DELETE SET NULL,
  codice_postale_id INTEGER REFERENCES config.codici_postali ON DELETE SET NULL,
  stato_id INTEGER REFERENCES config.stati ON DELETE SET NULL,
  administrative_area VARCHAR(100),
  locality VARCHAR(100),
  sublocality VARCHAR(100),
  postal_box VARCHAR(20),
  geoloc geometry(Point,4326),
  data_insert TIMESTAMP NOT NULL,
  user_insert VARCHAR(80) NOT NULL,
  data_update TIMESTAMP NOT NULL,
  user_update VARCHAR(80) NOT NULL,
  CONSTRAINT uq_indirizzi_dettaglio UNIQUE(soggetto_ruolo_id,tipo_indirizzo_id,indirizzi_dettaglio_id),
  CONSTRAINT uq_indirizzi_libero UNIQUE(soggetto_ruolo_id,tipo_indirizzo_id,indirizzo_libero)
);
```

### 3.2. Logica di gestione
- **Tipo di indirizzo** (`config.tipi_indirizzi`) definisce schede: residenza, domicilio fiscale, fornitura, corrispondenza, ecc.
- **Unicità**: per ogni `soggetto_ruolo_id` e `tipo_indirizzo_id`, non possono esistere due record con lo stesso dettaglio né lo stesso testo libero.
- **Fallback**: se `indirizzi_dettaglio_id` è NULL, si usa `indirizzo_libero` e campi di internazionalizzazione.

### 3.3. Esempi
1. **Residenza catalogata**:  
   ```sql
   INSERT INTO anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id, indirizzi_dettaglio_id, stato_id, data_insert, user_insert)
   VALUES (10, 1 /*residenza*/, 123 /*dettaglio*/, 1 /*IT*/, now(), 'user');
   ```
2. **Domicilio fiscale libero**:  
   ```sql
   INSERT INTO anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero, comune_id, codice_postale_id, stato_id)
   VALUES (10, 2 /*fiscale*/, 'Via Nuova 5', 101, 50121, 1);
   ```
3. **Copia da residenza a fornitura**:
   ```sql
   INSERT INTO anagrafiche.indirizzi (soggetto_ruolo_id, tipo_indirizzo_id, indirizzi_dettaglio_id)
   SELECT soggetto_ruolo_id, 3 /*fornitura*/, indirizzi_dettaglio_id
   FROM anagrafiche.indirizzi
   WHERE soggetto_ruolo_id=10 AND tipo_indirizzo_id=1;
   ```

---

## 4. Lettura Indirizzi

### 4.1. Funzioni in `script` schema
- `script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)` → elenco di (tipo_indirizzo, indirizzo_completo, geoloc)
- `script.fn_get_indirizzo(p_soggetto_ruolo_id, p_tipo_codice)` → singolo indirizzo

### 4.2. Output Esempio
```txt
residenza | "VIA ROMA 10 INT 2, Milano 20121" | POINT(...)
fisca...   | "Via Nuova 5, Bologna 40121"      | null
```

---

## 5. Storicizzazione

### 5.1. Comune e Stradario
- `storico.comuni` e `storico.comune_trasformazioni` per fusioni/scissioni comuni.
- `storico.stradario` e `storico.stradario_trasformazioni` per variazioni vie.

### 5.2. Indirizzi
```sql
CREATE TABLE storico.indirizzi (
  id SERIAL PRIMARY KEY,
  soggetto_ruolo_id INTEGER REFERENCES anagrafiche.soggetti_ruoli,
  tipo_indirizzo_id INTEGER REFERENCES config.tipi_indirizzi,
  indirizzi_dettaglio_id INTEGER,
  indirizzo_libero TEXT,
  comune_id INTEGER,
  codice_postale_id INTEGER,
  stato_id INTEGER,
  valid_from DATE NOT NULL,
  valid_to DATE,
  data_insert TIMESTAMP,
  user_insert VARCHAR(80)
);
```
Consente di ricostruire l’indirizzo valido su uno determinato periodo.

---

**Conclusione**: il modello consente di gestire in modo flessibile e performante la normalizzazione, il fallback e la storicizzazione degli indirizzi, tenendo separate le responsabilità (stradario, dettaglio civico, contesto di utilizzo, storicizzazione).



## 6. Aggiornamenti del 25 aprile 2025

A seguito delle attività svolte oggi, il modello ha ricevuto i seguenti arricchimenti e migliorie:

1. **Snapshot completo in `indirizzi_dettaglio`**
   - Inserite le colonne di snapshot: ora `indirizzo_normalizzato` è un _generated column_ che concatena automaticamente via, civico, palazzina, scala, piano, interno, comune e CAP senza join runtime.
   - Trigger `anagrafiche.fn_normalize_indirizzi_dettaglio()` rinnovato per popolare automaticamente `civico_norm`, `via_norm` e il reset del flag `modifica_storica` su ogni INSERT/UPDATE.

2. **Storicizzazione flag-driven sui lookup**
   - Introdotto il flag `storicizza` in `config.comuni` e `config.stradario`, impostato a `true` per innescare la storicizzazione solo quando richiesto.
   - Funzioni trigger `config.fn_storico_comuni()` e `config.fn_storico_stradario()` convertiti in `BEFORE UPDATE OR DELETE`, verificano l'esistenza di un snapshot aperto e creano, se necessario, il record iniziale con i valori `OLD`, chiudono il periodo e inseriscono il nuovo snapshot con `NEW`.

3. **Constraint foreign key immediato**
   - Modificata la FK `fk_stradario_comune_id` in `config.stradario` da `DEFERRABLE INITIALLY DEFERRED` a `NOT DEFERRABLE INITIALLY IMMEDIATE`, per far scattare l'errore di vincolo al momento di `INSERT/UPDATE` e non al `COMMIT`.

4. **Admin Toolkit in `dbops` con audit**
   - Implementate le funzioni `dbops.admin_merge_comune()` e `dbops.admin_merge_stradario()` per automatizzare fusione/spostamento di comuni e vie:
     - Validazioni input (esistenza ID, differenza origine/destino).
     - Inserimento in `storico.comune_trasformazioni` e `storico.stradario_trasformazioni`.
     - Propagazione automatica dell'`UPDATE` sulle tabelle dipendenti (`config.stradario`, `anagrafiche.indirizzi_dettaglio`).
     - Logging in `dbops.audit_log` con `function_name`, parametri in JSONB, stato (`STARTED`/`OK`/`ERROR`), messaggio di errore e durata in ms.

5. **Tabella di audit**
   - Definita la struttura di `dbops.audit_log` (id, function_name, executed_by, executed_at, params JSONB, status, message, duration_ms, tx_id), per tracciare ogni invocazione delle routine admin.

---

*Relazione aggiornata il 25/04/2025*

