# 📚 Tabella `erogazioni_fonti`

> 📝 **Descrizione**
>
> Le combinazioni coerenti di tipo_erogazione (come si fattura una riga: CANONE, UNA_TANTUM, ORARIO, CONSUMO) e fonte_quantita_attesa (da dove viene la quantità: FISSA, MANUALE, TIMESHEET, LETTURE). Una riga per combinazione ammessa; e_default marca la fonte che una riga prende quando nessuno la indica (al più una per erogazione). Le righe di vendite.contratti_righe e vendite.offerte_commerciali_eccezioni vi si legano con una FK composta, che ha preso il posto dei CHECK chk_*_tipo_erog, chk_*_fonte_qta e chk_*_coerenza_fonte_erogazione (20261007-54). La legge script.trgfn_righe_default_fonte_qta. Niente attivo: è ciò che il modello ammette, non una configurazione. Seed: 80_data/sql/config/erogazioni_fonti.csv. Brief: brief-db-offerta-emissione-ed-erogazione §C.7 (B1). Rev 2026-10-21 (§I.1, 20261021-51): DERIVATA_COMPONENTI ritirata.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
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
| PRIMARY KEY | pk_erogazioni_fonti | id |
| UNIQUE | uq_erogazioni_fonti_coppia | tipo_erogazione, fonte_quantita_attesa |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_erogazioni_fonti | `CREATE UNIQUE INDEX pk_erogazioni_fonti ON config.erogazioni_fonti USING btree (id)` |
| uq_erogazioni_fonti_coppia | `CREATE UNIQUE INDEX uq_erogazioni_fonti_coppia ON config.erogazioni_fonti USING btree (tipo_erogazione, fonte_quantita_attesa)` |
| uq_erogazioni_fonti_default | `CREATE UNIQUE INDEX uq_erogazioni_fonti_default ON config.erogazioni_fonti USING btree (tipo_erogazione) WHERE e_default` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_erogazioni_fonti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_erogazioni_fonti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_erogazioni_fonti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_erogazioni_fonti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
