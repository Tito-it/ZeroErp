# 📚 Tabella `tipi_entita`

> 📝 **Descrizione**
>
> Catalogo di «che cosa e' questa entita'», condiviso dal perimetro del giornale (vendite.event_log.entity_type) e dal bersaglio degli errori. ⛔ SENZA colonna attivo, e non e' una dimenticanza: una FK verso un padre con attivo fa generare a dbops.fn_run_automations_attivo un lucchetto require_attivo, e il diario smetterebbe di scrivere per una voce di elenco disattivata — la D-12 violata da un'automazione, alle 21:00. La deprecazione si fa con obsoleto_dal. ⚠️ Non si estende config.sorgenti e non ci si aggancia: quella dice «da dove NASCE questo documento» (lineage e push), questa dice «CHE COSA E' questa entita'» (perimetro e bersaglio) — vocabolari che si intersecano, domande no.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| codice | text | NO |  |
| etichetta_key | text | NO |  |
| modo_risoluzione_emittente | text | YES |  |
| obsoleto_dal | date | YES |  |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| key_selector | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_entita_key_selector |  |
| CHECK | chk_tipi_entita_modo |  |
| PRIMARY KEY | pk_tipi_entita | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_entita | `CREATE UNIQUE INDEX pk_tipi_entita ON config.tipi_entita USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_entita_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_entita_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
