# Schema `vendite`

## 📚 Tabelle
- [articoli_descrizioni_aggiuntive](tabelle/articoli_descrizioni_aggiuntive.md) — * Estendere le informazioni dell’articolo con **testi aggiuntivi** riutilizzabili. * Governare la **sequenza di presentazione** tramite un campo di ordinamento. * Abilitare **varianti di testo** per contesti differenti (catalogo vs. documento fiscale).
- [articoli_gruppi](tabelle/articoli_gruppi.md) — * Consentire la **classificazione gerarchica** degli articoli in gruppi omogenei. * Facilitare **statistiche e analisi di vendita** per categoria. * Supportare **criteri di stampa e raggruppamento** nei documenti fiscali e gestionali. * Offrire un **meccanismo di attivazione/disattivazione** senza perdere lo storico.
- [articoli_spesa](tabelle/articoli_spesa.md) — * Definire un **catalogo centralizzato** delle voci di spesa utilizzabili in fatturazione. * Abilitare **riepiloghi e totalizzazioni** per voce di spesa nei documenti (es. bolletta, fattura). * Offrire un **testo di stampa** specifico per la voce di spesa, distinto dalla descrizione interna.
- [articoli_tipologie](tabelle/articoli_tipologie.md) — * Classificare gli articoli secondo **tipologie funzionali** (es. materia prima, servizi, accessori). * Distinguere tra **descrizione estesa** e **descrizione breve**, per gestire contesti documentali differenti. * Fornire uno strumento di aggregazione per reportistica e controlli gestionali.
- [attivita_fatturabili](tabelle/attivita_fatturabili.md)
- [regole_fatturazione_articolo](tabelle/regole_fatturazione_articolo.md) — * Definire le **policy di calcolo** per ogni articolo. * Stabilire la **visibilità** dei componenti di un articolo complesso (solo padre, padre+componenti, solo componenti). * Impostare la logica di **calcolo della quantità del padre** (fissa o somma di componenti flaggati). * Definire regole di **arrotondamento** per importi e quantità. * Consentire estensioni tramite il campo JSONB `meta`.

## ⚙️ Funzioni

## 🔍 Views
