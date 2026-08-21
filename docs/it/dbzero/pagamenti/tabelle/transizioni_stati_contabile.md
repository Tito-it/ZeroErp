{% include-markdown "it/dbzero/pagamenti/manual/transizioni_stati_contabile.md" %}
# 📚 Tabella `transizioni_stati_contabile`

> 📝 **Descrizione**
>
> Matrice delle transizioni ammesse fra stati della DISTINTA contabile (pagamenti.vendite_contabili). Grafo letto da pagamenti.trgfn_vendite_contabili_guard_transizione: nessuna regola e' scritta nel codice. Percorso di D14-a-bis: BOZZA/IMPORTATA -&gt; VALIDATA|ANNULLATA, VALIDATA -&gt; CHIUSA|BOZZA|ANNULLATA, CHIUSA/ANNULLATA terminali. ⚠️ Le uscite da IMPORTATA non sono seminate finche' l'import da flusso non esiste.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| stato_da_id | smallint | NO |  |
| stato_a_id | smallint | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | ck_transizioni_stati_contabile_da_diverso_a |  |
| CHECK | ck_transizioni_stati_contabile_meta_ui |  |
| FOREIGN KEY | fk_transizioni_stati_contabile_a | stato_a_id |
| FOREIGN KEY | fk_transizioni_stati_contabile_da | stato_da_id |
| PRIMARY KEY | pk_transizioni_stati_contabile | id |
| UNIQUE | uq_transizioni_stati_contabile | stato_da_id, stato_a_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_transizioni_stati_contabile | `CREATE UNIQUE INDEX pk_transizioni_stati_contabile ON pagamenti.transizioni_stati_contabile USING btree (id)` |
| uq_transizioni_stati_contabile | `CREATE UNIQUE INDEX uq_transizioni_stati_contabile ON pagamenti.transizioni_stati_contabile USING btree (stato_da_id, stato_a_id)` |

---
{% include-markdown "signature-core.md" %}
