{% include-markdown "it/dbzero/pratiche/manual/giornale.md" %}
# 📚 Tabella `giornale`

> 📝 **Descrizione**
>
> Giornale di bordo — audit trail pratiche e flussi (append-only).

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
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

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

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_giornale_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_giornale_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_giornale_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_giornale_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
