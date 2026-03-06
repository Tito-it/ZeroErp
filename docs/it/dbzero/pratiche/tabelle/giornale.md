{% include-markdown "it/dbzero/pratiche/manual/giornale.md" %}
# 📚 Tabella `giornale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pratica_id | bigint | NO |  |
| flusso_id | bigint | YES |  |
| azione | character varying | NO |  |
| origine | character varying | NO | 'SISTEMA'::character varying |
| dettaglio | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_giornale_azione |  |
| CHECK | chk_giornale_origine |  |
| FOREIGN KEY | fk_giornale_flusso | flusso_id |
| FOREIGN KEY | fk_giornale_pratica | pratica_id |
| PRIMARY KEY | pk_pratiche_giornale | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_giornale_azione | `CREATE INDEX ix_pratiche_giornale_azione ON pratiche.giornale USING btree (azione)` |
| ix_pratiche_giornale_data_insert | `CREATE INDEX ix_pratiche_giornale_data_insert ON pratiche.giornale USING btree (data_insert)` |
| pk_pratiche_giornale | `CREATE UNIQUE INDEX pk_pratiche_giornale ON pratiche.giornale USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
