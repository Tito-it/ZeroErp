## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_rata`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — la rata di cui chiede il saldo
>
> Approfondimento viste:
>
> * [pagamenti.vw_saldi_rate](/dbzero/pagamenti/views/vw_saldi_rate) — la porta dello scadenzario sullo stesso nucleo
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — le rate uscite dalla banda, sugli stessi numeri
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) — il nucleo, dove sta la formula
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — la chiama per sapere quanto spazio c'è sulla rata
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — la sorella del documento, con la stessa forma
> * [script.fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura) — la domanda «di quale fattura è questa rata», fuori dalla row security

---

### 🎯 Scopo Principale

La funzione **`pagamenti.fn_get_saldo_rata`** restituisce il saldo di una rata in tre numeri:
quanto manca da registrare, quanto è già dichiarato e non registrato, e quanto di ciò che è
registrato è denaro davvero arrivato. È la porta a **un elemento** del nucleo
[`fn_get_saldi_rate`](/dbzero/pagamenti/funzioni/fn_get_saldi_rate).

| Colonna | Domanda |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa rata |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |
| `has_movimenti` | se almeno un movimento ha toccato la rata, come per la sorella di fattura |

---

### ⭐ La formula sta nel nucleo, qui restano il controllo e l'errore

La formula è scritta una volta, in [`fn_get_saldi_rate`](/dbzero/pagamenti/funzioni/fn_get_saldi_rate),
per tutte le porte: questa, [`vw_saldi_rate`](/dbzero/pagamenti/views/vw_saldi_rate), la chiamata
con l'array della pagina dal backend. Questa funzione aggiunge il controllo del parametro e
l'errore sulla rata che non c'è.

Arriva anche da qui ciò che il nucleo fa con i movimenti **senza rata**: li imputa alle rate del
documento, e la regola è descritta nella scheda del nucleo.

---

### ⭐ «Incassato» non è «registrato»

I centri di riscossione `is_fondo_fattura` e `is_compensazione` **non sono cassa**. Un movimento
su quei centri salda il documento, ed è corretto, perché il denaro si è mosso
per **trasferimento**; ma in banca non è entrato niente.

Chi misura gli incassi sommando tutti i movimenti sta misurando un'altra cosa, e non lo sa.

⚠️ **Un movimento senza centro non entra in `incassato`**: «canale non dichiarato» non è
«denaro arrivato», e su una misura di cassa si sta dalla parte prudente.

---

### ⚠️ `saldo` e `in_lavorazione` restano due colonne

È la stessa distinzione che a livello di **fattura** vive in due funzioni diverse.
Il **registrato** e il **dichiarato** non si sommano in un numero solo, o non si capisce più che cosa
si sta guardando: uno è un fatto, l'altro un'intenzione.

⭐ Chi vuole sapere **quanto spazio c'è ancora** fa `saldo - in_lavorazione`, ed è ciò che fa il
guard della capienza.

Le righe in lavorazione escludono le distinte finali: una riga sotto una distinta chiusa non è in
lavorazione, è ferma. Non può nemmeno più diventare pronta, ma il filtro resta perché
dice **perché** quelle righe non contano.

Il saldo **può essere negativo**: una rata sovra-incassata ha `saldo < 0`, ed è
un'informazione, non un errore.

---

### ⭐ Escludere una riga: «quanto spazio c'era prima di me»

`p_escludi_contabile_riga_id`, facoltativo, ha lo stesso mestiere del `p_source_id` di
`vendite.fn_saldo_sorgente_fondo`: chi sta scrivendo una riga deve poter chiedere quanto spazio
c'era **prima di sé**, altrimenti si troverebbe a confrontarsi con sé stesso. Il guard della rata
lo passa con l'id della riga che sta controllando. Senza esclusione, la risposta è su tutto.

---

### ⚠️ «Non esiste» e «non la vedi» sono lo stesso errore

La rata non esiste **oppure** non è visibile: lo stesso `E_RATA_NON_TROVATA`, di proposito. È la
stessa scelta di `E_FATTURA_NON_TROVATA`: dire «esiste ma non è tua» racconterebbe qualcosa a chi
non ha diritto di saperlo.

⭐ Dove invece la distinzione **conta** (il guard di coerenza, che deve poter dire «non è di
questa fattura» e non «non la vedo») la domanda si fa fuori dalla row security con
[`script.fn_check_scadenza_di_fattura`](/dbzero/script/funzioni/fn_check_scadenza_di_fattura). Le
due funzioni fanno cose diverse apposta: una risponde a chi ha diritto di sapere, l'altra a chi
deve decidere.

---

### ⚠️ Non è dichiarata `STABLE`

Il ramo d'errore **scrive** nel registro degli errori. Promettere stabilità su una funzione che in
un ramo scrive autorizza il planner a scelte che quel ramo non regge. È la stessa ragione di
`vendite.fn_saldo_sorgente_fondo`. Il nucleo, che non solleva mai, è `STABLE`.

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (`TECNICO`) — `p_scadenza_id` nullo o non positivo, oppure
  un'esclusione fornita e non positiva: valori che nessuna interfaccia produce.
* `E_RATA_NON_TROVATA` (`NON_TROVATO`) — la rata non esiste oppure non è visibile.

---

### Test

* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — separa il registrato dal dichiarato, dà un
  saldo negativo sulla rata sovra-incassata, conta in `incassato` solo la cassa, e la rata resta
  invisibile a chi non deve vederla.
* `db/pgtap/pagamenti/test-fn-get-saldi-rate-v1.sql` — dà gli stessi numeri del nucleo e della
  vista, e risponde `E_RATA_NON_TROVATA` su un id inesistente.
* `db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — il saldo della rata dopo il posting di
  una riga tardiva.

---

### Note di migrazione

* 2026-08-22 — nasce con il saldo a tre numeri.
* 2026-09-17 — diventa la porta a un elemento del nucleo `fn_get_saldi_rate`: firma, colonne e comportamento sui movimenti diretti
  invariati; con il nucleo arriva anche l'imputazione dei movimenti senza rata.

---

{% include-markdown "signature-core.md" %}
