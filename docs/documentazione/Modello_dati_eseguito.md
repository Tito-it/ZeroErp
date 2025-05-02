# Documentazione Modello Dati Zero ERP

Questa guida descrive in dettaglio le entità e le logiche implementate per:

1. **Anagrafica Soggetti** (`soggetti` e `soggetti_ruoli`)
2. **Gestori** (`gestori` e `gestori_utilities_ruoli`)
3. **Contatti** (`contatti` e `tipi_contatti`)

Ogni sezione include:
- Struttura tabelle (DDL)
- Chiavi primarie e relazioni (FK)
- Constraint e indici di unicità
- Trigger e funzioni di supporto
- Scenari d’uso e regole di business

---

## 1. Anagrafica Soggetti

### 1.1 Tabella `anagrafiche.soggetti`
```sql
CREATE TABLE anagrafiche.soggetti (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  codice TEXT,
  ragione_sociale TEXT,
  cognome TEXT,
  nome TEXT,
  tipo_soggetto CHAR(1) NOT NULL DEFAULT 'F',
  sesso CHAR(1) DEFAULT 'M',
  stato_id INTEGER NOT NULL REFERENCES config.stati(id) ON DELETE RESTRICT,
  partita_iva TEXT,
  codice_fiscale TEXT,
  comune_id INTEGER REFERENCES config.comuni(id) ON DELETE RESTRICT,
  -- campi generati
  id_fiscale_univoco_cf_piva TEXT GENERATED ALWAYS AS
    (COALESCE(codice_fiscale, partita_iva)) STORED,
  ragione_sociale_completa TEXT GENERATED ALWAYS AS
    (COALESCE(ragione_sociale, cognome || ' ' || nome)) STORED,
  -- audit
  data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert TEXT NOT NULL DEFAULT CURRENT_USER,
  data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update TEXT NOT NULL DEFAULT CURRENT_USER
);
```
- **Audit**: `data_insert/user_insert`, `data_update/user_update`.
- **Constraint**: validazioni `CHECK` su `tipo_soggetto`, unicità su `(stato_id, id_fiscale_univoco_cf_piva)`, ecc.

### 1.2 Tabella `anagrafiche.soggetti_ruoli`
```sql
CREATE TABLE anagrafiche.soggetti_ruoli (
  id_soggetto_ruolo SERIAL PRIMARY KEY,
  soggetto_id       UUID    NOT NULL
    REFERENCES anagrafiche.soggetti(id) ON DELETE CASCADE,
  ruolo_id          INTEGER NOT NULL
    REFERENCES config.tipi_ruoli(id) ON DELETE RESTRICT,
  extra             JSONB   DEFAULT '{}'::jsonb,
  -- audit
  date_insert       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert       TEXT      NOT NULL DEFAULT CURRENT_USER,
  date_update       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update       TEXT      NOT NULL DEFAULT CURRENT_USER,
  -- unicità
  CONSTRAINT uq_soggetto_ruolo UNIQUE (soggetto_id, ruolo_id)
);
```
- **FK**: assicura che ogni relazione soggetto → ruolo esista in `config.tipi_ruoli`.
- **Campo `extra`**: per dati specifici di ruolo.
- **Unicità**: un ruolo assegnato una sola volta.

---

## 2. Gestori

### 2.1 Tabella `anagrafiche.gestori`
```sql
CREATE TABLE anagrafiche.gestori (
  id SERIAL PRIMARY KEY,
  soggetto_id       UUID NOT NULL
    REFERENCES anagrafiche.soggetti(id) ON DELETE RESTRICT,
  soggetto_ruolo_id INTEGER NOT NULL
    REFERENCES anagrafiche.soggetti_ruoli(id_soggetto_ruolo) ON DELETE RESTRICT,
  descrizione       CHAR(50) NOT NULL,
  cd_prod_software  CHAR(20) NOT NULL,
  valuta_id         INTEGER NOT NULL
    REFERENCES config.pa_valute(id_valuta) ON DELETE RESTRICT,
  iban              CHAR(35) NOT NULL,
  -- audit
  date_insert       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert       TEXT      NOT NULL DEFAULT CURRENT_USER,
  date_update       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update       TEXT      NOT NULL DEFAULT CURRENT_USER
);
```
- **Relazione stretta**: `soggetto_ruolo_id` deve essere associato al ruolo `GE` (gestore). Controllato tramite trigger `check_ruolo_gestore`.

