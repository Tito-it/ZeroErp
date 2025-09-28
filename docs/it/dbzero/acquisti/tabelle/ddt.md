# 📚 Tabella `ddt`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | gen_random_uuid() |
| anno | smallint | YES |  |
| serie | character varying | YES |  |
| numero | character varying | YES |  |
| data | date | NO | CURRENT_DATE |
| stato_doc_ddt_id | bigint | NO |  |
| mittente_soggetto_ruolo_id | bigint | NO |  |
| destinatario_soggetto_ruolo_id | bigint | YES |  |
| causale_trasporto_id | bigint | YES |  |
| aspetto_bene_id | bigint | YES |  |
| modalita_addebito_trasporto_id | bigint | YES |  |
| num_colli | integer | YES |  |
| peso_lordo | numeric | YES |  |
| peso_netto | numeric | YES |  |
| volume | numeric | YES |  |
| data_ora_consegna_eff | timestamp with time zone | YES |  |
| ordine_id | bigint | YES |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_id | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| hash_contenuto | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_a_ddt_aspetto_bene | aspetto_bene_id |
| FOREIGN KEY | fk_a_ddt_causale_trasporto | causale_trasporto_id |
| FOREIGN KEY | fk_a_ddt_destinatario_ruolo | destinatario_soggetto_ruolo_id |
| FOREIGN KEY | fk_a_ddt_mittente_ruolo | mittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_a_ddt_mod_add_trasporto | modalita_addebito_trasporto_id |
| FOREIGN KEY | fk_a_ddt_ordine | ordine_id |
| FOREIGN KEY | fk_a_ddt_sorgente_tipo | sorgente_tipo_id |
| FOREIGN KEY | fk_a_ddt_stato_ddt | stato_doc_ddt_id |
| PRIMARY KEY | pk_ddta | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_a_ddt_mittente_stato_data | `CREATE INDEX ix_a_ddt_mittente_stato_data ON acquisti.ddt USING btree (mittente_soggetto_ruolo_id, stato_doc_ddt_id, data)` |
| pk_ddta | `CREATE UNIQUE INDEX pk_ddta ON acquisti.ddt USING btree (id)` |
| uq_a_ddt_anno_serie_numero | `CREATE UNIQUE INDEX uq_a_ddt_anno_serie_numero ON acquisti.ddt USING btree (anno, serie, numero)` |
| uq_a_ddt_sorgente | `CREATE UNIQUE INDEX uq_a_ddt_sorgente ON acquisti.ddt USING btree (sorgente_tipo_id, sorgente_id)` |
| uq_a_ddt_uid | `CREATE UNIQUE INDEX uq_a_ddt_uid ON acquisti.ddt USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ddt_a10_upd_a_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION acquisti.trgfn_a10_a_ddt_protect_num()` |

---
{% include-markdown "signature-core.md" %}
