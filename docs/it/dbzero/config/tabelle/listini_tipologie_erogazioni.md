# 📚 Tabella `listini_tipologie_erogazioni`

> 📝 **Descrizione**
>
> Come si eroga un articolo di questa tipologia di listino: le combinazioni (tipo_erogazione, fonte_quantita_attesa) ammesse e quella di default (e_default, al più una per tipologia), con la generazione_canone da proporre sulle righe CANONE. Sorgente del default e del perimetro delle righe di contratto e offerta per un articolo che ha una tipologia (decisioni B-R1, B-D4 di Tid del 2026-10-07: il perimetro è la tipologia dell'articolo, non la utility). Combinazioni coerenti per FK su config.erogazioni_fonti. Seed: 80_data/sql/config/listini_tipologie_erogazioni.csv. Brief: brief-db-offerta-emissione-ed-erogazione §C.5, §C.7 (B2).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| tipologia_id | smallint | NO |  |
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
| FOREIGN KEY | fk_listini_tipologie_erogazioni_erogazione_fonte | tipo_erogazione, fonte_quantita_attesa |
| FOREIGN KEY | fk_listini_tipologie_erogazioni_tipologia | tipologia_id |
| PRIMARY KEY | pk_listini_tipologie_erogazioni | id |
| UNIQUE | uq_listini_tipologie_erogazioni | tipologia_id, tipo_erogazione, fonte_quantita_attesa |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_tipologie_erogazioni | `CREATE UNIQUE INDEX pk_listini_tipologie_erogazioni ON config.listini_tipologie_erogazioni USING btree (id)` |
| uq_listini_tipologie_erogazioni | `CREATE UNIQUE INDEX uq_listini_tipologie_erogazioni ON config.listini_tipologie_erogazioni USING btree (tipologia_id, tipo_erogazione, fonte_quantita_attesa)` |
| uq_listini_tipologie_erogazioni_default | `CREATE UNIQUE INDEX uq_listini_tipologie_erogazioni_default ON config.listini_tipologie_erogazioni USING btree (tipologia_id) WHERE e_default` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_tipologie_erogazioni_a10_listini_tipologie_r_905c2f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_tipologie_erogazioni_a10_listini_tipologie_r_905c2f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_tipologie_erogazioni_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_erogazioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_erogazioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_erogazioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