### 2.2 Tabella `anagrafiche.gestori_utilities_ruoli`
```sql
CREATE TABLE anagrafiche.gestori_utilities_ruoli (
  id_gest_util_ruolo SERIAL PRIMARY KEY,
  gestore_id         INTEGER NOT NULL
    REFERENCES anagrafiche.gestori(id) ON DELETE CASCADE,
  utility_id         INTEGER NOT NULL
    REFERENCES config.utilities(id_utility) ON DELETE RESTRICT,
  ruolo_id           INTEGER NOT NULL
    REFERENCES config.tipi_ruoli(id) ON DELETE RESTRICT,
  extra               JSONB DEFAULT '{}'::jsonb,
  -- audit
  date_insert        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert        TEXT      NOT NULL DEFAULT CURRENT_USER,
  date_update        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update        TEXT      NOT NULL DEFAULT CURRENT_USER,
  -- unicità
  CONSTRAINT uq_gest_util_ruolo UNIQUE (gestore_id, utility_id, ruolo_id)
);
```
- **Permette** a un gestore di assumere più ruoli funzionali per ciascuna utility.
- **Campo `extra`** per parametri contrattuali.
- **Unicità**: evita duplicazioni.

---

## 3. Contatti

### 3.1 Tabella `config.tipi_contatti`
```sql
CREATE TABLE config.tipi_contatti (
  id                    SERIAL PRIMARY KEY,
  descrizione           TEXT    NOT NULL,
  cod_int_tipo_contatto VARCHAR(10) NOT NULL UNIQUE,
  data_insert           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert           TEXT    NOT NULL DEFAULT CURRENT_USER,
  data_update           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update           TEXT    NOT NULL DEFAULT CURRENT_USER
);
```
- **Catalogo** dei tipi di contatto (Admin, Tecnico, Default, ecc.).

### 3.2 Tabella `anagrafiche.contatti`
```sql
CREATE TABLE anagrafiche.contatti (
  id_contatto        SERIAL PRIMARY KEY,
  tipo_contatto_id   INTEGER NOT NULL
    REFERENCES config.tipi_contatti(id) ON DELETE RESTRICT,
  soggetto_id        UUID    NOT NULL
    REFERENCES anagrafiche.soggetti(id) ON DELETE CASCADE,
  soggetto_ruolo_id  INTEGER NULL
    REFERENCES anagrafiche.soggetti_ruoli(id_soggetto_ruolo) ON DELETE CASCADE,
  utility_id         INTEGER NULL
    REFERENCES config.utilities(id_utility) ON DELETE CASCADE,
  nominativo         VARCHAR(100) NOT NULL,
  email              VARCHAR(100),
  telefono           VARCHAR(20),
  cellulare          VARCHAR(20),
  pec                VARCHAR(100),
  note               TEXT,
  is_default         BOOLEAN NOT NULL DEFAULT FALSE,
  -- audit
  date_insert        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert        TEXT      NOT NULL DEFAULT CURRENT_USER,
  date_update        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update        TEXT      NOT NULL DEFAULT CURRENT_USER,
  -- default unico
  CONSTRAINT uq_contatti_default UNIQUE (soggetto_id) WHERE is_default
);

CREATE INDEX idx_contatti_soggetto ON anagrafiche.contatti(soggetto_id);
CREATE INDEX idx_contatti_tipo    ON anagrafiche.contatti(tipo_contatto_id);
CREATE INDEX idx_contatti_utility ON anagrafiche.contatti(utility_id);
```
- **Flag `is_default`**: il primo contatto inserito per ciascun soggetto è automaticamente marcato default dal trigger `set_default_contatto`.
- **Unique partial index**: garantisce un solo default per soggetto.

### 3.3 Logiche di default e fallback

#### Trigger `set_default_contatto`
- **BEFORE INSERT OR UPDATE** su `anagrafiche.contatti`
- Imposta **`is_default = TRUE`** per il primo contatto di un soggetto.
- Se un'altra riga è già default, la disattiva.

#### Funzione `script.fn_get_contatto_fallback(...)`
- Riceve i parametri: `p_soggetto_id`, `p_tipo_contatto_id`, opzionali `p_soggetto_ruolo_id`, `p_utility_id`.
- Restituisce il contatto con priorità:
  1. `utility_id` matching
  2. `soggetto_ruolo_id` matching
  3. `is_default = TRUE`
- Query in PL/pgSQL che ordina per `priority, date_insert DESC`.

#### Constraint Trigger `check_soggetto_contatti_complete`
- **AFTER INSERT OR UPDATE DEFERRABLE** su `anagrafiche.soggetti`
- Verifica al commit che esista almeno un contatto con `is_default = TRUE` oppure uno con un canale valorizzato.
- Solleva l’eccezione `E_SOGGETTO_NO_CONTATTI` in caso contrario.

---

Con questa architettura:
- **Soggetti** e **ruoli** sono separati e vincolati da FK e JSONB per estensioni.
- **Gestori** sono soggetti con ruolo `GE`, arricchiti con software, valuta e IBAN, e collegati a ruoli functional per ciascuna utility.
- **Contatti** sono centralizzati, con un unico punto di verità per email/telefono/PEC e un contatto principale esplicito.
- Tutta la logica di **integrità**, **default** e **fallback** è gestita in database tramite **trigger** e **funzioni**.

Questo modello garantisce robustezza, estendibilità e chiarezza nei flussi di business di Zero ERP.  

---


