# 📚 Tabella `eventi_dominio`

> 📝 **Descrizione**
>
> Catalogo dei codici evento del giornale (vendite.event_log.event_code), col DOMINIO come attributo del codice e non come secondo asse — ed e' la ragione per cui event_log.domain e' stata tolta: una copia derivabile su ogni riga puo' dissentire dal catalogo e nessun vincolo puo' impedirlo. ⛔ event_log NON ha una FK verso qui, ed e' deliberato: rifiutare una scrittura perche' il codice non e' dichiarato sarebbe il diario che smette di scrivere per un problema di configurazione, cioe' la D-12 violata. Il presidio e' un cancello che fallisce la BUILD (consegna BE-9), non la scrittura. ⛔ E niente colonna attivo, come su config.tipi_entita.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| dominio | text | NO |  |
| etichetta_key | text | NO |  |
| obsoleto_dal | date | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_eventi_dominio | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_eventi_dominio_dominio | `CREATE INDEX ix_eventi_dominio_dominio ON config.eventi_dominio USING btree (dominio)` |
| pk_eventi_dominio | `CREATE UNIQUE INDEX pk_eventi_dominio ON config.eventi_dominio USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_eventi_dominio_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_eventi_dominio_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_eventi_dominio_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_eventi_dominio_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
