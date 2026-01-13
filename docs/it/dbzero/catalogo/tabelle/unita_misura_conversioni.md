{% include-markdown "it/dbzero/catalogo/manual/unita_misura_conversioni.md" %}
# 📚 Tabella `unita_misura_conversioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uom_from_id | bigint | NO |  |
| uom_to_id | bigint | NO |  |
| fattore | numeric | NO |  |
| valido_dal | date | NO |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_uom_conv_fattore_pos |  |
| CHECK | chk_uom_conv_no_self |  |
| CHECK | chk_uom_conv_valid_dates |  |
| FOREIGN KEY | fk_uom_conv_from | uom_from_id |
| FOREIGN KEY | fk_uom_conv_to | uom_to_id |
| PRIMARY KEY | pk_unita_misura_conversioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_uom_conv_no_overlap | `CREATE INDEX ex_uom_conv_no_overlap ON catalogo.unita_misura_conversioni USING gist (uom_from_id, uom_to_id, daterange(valido_dal, COALESCE(valido_al, 'infinity'::date), '[]'::text))` |
| ix_uom_conv_from_to | `CREATE INDEX ix_uom_conv_from_to ON catalogo.unita_misura_conversioni USING btree (uom_from_id, uom_to_id, valido_dal, valido_al)` |
| ix_uom_conv_to_from | `CREATE INDEX ix_uom_conv_to_from ON catalogo.unita_misura_conversioni USING btree (uom_to_id, uom_from_id, valido_dal, valido_al)` |
| pk_unita_misura_conversioni | `CREATE UNIQUE INDEX pk_unita_misura_conversioni ON catalogo.unita_misura_conversioni USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
