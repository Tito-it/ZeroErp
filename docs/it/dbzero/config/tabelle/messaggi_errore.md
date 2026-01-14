{% include-markdown "it/dbzero/config/manual/messaggi_errore.md" %}
# 📚 Tabella `messaggi_errore`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| lingua | text | NO | 'it'::text |
| messaggio | text | NO |  |
| id | bigint | NO |  |
| causa | text | YES |  |
| soluzione | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_cfg_messaggi_errore_lingua | lingua |
| PRIMARY KEY | pk_messaggi_errore | id |
| UNIQUE | uq_messaggi_errore_codice_lingua | codice, lingua |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_messaggi_errore | `CREATE UNIQUE INDEX pk_messaggi_errore ON config.messaggi_errore USING btree (id)` |
| uq_messaggi_errore_codice_lingua | `CREATE UNIQUE INDEX uq_messaggi_errore_codice_lingua ON config.messaggi_errore USING btree (codice, lingua)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_messaggi_errore_a10_lingue_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'lingua')` |
| trg_messaggi_errore_a10_lingue_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'lingue', 'attivo', 'lingua')` |

---
{% include-markdown "signature-core.md" %}
