# 📚 Tabella `ubicazioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| magazzino_id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| tipo_id | bigint | NO |  |
| parent_id | bigint | YES |  |
| area | character varying | YES |  |
| corsia | character varying | YES |  |
| scaffale | character varying | YES |  |
| piano | character varying | YES |  |
| posizione | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_tipi_ubicazione_magazzino | tipo_id |
| FOREIGN KEY | fk_mag_ubicazioni_magazzino | magazzino_id |
| FOREIGN KEY | fk_mag_ubicazioni_parent | parent_id |
| PRIMARY KEY | pk_mag_ubicazioni | id |
| UNIQUE | uq_mag_ubicazioni_mag_codice | magazzino_id, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_mag_ubicazioni_magazzino | `CREATE INDEX ix_mag_ubicazioni_magazzino ON magazzino.ubicazioni USING btree (magazzino_id)` |
| ix_mag_ubicazioni_parent | `CREATE INDEX ix_mag_ubicazioni_parent ON magazzino.ubicazioni USING btree (parent_id)` |
| ix_mag_ubicazioni_tipo | `CREATE INDEX ix_mag_ubicazioni_tipo ON magazzino.ubicazioni USING btree (tipo_id)` |
| pk_mag_ubicazioni | `CREATE UNIQUE INDEX pk_mag_ubicazioni ON magazzino.ubicazioni USING btree (id)` |
| uq_mag_ubicazioni_mag_codice | `CREATE UNIQUE INDEX uq_mag_ubicazioni_mag_codice ON magazzino.ubicazioni USING btree (magazzino_id, codice)` |

---
{% include-markdown "signature-core.md" %}
