# Schema `vendite`

## 📚 Tabelle
- [articoli_descrizioni_aggiuntive](tabelle/articoli_descrizioni_aggiuntive.md) — * Estendere le informazioni dell’articolo con **testi aggiuntivi** riutilizzabili. * Governare la **sequenza di presentazione** tramite un campo di ordinamento. * Abilitare **varianti di testo** per contesti differenti (catalogo vs. documento fiscale).
- [articoli_gruppi](tabelle/articoli_gruppi.md) — * Consentire la **classificazione gerarchica** degli articoli in gruppi omogenei. * Facilitare **statistiche e analisi di vendita** per categoria. * Supportare **criteri di stampa e raggruppamento** nei documenti fiscali e gestionali. * Offrire un **meccanismo di attivazione/disattivazione** senza perdere lo storico.
- [articoli_spesa](tabelle/articoli_spesa.md) — * Definire un **catalogo centralizzato** delle voci di spesa utilizzabili in fatturazione. * Abilitare **riepiloghi e totalizzazioni** per voce di spesa nei documenti (es. bolletta, fattura). * Offrire un **testo di stampa** specifico per la voce di spesa, distinto dalla descrizione interna.
- [articoli_tipologie](tabelle/articoli_tipologie.md) — * Classificare gli articoli secondo **tipologie funzionali** (es. materia prima, servizi, accessori). * Distinguere tra **descrizione estesa** e **descrizione breve**, per gestire contesti documentali differenti. * Fornire uno strumento di aggregazione per reportistica e controlli gestionali.
- [articolo_regole_fatturazione](tabelle/articolo_regole_fatturazione.md) — Questa tabella definisce, **per ciascun articolo**, le regole di business che governano:
- [attivita_fatturabili](tabelle/attivita_fatturabili.md) — `vendite.attivita_fatturabili` è il **registro centrale delle prestazioni/attività da fatturare** (time & material, canoni, una‑tantum, letture/consumi valorizzati, import batch, ecc.). Ogni riga rappresenta **una voce fatturabile** riferita a un *articolo/servizio*, a una *istanza tecnica/utility* e, opzionalmente, a un *billing account*. Queste righe sono **pre‑documentali**: quando il ciclo di fatturazione le preleva, diventano **righe di fattura** (`vendite.fatture_righe`).
- [contratti](tabelle/contratti.md)
- [contratti_righe](tabelle/contratti_righe.md)
- [ddt](tabelle/ddt.md) — La tabella **`vendite.ddt`** rappresenta la **testata** dei Documenti di Trasporto. È il fulcro del ciclo logistico tra **Ordini** (evasione/spedizione) e **Fatture** (conto vendita / accompagnatoria).
- [ddt_indirizzi](tabelle/ddt_indirizzi.md)
- [ddt_righe](tabelle/ddt_righe.md)
- [fatture](tabelle/fatture.md) — `vendite.fatture` rappresenta la **testata del documento fiscale di vendita**. Gestisce **identità fiscale (registro/anno/serie/numero)**, **stato e tipo documento**, **intestatari economici** (BA, emittente, reseller), **valuta e pagamento**, **totali** e **metadati**. È il **punto di aggregazione** delle righe (`vendite.fatture_righe`) e dei riepiloghi IVA.
- [fatture_indirizzi](tabelle/fatture_indirizzi.md) — `vendite.fatture_indirizzi` **semplifica la gestione degli indirizzi di fattura** e garantisce la **ristampa conforme** nel tempo tramite **snapshot** JSON dell’indirizzo al momento dell’emissione.
- [fatture_rettifiche](tabelle/fatture_rettifiche.md) — `vendite.fatture_rettifiche` modella il **legame N:N** fra **documenti rettificanti** (es. note di credito/debito) e **documenti rettificati** (fatture originarie).
- [fatture_riepiloghi_iva](tabelle/fatture_riepiloghi_iva.md) — `vendite.fatture_riepiloghi_iva` è lo **specchietto fiscale** della fattura: aggrega le righe per **combinazione fiscale** e ne memorizza i totali. Serve per:
- [fatture_righe](tabelle/fatture_righe.md) — `vendite.fatture_righe` contiene le **righe economiche** di una fattura: descrizione, articolo (opzionale), UoM, quantità, prezzo, sconti, IVA e **importi congelati** (*snapshot*) al momento della generazione. Ogni riga è ordinata tramite `riga_nr` ed è collegata a una testata `vendite.fatture` (FK `fattura_id`). Supporta la **destinazione a BA diverso** dalla testata e l’idempotenza di import riga‑per‑riga.
- [fatture_scadenze](tabelle/fatture_scadenze.md) — `vendite.fatture_scadenze` memorizza lo **schedule di pagamento** (rate/scadenze) della fattura come **snapshot** al momento dell’emissione, così da:
- [note](tabelle/note.md) — `vendite.note` gestisce **note testuali** ancorabili sia alla **testata** del documento sia alla **riga**, con controllo di posizionamento e ordinamento di rendering. È una tabella **partizionata per `target_tipo`** per garantire prestazioni e manutenzione più semplici, con **FK forti** verso le rispettive testate/righe nelle singole partizioni.
- [note_attivita_fatturabili](tabelle/note_attivita_fatturabili.md) — `vendite.note_attivita_fatturabili` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [note_contratto](tabelle/note_contratto.md) — `vendite.note_contratto` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [note_ddt](tabelle/note_ddt.md) — `vendite.note_ddt` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [note_fatture](tabelle/note_fatture.md) — `vendite.note_fatture` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [note_ordini](tabelle/note_ordini.md) — `vendite.note_ordini` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [note_preventivo](tabelle/note_preventivo.md) — `vendite.note_preventivo` gestisce **note testuali**.  Vedi documento principale [vendite.note](/dbzero/vendite/tabelle/note)
- [ordini](tabelle/ordini.md) — La tabella **`vendite.ordini`** rappresenta la **testata dell’ordine di vendita**, documento commerciale preliminare che raccoglie le condizioni di vendita, spedizione e pagamento concordate con il cliente.   È il punto di partenza del ciclo attivo, destinato a generare documenti successivi (DDT, fatture, contratti di fornitura).
- [ordini_indirizzi](tabelle/ordini_indirizzi.md)
- [ordini_righe](tabelle/ordini_righe.md)
- [ordini_righe_fulfillment](tabelle/ordini_righe_fulfillment.md)
- [preventivi](tabelle/preventivi.md)
- [preventivi_indirizzi](tabelle/preventivi_indirizzi.md)
- [preventivi_righe](tabelle/preventivi_righe.md)
- [registri_fatturazione](tabelle/registri_fatturazione.md)
- [registri_fatturazione_progressivi](tabelle/registri_fatturazione_progressivi.md)
- [regole_fatturazione_articolo](tabelle/regole_fatturazione_articolo.md) — * Definire le **policy di calcolo** per ogni articolo. * Stabilire la **visibilità** dei componenti di un articolo complesso (solo padre, padre+componenti, solo componenti). * Impostare la logica di **calcolo della quantità del padre** (fissa o somma di componenti flaggati). * Definire regole di **arrotondamento** per importi e quantità. * Consentire estensioni tramite il campo JSONB `meta`.

