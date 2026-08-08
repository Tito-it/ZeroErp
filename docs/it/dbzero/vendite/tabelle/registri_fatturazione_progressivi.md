{% include-markdown "it/dbzero/vendite/manual/registri_fatturazione_progressivi.md" %}
# 📚 Tabella `registri_fatturazione_progressivi`

> 📝 **Descrizione**
>
> Progressivi per assegnazione numeri fattura (registro/anno[/mese]/serie).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| registro_id | bigint | NO |  |
| anno | smallint | NO |  |
| mese | smallint | NO | 0 |
| serie | character varying | NO | ''::character varying |
| last_numero | bigint | NO | 0 |
| attivo | boolean | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_regprog_mese_valid |  |
| FOREIGN KEY | fk_registri_progressivi_registro | registro_id |
| PRIMARY KEY | pk_registri_progressivi | id |
| UNIQUE | uq_regprog_key | registro_id, anno, mese, serie |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_registri_progressivi | `CREATE UNIQUE INDEX pk_registri_progressivi ON vendite.registri_fatturazione_progressivi USING btree (id)` |
| uq_registri_progressivi_scope | `CREATE UNIQUE INDEX uq_registri_progressivi_scope ON vendite.registri_fatturazione_progressivi USING btree (registro_id, anno, COALESCE((mese)::integer, 0), COALESCE(serie, ''::character varying))` |
| uq_regprog_key | `CREATE UNIQUE INDEX uq_regprog_key ON vendite.registri_fatturazione_progressivi USING btree (registro_id, anno, mese, serie)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_registri_fatturazione_progressivi_a10_registri_fattu_285752 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_registri_fatturazione_progressivi_a10_registri_fattu_285752 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |

---
{% include-markdown "signature-core.md" %}
