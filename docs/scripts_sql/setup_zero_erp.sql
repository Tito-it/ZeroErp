
-- Schema Configurazione Zero ERP

CREATE SCHEMA IF NOT EXISTS config;

-- Tabella config.utilities
CREATE TABLE config.utilities (
    id SERIAL PRIMARY KEY,
    cod_utility VARCHAR(10) NOT NULL UNIQUE,
    descrizione VARCHAR(100) NOT NULL,
    cd_int_utility VARCHAR(10) NOT NULL UNIQUE,
    data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER,
    data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update VARCHAR(80) NOT NULL DEFAULT CURRENT_USER
);

-- Tabella config.tipi_attivita
CREATE TABLE config.tipi_attivita (
    id SERIAL PRIMARY KEY,
    cod_tipo_attivita VARCHAR(10) NOT NULL UNIQUE,
    descrizione VARCHAR(100) NOT NULL,
    cd_int_tipo_attivita VARCHAR(10) NOT NULL UNIQUE,
    data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER,
    data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update VARCHAR(80) NOT NULL DEFAULT CURRENT_USER
);

-- Tabella config.tipi_documenti
CREATE TABLE config.tipi_documenti (
    id SERIAL PRIMARY KEY,
    cod_tipo_documento VARCHAR(10) NOT NULL UNIQUE,
    descrizione VARCHAR(100) NOT NULL,
    cd_int_tipo_documento VARCHAR(10) NOT NULL UNIQUE,
    data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER,
    data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update VARCHAR(80) NOT NULL DEFAULT CURRENT_USER
);

-- Tabella config.stati_pratiche
CREATE TABLE config.stati_pratiche (
    id SERIAL PRIMARY KEY,
    cod_stato VARCHAR(10) NOT NULL UNIQUE,
    descrizione VARCHAR(100) NOT NULL,
    cd_int_stato VARCHAR(10) NOT NULL UNIQUE,
    data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER,
    data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update VARCHAR(80) NOT NULL DEFAULT CURRENT_USER
);

-- Tabella config.tipi_ruoli
CREATE TABLE config.tipi_ruoli (
    id SERIAL PRIMARY KEY,
    cod_ruolo VARCHAR(10) NOT NULL UNIQUE,
    descrizione VARCHAR(100) NOT NULL,
    cd_int_ruolo VARCHAR(10) NOT NULL UNIQUE,
    data_insert TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert VARCHAR(80) NOT NULL DEFAULT CURRENT_USER,
    data_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update VARCHAR(80) NOT NULL DEFAULT CURRENT_USER
);

-- Trigger generico
CREATE OR REPLACE FUNCTION lock_cd_int_generic()
RETURNS trigger AS $$
BEGIN
    IF NEW.cd_int_utility <> OLD.cd_int_utility THEN
        RAISE EXCEPTION 'Il codice interno non può essere modificato';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lock_cd_int_utility
BEFORE UPDATE ON config.utilities
FOR EACH ROW
WHEN (OLD.cd_int_utility IS DISTINCT FROM NEW.cd_int_utility)
EXECUTE FUNCTION lock_cd_int_generic();

-- INSERT iniziali
INSERT INTO config.utilities (cod_utility, descrizione, cd_int_utility) VALUES
('ENE', 'Energia Elettrica', 'EE'),
('GAS', 'Gas Naturale', 'GG'),
('ACQ', 'Acqua Potabile', 'AA'),
('TEL', 'Telefonia', 'FF'),
('STD', 'Servizio Base', 'BASE');

INSERT INTO config.tipi_attivita (cod_tipo_attivita, descrizione, cd_int_tipo_attivita) VALUES
('AP', 'Apertura Pratica', 'AP'),
('VA', 'Verifica Attività', 'VA'),
('CH', 'Chiusura Pratica', 'CH');

INSERT INTO config.tipi_documenti (cod_tipo_documento, descrizione, cd_int_tipo_documento) VALUES
('PDF', 'Documento PDF', 'PDF'),
('XML', 'Flusso XML', 'XML'),
('IMG', 'Immagine Allegata', 'IMG');

INSERT INTO config.stati_pratiche (cod_stato, descrizione, cd_int_stato) VALUES
('APER', 'Aperta', 'APER'),
('CHIU', 'Chiusa', 'CHIU'),
('SOSP', 'Sospesa', 'SOSP');

INSERT INTO config.tipi_ruoli (cod_ruolo, descrizione, cd_int_ruolo) VALUES
('CL', 'Cliente', 'CL'),
('FO', 'Fornitore', 'FO'),
('GE', 'Gestore', 'GE');
