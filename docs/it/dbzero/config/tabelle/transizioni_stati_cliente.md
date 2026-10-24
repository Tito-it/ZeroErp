{% include-markdown "it/dbzero/config/manual/transizioni_stati_cliente.md" %}
# 📚 Tabella `transizioni_stati_cliente`

> 📝 **Descrizione**
>
> Passaggi di stato ammessi per anagrafiche.clienti (C-5, C-6 di Tid del 2026-10-14): da CH, CM, CW si va solo a CF; CF e AN sono terminali; fra attivo e sospeso nei due versi. Lo legge anagrafiche.trgfn_clienti_guard_stato_date sul cambio di stato (E_CLIENTE_STATO_TRANSIZIONE_INVALIDA); l'INSERT non passa dal grafo. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | integer | NO |  |
| stato_a_id | integer | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_cliente_da_diverso_a |  |
| FOREIGN KEY | fk_tsc_a | stato_a_id |
| FOREIGN KEY | fk_tsc_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_cliente | id |
| UNIQUE | uq_transizioni_stati_cliente | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_cliente | `CREATE UNIQUE INDEX pk_transizioni_stati_cliente ON config.transizioni_stati_cliente USING btree (id)` |
| uq_transizioni_stati_cliente | `CREATE UNIQUE INDEX uq_transizioni_stati_cliente ON config.transizioni_stati_cliente USING btree (stato_da_id, stato_a_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transizioni_stati_cliente_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transizioni_stati_cliente_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
