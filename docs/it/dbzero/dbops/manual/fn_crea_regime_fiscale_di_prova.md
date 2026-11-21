## 📘 Documentazione Concettuale – Funzione `dbops.fn_crea_regime_fiscale_di_prova`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — il catalogo in cui il regime di prova nasce
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente dichiarato
>
> Approfondimento viste:
>
> * [dbops.vw_radici_di_prova_in_produzione](/dbzero/dbops/views/vw_radici_di_prova_in_produzione) — il presidio che vede un regime di prova finito in produzione
>
> Approfondimento funzioni:
>
> * [dbops.fn_dati_di_sviluppo_ammessi_su_valori](/dbzero/dbops/funzioni/fn_dati_di_sviluppo_ammessi_su_valori) — la regola sull'ambiente
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore dell'ambiente, che fallisce se manca
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — l'altra porta dei dati di sviluppo, con la stessa regola

---

### 🎯 Scopo Principale

**La porta dei test verso il catalogo dei regimi fiscali.** L'applicazione i regimi li legge e
basta: il catalogo lo scrive il CSV. Un test e2e che deve provare sul database vero il
rifiuto di un regime spento ha però bisogno di un regime acceso e di uno spento costruiti
da lui. Questa funzione li crea e restituisce l'id.

---

### ⛔ I tre limiti

| Limite | Come |
| --- | --- |
| Solo in un'installazione di sviluppo | Legge l'ambiente vero e chiede alla regola dei dati di sviluppo. Fuori da `SVILUPPO` rifiuta con `E_DATI_DI_SVILUPPO_IN_PRODUZIONE`, lo stesso codice della porta dei dati di sviluppo, perché la decisione è la stessa. La CI è un'installazione di sviluppo |
| Solo righe nuove, col segno di prova | Scrive `meta` = `{"di_prova": true}`. Un `codice_interno` o un `codice` che esistono già li rifiutano i due vincoli di unicità del catalogo (`23505`): un regime vero non si tocca mai |
| Solo nascita | Non modifica e non spegne. Un regime spento nasce spento, con `attivo` = `false` |

⚠️ Il `codice_interno` resta nella forma del tracciato FatturaPA (`RF` e due cifre): il segno
di prova sta in `meta`, non nel codice. Chi chiama sceglie un codice libero.

---

### ⚠️ Scrive come proprietario

È `SECURITY DEFINER`: l'applicazione non ha la scrittura sul catalogo, e la funzione la
esercita al posto suo, dentro i tre limiti. Per questo non porta il prefisso dei builder
`fn_pgtap_*`, che scrivono coi privilegi di chi li chiama e non aprono porte.

Un regime di prova vive quanto la transazione del test che lo crea. Se una transazione
confermata lo lascia su un database di sviluppo, compare nelle tendine: il segno in `meta`
lo rende riconoscibile. Su un database di produzione lo vede il presidio delle radici di prova.

---

### Test

* `db/pgtap/config/test-regimi-fiscali-sola-lettura-v1.sql` — come applicazione, in sviluppo:
  il regime spento nasce col segno; un `codice_interno` o un `codice` del catalogo sono
  rifiutati dai due vincoli di unicità.
* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — in produzione (costruita) la funzione non
  parte, e il presidio vede il regime di prova nato prima.

---

### Note di migrazione

* 2026-11-22 — nasce, per i test e2e del regime spento (`20261121-17`,
  `brief-db-fornitore-doppioni-del-soggetto`, D-9).

---

{% include-markdown "signature-core.md" %}
