# 📚 Tabella `periodicita`

> 📝 **Descrizione**
>
> Ogni quanto si addebita un canone: una riga per periodicità, con la durata del periodo in mesi. La leggono le righe di vendite.contratti_righe, vendite.offerte_commerciali_eccezioni e vendite.listini_righe (FK sul codice, 20261029-13) e il generatore dei periodi del canone. Niente attivo: è ciò che il modello ammette, non una configurazione. Seed: 80_data/sql/config/periodicita.csv. Brief: brief-db-contratto-righe-periodiche-in-commessa §6.5.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(100) | NO |  |
| mesi | smallint | NO |  |
| ordine | smallint | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_periodicita_mesi_divide_anno |  |
| PRIMARY KEY | pk_periodicita | id |
| UNIQUE | uq_periodicita_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_periodicita | `CREATE UNIQUE INDEX pk_periodicita ON config.periodicita USING btree (id)` |
| uq_periodicita_codice | `CREATE UNIQUE INDEX uq_periodicita_codice ON config.periodicita USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_periodicita_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_periodicita_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_periodicita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_periodicita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_periodicita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_periodicita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
