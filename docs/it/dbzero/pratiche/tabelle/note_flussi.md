{% include-markdown "it/dbzero/pratiche/manual/note_flussi.md" %}
# 📚 Tabella `note_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| flusso_id | bigint | NO |  |
| tipo_nota_id | integer | NO |  |
| contenuto | text | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_note_flussi_flusso | flusso_id |
| FOREIGN KEY | fk_note_flussi_tipo_nota | tipo_nota_id |
| PRIMARY KEY | pk_pratiche_note_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_note_flussi | `CREATE UNIQUE INDEX pk_pratiche_note_flussi ON pratiche.note_flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_flussi_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_note_flussi_giornale()` |

---
{% include-markdown "signature-core.md" %}
