# 📚 Tabella `magazzini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| indirizzo_dettaglio_id | bigint | NO |  |
| attivo | boolean | NO | true |
| predefinito | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_magazzini_codice_nonvuoto |  |
| FOREIGN KEY | fk_magazzini_indirizzo_dettaglio | indirizzo_dettaglio_id |
| PRIMARY KEY | pk_magazzini | id |
| UNIQUE | uq_magazzini_codice | codice |
| UNIQUE | uq_magazzini_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_magazzini_indirizzo_dettaglio_id | `CREATE INDEX ix_magazzino_magazzini_indirizzo_dettaglio_id ON magazzino.magazzini USING btree (indirizzo_dettaglio_id)` |
| pk_magazzini | `CREATE UNIQUE INDEX pk_magazzini ON magazzino.magazzini USING btree (id)` |
| uq_magazzini_codice | `CREATE UNIQUE INDEX uq_magazzini_codice ON magazzino.magazzini USING btree (codice)` |
| uq_magazzini_uid | `CREATE UNIQUE INDEX uq_magazzini_uid ON magazzino.magazzini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_magazzini_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_magazzini_normalize()` |
| trg_magazzini_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_magazzini_normalize()` |

---
{% include-markdown "signature-core.md" %}
