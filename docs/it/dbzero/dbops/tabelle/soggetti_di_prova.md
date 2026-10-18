{% include-markdown "it/dbzero/dbops/manual/soggetti_di_prova.md" %}
# 📚 Tabella `soggetti_di_prova`

> 📝 **Descrizione**
>
> L'etichetta di un soggetto di prova: una riga per ogni soggetto creato dal verbo dei dati di sviluppo (anagrafiche.fn_provisiona_dati_di_sviluppo), nella stessa transazione: gli emittenti, i clienti, il fornitore, le persone dietro le credenziali. Si etichettano le radici, non le righe: contratti, BA e documenti si ritrovano dalla radice a cui sono legati. Non cambia e non si toglie; in un'installazione PRODUZIONE non nasce (guard dbops.trgfn_etichette_di_prova_guard). L'app la legge e non la scrive. Il presidio dbops.vw_radici_di_prova_in_produzione la guarda. Brief: brief-db-processi-accensione-per-ambiente (R-4).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| soggetto_id | uuid | NO |  |
| chiave | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_di_prova_chiave |  |
| FOREIGN KEY | fk_soggetti_di_prova_soggetto | soggetto_id |
| PRIMARY KEY | pk_soggetti_di_prova | soggetto_id |
| UNIQUE | uq_soggetti_di_prova_chiave | chiave |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_soggetti_di_prova | `CREATE UNIQUE INDEX pk_soggetti_di_prova ON dbops.soggetti_di_prova USING btree (soggetto_id)` |
| uq_soggetti_di_prova_chiave | `CREATE UNIQUE INDEX uq_soggetti_di_prova_chiave ON dbops.soggetti_di_prova USING btree (chiave)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_di_prova_a05_guard_ins_upd_dlt | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |
| trg_soggetti_di_prova_a05_guard_ins_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |
| trg_soggetti_di_prova_a05_guard_ins_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_etichette_di_prova_guard()` |

---
{% include-markdown "signature-core.md" %}
