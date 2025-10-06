{% include-markdown "it/dbzero/vendite/manual/articolo_regole_fatturazione.md" %}
# 📚 Tabella `articolo_regole_fatturazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
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
| FOREIGN KEY | fk_articolo_regole_fatturazione_articoli | articolo_id |
| PRIMARY KEY | pk_articolo_regole_fatturazione | id |
| UNIQUE | uq_articolo_regole_fatturazione_articolo | articolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_articolo_regole_fatturazione | `CREATE UNIQUE INDEX pk_articolo_regole_fatturazione ON vendite.articolo_regole_fatturazione USING btree (id)` |
| uq_articolo_regole_fatturazione_articolo | `CREATE UNIQUE INDEX uq_articolo_regole_fatturazione_articolo ON vendite.articolo_regole_fatturazione USING btree (articolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articolo_regole_fatturazione_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
