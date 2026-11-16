## 📘 Documentazione Concettuale – Tabella `documenti.tipi_documento_output`

> **Ultimo aggiornamento**: 15 novembre 2026
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

### Le righe le porta il seed

I tipi nascono dal seed, con il motore che li sa stampare: un tipo nuovo senza un contesto di stampa
che il backend sappia costruire non produrrebbe niente. La tabella è nel lookup generico, per le
tendine, e non nel pannello di configurazione.

* `codice_interno` è la chiave su cui confronta la logica, ed è bloccato dopo l'inserimento;
* `codice` e `descrizione` sono le etichette;
* `meta` non ha lettori.

---

### Spegnere un tipo

`attivo = false` impedisce che un tipo nuovo entri in un modello. Un tipo non si spegne finché un modello
attivo lo usa. Le stampe registrate e la coda di stampa delle fatture sono escluse dal controllo: una
stampa è storia, la coda è lavoro, e se il tipo può stampare lo decide la risoluzione del modello.

Le modifiche sono storicizzate in `storico.tipi_documento_output`.

---

### Test

* `db/pgtap/documenti/test-documenti-lookup.sql` — le righe del seed, l'unicità di `codice_interno`, il
  blocco della chiave.
* `db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql` — il tipo dell'ordine di vendita.
* `db/pgtap/documenti/test-documenti-storico-disabled.sql` — la tabella di storico esiste.

---

### Note di migrazione

* 2026-04-29 — nasce con il solo `PREVENTIVO`.
* 2026-05-26 — `OFFERTA_COMMERCIALE`; 2026-06-04 `ORDINE_VENDITA`; 2026-07-10 `DDT_VENDITA` e
  `FATTURA_VENDITA`.

---

{% include-markdown "signature-core.md" %}
