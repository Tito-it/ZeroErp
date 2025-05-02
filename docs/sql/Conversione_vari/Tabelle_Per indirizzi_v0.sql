-- Table: anagrafiche.indirizzi

-- DROP TABLE IF EXISTS anagrafiche.indirizzi;

CREATE TABLE IF NOT EXISTS anagrafiche.indirizzi
(
    id integer NOT NULL DEFAULT nextval('anagrafiche.indirizzi_id_seq'::regclass),
    soggetto_ruolo_id integer NOT NULL,
    tipo_indirizzo_id integer NOT NULL,
    indirizzo_dettaglio_id integer,
    indirizzo_libero text COLLATE pg_catalog."default",
    stato_id integer,
    administrative_area character varying(100) COLLATE pg_catalog."default",
    locality character varying(100) COLLATE pg_catalog."default",
    sublocality character varying(100) COLLATE pg_catalog."default",
    postal_box character varying(20) COLLATE pg_catalog."default",
    geoloc geometry(Point,4326),
    data_insert timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    data_update timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    comune_id integer,
    codice_postale_id integer,
    modifica_storica boolean NOT NULL DEFAULT false,
    CONSTRAINT pr_indirizzi_pk PRIMARY KEY (id),
    CONSTRAINT uq_indirizzi_dettaglio_unique UNIQUE (soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_dettaglio_id),
    CONSTRAINT uq_indirizzi_libero_unique UNIQUE (soggetto_ruolo_id, tipo_indirizzo_id, indirizzo_libero),
    CONSTRAINT fk_indirizzi_codice_postale_id FOREIGN KEY (codice_postale_id)
        REFERENCES config.codici_postali (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_indirizzi_comune_id FOREIGN KEY (comune_id)
        REFERENCES config.comuni (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_indirizzi_indirizzo_dettaglio_id FOREIGN KEY (indirizzo_dettaglio_id)
        REFERENCES anagrafiche.indirizzi_dettaglio (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_indirizzi_soggetto_ruolo_id FOREIGN KEY (soggetto_ruolo_id)
        REFERENCES anagrafiche.soggetti_ruoli (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_indirizzi_stato_id FOREIGN KEY (stato_id)
        REFERENCES config.stati (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_indirizzi_tipo_indirizzo_id FOREIGN KEY (tipo_indirizzo_id)
        REFERENCES config.tipi_indirizzi (id) MATCH SIMPLE
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT chk_indirizzi_dettaglio_exclusive CHECK (NOT (indirizzo_dettaglio_id IS NOT NULL AND (indirizzo_libero IS NOT NULL OR comune_id IS NOT NULL OR codice_postale_id IS NOT NULL OR administrative_area IS NOT NULL OR locality IS NOT NULL OR sublocality IS NOT NULL OR postal_box IS NOT NULL OR stato_id IS NOT NULL))),
    CONSTRAINT chk_indirizzi_fallback_required CHECK (indirizzo_dettaglio_id IS NOT NULL OR comune_id IS NOT NULL AND codice_postale_id IS NOT NULL AND indirizzo_libero IS NOT NULL OR stato_id IS NOT NULL AND postal_box IS NOT NULL AND indirizzo_libero IS NOT NULL AND locality IS NOT NULL)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS anagrafiche.indirizzi
    OWNER to postgres;

COMMENT ON TABLE anagrafiche.indirizzi
    IS 'Associa a un soggetto/ruolo un indirizzo di un certo tipo, normalizzato o libero, con supporto internazionale';

COMMENT ON COLUMN anagrafiche.indirizzi.indirizzo_dettaglio_id
    IS 'FK facoltativo al dettaglio civico/geoloc in anagrafiche.indirizzi_dettaglio';

COMMENT ON COLUMN anagrafiche.indirizzi.indirizzo_libero
    IS 'Testo libero se non ho un record normalizzato';

COMMENT ON COLUMN anagrafiche.indirizzi.stato_id
    IS 'Stato (usato per CF e internazionalizzazione)';

COMMENT ON COLUMN anagrafiche.indirizzi.administrative_area
    IS 'Suddivisione amministrativa per indirizzi esteri (es. stato, regione)';

COMMENT ON COLUMN anagrafiche.indirizzi.locality
    IS 'Città o municipalità per indirizzi esteri';

COMMENT ON COLUMN anagrafiche.indirizzi.sublocality
    IS 'Frazione o quartiere per indirizzi esteri';

COMMENT ON COLUMN anagrafiche.indirizzi.postal_box
    IS 'Casella postale (PO Box) per indirizzi esteri';

COMMENT ON COLUMN anagrafiche.indirizzi.modifica_storica
    IS 'Se true, al prossimo UPDATE/DELETE verrà creato uno snapshot in storico.indirizzi';

COMMENT ON CONSTRAINT chk_indirizzi_dettaglio_exclusive ON anagrafiche.indirizzi
    IS 'Se presente indirizzo dettaglio non devono esserci le altre informazioni';
-- Index: ix_indirizzi_codice_postale_id

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_codice_postale_id;

CREATE INDEX IF NOT EXISTS ix_indirizzi_codice_postale_id
    ON anagrafiche.indirizzi USING btree
    (codice_postale_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: ix_indirizzi_comune_id

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_comune_id;

CREATE INDEX IF NOT EXISTS ix_indirizzi_comune_id
    ON anagrafiche.indirizzi USING btree
    (comune_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: ix_indirizzi_geoloc_gist

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_geoloc_gist;

CREATE INDEX IF NOT EXISTS ix_indirizzi_geoloc_gist
    ON anagrafiche.indirizzi USING gist
    (geoloc)
    TABLESPACE pg_default;
-- Index: ix_indirizzi_soggetto_ruolo_id

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_soggetto_ruolo_id;

CREATE INDEX IF NOT EXISTS ix_indirizzi_soggetto_ruolo_id
    ON anagrafiche.indirizzi USING btree
    (soggetto_ruolo_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: ix_indirizzi_stato_id

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_stato_id;

CREATE INDEX IF NOT EXISTS ix_indirizzi_stato_id
    ON anagrafiche.indirizzi USING btree
    (stato_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: ix_indirizzi_tipo_indirizzo_id

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_tipo_indirizzo_id;

CREATE INDEX IF NOT EXISTS ix_indirizzi_tipo_indirizzo_id
    ON anagrafiche.indirizzi USING btree
    (tipo_indirizzo_id ASC NULLS LAST)
    TABLESPACE pg_default;

-- Trigger: trg_clean_indirizzi_fields

-- DROP TRIGGER IF EXISTS trg_clean_indirizzi_fields ON anagrafiche.indirizzi;

CREATE OR REPLACE TRIGGER trg_clean_indirizzi_fields
    BEFORE INSERT OR UPDATE 
    ON anagrafiche.indirizzi
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.trg_clean_indirizzi_fields();

COMMENT ON TRIGGER trg_clean_indirizzi_fields ON anagrafiche.indirizzi
    IS 'Pulizia campi alternativi a stradario_id';

-- Trigger: trg_storico_indirizzi

-- DROP TRIGGER IF EXISTS trg_storico_indirizzi ON anagrafiche.indirizzi;

CREATE OR REPLACE TRIGGER trg_storico_indirizzi
    AFTER DELETE OR UPDATE 
    ON anagrafiche.indirizzi
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.fn_storico_indirizzi();
	
	
	
	




-- Table: anagrafiche.indirizzi_dettaglio

-- DROP TABLE IF EXISTS anagrafiche.indirizzi_dettaglio;

CREATE TABLE IF NOT EXISTS anagrafiche.indirizzi_dettaglio
(
    id integer NOT NULL DEFAULT nextval('anagrafiche.indirizzi_dettaglio_id_seq'::regclass),
    stradario_id integer NOT NULL,
    civico integer,
    estensione_civico character varying(10) COLLATE pg_catalog."default",
    palazzina character varying(50) COLLATE pg_catalog."default",
    interno character varying(10) COLLATE pg_catalog."default",
    piano character varying(10) COLLATE pg_catalog."default",
    civic_geoloc geometry(Point,4326),
    altro text COLLATE pg_catalog."default",
    via_norm text COLLATE pg_catalog."default" NOT NULL,
    civico_norm text COLLATE pg_catalog."default" NOT NULL,
    street_geoloc geometry(Point,4326),
    data_insert timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    data_update timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    scala character varying(10) COLLATE pg_catalog."default",
    indirizzo_normalizzato text COLLATE pg_catalog."default" GENERATED ALWAYS AS (TRIM(BOTH FROM (((((via_norm || COALESCE((', '::text || civico_norm), ''::text)) || COALESCE((', Pal.'::text || (palazzina)::text), ''::text)) || COALESCE((', Scala '::text || (scala)::text), ''::text)) || COALESCE((', P'::text || (piano)::text), ''::text)) || COALESCE((', Int.'::text || (interno)::text), ''::text)))) STORED,
    CONSTRAINT pk_indirizzi_dettaglio PRIMARY KEY (id),
    CONSTRAINT uq_indirizzi_dettaglio_norm UNIQUE (via_norm, civico_norm, interno, piano, palazzina),
    CONSTRAINT fk_indirizzi_dettaglio_stradario_id FOREIGN KEY (stradario_id)
        REFERENCES config.stradario (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS anagrafiche.indirizzi_dettaglio
    OWNER to postgres;

COMMENT ON TABLE anagrafiche.indirizzi_dettaglio
    IS 'Dettaglio degli indirizzi, collegate allo stradario';

COMMENT ON COLUMN anagrafiche.indirizzi_dettaglio.altro
    IS 'Campo libero per informazioni aggiuntive non strutturate';
-- Index: ix_indirizzi_dettaglio_civic_geoloc_gist

-- DROP INDEX IF EXISTS anagrafiche.ix_indirizzi_dettaglio_civic_geoloc_gist;

CREATE INDEX IF NOT EXISTS ix_indirizzi_dettaglio_civic_geoloc_gist
    ON anagrafiche.indirizzi_dettaglio USING gist
    (civic_geoloc)
    TABLESPACE pg_default;

-- Trigger: trg_norm_indirizzi_dettaglio

-- DROP TRIGGER IF EXISTS trg_norm_indirizzi_dettaglio ON anagrafiche.indirizzi_dettaglio;

CREATE OR REPLACE TRIGGER trg_norm_indirizzi_dettaglio
    BEFORE INSERT OR UPDATE 
    ON anagrafiche.indirizzi_dettaglio
    FOR EACH ROW
    EXECUTE FUNCTION anagrafiche.fn_normalize_indirizzi_dettaglio();
	
	
	
	
	
	
-- Table: config.stradario

-- DROP TABLE IF EXISTS config.stradario;

CREATE TABLE IF NOT EXISTS config.stradario
(
    id integer NOT NULL DEFAULT nextval('config.stradario_id_seq'::regclass),
    comune_id integer NOT NULL,
    via_id integer NOT NULL,
    geoloc geometry(Point,4326),
    extra_info jsonb,
    data_insert timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    data_update timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_update character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    codice_postale_id integer NOT NULL,
    CONSTRAINT pk_stradario PRIMARY KEY (id),
    CONSTRAINT fk_stradario_codice_postale_id FOREIGN KEY (codice_postale_id)
        REFERENCES config.codici_postali (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_stradario_comune_id FOREIGN KEY (comune_id)
        REFERENCES config.comuni (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_stradario_via_id FOREIGN KEY (via_id)
        REFERENCES config.stradario_generale (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS config.stradario
    OWNER to postgres;

COMMENT ON TABLE config.stradario
    IS 'Stradario con CAP obbligatorio esclusivamente sulle vie';

COMMENT ON COLUMN config.stradario.codice_postale_id
    IS 'Riferimento obbligatorio al CAP (tabella codici_postali)';
-- Index: idx_config_stradario_via_id

-- DROP INDEX IF EXISTS config.idx_config_stradario_via_id;

CREATE INDEX IF NOT EXISTS idx_config_stradario_via_id
    ON config.stradario USING btree
    (via_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_stradario_codice_postale_id

-- DROP INDEX IF EXISTS config.idx_stradario_codice_postale_id;

CREATE INDEX IF NOT EXISTS idx_stradario_codice_postale_id
    ON config.stradario USING btree
    (codice_postale_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_stradario_comune

-- DROP INDEX IF EXISTS config.idx_stradario_comune;

CREATE INDEX IF NOT EXISTS idx_stradario_comune
    ON config.stradario USING btree
    (comune_id ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	
	
	
-- Table: config.stradario_generale

-- DROP TABLE IF EXISTS config.stradario_generale;

CREATE TABLE IF NOT EXISTS config.stradario_generale
(
    id integer NOT NULL DEFAULT nextval('config.stradario_generale_id_seq'::regclass),
    toponomastica_id integer NOT NULL,
    descrizione character varying(100) COLLATE pg_catalog."default" NOT NULL,
    descrizione_breve character varying(50) COLLATE pg_catalog."default" NOT NULL,
    data_insert timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    data_update timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_update character varying(80) COLLATE pg_catalog."default" NOT NULL DEFAULT CURRENT_USER,
    CONSTRAINT pk_stradario_generale PRIMARY KEY (id),
    CONSTRAINT unq_toponomastica_descr UNIQUE (toponomastica_id, descrizione),
    CONSTRAINT fk_stradario_generale_toponomastica_id FOREIGN KEY (toponomastica_id)
        REFERENCES config.toponomastica (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS config.stradario_generale
    OWNER to postgres;

COMMENT ON TABLE config.stradario_generale
    IS 'Stradario generale: vie, strade, piazze con riferimento alla toponomastica.';

COMMENT ON COLUMN config.stradario_generale.toponomastica_id
    IS 'Collegamento alla tipologia di toponimo (es. VIA, PIAZZA)';

COMMENT ON COLUMN config.stradario_generale.descrizione
    IS 'Descrizione estesa della strada (es. Roma)';

COMMENT ON COLUMN config.stradario_generale.descrizione_breve
    IS 'Descrizione breve della strada (es. RM)';
-- Index: idx_toponomastica_id

-- DROP INDEX IF EXISTS config.idx_toponomastica_id;

CREATE INDEX IF NOT EXISTS idx_toponomastica_id
    ON config.stradario_generale USING btree
    (toponomastica_id ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	
	
-- Table: storico.comune_trasformazioni

-- DROP TABLE IF EXISTS storico.comune_trasformazioni;

CREATE TABLE IF NOT EXISTS storico.comune_trasformazioni
(
    id integer NOT NULL DEFAULT nextval('storico.comune_trasformazioni_id_seq'::regclass),
    id_comune_orig integer NOT NULL,
    id_comune_nuovo integer NOT NULL,
    tipo_evento character(1) COLLATE pg_catalog."default" NOT NULL,
    data_evento date NOT NULL,
    note text COLLATE pg_catalog."default",
    data_insert timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    CONSTRAINT comune_trasformazioni_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS storico.comune_trasformazioni
    OWNER to postgres;

COMMENT ON TABLE storico.comune_trasformazioni
    IS 'Trasformazioni tra comuni: accorpamenti e scissioni';

COMMENT ON COLUMN storico.comune_trasformazioni.tipo_evento
    IS 'A=Accorpamento, S=Scissione';
-- Index: idx_comune_trasformazioni_nuovo

-- DROP INDEX IF EXISTS storico.idx_comune_trasformazioni_nuovo;

CREATE INDEX IF NOT EXISTS idx_comune_trasformazioni_nuovo
    ON storico.comune_trasformazioni USING btree
    (id_comune_nuovo ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_comune_trasformazioni_orig

-- DROP INDEX IF EXISTS storico.idx_comune_trasformazioni_orig;

CREATE INDEX IF NOT EXISTS idx_comune_trasformazioni_orig
    ON storico.comune_trasformazioni USING btree
    (id_comune_orig ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	



-- Table: storico.comuni

-- DROP TABLE IF EXISTS storico.comuni;

CREATE TABLE IF NOT EXISTS storico.comuni
(
    id integer,
    descrizione text COLLATE pg_catalog."default",
    extra_country jsonb,
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    stato character(1) COLLATE pg_catalog."default" DEFAULT 'A'::bpchar,
    data_insert timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS storico.comuni
    OWNER to postgres;

COMMENT ON TABLE storico.comuni
    IS 'Storico dei comuni con dati anagrafici e JSONB';

COMMENT ON COLUMN storico.comuni.extra_country
    IS 'Dati estesi del comune (JSONB)';

COMMENT ON COLUMN storico.comuni.stato
    IS 'A=Attivo, S=Soppresso, F=Fuso, D=Diviso';
-- Index: idx_storico_comuni_descrizione

-- DROP INDEX IF EXISTS storico.idx_storico_comuni_descrizione;

CREATE INDEX IF NOT EXISTS idx_storico_comuni_descrizione
    ON storico.comuni USING btree
    (descrizione COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_storico_comuni_valid

-- DROP INDEX IF EXISTS storico.idx_storico_comuni_valid;

CREATE INDEX IF NOT EXISTS idx_storico_comuni_valid
    ON storico.comuni USING btree
    (valid_from ASC NULLS LAST, valid_to ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	
	


-- Table: storico.indirizzi

-- DROP TABLE IF EXISTS storico.indirizzi;

CREATE TABLE IF NOT EXISTS storico.indirizzi
(
    id integer NOT NULL DEFAULT nextval('storico.indirizzi_id_seq'::regclass),
    soggetto_ruolo_id integer NOT NULL,
    tipo_indirizzo_id integer NOT NULL,
    indirizzi_dettaglio_id integer,
    indirizzo_libero text COLLATE pg_catalog."default",
    stato_id integer,
    valid_from timestamp with time zone NOT NULL DEFAULT CURRENT_DATE,
    valid_to timestamp with time zone,
    data_insert timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    comune_id integer,
    codice_postale_id integer,
    administrative_area character varying(100) COLLATE pg_catalog."default",
    locality character varying(100) COLLATE pg_catalog."default",
    sublocality character varying(100) COLLATE pg_catalog."default",
    postal_box character varying(20) COLLATE pg_catalog."default",
    geoloc geometry(Point,4326),
    indirizzi_id integer,
    CONSTRAINT indirizzi_pkey PRIMARY KEY (id),
    CONSTRAINT fk_storico_indirizzi_codice_postale_id FOREIGN KEY (codice_postale_id)
        REFERENCES config.codici_postali (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_storico_indirizzi_comune_id FOREIGN KEY (comune_id)
        REFERENCES config.comuni (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_storico_indirizzi_dettaglio FOREIGN KEY (indirizzi_dettaglio_id)
        REFERENCES anagrafiche.indirizzi_dettaglio (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_storico_indirizzi_soggetto_ruolo FOREIGN KEY (soggetto_ruolo_id)
        REFERENCES anagrafiche.soggetti_ruoli (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_storico_indirizzi_stato_id FOREIGN KEY (stato_id)
        REFERENCES config.stati (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_storico_indirizzi_tipo_indirizzo FOREIGN KEY (tipo_indirizzo_id)
        REFERENCES config.tipi_indirizzi (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_storico_indirizzi_to_live FOREIGN KEY (indirizzi_id)
        REFERENCES anagrafiche.indirizzi (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS storico.indirizzi
    OWNER to postgres;

COMMENT ON TABLE storico.indirizzi
    IS 'Storico degli indirizzi associati a soggetto/ruolo per tipo indirizzo';

COMMENT ON COLUMN storico.indirizzi.valid_from
    IS 'Data inizio validità indirizzo (inclusiva), con fuso orario';

COMMENT ON COLUMN storico.indirizzi.valid_to
    IS 'Data fine validità indirizzo (esclusiva), con fuso orario';

COMMENT ON COLUMN storico.indirizzi.data_insert
    IS 'Data di inserimento del record storico, con fuso orario';

COMMENT ON COLUMN storico.indirizzi.user_insert
    IS 'Utente che ha creato il record storico';

COMMENT ON COLUMN storico.indirizzi.indirizzi_id
    IS 'Id dell''indirizzo su schema anagrafiche per collegamento diretto.';
-- Index: idx_storico_indirizzi_periodo

-- DROP INDEX IF EXISTS storico.idx_storico_indirizzi_periodo;

CREATE INDEX IF NOT EXISTS idx_storico_indirizzi_periodo
    ON storico.indirizzi USING btree
    (valid_from ASC NULLS LAST, valid_to ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_storico_indirizzi_soggetto_ruolo

-- DROP INDEX IF EXISTS storico.idx_storico_indirizzi_soggetto_ruolo;

CREATE INDEX IF NOT EXISTS idx_storico_indirizzi_soggetto_ruolo
    ON storico.indirizzi USING btree
    (soggetto_ruolo_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_storico_indirizzi_tipo

-- DROP INDEX IF EXISTS storico.idx_storico_indirizzi_tipo;

CREATE INDEX IF NOT EXISTS idx_storico_indirizzi_tipo
    ON storico.indirizzi USING btree
    (tipo_indirizzo_id ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	



-- Table: storico.stradario

-- DROP TABLE IF EXISTS storico.stradario;

CREATE TABLE IF NOT EXISTS storico.stradario
(
    id integer NOT NULL DEFAULT nextval('storico.stradario_id_seq'::regclass),
    via_id integer NOT NULL,
    comune_id integer NOT NULL,
    codice_postale_id integer,
    descrizione_via text COLLATE pg_catalog."default",
    valid_from date NOT NULL DEFAULT CURRENT_DATE,
    valid_to date,
    stato character(1) COLLATE pg_catalog."default" DEFAULT 'A'::bpchar,
    data_insert timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    CONSTRAINT pk_stradario PRIMARY KEY (id),
    CONSTRAINT fk_stradario_codice_postale_id FOREIGN KEY (codice_postale_id)
        REFERENCES config.codici_postali (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    CONSTRAINT fk_stradario_comune_id FOREIGN KEY (comune_id)
        REFERENCES config.comuni (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_stradario_via_id FOREIGN KEY (via_id)
        REFERENCES config.stradario (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS storico.stradario
    OWNER to postgres;

COMMENT ON TABLE storico.stradario
    IS 'Storico dei riferimenti alle vie nel tempo';

COMMENT ON COLUMN storico.stradario.via_id
    IS 'Collegamento alla via (config.stradario.id)';

COMMENT ON COLUMN storico.stradario.descrizione_via
    IS 'Descrizione testuale storica della via';

COMMENT ON COLUMN storico.stradario.valid_from
    IS 'Data inizio validità storica';

COMMENT ON COLUMN storico.stradario.valid_to
    IS 'Data fine validità (se nota)';

COMMENT ON COLUMN storico.stradario.stato
    IS 'Stato della via nel periodo: A=Attiva, S=Soppressa, F=Fusa, D=Divisa';
-- Index: idx_storico_stradario_comune

-- DROP INDEX IF EXISTS storico.idx_storico_stradario_comune;

CREATE INDEX IF NOT EXISTS idx_storico_stradario_comune
    ON storico.stradario USING btree
    (comune_id ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_storico_stradario_valid_periodo

-- DROP INDEX IF EXISTS storico.idx_storico_stradario_valid_periodo;

CREATE INDEX IF NOT EXISTS idx_storico_stradario_valid_periodo
    ON storico.stradario USING btree
    (valid_from ASC NULLS LAST, valid_to ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_storico_stradario_via_id

-- DROP INDEX IF EXISTS storico.idx_storico_stradario_via_id;

CREATE INDEX IF NOT EXISTS idx_storico_stradario_via_id
    ON storico.stradario USING btree
    (via_id ASC NULLS LAST)
    TABLESPACE pg_default;
	
	
	
	
	
	
	


-- Table: storico.stradario_trasformazioni

-- DROP TABLE IF EXISTS storico.stradario_trasformazioni;

CREATE TABLE IF NOT EXISTS storico.stradario_trasformazioni
(
    id integer NOT NULL DEFAULT nextval('storico.stradario_trasformazioni_id_seq'::regclass),
    via_id_orig integer NOT NULL,
    via_id_nuovo integer NOT NULL,
    tipo_evento character(1) COLLATE pg_catalog."default" NOT NULL,
    data_evento date NOT NULL,
    note text COLLATE pg_catalog."default",
    data_insert timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_insert character varying(80) COLLATE pg_catalog."default" DEFAULT CURRENT_USER,
    CONSTRAINT stradario_trasformazioni_pkey PRIMARY KEY (id),
    CONSTRAINT fk_stradario_trasf_via_nuovo FOREIGN KEY (via_id_nuovo)
        REFERENCES config.stradario (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_stradario_trasf_via_orig FOREIGN KEY (via_id_orig)
        REFERENCES config.stradario (id) MATCH SIMPLE
        ON UPDATE CASCADE
        ON DELETE RESTRICT
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS storico.stradario_trasformazioni
    OWNER to postgres;

COMMENT ON TABLE storico.stradario_trasformazioni
    IS 'Trasformazioni storiche delle vie (stradario)';

COMMENT ON COLUMN storico.stradario_trasformazioni.via_id_orig
    IS 'Via originale';

COMMENT ON COLUMN storico.stradario_trasformazioni.via_id_nuovo
    IS 'Via risultante dalla trasformazione';

COMMENT ON COLUMN storico.stradario_trasformazioni.tipo_evento
    IS 'Tipo evento: R=Rinominata, F=Fusa, D=Divisa';
-- Index: idx_stradario_trasf_via_nuovo

-- DROP INDEX IF EXISTS storico.idx_stradario_trasf_via_nuovo;

CREATE INDEX IF NOT EXISTS idx_stradario_trasf_via_nuovo
    ON storico.stradario_trasformazioni USING btree
    (via_id_nuovo ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_stradario_trasf_via_orig

-- DROP INDEX IF EXISTS storico.idx_stradario_trasf_via_orig;

CREATE INDEX IF NOT EXISTS idx_stradario_trasf_via_orig
    ON storico.stradario_trasformazioni USING btree
    (via_id_orig ASC NULLS LAST)
    TABLESPACE pg_default;