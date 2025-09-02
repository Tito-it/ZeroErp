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
# Zero ERP — Acquisti: DDT (Documento di Trasporto)
# ------------------------------------------------------------

databaseChangeLog:

  - changeSet:
      id: 20250902-17-create_acquisti_ddt
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
            schemaName: acquisti
            tableName: ddt
            remarks: "Documento di Trasporto (DDT) – acquisto (ricezione da fornitore)."
            columns:
              - column: { name: id, type: BIGINT, autoIncrement: true, generationType: BY DEFAULT, constraints: { primaryKey: true, primaryKeyName: pk_ddta, nullable: false }, remarks: "PK" }
              - column: { name: uid, type: UUID, defaultValueComputed: gen_random_uuid(), constraints: { nullable: false }, remarks: "Identificatore esterno (UUID) per API/integrazioni." }
              # Numerazione fornitore (opzionale)
              - column: { name: anno, type: SMALLINT, remarks: "Anno numerazione fornitore (opzionale)" }
              - column: { name: serie, type: VARCHAR(8), remarks: "Serie numerazione fornitore (opzionale)" }
              - column: { name: numero, type: VARCHAR(40), remarks: "Numero DDT del fornitore (spesso alfanumerico)." }
              - column: { name: data, type: DATE, defaultValueComputed: CURRENT_DATE, constraints: { nullable: false }, remarks: "Data DDT" }
              - column: { name: stato, type: VARCHAR(16), defaultValue: "DRAFT", constraints: { nullable: false }, remarks: "Stato: DRAFT|RICEVUTO|VERIFICATO|ANNULLATO" }
              # Attori
              - column: { name: mittente_soggetto_ruolo_id, type: BIGINT, constraints: { nullable: false }, remarks: "Mittente (fornitore/ruolo)" }
              - column: { name: destinatario_soggetto_ruolo_id, type: BIGINT, remarks: "Destinatario (nostra azienda/ruolo, facoltativo)" }
              # Indirizzi + snapshot
              - column: { name: indirizzo_partenza_id, type: INTEGER, remarks: "FK → indirizzo partenza" }
              - column: { name: indirizzo_part_snapshot, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Snapshot indirizzo partenza" }
              - column: { name: indirizzo_consegna_id, type: INTEGER, remarks: "FK → indirizzo consegna" }
              - column: { name: indirizzo_cons_snapshot, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Snapshot indirizzo consegna" }
              # Dati trasporto
              - column: { name: causale_trasporto, type: VARCHAR(40), remarks: "Causale trasporto" }
              - column: { name: aspetto_beni, type: VARCHAR(40), remarks: "Aspetto beni" }
              - column: { name: porto, type: VARCHAR(16), remarks: "FRANCO|ASSEGNATO" }
              - column: { name: num_colli, type: INTEGER, remarks: "Numero colli" }
              - column: { name: peso_lordo, type: NUMERIC("18,3"), remarks: "Peso lordo" }
              - column: { name: peso_netto, type: NUMERIC("18,3"), remarks: "Peso netto" }
              - column: { name: volume, type: NUMERIC("18,3"), remarks: "Volume" }
              - column: { name: data_ora_consegna_eff, type: TIMESTAMPTZ, remarks: "Data/ora consegna effettiva" }
              # Collegamenti
              - column: { name: ordine_id, type: BIGINT, remarks: "FK → acquisti.ordini.id (opzionale)" }
              # Origine / idempotenza
              - column: { name: source_tipo, type: VARCHAR(32), remarks: "Origine import (tipo)" }
              - column: { name: source_id, type: UUID, remarks: "Origine import (id)" }
              # Note/meta/audit
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
            baseTableSchemaName: acquisti
            baseTableName: ddt
            baseColumnNames: mittente_soggetto_ruolo_id
            constraintName: fk_ddt_acquisto_mittente_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ddt
            baseColumnNames: destinatario_soggetto_ruolo_id
            constraintName: fk_ddt_acquisto_destinatario_ruolo
            referencedTableSchemaName: anagrafiche
            referencedTableName: soggetti_ruoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ddt
            baseColumnNames: indirizzo_partenza_id
            constraintName: fk_ddt_acquisto_ind_part
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ddt
            baseColumnNames: indirizzo_consegna_id
            constraintName: fk_ddt_acquisto_ind_cons
            referencedTableSchemaName: anagrafiche
            referencedTableName: indirizzi
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ddt
            baseColumnNames: ordine_id
            constraintName: fk_ddt_acquisto_ordine
            referencedTableSchemaName: acquisti
            referencedTableName: ordini
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        # Check constraints
        - addCheckConstraint:
            schemaName: acquisti
            tableName: ddt
            constraintName: chk_ddt_acquisto_stato
            checkConstraint: "stato IN ('DRAFT','RICEVUTO','VERIFICATO','ANNULLATO')"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ddt
            constraintName: chk_ddt_acquisto_porto
            checkConstraint: "(porto IS NULL OR porto IN ('FRANCO','ASSEGNATO'))"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ddt
            constraintName: chk_ddt_acquisto_pesi_nonneg
            checkConstraint: "((peso_lordo IS NULL OR peso_lordo >= 0) AND (peso_netto IS NULL OR peso_netto >= 0) AND (volume IS NULL OR volume >= 0))"

        # Indici (unici e non)
        - createIndex:
            schemaName: acquisti
            tableName: ddt
            indexName: uq_ddt_acquisto_anno_serie_numero
            unique: true
            columns:
              - column: { name: anno }
              - column: { name: serie }
              - column: { name: numero }
            where: "numero IS NOT NULL"

        - createIndex:
            schemaName: acquisti
            tableName: ddt
            indexName: uq_ddt_acquisto_uid
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
                  WHERE n.nspname='acquisti' AND c.relname='uq_ddt_acquisto_source'
                ) THEN
                  CREATE UNIQUE INDEX uq_ddt_acquisto_source
                    ON acquisti.ddt(source_tipo, source_id)
                    WHERE source_tipo IS NOT NULL;
                  COMMENT ON INDEX acquisti.uq_ddt_acquisto_source IS 'Idempotenza import (source_tipo, source_id).';
                END IF;
              END$$;

              -- Indici operativi
              CREATE INDEX IF NOT EXISTS ix_ddt_acquisto_mittente_stato_data
                ON acquisti.ddt(mittente_soggetto_ruolo_id, stato, data);
              CREATE INDEX IF NOT EXISTS ix_ddt_acquisto_stato
                ON acquisti.ddt(stato);

              
              -- Normalize: UPPER/trim su source_tipo
              CREATE OR REPLACE FUNCTION acquisti.trgfn_ddt_acquisto_norm_source()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF NEW.source_tipo IS NOT NULL THEN
                  NEW.source_tipo := upper(btrim(NEW.source_tipo));
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_ddt_acquisto_norm_source ON acquisti.ddt;
              CREATE TRIGGER trg_ddt_acquisto_norm_source
              BEFORE INSERT OR UPDATE ON acquisti.ddt
              FOR EACH ROW EXECUTE FUNCTION acquisti.trgfn_ddt_acquisto_norm_source();

              -- Protect: dopo RICEVUTO/VERIFICATO, blocca numerazione/data
              CREATE OR REPLACE FUNCTION acquisti.trgfn_a10_ddt_acquisto_protect_num()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF OLD.stato IN ('RICEVUTO','VERIFICATO','ANNULLATO') THEN
                  IF NEW.numero IS DISTINCT FROM OLD.numero OR NEW.serie IS DISTINCT FROM OLD.serie OR NEW.anno IS DISTINCT FROM OLD.anno OR NEW.data IS DISTINCT FROM OLD.data THEN
                    PERFORM script.fn_log_and_raise_error('database', TG_NAME, 'E_NUMERAZIONE_IMMUTABILE',
                      jsonb_build_object('id', OLD.id, 'stato', OLD.stato), NULL::uuid, OLD.id::text);
                  END IF;
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_a10_ddt_acquisto_protect_num ON acquisti.ddt;
              CREATE TRIGGER trg_a10_ddt_acquisto_protect_num
              BEFORE UPDATE ON acquisti.ddt
              FOR EACH ROW EXECUTE FUNCTION acquisti.trgfn_a10_ddt_acquisto_protect_num();


# Metto un  tag fine modifiche
  - changeSet:
      id: 20250902-90-create_acquisti_ddt
      author: mctit
      changes:
        - tagDatabase:
            tag: 20250902-17-create_acquisti_ddt