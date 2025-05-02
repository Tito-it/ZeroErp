
-- Creazione schema storico se non esiste
CREATE SCHEMA IF NOT EXISTS storico;

-- Tabella storica dei comuni
CREATE TABLE storico.comuni (
    id INTEGER,
    codice_istat CHAR(6),
    codice_catastale CHAR(10),
    descrizione TEXT,
    fascia_climatica CHAR(1),
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    stato CHAR(1) DEFAULT 'A',  -- A = Attivo, S = Soppresso, F = Fuso

    data_insert TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) DEFAULT CURRENT_USER
);

-- Indici
CREATE INDEX idx_storico_comuni_codice_istat ON storico.comuni(codice_istat);
CREATE INDEX idx_storico_comuni_descrizione ON storico.comuni(descrizione);

-- Commenti
COMMENT ON TABLE storico.comuni IS 'Storicizzazione dei comuni italiani, con validità e stato (fusi, soppressi, ecc.)';
COMMENT ON COLUMN storico.comuni.stato IS 'Stato del comune: A = Attivo, S = Soppresso, F = Fuso';
COMMENT ON COLUMN storico.comuni.valid_from IS 'Data inizio validità del comune';
COMMENT ON COLUMN storico.comuni.valid_to IS 'Data fine validità del comune (NULL = attivo)';

-- Tabella storica dei CAP
CREATE TABLE storico.codici_postali (
    codice_postale CHAR(10),
    comune_id INTEGER,
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE,
    stato CHAR(1) DEFAULT 'A',  -- A = Attivo, S = Soppresso

    data_insert TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) DEFAULT CURRENT_USER
);

-- Indici
CREATE INDEX idx_storico_cap_codice ON storico.codici_postali(codice_postale);
CREATE INDEX idx_storico_cap_comune_id ON storico.codici_postali(comune_id);

-- Commenti
COMMENT ON TABLE storico.codici_postali IS 'Storicizzazione dei codici postali (CAP) per comune';
COMMENT ON COLUMN storico.codici_postali.stato IS 'Stato del CAP: A = Attivo, S = Soppresso';
COMMENT ON COLUMN storico.codici_postali.valid_from IS 'Data inizio validità CAP';
COMMENT ON COLUMN storico.codici_postali.valid_to IS 'Data fine validità CAP (NULL = attivo)';
