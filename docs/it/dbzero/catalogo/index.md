# Schema `catalogo`

## 📚 Tabelle
- [articoli](tabelle/articoli.md) — (latest review 13-01-26) `catalogo.articoli` è l’anagrafica **centrale** di articoli/voci, utilizzabile sia per il **catalogo prodotti** tradizionale sia per **voci utility** (canoni, oneri, misurazioni, ecc.). Supporta:
- [articoli_componenti](tabelle/articoli_componenti.md) — (latest review 13-01-26) `catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valido_dal`..`valido_al`).
- [articoli_uom_operativa](tabelle/articoli_uom_operativa.md) — (latest review 13-01-26) Mappa, per ciascun **articolo**, le **unità di misura operative** ammesse e il **fattore di conversione** verso la **UoM base**. Permette di lavorare con confezioni (es. *cartone 6 bottiglie*, *scatola 50 pz*) mantenendo **coerenza contabile e di stock** in **UoM base**.
- [note](tabelle/note.md) — (last review 13-01-26) `catalogo.note` centralizza le **note testuali** associate agli oggetti del catalogo, con **tabella partizionata** per tipo di target. Supporta note su:
- [note_articoli](tabelle/note_articoli.md)
- [note_articoli_componenti](tabelle/note_articoli_componenti.md)
- [unita_misura](tabelle/unita_misura.md) — (latest review 13-01-26) * Centralizzare le **unità di misura** in un unico repository. * Fornire sia una **descrizione tecnica interna** sia una **descrizione breve** per la stampa in documenti fiscali e commerciali. * Garantire la **coerenza** tra articoli, movimenti di magazzino e righe di fattura.
- [unita_misura_conversioni](tabelle/unita_misura_conversioni.md) — (latest review 13-01-26) `catalogo.unita_misura_conversioni` definisce **conversioni globali** tra unita di misura, indipendenti dall’articolo. Serve come **fallback** quando una conversione non e' stata specificata per articolo in `catalogo.articoli_uom_operativa`.

## ⚙️ Funzioni
- [fn_duplica_componente_versione](funzioni/fn_duplica_componente_versione.md)
- [fn_get_uom_base](funzioni/fn_get_uom_base.md) — (latest updates 13-01-26) La funzione **`catalogo.fn_get_uom_base(p_articolo_id)`** ritorna la **UoM base** dell’articolo, leggendo il campo `catalogo.articoli.uom_id`.
- [fn_get_uom_factor](funzioni/fn_get_uom_factor.md) — (latest review 13-01-26) La funzione **`catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)`** ritorna il **fattore di conversione** dalla UoM richiesta alla **UoM base** dell’articolo.
- [trgfn_articoli_componenti_block_modifica_struttura](funzioni/trgfn_articoli_componenti_block_modifica_struttura.md) — (latest review 22-04-2026) La funzione **`catalogo.trgfn_articoli_componenti_block_modifica_struttura()`** protegge l'immutabilita' strutturale della distinta base (`catalogo.articoli_componenti`) dopo l'inserimento della riga.
- [trgfn_articoli_componenti_guard_is_composito](funzioni/trgfn_articoli_componenti_guard_is_composito.md) — (latest review 15-01-26) La funzione **`catalogo.trgfn_articoli_componenti_guard_is_composito`** impedisce di usare come **prodotto** un articolo con `is_composito = false`. Serve a garantire che la distinta base sia definita solo per articoli realmente compositi.
- [trgfn_articoli_componenti_guard_solo_componente](funzioni/trgfn_articoli_componenti_guard_solo_componente.md) — (latest review 14-01-26) La funzione **`catalogo.trgfn_articoli_componenti_guard_solo_componente`** impedisce di usare come **prodotto** un articolo marcato `is_solo_componente = true`. Serve a garantire che articoli “solo componente” non vengano messi come `prodotto_id` in `catalogo.articoli_componenti`.
- [trgfn_articoli_seed_uom_base](funzioni/trgfn_articoli_seed_uom_base.md)

## 🔍 Views
- [vw_articoli_componenti_dettaglio](views/vw_articoli_componenti_dettaglio.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_componenti_dettaglio`** espone i legami prodotto–componente e arricchisce la riga con codice/descrizione di prodotto e componente.
- [vw_articoli_componenti_note](views/vw_articoli_componenti_note.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_componenti_note`** fornisce una lettura delle note legate ai componenti articolo, includendo i riferimenti a prodotto, componente, stile e lingua.
- [vw_articoli_dettaglio](views/vw_articoli_dettaglio.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_dettaglio`** espone i dati dell’articolo con le anagrafiche di supporto (unita misura, tipologie, gruppi, spese e iva), evitando join ripetitivi in applicazione.
- [vw_articoli_note](views/vw_articoli_note.md) — (latest review 14-01-26) La vista **`catalogo.vw_articoli_note`** fornisce una lettura immediata delle note legate agli articoli, arricchite con stile e lingua.
