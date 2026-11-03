## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — i movimenti registrati che abbassano il residuo
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — i due flag che separano la cassa dai trasferimenti
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — il totale da pagare del documento
>
> Approfondimento viste:
>
> * [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare) — legge il saldo del documento per trovare le eccedenze
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura_contabili](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili) — la sede del dichiarato, a cui delega `in_lavorazione`
> * [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata) — la sorella della rata, con la stessa forma
> * [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo) — chi ne usa il residuo per il fondo fattura
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — la regola dei saldi, per chi non è tecnico

---

### 🎯 Scopo Principale

La funzione **`pagamenti.fn_get_saldo_fattura`** restituisce il saldo di una fattura in tre
numeri: quanto manca da registrare, quanto è già dichiarato e non registrato, e quanto di ciò che
è registrato è denaro davvero arrivato. Tenere separate le tre domande è il motivo per cui esiste.

| Colonna | Domanda a cui risponde |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa fattura: il totale da pagare meno i movimenti attivi |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |
| `has_movimenti` | se almeno un movimento attivo ha toccato la fattura |

⭐ È la **stessa forma e lo stesso ordine** di
[`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata): documento e rata
rispondono con lo stesso vocabolario, ed è la base su cui nascerà il saldo **cliente**.

---

### ⭐ «Incassato» non è «saldato»

Un movimento su un centro di riscossione **interno** (il fondo fattura, la
compensazione) **salda il documento**: il denaro si è mosso davvero, per trasferimento. Ma **in banca non è
entrato niente**.

Chi misura gli incassi sommando tutti i movimenti sta misurando un'altra cosa e non lo sa. Da qui
la terza colonna, che somma **solo** i movimenti il cui centro è di cassa.

⚠️ Un movimento **senza centro** non entra in `incassato`: «canale non dichiarato» non è
«denaro arrivato», e su una misura di cassa si sta dalla parte prudente.

⇒ **Regola d'uso**: qualunque colonna, badge o totale che dica «incassato» deve
dichiarare **quale dei due** è. «Questa fattura è a posto?» si risponde col `saldo`; «quanto è entrato in
banca?» con `incassato`.

---

### ⭐ `in_lavorazione` non si calcola qui

Il **dichiarato** ha una sede sola, ed è
[`fn_get_saldo_fattura_contabili`](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura_contabili):
somma le righe contabili in stato *postabile* sotto una testata **non finale**. Questa funzione
gliela **chiede**, non la ricalcola.

Non è pignoleria: due formule per la stessa regola divergono al primo aggiustamento, e sono
numeri su cui qualcuno decide se sollecitare un cliente.

⚠️ E `saldo` e `in_lavorazione` **non si sommano**: sono due stati diversi dello stesso denaro
(promesso, registrato), e sommarli fa perdere di vista quale si sta guardando.

---

### ⭐ Escludere una riga: «quanto c'era prima di me»

`p_escludi_contabile_riga_id`, facoltativo, serve a chi sta correggendo una riga contabile:
chiede il saldo del documento *senza* quella riga, altrimenti si confronterebbe con sé stesso e
leggerebbe come «già dichiarato» l'importo che sta cambiando.

La riga esclusa esce da **entrambi** i conti:

* dal dichiarato, ed è la funzione delegata a toglierla, non una seconda esclusione scritta qui;
* dal registrato: il movimento che quella riga ha scritto, se è già stata registrata.

È la stessa forma e lo stesso parametro della sorella
[`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata): lo stesso nome deve
rispondere alla stessa domanda su rata e documento, o il pannello dei saldi direbbe due cose
diverse con le stesse parole. Senza esclusione i numeri sono quelli di sempre.

---

### ⚠️ «Non esiste» e «non la vedi» sono lo stesso errore

La fattura ha la row security: una fattura inesistente e una fuori perimetro danno lo **stesso**
errore, per scelta. Chi ha bisogno della differenza la chiede a una funzione che gira fuori dalla
row security.

Conta solo i movimenti attivi.

---

### ⚠️ Non è dichiarata `STABLE`

Il ramo d'errore scrive nel registro degli errori, e promettere stabilità su una funzione che in
un ramo scrive autorizzerebbe il planner a scelte che quel ramo non regge.

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (`TECNICO`) — `p_fattura_id` nullo o non positivo, oppure
  un'esclusione fornita e non positiva: valori che nessuna interfaccia produce, li produce un
  chiamante rotto.
* `E_FATTURA_NON_TROVATA` (`NON_TROVATO`) — la fattura non esiste, oppure non è visibile.

---

### Test

* `db/pgtap/pagamenti/test-fn-get-saldo-fattura-tre-numeri.sql` — i tre numeri lungo la vita
  di una fattura: una riga pronta entra in `in_lavorazione` senza muovere il residuo, il posting
  su banca abbassa il residuo e alza `incassato`, un movimento su un centro fondo fattura abbassa
  il residuo e **non** tocca `incassato`; `in_lavorazione` coincide con la funzione delegata;
  l'esclusione di una riga, pronta o già postata; la quadratura residuo = totale − movimenti; i
  rifiuti dei parametri e della fattura inesistente.

---

### Note di migrazione

* 2026-02-13 — prima stesura.
* 2026-08-21 — i due `E_GENERICO` passano ai codici registrati.
* 2026-08-25 — da due colonne a quattro. Fino ad allora la
  distinzione fra registrato e incassato esisteva sulla rata e non sul documento, cioè mancava
  proprio al livello che si guarda per primo. Nessun predicato preesistente è cambiato: `saldo`
  e `has_movimenti` rispondevano come prima.
* 2026-09-18 — nasce `p_escludi_contabile_riga_id`:
  l'esclusione «prima di sé» esisteva solo sulla rata, e chi correggeva una riga **senza rata**
  (fondo fattura, riga manuale «fattura sì, rata no») leggeva un dichiarato che contava la riga
  stessa. Cambiando la firma la funzione è stata ricreata, e con lei, identica, la vista
  `vw_eccedenze_da_sistemare` che ne dipende. Nessun numero è cambiato per chi chiama con un
  argomento solo.

---

{% include-markdown "signature-core.md" %}
