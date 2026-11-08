{% include-markdown "it/dbzero/config/manual/messaggi_errore.md" %}
# 📚 Tabella `messaggi_errore`

> 📝 **Descrizione**
>
> Catalogo centralizzato dei messaggi (errori, avvisi, ecc.) con supporto i18n

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
| FOREIGN KEY | fk_messaggi_errore_codici_errore | codice |
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
| trg_messaggi_errore_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_messaggi_errore_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |

---
{% include-markdown "signature-core.md" %}
