{% include-markdown "it/dbzero/pratiche/manual/pratiche_sorgenti.md" %}
# 📚 Tabella `pratiche_sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| sorgente_tipo_id | bigint | NO |  |
| sorgente_uid | text | NO |  |
| sorgente_riga | bigint | YES |  |
| ruolo_link | character varying | NO | 'ROOT'::character varying |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_pratiche_sorgenti_ruolo |  |
| FOREIGN KEY | fk_pratiche_sorgenti_pratica | pratica_id |
| FOREIGN KEY | fk_pratiche_sorgenti_tipo | sorgente_tipo_id |
| PRIMARY KEY | pk_pratiche_sorgenti | id |
| UNIQUE | uq_pratiche_sorgenti_pratica_tipo_uid_ruolo | pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_sorgenti_tipo_uid | `CREATE INDEX ix_pratiche_sorgenti_tipo_uid ON pratiche.pratiche_sorgenti USING btree (sorgente_tipo_id, sorgente_uid)` |
| pk_pratiche_sorgenti | `CREATE UNIQUE INDEX pk_pratiche_sorgenti ON pratiche.pratiche_sorgenti USING btree (id)` |
| uq_pratiche_sorgenti_pratica_tipo_uid_ruolo | `CREATE UNIQUE INDEX uq_pratiche_sorgenti_pratica_tipo_uid_ruolo ON pratiche.pratiche_sorgenti USING btree (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)` |

---
{% include-markdown "signature-core.md" %}
