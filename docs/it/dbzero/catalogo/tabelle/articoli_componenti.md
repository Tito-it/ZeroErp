{% include-markdown "it/dbzero/catalogo/manual/articoli_componenti.md" %}
# 📚 Tabella `articoli_componenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| prodotto_id | uuid | NO |  |
| componente_id | uuid | NO |  |
| coeff_qta | numeric | NO | 1 |
| partecipa_qta | boolean | NO | false |
| obbligatorio | boolean | NO | true |
| valid_from | date | NO |  |
| valid_to | date | YES |  |
| note | character varying | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |
| storicizza | boolean | YES | true |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_articoli_componenti_coeff_qta_pos |  |
| CHECK | chk_articoli_componenti_no_selfref |  |
| CHECK | chk_articoli_componenti_valid_dates |  |
| FOREIGN KEY | fk_articoli_componenti_articoli_componente | componente_id |
| FOREIGN KEY | fk_articoli_componenti_articoli_prodotto | prodotto_id |
| PRIMARY KEY | pk_articoli_componenti | id |
| UNIQUE | uq_articoli_componenti_prodotto_componente_from | componente_id, valid_from, prodotto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_articoli_componenti_no_overlap | `CREATE INDEX ex_articoli_componenti_no_overlap ON catalogo.articoli_componenti USING gist (prodotto_id, componente_id, daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[]'::text))` |
| ix_articoli_componenti_componente_from_to | `CREATE INDEX ix_articoli_componenti_componente_from_to ON catalogo.articoli_componenti USING btree (componente_id, valid_from, valid_to)` |
| ix_articoli_componenti_prodotto_from_to | `CREATE INDEX ix_articoli_componenti_prodotto_from_to ON catalogo.articoli_componenti USING btree (prodotto_id, valid_from, valid_to)` |
| pk_articoli_componenti | `CREATE UNIQUE INDEX pk_articoli_componenti ON catalogo.articoli_componenti USING btree (id)` |
| uq_articoli_componenti_prodotto_componente_from | `CREATE UNIQUE INDEX uq_articoli_componenti_prodotto_componente_from ON catalogo.articoli_componenti USING btree (prodotto_id, componente_id, valid_from)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_componenti_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
