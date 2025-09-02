{% include-markdown "it/dbzero/vendite/manual/regole_fatturazione_articolo.md" %}
# 📚 Tabella `regole_fatturazione_articolo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| prodotto_id | uuid | NO |  |
| visibilita_componenti | character varying | NO | 'solo_padre'::character varying |
| calcolo_qta_padre | character varying | NO | 'fissa'::character varying |
| arrotondamento_importi_dec | smallint | NO | 2 |
| arrotondamento_quantita_dec | smallint | NO | 3 |
| metodo_arrotondamento_importi | character varying | NO | 'HALF_UP'::character varying |
| metodo_arrotondamento_quantita | character varying | NO | 'HALF_UP'::character varying |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_regole_calcolo_qta_padre |  |
| CHECK | chk_regole_decimali_importi |  |
| CHECK | chk_regole_decimali_quantita |  |
| CHECK | chk_regole_metodo_arrotondamento_importi |  |
| CHECK | chk_regole_metodo_arrotondamento_quantita |  |
| CHECK | chk_regole_visibilita_componenti |  |
| FOREIGN KEY | fk_regole_fatturazione_articolo_articoli | prodotto_id |
| PRIMARY KEY | pk_regole_fatturazione_articolo | id |
| UNIQUE | uq_regole_fatturazione_articolo_prodotto | prodotto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_regole_fatturazione_articolo_prodotto | `CREATE INDEX ix_regole_fatturazione_articolo_prodotto ON vendite.regole_fatturazione_articolo USING btree (prodotto_id)` |
| pk_regole_fatturazione_articolo | `CREATE UNIQUE INDEX pk_regole_fatturazione_articolo ON vendite.regole_fatturazione_articolo USING btree (id)` |
| uq_regole_fatturazione_articolo_prodotto | `CREATE UNIQUE INDEX uq_regole_fatturazione_articolo_prodotto ON vendite.regole_fatturazione_articolo USING btree (prodotto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regole_fatturazione_articolo_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regole_fatturazione_articolo_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_regole_fatturazione_articolo_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_regole_fatturazione_articolo_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('regole_fatturazione_articolo_id')` |
| trg_z90_regole_fatturazione_articolo_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('regole_fatturazione_articolo_id')` |

---
{% include-markdown "signature-core.md" %}
