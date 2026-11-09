{% include-markdown "it/dbzero/dbops/manual/credenziali_di_prova.md" %}
# 📚 Tabella `credenziali_di_prova`

> 📝 **Descrizione**
>
> L'etichetta di una credenziale di prova: una riga per ogni credenziale creata dal verbo dei dati di sviluppo (anagrafiche.fn_provisiona_dati_di_sviluppo), nella stessa transazione. Dato di macchina, come dbops.processi_identita. La FK fk_credenziali_di_prova_auth_user verso django.auth_user sta nel ponte di 90_end (nasce dove lo schema di Django c'e'), ON DELETE CASCADE: l'etichetta va via con la sua credenziale (script.fn_elimina_credenziale), e solo cosi'. Non cambia e non si toglie da sola (guard dbops.trgfn_etichette_di_prova_guard); in un'installazione PRODUZIONE non nasce. L'app la legge e non la scrive. Il presidio dbops.vw_radici_di_prova_in_produzione la guarda.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| auth_user_id | integer | NO |  |
| chiave | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_credenziali_di_prova_chiave |  |
| FOREIGN KEY | fk_credenziali_di_prova_auth_user | auth_user_id |
| PRIMARY KEY | pk_credenziali_di_prova | auth_user_id |
| UNIQUE | uq_credenziali_di_prova_chiave | chiave |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_credenziali_di_prova | `CREATE UNIQUE INDEX pk_credenziali_di_prova ON dbops.credenziali_di_prova USING btree (auth_user_id)` |
| uq_credenziali_di_prova_chiave | `CREATE UNIQUE INDEX uq_credenziali_di_prova_chiave ON dbops.credenziali_di_prova USING btree (chiave)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_credenziali_di_prova_a05_guard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |
| trg_credenziali_di_prova_a05_guard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |
| trg_credenziali_di_prova_a05_guard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |

---
{% include-markdown "signature-core.md" %}
