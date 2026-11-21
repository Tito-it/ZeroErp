## 📘 Documentazione Concettuale – Tabella `documenti.tipi_documento_output`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — ogni modello produce un tipo di documento
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — ogni stampa registrata dice che tipo di documento è
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda di stampa delle fatture nomina il tipo da stampare
>
> Approfondimento funzioni:
>
> * [documenti.fn_risolvi_template_applicabile](/dbzero/documenti/funzioni/fn_risolvi_template_applicabile) — il tipo, con la sorgente, sceglie il modello
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §2.1, il tipo di documento

---

### 🎯 Scopo Principale

Il vocabolario dei tipi di documento che il motore documentale sa produrre: preventivo, offerta
commerciale, contratto, ordine, bolla e fattura di vendita. Separa «che cosa stampo» dalla sorgente da
cui il documento viene e dal modello che ne decide la grafica.

---

### Il tipo, con la sorgente, sceglie il modello

Un modello è per una coppia (tipo di documento, sorgente), e la risoluzione della stampa cerca i
modelli di quella coppia. La stessa coppia classifica la stampa registrata, e la coda di stampa delle
fatture la usa per sapere che cosa stampare.

---

### Un vocabolario si legge, non si configura

Un tipo nasce con un changeSet, insieme al contesto di stampa che il backend sa costruire: senza, non produrrebbe niente. Non ha `attivo`: c'è o non c'è. L'applicazione lo legge soltanto.

* `codice_interno` è la chiave su cui confronta la logica, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono per chi legge il catalogo; a video l'etichetta viene da
  `etichetta_key` (`documenti.tipi_documento_output.<codice_interno minuscolo>`);
* `ordine` dà l'ordine della tendina.

È la forma dei sette vocabolari dello schema.

---

### Test

* `db/pgtap/documenti/test-documenti-lookup.sql` — le righe del seed, l'unicità di `codice_interno`, il
  blocco della chiave.
* `db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql` — il tipo dell'ordine di vendita.
* `db/pgtap/documenti/test-documenti-storico-disabled.sql` — il vocabolario non ha storico.
* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma e la sola lettura.

---

### Note di migrazione

* 2026-04-29 — nasce con il solo `PREVENTIVO`.
* 2026-05-26 — `OFFERTA_COMMERCIALE`; 2026-06-04 `ORDINE_VENDITA`; 2026-07-10 `DDT_VENDITA` e
  `FATTURA_VENDITA`.
* 2026-11-16 — prende la forma dei vocabolari della versione: entrano `etichetta_key` e `ordine`,
  escono `attivo`, `meta` e lo storico.

---

{% include-markdown "signature-core.md" %}
