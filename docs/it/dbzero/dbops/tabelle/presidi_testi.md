{% include-markdown "it/dbzero/dbops/manual/presidi_testi.md" %}
# 📚 Tabella `presidi_testi`

> 📝 **Descrizione**
>
> Il testo di un presidio per CHI DEVE AGIRE, per lingua: `significato` (cosa vuol dire una riga) e `azione` (cosa fare per spegnerlo). ⛔ Non sostituisce il COMMENT della vista ne' la `nota` di dbops.presidi: quelli sono scritti per chi MANTIENE il presidio e restano com'erano. Chi lo spegne e' un dato del presidio, non del testo: dbops.presidi.chi_agisce. Lo leggono il pannello dei processi automatici e il digest (che va per email, senza i locali del frontend: per questo il testo sta a DB, come config.messaggi_errore). ⭐ VARIANTI, dal 2026-10-09: `variante` NULL e' il testo del presidio; valorizzata e' il testo delle righe la cui colonna dbops.presidi.colonna_variante vale quel valore. Chiave (vista, lingua, variante) NULLS NOT DISTINCT. ⛔ Il testo generico non fa da ripiego per una variante senza testo; una lingua che manca ripiega sull'italiano DELLA STESSA variante. La completezza — ogni presidio attivo, non obsoleto e non INVENTARIO ha la riga `it` generica; le varianti stanno solo sui presidi che dichiarano colonna_variante, e ognuna ha la sua riga `it` — la garantisce il pgTAP dbops/test-presidi-testi-v1, perche' un CHECK non guarda un'altra tabella; che ogni causa che la vista puo' produrre abbia il suo testo lo garantisce il pgTAP del presidio. Seed: 80_data/sql/dbops/presidi_testi.csv. Brief: brief-db-presidi-cosa-significa-cosa-fare §4.1, brief-db-presidio-processi-testo-per-causa §3 B.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| vista | text | NO |  |
| lingua | text | NO |  |
| significato | text | NO |  |
| azione | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| variante | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_presidi_testi_azione_non_vuota |  |
| CHECK | chk_presidi_testi_significato_non_vuoto |  |
| CHECK | chk_presidi_testi_variante_non_vuota |  |
| FOREIGN KEY | fk_presidi_testi_lingue | lingua |
| FOREIGN KEY | fk_presidi_testi_presidi | vista |
| FOREIGN KEY | fk_presidi_testi_presidi_cause | vista, variante |
| PRIMARY KEY | pk_presidi_testi | id |
| UNIQUE | uq_presidi_testi_vista_lingua_variante | vista, lingua, variante |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_presidi_testi | `CREATE UNIQUE INDEX pk_presidi_testi ON dbops.presidi_testi USING btree (id)` |
| uq_presidi_testi_vista_lingua_variante | `CREATE UNIQUE INDEX uq_presidi_testi_vista_lingua_variante ON dbops.presidi_testi USING btree (vista, lingua, variante) NULLS NOT DISTINCT` |

---
{% include-markdown "signature-core.md" %}
