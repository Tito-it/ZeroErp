# Schema `catalogo`

## 📚 Tabelle (manuale)
- [articoli](manual/articoli.md) — `catalogo.articoli` è l’anagrafica **centrale** di articoli/voci, utilizzabile sia per il **catalogo prodotti** tradizionale sia per **voci utility** (canoni, oneri, misurazioni, ecc.). Supporta:
- [articoli_componenti](manual/articoli_componenti.md) — `catalogo.articoli_componenti` rappresenta la **distinta base (BoM)** lato **vendita**, con **versionamento temporale**: ogni riga lega un **prodotto** a un **componente** con una finestra di validità (`valid_from`..`valid_to`).
- [articoli_uom_operativa](manual/articoli_uom_operativa.md) — Mappa, per ciascun **articolo**, le **unità di misura operative** ammesse e il **fattore di conversione** verso la **UoM base**. Permette di lavorare con confezioni (es. *cartone 6 bottiglie*, *scatola 50 pz*) mantenendo **coerenza contabile e di stock** in **UoM base**.
- [unita_misura](manual/unita_misura.md) — * Centralizzare le **unità di misura** in un unico repository. * Fornire sia una **descrizione tecnica interna** sia una **descrizione breve** per la stampa in documenti fiscali e commerciali. * Garantire la **coerenza** tra articoli, movimenti di magazzino e righe di fattura.
