# Schema `catalogo`

## 📚 Tabelle (manuale)
- [articoli](manual/articoli.md) — (latest review 13-01-26) `catalogo.articoli` è l’anagrafica **centrale** di articoli/voci, utilizzabile sia per il **catalogo prodotti** tradizionale sia per **voci utility** (canoni, oneri, misurazioni, ecc.). Supporta:
- [articoli_componenti](manual/articoli_componenti.md) — (latest review 13-01-26) `catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valid_from`..`valid_to`).
- [articoli_uom_operativa](manual/articoli_uom_operativa.md) — (latest review 13-01-26) Mappa, per ciascun **articolo**, le **unità di misura operative** ammesse e il **fattore di conversione** verso la **UoM base**. Permette di lavorare con confezioni (es. *cartone 6 bottiglie*, *scatola 50 pz*) mantenendo **coerenza contabile e di stock** in **UoM base**.
- [note](manual/note.md) — (last review 13-01-26) `catalogo.note` centralizza le **note testuali** associate agli oggetti del catalogo, con **tabella partizionata** per tipo di target. Supporta note su:
- [unita_misura](manual/unita_misura.md) — (latest review 13-01-26) * Centralizzare le **unità di misura** in un unico repository. * Fornire sia una **descrizione tecnica interna** sia una **descrizione breve** per la stampa in documenti fiscali e commerciali. * Garantire la **coerenza** tra articoli, movimenti di magazzino e righe di fattura.
- [unita_misura_conversioni](manual/unita_misura_conversioni.md) — (latest review 13-01-26) `catalogo.unita_misura_conversioni` definisce **conversioni globali** tra unita di misura, indipendenti dall’articolo. Serve come **fallback** quando una conversione non e' stata specificata per articolo in `catalogo.articoli_uom_operativa`.

## ⚙️ Funzioni (manuale)
- [fn_get_uom_base](manual/fn_get_uom_base.md) — (latest updates 13-01-26) La funzione **`catalogo.fn_get_uom_base(p_articolo_id)`** ritorna la **UoM base** dell’articolo, leggendo il campo `catalogo.articoli.uom_id`.
- [fn_get_uom_factor](manual/fn_get_uom_factor.md) — (latest review 13-01-26) La funzione **`catalogo.fn_get_uom_factor(p_articolo_id, p_uom_id)`** ritorna il **fattore di conversione** dalla UoM richiesta alla **UoM base** dell’articolo.
