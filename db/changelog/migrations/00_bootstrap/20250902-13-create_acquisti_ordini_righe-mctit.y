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
      id: 20250902-13-create-acquisti-ordini-righe
      author: mctit
      preConditions:
        - onFail: HALT
        
        - tableExists:  { schemaName: acquisti, tableName: ordini }   # testata già presente
      changes:
        - createTable:
            schemaName: acquisti
            tableName: ordini_righe
            remarks: "Righe ordine di acquisto, con snapshot descrizione/UoM/IVA e campi idempotenza."
            columns:
              - column: { name: id, type: BIGINT, autoIncrement: true, generationType: BY DEFAULT, constraints: { primaryKey: true, primaryKeyName: pk_orda_righe, nullable: false }, remarks: "PK" }
              - column: { name: ordine_id, type: BIGINT, constraints: { nullable: false }, remarks: "FK → acquisti.ordini.id (testata)" }
              - column: { name: riga_nr, type: INTEGER, constraints: { nullable: false }, remarks: "Numero riga (progressivo per ordine)" }
              - column: { name: articolo_id, type: UUID, constraints: { nullable: false }, remarks: "Articolo (catalogo.articoli.id)" }
              - column: { name: descrizione, type: VARCHAR(150), constraints: { nullable: false }, remarks: "Descrizione riga (snapshot)" }
              - column: { name: uom_id, type: BIGINT, remarks: "Unità di misura (catalogo.unita_misura.id)" }
              - column: { name: qta, type: NUMERIC(18,6), constraints: { nullable: false }, remarks: "Quantità" }
              - column: { name: prezzo_unitario, type: NUMERIC(18,6), constraints: { nullable: false }, remarks: "Prezzo unitario" }
              - column: { name: sconto_perc, type: NUMERIC(5,2), remarks: "Sconto % (0–100)" }
              - column: { name: iva_id, type: INTEGER, remarks: "Aliquota IVA (config.iva.id)" }
              - column: { name: iva_perc, type: NUMERIC(5,2), remarks: "IVA % (snapshot calcolo)" }
              - column: { name: stato_riga, type: VARCHAR(16), defaultValue: "DRAFT", constraints: { nullable: false }, remarks: "DRAFT|SENT|CONFIRMED|RECEIVED|INVOICED|CANCELLED" }
              - column: { name: source_tipo, type: VARCHAR(32), remarks: "Origine import (tipo)" }
              - column: { name: source_id, type: UUID, remarks: "Origine import (id)" }
              - column: { name: source_riga, type: BIGINT, defaultValueNumeric: 0, remarks: "Origine import (riga)" }
              - column: { name: note, type: TEXT, remarks: "Note riga" }
              - column: { name: meta, type: JSONB, defaultValue: "{}", constraints: { nullable: false }, remarks: "Estensioni JSON" }
              - column: { name: tx_id, type: UUID, remarks: "Id transazione" }
              - column: { name: storicizza, type: BOOLEAN, defaultValueBoolean: true, constraints: { nullable: false }, remarks: "Snapshot su UPDATE/DELETE" }
              - column: { name: data_insert, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data inserimento" }
              - column: { name: user_insert, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, constraints: { nullable: false }, remarks: "Audit: utente inserimento" }
              - column: { name: data_update, type: TIMESTAMPTZ, defaultValueComputed: now(), constraints: { nullable: false }, remarks: "Audit: data aggiornamento" }
              - column: { name: user_update, type: VARCHAR(80), defaultValueComputed: CURRENT_USER, remarks: "Audit: utente aggiornamento" }

        # Foreign keys
        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini_righe
            baseColumnNames: ordine_id
            constraintName: fk_ordini_a_r_testata
            referencedTableSchemaName: acquisti
            referencedTableName: ordini
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: CASCADE

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini_righe
            baseColumnNames: articolo_id
            constraintName: fk_ordini_a_r_articolo
            referencedTableSchemaName: catalogo
            referencedTableName: articoli
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini_righe
            baseColumnNames: uom_id
            constraintName: fk_ordini_a_r_uom
            referencedTableSchemaName: catalogo
            referencedTableName: unita_misura
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        - addForeignKeyConstraint:
            baseTableSchemaName: acquisti
            baseTableName: ordini_righe
            baseColumnNames: iva_id
            constraintName: fk_ordini_a_r_iva
            referencedTableSchemaName: config
            referencedTableName: iva
            referencedColumnNames: id
            onUpdate: CASCADE
            onDelete: NO ACTION

        # Checks
        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini_righe
            constraintName: chk_ordini_a_r_qta_pos
            checkConstraint: "(qta > 0)"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini_righe
            constraintName: chk_ordini_a_r_prezzo_pos
            checkConstraint: "(prezzo_unitario >= 0)"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini_righe
            constraintName: chk_ordini_a_r_sconto_perc
            checkConstraint: "(sconto_perc IS NULL OR (sconto_perc >= 0 AND sconto_perc <= 100))"

        - addCheckConstraint:
            schemaName: acquisti
            tableName: ordini_righe
            constraintName: chk_ordini_a_r_stato_riga
            checkConstraint: "(stato_riga IN ('DRAFT','SENT','CONFIRMED','RECEIVED','INVOICED','CANCELLED'))"

        # Indice unico su (ordine_id, riga_nr)
        - createIndex:
            schemaName: acquisti
            tableName: ordini_righe
            indexName: uq_ordini_a_r_riga_nr
            unique: true
            columns:
              - column: { name: ordine_id }
              - column: { name: riga_nr }

      
        - sql:
            splitStatements: false
            sql: |

              -- Idempotenza riga
              DO $$
              BEGIN
                IF NOT EXISTS (
                  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  WHERE n.nspname='acquisti' AND c.relname='uq_ordini_a_r_source'
                ) THEN
                  CREATE UNIQUE INDEX uq_ordini_a_r_source
                    ON acquisti.ordini_righe(source_tipo, source_id, source_riga)
                    WHERE source_tipo IS NOT NULL;
                  COMMENT ON INDEX acquisti.uq_ordini_a_r_source IS 'Idempotenza import riga (source_tipo, source_id, source_riga).';
                END IF;
              END$$;

              -- Indici operativi
              CREATE INDEX IF NOT EXISTS ix_ordini_a_r_testata ON acquisti.ordini_righe(ordine_id);
              CREATE INDEX IF NOT EXISTS ix_ordini_a_r_articolo ON acquisti.ordini_righe(articolo_id);
              CREATE INDEX IF NOT EXISTS ix_ordini_a_r_stato    ON acquisti.ordini_righe(stato_riga);

              
              -- Normalize source_* riga
              CREATE OR REPLACE FUNCTION acquisti.trgfn_ordini_a_r_norm_source()
              RETURNS trigger LANGUAGE plpgsql AS $$
              BEGIN
                IF NEW.source_tipo IS NOT NULL THEN
                  NEW.source_tipo := upper(btrim(NEW.source_tipo));
                  IF NEW.source_riga IS NULL THEN NEW.source_riga := 0; END IF;
                END IF;
                RETURN NEW;
              END$$;

              DROP TRIGGER IF EXISTS trg_ordini_a_r_norm_source ON acquisti.ordini_righe;
              CREATE TRIGGER trg_ordini_a_r_norm_source
              BEFORE INSERT OR UPDATE ON acquisti.ordini_righe
              FOR EACH ROW EXECUTE FUNCTION acquisti.trgfn_ordini_a_r_norm_source();

# Metto un  tag fine modifiche
  - changeSet:
      id: 20250902-90-create-acquisti-ordini_righe
      author: mctit
      changes:
        - tagDatabase:
            tag: 20250902-13-create-acquisti-ordini_righe