---
search:
  exclude: true
---

# Schema `catalogo`

## 📚 Tabelle
- [articoli](tabelle/articoli.md) — (latest review 13-01-26) `catalogo.articoli` è l’anagrafica **centrale** di articoli/voci, utilizzabile sia per il **catalogo prodotti** tradizionale sia per **voci utility** (canoni, oneri, misurazioni, ecc.). Supporta:
- [articoli_componenti](tabelle/articoli_componenti.md) — (latest review 13-01-26) `catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valido_dal`..`valido_al`).
- [articoli_uom_operativa](tabelle/articoli_uom_operativa.md) — (latest review 13-01-26) Mappa, per ciascun **articolo**, le **unità di misura operative** ammesse e il **fattore di conversione** verso la **UoM base**. Permette di lavorare con confezioni (es. *cartone 6 bottiglie*, *scatola 50 pz*) mantenendo **coerenza contabile e di stock** in **UoM base**.
- [note](tabelle/note.md) — (last review 13-01-26) `catalogo.note` centralizza le **note testuali** associate agli oggetti del catalogo, con **tabella partizionata** per tipo di target. Supporta note su:
- [note_articoli](tabelle/note_articoli.md) — (rev 2026-08-21)
- [note_articoli_componenti](tabelle/note_articoli_componenti.md) — (rev 2026-08-21)
- [unita_misura](tabelle/unita_misura.md)
- [unita_misura_conversioni](tabelle/unita_misura_conversioni.md)
- [uom_tipi](tabelle/uom_tipi.md)

## ⚙️ Funzioni
- [fn_articoli_ammessi](funzioni/fn_articoli_ammessi.md) — (nasce 2026-10-14, brief-db-articoli-ammessi-per-documento, Lotto 4: R-2, R-4, R-5; A-1, A-2, A-7)
- [fn_articolo_colonne_struttura](funzioni/fn_articolo_colonne_struttura.md) — (nasce 2026-10-18, brief-db-articoli-ammessi-per-documento R-DB-3)
- [fn_articolo_correggi_struttura](funzioni/fn_articolo_correggi_struttura.md) — (latest review 2026-10-18, brief-db-articoli-ammessi-per-documento A-10, R-DB-3)
- [fn_articolo_righe_vive_non_ammesse](funzioni/fn_articolo_righe_vive_non_ammesse.md) — (nasce 2026-10-18, brief-db-articoli-ammessi-per-documento A-11)
- [fn_articolo_usato](funzioni/fn_articolo_usato.md) — (latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)
- [fn_get_uom_base](funzioni/fn_get_uom_base.md) — (latest updates 13-01-26) La funzione **`catalogo.fn_get_uom_base(p_articolo_id)`** ritorna la **UoM base** dell’articolo, leggendo il campo `catalogo.articoli.uom_id`.
- [fn_get_uom_factor](funzioni/fn_get_uom_factor.md) — (latest review 13-01-26) La funzione **`catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)`** ritorna il **fattore di conversione** dalla UoM richiesta alla **UoM base** dell’articolo.
- [fn_riattiva_articolo](funzioni/fn_riattiva_articolo.md) — (latest review 28-04-2026)
- [trgfn_articoli_componenti_block_modifica_struttura](funzioni/trgfn_articoli_componenti_block_modifica_struttura.md) — (latest review 22-04-2026) La funzione **`catalogo.trgfn_articoli_componenti_block_modifica_struttura()`** protegge l'immutabilita' strutturale della distinta base (`catalogo.articoli_componenti`) dopo l'inserimento della riga.
- [trgfn_articoli_componenti_guard_componente](funzioni/trgfn_articoli_componenti_guard_componente.md) — (latest review 2026-10-13, brief-db-articoli-ammessi-per-documento Lotto 3c)
- [trgfn_articoli_componenti_guard_is_composito](funzioni/trgfn_articoli_componenti_guard_is_composito.md) — (latest review 15-01-26) La funzione **`catalogo.trgfn_articoli_componenti_guard_is_composito`** impedisce di usare come **prodotto** un articolo con `is_composito = false`. Serve a garantire che la distinta base sia definita solo per articoli realmente compositi.
- [trgfn_articoli_componenti_guard_solo_componente](funzioni/trgfn_articoli_componenti_guard_solo_componente.md) — (latest review 14-01-26) La funzione **`catalogo.trgfn_articoli_componenti_guard_solo_componente`** impedisce di usare come **prodotto** un articolo marcato `is_solo_componente = true`. Serve a garantire che articoli “solo componente” non vengano messi come `prodotto_id` in `catalogo.articoli_componenti`.
- [trgfn_articoli_guard_flags_struttura_bom_attiva](funzioni/trgfn_articoli_guard_flags_struttura_bom_attiva.md)
- [trgfn_articoli_guard_iva_bom_attiva](funzioni/trgfn_articoli_guard_iva_bom_attiva.md)
- [trgfn_articoli_guard_listino_se_composito](funzioni/trgfn_articoli_guard_listino_se_composito.md)
- [trgfn_articoli_guard_onere_natura](funzioni/trgfn_articoli_guard_onere_natura.md) — (latest review 2026-10-13)
- [trgfn_articoli_guard_struttura_se_usato](funzioni/trgfn_articoli_guard_struttura_se_usato.md) — (latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)
- [trgfn_articoli_seed_uom_base](funzioni/trgfn_articoli_seed_uom_base.md) — (rev 2026-08-21)
- [trgfn_unita_misura_guard_tipo_update](funzioni/trgfn_unita_misura_guard_tipo_update.md) — (rev 2026-08-21)
- [trgfn_uom_conversioni_guard_tipo](funzioni/trgfn_uom_conversioni_guard_tipo.md) — (rev 2026-08-21)

## 🔍 Views
- [vw_articoli_componenti_dettaglio](views/vw_articoli_componenti_dettaglio.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_componenti_dettaglio`** espone i legami prodotto–componente e arricchisce la riga con codice/descrizione di prodotto e componente.
- [vw_articoli_componenti_note](views/vw_articoli_componenti_note.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_componenti_note`** fornisce una lettura delle note legate ai componenti articolo, includendo i riferimenti a prodotto, componente, stile e lingua.
- [vw_articoli_dettaglio](views/vw_articoli_dettaglio.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_dettaglio`** espone i dati dell’articolo con le anagrafiche di supporto (unita misura, tipologie, gruppi, spese, iva e natura di vendita), evitando join ripetitivi in applicazione.
- [vw_articoli_note](views/vw_articoli_note.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_note`** fornisce una lettura immediata delle note legate agli articoli, arricchite con stile e lingua.
- [vw_articoli_uom_operativa_dettaglio](views/vw_articoli_uom_operativa_dettaglio.md) — (latest review 28-04-2026)
