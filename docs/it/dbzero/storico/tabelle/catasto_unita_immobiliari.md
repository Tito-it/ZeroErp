{% include-markdown "it/dbzero/storico/manual/catasto_unita_immobiliari.md" %}
# 📚 Tabella `catasto_unita_immobiliari`

> 📝 **Descrizione**
>
> Storico snapshot (JSONB) per anagrafiche.catasto_unita_immobiliari con campi di audit e tx_id.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| catasto_unita_immobiliare_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_catasto_unita_immobiliari | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_storico_catasto_unita_immobiliari | `CREATE UNIQUE INDEX pk_storico_catasto_unita_immobiliari ON storico.catasto_unita_immobiliari USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_catasto_unita_immobiliari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_catasto_unita_immobiliari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