## ⚙️ Funzioni
- [fn_get_vendite_note](funzioni/fn_get_vendite_note.md)
- [fn_numera_fattura_opz_emessa](funzioni/fn_numera_fattura_opz_emessa.md)
- [fn_resolve_termini_pagamento](funzioni/fn_resolve_termini_pagamento.md)
- [trgfn_a10_attivita_fatturabili_guard_fatturato](funzioni/trgfn_a10_attivita_fatturabili_guard_fatturato.md)
- [trgfn_a10_dlt_block_ordrig_ddtrig](funzioni/trgfn_a10_dlt_block_ordrig_ddtrig.md)
- [trgfn_a10_fatture_protect_num](funzioni/trgfn_a10_fatture_protect_num.md)
- [trgfn_a10_ins_upd_ordini_ful_guard_consistenza](funzioni/trgfn_a10_ins_upd_ordini_ful_guard_consistenza.md)
- [trgfn_a10_ordini_v_protect_num](funzioni/trgfn_a10_ordini_v_protect_num.md)
- [trgfn_a10_v_contratti_protect_num](funzioni/trgfn_a10_v_contratti_protect_num.md)
- [trgfn_a10_v_ddt_protect_num](funzioni/trgfn_a10_v_ddt_protect_num.md)
- [trgfn_a10_v_preventivi_protect_num](funzioni/trgfn_a10_v_preventivi_protect_num.md)
- [trgfn_a11_fatture_numerata_non_annulabile](funzioni/trgfn_a11_fatture_numerata_non_annulabile.md)
- [trgfn_attivita_fatturabili_guard_ba_coerenza](funzioni/trgfn_attivita_fatturabili_guard_ba_coerenza.md)
- [trgfn_attivita_fatturabili_guard_fonte](funzioni/trgfn_attivita_fatturabili_guard_fonte.md)
- [trgfn_attivita_fatturabili_norm](funzioni/trgfn_attivita_fatturabili_norm.md)
- [trgfn_attivita_guard_ba_coerenza](funzioni/trgfn_attivita_guard_ba_coerenza.md)
- [trgfn_attivita_guard_fonte](funzioni/trgfn_attivita_guard_fonte.md)
- [trgfn_attivita_norm_competenza_mese](funzioni/trgfn_attivita_norm_competenza_mese.md)
- [trgfn_contratti_norm](funzioni/trgfn_contratti_norm.md)
- [trgfn_ddt_norm](funzioni/trgfn_ddt_norm.md)
- [trgfn_fatture_righe_norm_guard](funzioni/trgfn_fatture_righe_norm_guard.md)
- [trgfn_note_validate_generic](funzioni/trgfn_note_validate_generic.md)
- [trgfn_ordini_norm](funzioni/trgfn_ordini_norm.md)
- [trgfn_preventivi_norm](funzioni/trgfn_preventivi_norm.md)
- [trgfn_tipi_indirizzi_only_allowed](funzioni/trgfn_tipi_indirizzi_only_allowed.md)

## 🔍 Views
