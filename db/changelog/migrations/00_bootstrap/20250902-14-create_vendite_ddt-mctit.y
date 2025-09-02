# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Zero ERP — Acquisti: ordini_righe
# ------------------------------------------------------------
databaseChangeLog:

  - changeSet:
      id: 20250902-30-create_vendite_ddt
      author: mctit
      runOnChange: true
      validCheckSums: [ANY]

              #  -- Attori
              #  mittente_soggetto_ruolo_id  BIGINT,       -- es. la nostra azienda/ruolo
              #  destinatario_soggetto_ruolo_id BIGINT NOT NULL, -- cliente/ruolo
              #  vettore_soggetto_ruolo_id   BIGINT,       -- corriere/trasportatore (ruolo)
              #  -- Indirizzi (FK + snapshot)
              #  indirizzo_partenza_id       INTEGER,
              #  indirizzo_part_snapshot     JSONB          NOT NULL DEFAULT '{}'::jsonb,
              #  indirizzo_consegna_id       INTEGER,
              #  indirizzo_cons_snapshot     JSONB          NOT NULL DEFAULT '{}'::jsonb,
              
      changes:
        - createTable:
            schemaName: vendite
            tableName: ddt
            remarks: "Documento di Trasporto (DDT) – vendita."
            columns:
              - column: { name: id, type: BIGINT, autoIncrement: true, generationType: BY DEFAULT, constraints: { primaryKey: true, primaryKeyName: pk_ddtv, nullable: false }, remarks: "PK" }
              - column: { name: uid, type: UUID, defaultValueComputed: gen_random_uuid(), constraints: { nullable: false }, remarks: "Identificatore esterno (UUID) per API/integrazioni." }
              - column: { name: anno, type: SMALLINT, remarks: "Anno numerazione" }
              - column: { name: serie, type: VARCHAR(8), remarks: "Serie numerazione" }
              - column: { name: numero, type: VARCHAR(20), remarks: "Numero documento" }
              - column: { name: data, type: DATE, defaultValueComputed: CURRENT_DATE, constraints: { nullable: false }, remarks: "Data DDT" }
              - column: { name: stato, type: VARCHAR(16), defaultValue: "DRAFT", constraints: { nullable: false }, remarks: "Stato documento: DRAFT|EMESSO|SPEDITO|CONSEGNATO|RESO|ANNULLATO" }
              - column: { name: mittente_soggetto_ruolo_id, type: BIGINT, remarks: "Mittente (es. nostra azienda/ruolo)" }
              - column: { name: destinatario_soggetto_ruolo_id, type: BIGINT, constraints: { nullable: false }, remarks: "Destinatario (cliente/ruolo)" }
              - column: { name: vettore_soggetto_ruolo_id, type: BIGINT, remarks: "Vettore/corriere (ruolo anagrafico)" }
              - column: { name: indirizzo_partenza_id, type: INTEGER, remarks: "FK → indirizzo partenza" }
              - column: { name: indirizzo_part_snapshot, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Snapshot indirizzo partenza" }
              - column: { name: indirizzo_consegna_id, type: INTEGER, remarks: "FK → indirizzo consegna" }
              - column: { name: indirizzo_cons_snapshot, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Snapshot indirizzo consegna" }
              - column: { name: causale_trasporto, type: VARCHAR(40), remarks: "Causale trasporto" }
              - column: { name: aspetto_beni, type: VARCHAR(40), remarks: "Aspetto beni" }
              - column: { name: porto, type: VARCHAR(16), remarks: "FRANCO|ASSEGNATO." }
              - column: { name: num_colli, type: INTEGER, remarks: "Numero colli" }
              - column: { name: peso_lordo, type: NUMERIC("18,3"), remarks: "Peso lordo" }
              - column: { name: peso_netto, type: NUMERIC("18,3"), remarks: "Peso netto" }
              - column: { name: volume, type: NUMERIC("18,3"), remarks: "Volume" }
              - column: { name: targa, type: VARCHAR(20), remarks: "Targa veicolo" }
              - column: { name: autista, type: VARCHAR(80), remarks: "Nome autista" }
              - column: { name: data_ora_partenza, type: TIMESTAMPTZ, remarks: "Data/ora partenza" }
              - column: { name: data_ora_consegna_prev, type: TIMESTAMPTZ, remarks: "Data/ora consegna prevista" }
              - column: { name: tracking_code, type: VARCHAR(64), remarks: "Codice tracking spedizione (se disponibile)" }
              - column: { name: ordine_id, type: BIGINT, remarks: "FK → vendite.ordini.id (opzionale)" }
              - column: { name: source_tipo, type: VARCHAR(32), remarks: "Origine import (tipo)" }
              - column: { name: source_id, type: UUID, remarks: "Origine import (id)" }
              - column: { name: note, type: TEXT, remarks: "Note documento" }
              - column: { name: meta, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Estensioni JSON" }
              - column: { name: storicizza, type: BOOLEAN, defaultValueBoolean: true, constraints: { nullable: false }, remarks: "Snapshot su UPDATE/DELETE" }
              - column: { name: tx_id, type: UUID, remarks: "Id transazione" }
              - column: { name: data_insert, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data inserimento" }
              - column: { name: user_insert, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, constraints: { nullable: false }, remarks: "Audit: utente inserimento" }
              - column: { name: data_update, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data aggiornamento" }
              - column: { name: user_update, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, remarks: "Audit: utente aggiornamento" }

        # Foreign keys
        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: destinatario_soggetto_ruolo_id
            constraintName: fk_ddt_vendita_destinatario_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: mittente_soggetto_ruolo_id
            constraintName: fk_ddt_vendita_mittente_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: vettore_soggetto_ruolo_id
            constraintName: fk_ddt_vendita_vettore_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: indirizzo_partenza_id
            constraintName: fk_ddt_vendita_ind_part
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: indirizzo_consegna_id
            constraintName: fk_ddt_vendita_ind_cons
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: vendite
            baseTableName: ddt
            baseColumnNames: ordine_id
            constraintName: fk_ddt_vendita_ordine
            referencedTableSchemaName: vendite
            referencedTableName: ordini
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        # Check constraints
        - addCheckConstraint:
            schemaName: vendite
            tableName: ddt
            constraintName: chk_ddt_vendita_stato
            checkConstraint: "stato IN ('DRAFT','EMESSO','SPEDITO','CONSEGNATO','RESO','ANNULLATO')"

        - addCheckConstraint:
            schemaName: vendite
            tableName: ddt
            constraintName: chk_ddt_vendita_porto
            checkConstraint: "(porto IS NULL OR porto IN ('FRANCO','ASSEGNATO'))"

        - addCheckConstraint:
            schemaName: vendite
            tableName: ddt
            constraintName: chk_ddt_vendita_pesi_volumi_nonneg
            checkConstraint: "((peso_lordo IS NULL OR peso_lordo >= 0) AND (peso_netto IS NULL OR peso_netto >= 0) AND (volume IS NULL OR volume >= 0))"

        # Indici univoci
        - createIndex:
            schemaName: vendite
            tableName: ddt
            indexName: uq_ddt_vendita_anno_serie_numero
            unique: true
            columns:
              - column: { name: anno }
              - column: { name: serie }
              - column: { name: numero }
            where: "numero IS NOT NULL"

        - createIndex:
            schemaName: vendite
            tableName: ddt
            indexName: uq_ddt_vendita_uid
            unique: true
            columns:
              - column: { name: uid }
      
        - sql:
            splitStatements: false
            sql: |
               
                -- Idempotenza import
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='vendite' AND c.relname='uq_ddt_vendita_source'
                  ) THEN
                    CREATE UNIQUE INDEX uq_ddt_vendita_source
                      ON vendite.ddt(source_tipo, source_id)
                      WHERE source_tipo IS NOT NULL;
                    COMMENT ON INDEX vendite.uq_ddt_vendita_source IS 'Idempotenza import (source_tipo, source_id).';
                  END IF;
                END$$;

                -- Indici operativi
                CREATE INDEX IF NOT EXISTS ix_ddt_vendita_dest_stato_data
                  ON vendite.ddt(destinatario_soggetto_ruolo_id, stato, data);
                CREATE INDEX IF NOT EXISTS ix_ddt_vendita_stato
                  ON vendite.ddt(stato);

                
                -- Normalize: UPPER/trim su source_tipo
                CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_vendita_norm_source()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF NEW.source_tipo IS NOT NULL THEN
                    NEW.source_tipo := upper(btrim(NEW.source_tipo));
                  END IF;
                  RETURN NEW;
                END$$;

                DROP TRIGGER IF EXISTS trg_ddt_vendita_norm_source ON vendite.ddt;
                CREATE TRIGGER trg_ddt_vendita_norm_source
                BEFORE INSERT OR UPDATE ON vendite.ddt
                FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_ddt_vendita_norm_source();

                -- Protect: dopo EMESSO, vieta cambiare numerazione/data
                CREATE OR REPLACE FUNCTION vendite.trgfn_a10_ddt_vendita_protect_num()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                  IF OLD.stato IN ('EMESSO','SPEDITO','CONSEGNATO','RESO','ANNULLATO') THEN
                    IF NEW.numero IS DISTINCT FROM OLD.numero OR NEW.serie IS DISTINCT FROM OLD.serie OR NEW.anno IS DISTINCT FROM OLD.anno OR NEW.data IS DISTINCT FROM OLD.data THEN
                      PERFORM script.fn_log_and_raise_error('database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
                        jsonb_build_object('id', OLD.id, 'stato', OLD.stato), NULL::uuid, OLD.id::text);
                    END IF;
                  END IF;
                  RETURN NEW;
                END$$;

                DROP TRIGGER IF EXISTS trg_a10_ddt_vendita_protect_num ON vendite.ddt;
                CREATE TRIGGER trg_a10_ddt_vendita_protect_num
                BEFORE UPDATE ON vendite.ddt
                FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_a10_ddt_vendita_protect_num();


# Metto un  tag fine modifiche
  - changeSet:
      id: 20250902-90-create_vendite_ddt
      author: mctit
      changes:
        - tagDatabase:
            tag: 20250902-14-create_vendite_ddt