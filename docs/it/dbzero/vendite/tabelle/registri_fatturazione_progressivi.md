# 📚 Tabella `registri_fatturazione_progressivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| registro_id | bigint | NO |  |
| anno | smallint | NO |  |
| mese | smallint | YES |  |
| serie | character varying | YES |  |
| last_numero | bigint | NO | 0 |
| attivo | boolean | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | registri_fatturazione_progressivi |  |
| FOREIGN KEY | fk_registri_progressivi_registro | registro_id |
| PRIMARY KEY | pk_registri_progressivi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_registri_progressivi | `CREATE UNIQUE INDEX pk_registri_progressivi ON vendite.registri_fatturazione_progressivi USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
