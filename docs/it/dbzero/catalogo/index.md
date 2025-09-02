# Schema `catalogo`

## 📚 Tabelle
- [articoli](tabelle/articoli.md) — `catalogo.articoli` è l’anagrafica **centrale** di articoli/voci, utilizzabile sia per il **catalogo prodotti** tradizionale sia per **voci utility** (canoni, oneri, misurazioni, ecc.). Supporta:
- [articoli_componenti](tabelle/articoli_componenti.md) — `catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valid_from`..`valid_to`).
- [unita_misura](tabelle/unita_misura.md) — * Centralizzare le **unità di misura** in un unico repository. * Fornire sia una **descrizione tecnica interna** sia una **descrizione breve** per la stampa in documenti fiscali e commerciali. * Garantire la **coerenza** tra articoli, movimenti di magazzino e righe di fattura.

## ⚙️ Funzioni
- [trgfn_articoli_upd_protect_codice](funzioni/trgfn_articoli_upd_protect_codice.md)

## 🔍 Views
