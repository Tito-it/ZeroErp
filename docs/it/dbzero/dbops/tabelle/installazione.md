{% include-markdown "it/dbzero/dbops/manual/installazione.md" %}
# 📚 Tabella `installazione`

> 📝 **Descrizione**
>
> L'ambiente di questa installazione: SVILUPPO o PRODUZIONE. Una riga sola (id = 1), vuota alla nascita: la scrive la fase post di scripts/sql/provision_zeroerp.sql col parametro -v ambiente=..., una volta, e poi non cambia piu' (guard trgfn_installazione_guard_immutabile, E_AMBIENTE_IMMUTABILE). Nessun default: un changeSet troverebbe database gia' esistenti e li dichiarerebbe al posto di chi li conosce. Fuori da config.parameters: il mirror CSV la riscriverebbe e l'app la potrebbe cambiare. L'app la legge e non la scrive. Si legge con script.fn_ambiente_installazione() (che fallisce se manca) o script.fn_ambiente_dichiarato() (che torna NULL, per i panorami). Brief: brief-db-processi-accensione-per-ambiente (A-1, R-1, R-2, R-3).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO | 1 |
| ambiente | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_installazione_ambiente |  |
| CHECK | chk_installazione_riga_unica |  |
| PRIMARY KEY | pk_installazione | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_installazione | `CREATE UNIQUE INDEX pk_installazione ON dbops.installazione USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_installazione_a05_guard_immutabile_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION dbops.trgfn_installazione_guard_immutabile()` |
| trg_installazione_a05_guard_immutabile_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_installazione_guard_immutabile()` |

---
{% include-markdown "signature-core.md" %}
