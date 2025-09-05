# 📚 Tabella `magazzini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| indirizzo_dettaglio_id | integer | NO |  |
| attivo | boolean | NO | true |
| predefinito | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

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
| ix_magazzini_codice_upper | `CREATE INDEX ix_magazzini_codice_upper ON magazzino.magazzini USING btree (upper((codice)::text))` |
| ix_magazzini_indirizzo_dettaglio | `CREATE INDEX ix_magazzini_indirizzo_dettaglio ON magazzino.magazzini USING btree (indirizzo_dettaglio_id)` |
| pk_magazzini | `CREATE UNIQUE INDEX pk_magazzini ON magazzino.magazzini USING btree (id)` |
| uq_magazzini_codice | `CREATE UNIQUE INDEX uq_magazzini_codice ON magazzino.magazzini USING btree (codice)` |
| uq_magazzini_uid | `CREATE UNIQUE INDEX uq_magazzini_uid ON magazzino.magazzini USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_a10_magazzini_upd_protect_codice | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_a10_magazzini_protect_codice()` |
| trg_magazzini_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION magazzino.trgfn_magazzini_norm()` |
| trg_magazzini_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION magazzino.trgfn_magazzini_norm()` |

---
{% include-markdown "signature-core.md" %}
