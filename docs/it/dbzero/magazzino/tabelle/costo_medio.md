# 📚 Tabella `costo_medio`

> 📝 **Descrizione**
>
> Stato corrente CMP per Articolo × Magazzino

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| magazzino_id | bigint | NO |  |
| qta | numeric | NO | 0 |
| valore | numeric | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_mag_costo_medio_magazzino | magazzino_id |
| PRIMARY KEY | pk_mag_costo_medio | id |
| UNIQUE | uq_mag_costo_medio_art_mag | articolo_id, magazzino_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_magazzino_costo_medio_magazzino_id | `CREATE INDEX ix_magazzino_costo_medio_magazzino_id ON magazzino.costo_medio USING btree (magazzino_id)` |
| pk_mag_costo_medio | `CREATE UNIQUE INDEX pk_mag_costo_medio ON magazzino.costo_medio USING btree (id)` |
| uq_mag_costo_medio_art_mag | `CREATE UNIQUE INDEX uq_mag_costo_medio_art_mag ON magazzino.costo_medio USING btree (articolo_id, magazzino_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_costo_medio_a10_magazzini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_costo_medio_a10_magazzini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('magazzino', 'magazzini', 'attivo', 'magazzino_id', 'id')` |
| trg_costo_medio_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_costo_medio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
