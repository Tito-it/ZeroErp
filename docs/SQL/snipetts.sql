**SQL Cheat Sheet per Zero - Snippet Principali e Pattern Ricorrenti**

---

### 1. Sequenze e Primary Key
```sql
-- Sequenza autonumerica
CREATE SEQUENCE IF NOT EXISTS schema.sequence_name_seq
  START WITH 1
  INCREMENT BY 1;

-- Uso in tabella
CREATE TABLE schema.table_name (
  id INTEGER NOT NULL
    DEFAULT nextval('schema.sequence_name_seq'::regclass)
    CONSTRAINT pk_table_name PRIMARY KEY,
  ...
);
```

---

### 2. Definizione di FK e vincoli
```sql
CREATE TABLE schema.child (
  parent_id INTEGER NOT NULL
    CONSTRAINT fk_child_parent_id
    REFERENCES schema.parent(id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  ...
);

-- Vincolo di unicità composita
ALTER TABLE schema.table_name
  ADD CONSTRAINT uq_table_cols UNIQUE(col1, col2);

-- Vincolo CHECK
ALTER TABLE schema.table_name
  ADD CONSTRAINT chk_table_flag CHECK(flag_col IN (TRUE, FALSE));
```

---

### 3. Indici di supporto (B‑Tree e GIST)
```sql
-- B‑tree semplice
CREATE INDEX ix_table_col
  ON schema.table_name(col);

-- Spaziale GIST per geometry
CREATE INDEX ix_table_geoloc_gist
  ON schema.table_name USING GIST(geoloc);
```

---

### 4. Trigger e Funzioni PL/pgSQL
```sql
-- Funzione di trigger
CREATE OR REPLACE FUNCTION schema.trg_fn_name()
RETURNS trigger AS $$
BEGIN
  -- logica PL/pgSQL
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attacco trigger BEFORE/AFTER INSERT/UPDATE
CREATE TRIGGER trg_fn_name
  BEFORE INSERT OR UPDATE ON schema.table_name
  FOR EACH ROW
  EXECUTE FUNCTION schema.trg_fn_name();
```

---

### 5. Generazione di codici sequenziali
```sql
-- Lettura da config.sistema_codici e nextval
EXECUTE format('SELECT nextval(%L)', seq_name) INTO seq_val;
NEW.codice := prefix || sep || lpad(seq_val::TEXT, len, '0');
```

---

### 6. Normalizzazione e lookup stradario
```sql
-- Chiamata alla funzione di catalogo
SELECT * FROM script.fn_get_stradario(p_comune_id, p_testo_parziale);
```

---

### 7. Recursive CTE per catene di trasformazione
```sql
WITH RECURSIVE chain(id_child, lvl) AS (
  SELECT via_id_nuovo, 1
    FROM storico.stradario_trasformazioni
   WHERE via_id_orig = :start_id

  UNION ALL

  SELECT t.via_id_nuovo, c.lvl+1
    FROM storico.stradario_trasformazioni t
    JOIN chain c ON t.via_id_orig = c.id_child
)
SELECT * FROM chain;
```

---

### 8. Funzioni di lettura indirizzi
```sql
-- Tutti gli indirizzi per soggetto_ruolo
SELECT * FROM script.fn_get_indirizzi_by_ruolo(:soggetto_ruolo_id);

-- Uno per tipo
SELECT * FROM script.fn_get_indirizzo(:soggetto_ruolo_id, 'residenza');
```

---

### 9. Storicizzazione
```sql
-- Tabella storico.indirizzi
CREATE TABLE storico.indirizzi (
  id SERIAL PRIMARY KEY,
  soggetto_ruolo_id INTEGER NOT NULL,
  tipo_indirizzo_id INTEGER NOT NULL,
  ...,
  valid_from DATE NOT NULL,
  valid_to DATE
);

-- Tabella storico.stradario_trasformazioni
CREATE TABLE storico.stradario_trasformazioni (
  id SERIAL PRIMARY KEY,
  via_id_orig INTEGER,
  via_id_nuovo INTEGER,
  tipo_evento CHAR(1),
  data_evento DATE
);
```

---

**Consiglio pratico**: salva questi snippet in un file `.sql` o un repository Git come _snippets.sql_ e tienilo a portata di mano mentre lavori. Buon coding!  

