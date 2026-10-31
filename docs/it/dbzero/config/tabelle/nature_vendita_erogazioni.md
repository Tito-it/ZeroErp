# 📚 Tabella `nature_vendita_erogazioni`

> 📝 **Descrizione**
>
> Come si eroga un articolo di questa natura di vendita, quando l'articolo non ha una tipologia di listino (decisione B-D1 di Tid del 2026-10-07: vince la tipologia, la natura è il ripiego). Stessa forma di config.listini_tipologie_erogazioni: combinazioni ammesse, default (al più uno per natura), generazione_canone sulle righe CANONE. Nessuna natura ammette LETTURE: le letture vengono da una tipologia a contatore. Seed: 80_data/sql/config/nature_vendita_erogazioni.csv. Brief: brief-db-offerta-emissione-ed-erogazione §C.5, §C.7 (B2).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| natura_vendita_id | bigint | NO |  |
| tipo_erogazione | character varying(16) | NO |  |
| fonte_quantita_attesa | character varying(32) | NO |  |
| e_default | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_nature_vendita_erogazioni_erogazione_fonte | tipo_erogazione, fonte_quantita_attesa |
| FOREIGN KEY | fk_nature_vendita_erogazioni_natura | natura_vendita_id |
| PRIMARY KEY | pk_nature_vendita_erogazioni | id |
| UNIQUE | uq_nature_vendita_erogazioni | natura_vendita_id, tipo_erogazione, fonte_quantita_attesa |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_nature_vendita_erogazioni | `CREATE UNIQUE INDEX pk_nature_vendita_erogazioni ON config.nature_vendita_erogazioni USING btree (id)` |
| uq_nature_vendita_erogazioni | `CREATE UNIQUE INDEX uq_nature_vendita_erogazioni ON config.nature_vendita_erogazioni USING btree (natura_vendita_id, tipo_erogazione, fonte_quantita_attesa)` |
| uq_nature_vendita_erogazioni_default | `CREATE UNIQUE INDEX uq_nature_vendita_erogazioni_default ON config.nature_vendita_erogazioni USING btree (natura_vendita_id) WHERE e_default` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_nature_vendita_erogazioni_a10_nature_vendita_require_552b1d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_nature_vendita_erogazioni_a10_nature_vendita_require_552b1d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_vendita', 'attivo', 'natura_vendita_id', 'id')` |
| trg_nature_vendita_erogazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_nature_vendita_erogazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_nature_vendita_erogazioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_nature_vendita_erogazioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
