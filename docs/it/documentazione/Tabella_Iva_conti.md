# Documentazione Tabelle e Logiche IVA (Sessione odierna)

Questo documento riassume le entità e le logiche definite durante la sessione odierna, focalizzate sulla gestione dei conti contabili e dei codici IVA.

---

## 1. `config.conti_contabili`

### Scopo
Catalogo dei conti contabili utilizzabili, suddivisi tra acquisto e vendita.

### Struttura DDL
```sql
CREATE TABLE config.conti_contabili (
  id                 SERIAL PRIMARY KEY,
  codice_conto       VARCHAR(20) NOT NULL UNIQUE,
  descrizione        VARCHAR(100) NOT NULL,
  tipo_conto         CHAR(1)    NOT NULL CHECK (tipo_conto IN ('A','V')),
  data_insert        TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert        TEXT       NOT NULL DEFAULT CURRENT_USER,
  data_update        TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update        TEXT       NOT NULL DEFAULT CURRENT_USER
);

CREATE INDEX idx_ftcc_tipo_conto   ON config.conti_contabili(tipo_conto);
CREATE INDEX idx_ftcc_descrizione  ON config.conti_contabili(descrizione);
```

### Logiche e vincoli
- **`codice_conto`**: stringa univoca identificativa del conto.
- **`tipo_conto`**: deve essere **`'A'`** (Acquisto) o **`'V'`** (Vendita).
- **Indici** su `tipo_conto` e `descrizione` per velocizzare filtri e ricerche.

---

## 2. `config.iva`

### Scopo
Catalogo dei codici IVA, con aliquota e riferimenti a natura e conti contabili.

### Struttura DDL
```sql
CREATE TABLE config.iva (
  id                      SERIAL PRIMARY KEY,
  codice_iva              CHAR(10)   NOT NULL UNIQUE,
  desc_iva                VARCHAR(80) NOT NULL,
  desc_breve_iva          VARCHAR(40) NOT NULL,
  aliquota_iva            NUMERIC(5,2) NOT NULL DEFAULT 0,
  assoggettamento_iva     CHAR(2)    NOT NULL DEFAULT '',
  natura_iva_id           INTEGER    NULL
      REFERENCES config.iva_natura(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,
  conto_iva_acquisti_id   INTEGER    NULL
      REFERENCES config.conti_contabili(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,
  conto_iva_vendita_id    INTEGER    NULL
      REFERENCES config.conti_contabili(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,
  id_iva_split            INTEGER    NULL
      REFERENCES config.iva(id)
      ON UPDATE CASCADE ON DELETE RESTRICT,
  data_insert             TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert             TEXT       NOT NULL DEFAULT CURRENT_USER,
  data_update             TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update             TEXT       NOT NULL DEFAULT CURRENT_USER,
  CHECK (assoggettamento_iva IN ('NS','NI','ND','ES','RC','ED',''))
);

CREATE INDEX idx_iva_desc ON config.iva(desc_iva);
```

### Logiche e vincoli
- **Unicità** su `codice_iva`.
- **Assoggettamento**: deve appartenere all’insieme di codici validi (`NS`, `NI`, etc.).
- **FK** sui conti contabili:
  - `conto_iva_acquisti_id` deve essere un **conto di tipo A**
  - `conto_iva_vendita_id` deve essere un **conto di tipo V**
- **Split payment**: `id_iva_split` punta allo stesso catalogo `config.iva`.

---

## 3. `config.iva_stati`

### Scopo
Override delle aliquote e dell’assoggettamento IVA per specifico Stato/Paese.

### Struttura DDL
```sql
CREATE TABLE config.iva_stati (
  iva_id                INTEGER NOT NULL
      REFERENCES config.iva(id) ON UPDATE CASCADE ON DELETE CASCADE,
  stato_id              INTEGER NOT NULL
      REFERENCES config.stati(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  aliquota_override     NUMERIC(5,2) NOT NULL,
  assoggettamento_override CHAR(2)
      NOT NULL CHECK (assoggettamento_override IN ('NS','NI','ND','ES','RC','ED','')),
  data_insert           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_insert           TEXT      NOT NULL DEFAULT CURRENT_USER,
  data_update           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_update           TEXT      NOT NULL DEFAULT CURRENT_USER,
  PRIMARY KEY (iva_id, stato_id)
);

CREATE INDEX idx_iva_stati_stato ON config.iva_stati(stato_id);
```

### Logiche e vincoli
- **PK composito** `(iva_id, stato_id)` garantisce un solo override per coppia.
- **FK** a `config.iva` e `config.stati`.
- **Delete cascade** su `iva` per rimuovere automaticamente gli override.
- **Restrict** su `stati` per evitare cancellazioni se in uso.

---

## 4. Funzione `config.fn_get_iva_override`

### Scopo
Restituire i dati del codice IVA per un dato Paese, combinando valori base e override.

### Definizione
```sql
CREATE OR REPLACE FUNCTION config.fn_get_iva_override(
  p_codice_iva TEXT,
  p_stato_id   INTEGER
)
RETURNS TABLE (
  id_iva                INTEGER,
  codice_iva            CHAR(10),
  desc_iva              VARCHAR,
  desc_breve_iva        VARCHAR,
  aliquota_base         NUMERIC(5,2),
  assoggettamento_base  CHAR(2),
  aliquota              NUMERIC(5,2),
  assoggettamento       CHAR(2),
  id_natura_iva         INTEGER,
  conto_iva_acquisti_id INTEGER,
  conto_iva_vendita_id  INTEGER,
  stato_id              INTEGER,
  stato_sigla           VARCHAR,
  data_insert           TIMESTAMP,
  user_insert           TEXT,
  data_update           TIMESTAMP,
  user_update           TEXT
) LANGUAGE sql STABLE AS $$
  SELECT
    i.id_iva,
    i.codice_iva,
    i.desc_iva,
    i.desc_breve_iva,
    i.aliquota_iva        AS aliquota_base,
    i.assoggettamento_iva AS assoggettamento_base,
    COALESCE(s.aliquota_override, i.aliquota_iva)         AS aliquota,
    COALESCE(s.assoggettamento_override, i.assoggettamento_iva) AS assoggettamento,
    i.natura_iva_id,
    i.conto_iva_acquisti_id,
    i.conto_iva_vendita_id,
    st.id                    AS stato_id,
    st.sigla_stato           AS stato_sigla,
    i.data_insert,
    i.user_insert,
    i.data_update,
    i.user_update
  FROM config.iva i
  JOIN config.stati st ON st.id = p_stato_id
  LEFT JOIN config.iva_stati s
    ON s.iva_id   = i.id_iva
   AND s.stato_id = p_stato_id
  WHERE i.codice_iva = p_codice_iva;
$$;
```

### Logica di funzionamento
1. **Ricerca** del record base in `config.iva` tramite `codice_iva`.
2. **Join** con `config.stati` per ottenere informazioni sul Paese.
3. **Left join** con `config.iva_stati` per verificare eventuale override.
4. **`COALESCE`** tra valori override e base per `aliquota` e `assoggettamento`.

---

*Fine documentazione.*

