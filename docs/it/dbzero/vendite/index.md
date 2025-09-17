# Schema `vendite`

## 📚 Tabelle
- [articoli_descrizioni_aggiuntive](tabelle/articoli_descrizioni_aggiuntive.md) — * Estendere le informazioni dell’articolo con **testi aggiuntivi** riutilizzabili. * Governare la **sequenza di presentazione** tramite un campo di ordinamento. * Abilitare **varianti di testo** per contesti differenti (catalogo vs. documento fiscale).
- [articoli_gruppi](tabelle/articoli_gruppi.md) — * Consentire la **classificazione gerarchica** degli articoli in gruppi omogenei. * Facilitare **statistiche e analisi di vendita** per categoria. * Supportare **criteri di stampa e raggruppamento** nei documenti fiscali e gestionali. * Offrire un **meccanismo di attivazione/disattivazione** senza perdere lo storico.
- [articoli_spesa](tabelle/articoli_spesa.md) — * Definire un **catalogo centralizzato** delle voci di spesa utilizzabili in fatturazione. * Abilitare **riepiloghi e totalizzazioni** per voce di spesa nei documenti (es. bolletta, fattura). * Offrire un **testo di stampa** specifico per la voce di spesa, distinto dalla descrizione interna.
- [articoli_tipologie](tabelle/articoli_tipologie.md) — * Classificare gli articoli secondo **tipologie funzionali** (es. materia prima, servizi, accessori). * Distinguere tra **descrizione estesa** e **descrizione breve**, per gestire contesti documentali differenti. * Fornire uno strumento di aggregazione per reportistica e controlli gestionali.
- [articolo_regole_fatturazione](tabelle/articolo_regole_fatturazione.md)
- [attivita_fatturabili](tabelle/attivita_fatturabili.md)
- [contratti](tabelle/contratti.md)
- [contratti_righe](tabelle/contratti_righe.md)
- [ddt](tabelle/ddt.md)
- [ddt_indirizzi](tabelle/ddt_indirizzi.md)
- [ddt_righe](tabelle/ddt_righe.md)
- [fatture](tabelle/fatture.md)
- [fatture_indirizzi](tabelle/fatture_indirizzi.md)
- [fatture_rettifiche](tabelle/fatture_rettifiche.md)
- [fatture_riepiloghi_iva](tabelle/fatture_riepiloghi_iva.md)
- [fatture_righe](tabelle/fatture_righe.md)
- [fatture_scadenze](tabelle/fatture_scadenze.md)
- [note](tabelle/note.md)
- [note_contratto](tabelle/note_contratto.md)
- [note_ddt](tabelle/note_ddt.md)
- [note_fatture](tabelle/note_fatture.md)
- [note_ordini](tabelle/note_ordini.md)
- [note_preventivo](tabelle/note_preventivo.md)
- [ordini](tabelle/ordini.md)
- [ordini_indirizzi](tabelle/ordini_indirizzi.md)
- [ordini_righe](tabelle/ordini_righe.md)
- [ordini_righe_fulfillment](tabelle/ordini_righe_fulfillment.md)
- [preventivi](tabelle/preventivi.md)
- [preventivi_righe](tabelle/preventivi_righe.md)
- [registri_fatturazione](tabelle/registri_fatturazione.md)
- [registri_fatturazione_progressivi](tabelle/registri_fatturazione_progressivi.md)
- [regole_fatturazione_articolo](tabelle/regole_fatturazione_articolo.md) — * Definire le **policy di calcolo** per ogni articolo. * Stabilire la **visibilità** dei componenti di un articolo complesso (solo padre, padre+componenti, solo componenti). * Impostare la logica di **calcolo della quantità del padre** (fissa o somma di componenti flaggati). * Definire regole di **arrotondamento** per importi e quantità. * Consentire estensioni tramite il campo JSONB `meta`.

## ⚙️ Funzioni
- [fn_numera_fattura_opz_emessa](funzioni/fn_numera_fattura_opz_emessa.md)
- [trgfn_a10_attivita_fatturabili_guard_fatturato](funzioni/trgfn_a10_attivita_fatturabili_guard_fatturato.md)
- [trgfn_a10_fatture_protect_num](funzioni/trgfn_a10_fatture_protect_num.md)
- [trgfn_a10_ordini_v_protect_num](funzioni/trgfn_a10_ordini_v_protect_num.md)
- [trgfn_a11_fatture_numerata_non_annulabile](funzioni/trgfn_a11_fatture_numerata_non_annulabile.md)
- [trgfn_attivita_fatturabili_guard_ba_coerenza](funzioni/trgfn_attivita_fatturabili_guard_ba_coerenza.md)
- [trgfn_attivita_fatturabili_guard_fonte](funzioni/trgfn_attivita_fatturabili_guard_fonte.md)
- [trgfn_attivita_fatturabili_norm](funzioni/trgfn_attivita_fatturabili_norm.md)
- [trgfn_attivita_guard_ba_coerenza](funzioni/trgfn_attivita_guard_ba_coerenza.md)
- [trgfn_attivita_guard_fonte](funzioni/trgfn_attivita_guard_fonte.md)
- [trgfn_attivita_norm_competenza_mese](funzioni/trgfn_attivita_norm_competenza_mese.md)
- [trgfn_contnote_validate](funzioni/trgfn_contnote_validate.md)
- [trgfn_fatture_righe_norm_guard](funzioni/trgfn_fatture_righe_norm_guard.md)
- [trgfn_preventivi_norm](funzioni/trgfn_preventivi_norm.md)
- [trgfn_prevnote_validate](funzioni/trgfn_prevnote_validate.md)

## 🔍 Views
