{% include-markdown "it/dbzero/storico/manual/identita_digitali.md" %}
# 📚 Tabella `identita_digitali`

> 📝 **Descrizione**
>
> Storico di anagrafiche.identita_digitali. Riceve uno snapshot JSON del record ad ogni UPDATE/DELETE tramite script.trgfn_storico_generic.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.identita_digitali_id_seq'::regclass) |
| identita_digitali_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_identita_digitali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_identita_digitali_identita_digitali_id_fk | `CREATE INDEX ix_identita_digitali_identita_digitali_id_fk ON storico.identita_digitali USING btree (identita_digitali_id)` |
| pk_storico_identita_digitali | `CREATE UNIQUE INDEX pk_storico_identita_digitali ON storico.identita_digitali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_identita_digitali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_digitali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
