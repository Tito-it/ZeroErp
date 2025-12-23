{% include-markdown "it/dbzero/config/manual/forme_giuridiche.md" %}
# 📚 Tabella `forme_giuridiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_iso2 | character varying | NO |  |
| stato_id | bigint | YES |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| rea_policy | text | NO | 'NONE'::text |
| capitale_sociale_policy | text | NO | 'NONE'::text |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_forme_giuridiche_capitale_sociale_policy |  |
| CHECK | chk_forme_giuridiche_rea_policy |  |
| FOREIGN KEY | fk_forme_giuridiche_stato_id | stato_id |
| PRIMARY KEY | pk_forme_giuridiche | id |
| UNIQUE | uq_forme_giuridiche_statoiso2_codice | stato_iso2, codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_forme_giuridiche_codice | `CREATE INDEX ix_forme_giuridiche_codice ON config.forme_giuridiche USING btree (codice)` |
| ix_forme_giuridiche_stato_id | `CREATE INDEX ix_forme_giuridiche_stato_id ON config.forme_giuridiche USING btree (stato_id)` |
| pk_forme_giuridiche | `CREATE UNIQUE INDEX pk_forme_giuridiche ON config.forme_giuridiche USING btree (id)` |
| uq_forme_giuridiche_statoiso2_codice | `CREATE UNIQUE INDEX uq_forme_giuridiche_statoiso2_codice ON config.forme_giuridiche USING btree (stato_iso2, codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_forme_giuridiche_sync_stato_iso2_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |
| trg_forme_giuridiche_sync_stato_iso2_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_sync_stato_iso2()` |

---
{% include-markdown "signature-core.md" %}
