## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldi_rate`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — il piano delle rate, letto per intero
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — il registrato, diretto o senza rata
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — il dichiarato, diretto o senza rata
>
> Approfondimento viste:
>
> * [pagamenti.vw_saldi_rate](/dbzero/pagamenti/views/vw_saldi_rate) — la porta dello scadenzario: tutte le rate visibili
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — la chiama una volta sull'insieme dei candidati
> * [vendite.vw_fatture_scadenze_lista](/dbzero/vendite/views/vw_fatture_scadenze_lista) — l'identità delle rate, senza saldi: chi la legge li chiede al nucleo
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata) — la porta a un elemento: controllo del parametro ed `E_RATA_NON_TROVATA`
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — il guard di capienza, che ci arriva dalla porta a un elemento
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — la regola dei saldi, per chi non è tecnico

---

### 🎯 Scopo Principale

La funzione **`pagamenti.fn_get_saldi_rate`** è il **nucleo** dei saldi delle rate: la formula
scritta una volta, in forma set-based, che per un insieme di rate restituisce saldo, dichiarato,
incassato e presenza di movimenti, imputando alle rate anche i movimenti e le righe senza rata.

| Colonna | Domanda |
| --- | --- |
| `saldo` | quanto manca ancora da **registrare** su questa rata |
| `in_lavorazione` | quanto è già stato **dichiarato** e non ancora registrato |
| `incassato` | quanto di ciò che è registrato è **denaro davvero arrivato** |
| `has_movimenti` | se almeno un movimento ha toccato la rata, anche solo con una quota imputata |

Il significato delle colonne è quello della porta a un elemento
([`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata)), che questa scheda non
ripete.

---

### ⭐ Una formula, tre porte

Le porte sono tre e leggono tutte questo nucleo:

* [`fn_get_saldo_rata`](/dbzero/pagamenti/funzioni/fn_get_saldo_rata), per una rata sola;
* [`vw_saldi_rate`](/dbzero/pagamenti/views/vw_saldi_rate), per lo scadenzario;
* la chiamata con l'array degli id della pagina, dal backend.

Una porta per rata, a tre letture, regge su una fattura; su uno **scadenzario** (tutte le rate
aperte, e «aperta» *è* un predicato sul residuo) sono N × 3 letture prima di poter filtrare. Uno
scadenzario è il perimetro intero per costruzione.

Le tre porte leggono lo stesso nucleo, quindi **non possono divergere**: due sedi del residuo
divergono alla prima regola nuova, e sono numeri su cui si sollecita un cliente.

---

### ⭐ I movimenti senza rata si imputano alle rate

Il saldo di una **fattura** somma i movimenti per `fattura_id`. Se il saldo di una rata contasse
solo i movimenti che la **nominano**, un incasso registrato «sulla fattura, senza rata» (il fondo
fattura lo scrive sempre così, e l'operatore può farlo dal lookup) abbasserebbe il saldo del
documento e **non** quello delle rate: una fattura a rata unica pagata senza rata avrebbe saldo
documento 0 e saldo rata 100. È il punto cieco della rata, e il nucleo lo chiude con una regola
derivata, che nessuno scrive: lo stato della rata si calcola, non si registra.

* I movimenti attivi del documento **senza** `scadenza_id` si attribuiscono alle sue rate in
  ordine di `data_scadenza` (poi `numero_rata`, `id`), fino alla capienza di ciascuna al netto
  dei movimenti diretti; **l'ultima rata assorbe l'eccedenza**, così la somma dei saldi delle
  rate è uguale al saldo del documento, sempre.
* Lo stesso, in un secondo stadio, per le righe postabili senza rata (`in_lavorazione`): così il
  guard di capienza vede lo spazio che il documento conosce anche **prima** del posting (la riga
  del fondo è in lavorazione finché non si registra).
* `incassato` segue l'imputazione in proporzione.
* Il verso è quello del **documento**: su una nota di credito le rate sono negative e la capienza
  si misura in valore assoluto. Un non imputato di verso contrario va tutto sulla **prima** rata,
  dove resta visibile come anomalia.

⚠️ **L'ordine dei fatti conta, ed è una scelta.** Su un piano 30/70 un acconto di 20 senza rata
va sulla rata 1; una riga diretta da 30 sulla rata 1 che arriva *dopo* trova 10, e il guard la
respinge coi numeri. Nell'ordine inverso l'acconto scivola sulla rata 2. Non è un difetto: il
picker delle rate mostra **esattamente** i numeri del nucleo, quindi l'operatore vede «10» e il
guard accetta «10». Far accettare al guard ciò che il picker non mostra sarebbe la divergenza fra
suggerimento e rifiuto che le linee guida vietano. La forzatura a due tempi resta la via per il
caso vero.

---

### ⛔ L'array è obbligatorio, e nullo vuol dire nessuna rata

`p_scadenza_ids` si filtra con un confronto `= ANY` nudo: un array nullo restituisce **zero
righe**, non «tutte». ⛔ Non si scrive il «nullo = tutte» con un `p IS NULL OR …`: provato con
`EXPLAIN`, dentro un `LATERAL` o con un parametro plpgsql in piano generico il ramo `IS NULL` non
si piega, e l'`OR` diventa una scansione intera dei movimenti per rata, sul percorso del guard di
capienza. Per tutte le rate c'è `vw_saldi_rate`, che costruisce l'array.

Per imputare servono **tutte** le rate del documento: il nucleo legge il piano intero dei
documenti delle rate chieste e restituisce solo le chieste.

Una rata **senza movimenti torna lo stesso**, con `has_movimenti = false`: senza, il picker
perderebbe le rate mai toccate.

`p_escludi_contabile_riga_id` toglie la riga che sta scrivendo, diretta o senza rata: «quanto
spazio c'era prima di me».

---

### ⭐ Non solleva mai, e somma ciò che chi legge vede

È `STABLE` e `LANGUAGE sql`: **non solleva mai** (una rata invisibile è zero righe; a dire
`E_RATA_NON_TROVATA` è la porta a un elemento) e il planner può incorporarla nella query che la
chiama. Gira con i privilegi di chi legge: somma ciò che chi legge vede, e le tabelle lette hanno
la row security.

---

### Test

* `db/pgtap/pagamenti/test-fn-get-saldi-rate-v1.sql` — le tre porte danno gli stessi numeri; una
  rata mai toccata torna lo stesso; un array nullo dà zero righe. I casi dell'imputazione sono
  **costruiti**: rata unica pagata senza rata → 0; acconto distribuito per scadenza su tre rate;
  somma delle rate = documento; la riga in lavorazione occupa lo spazio e il guard la vede; il
  verso contrario resta visibile sulla prima; l'esclusione vale anche su una riga senza rata;
  l'eccedenza resta sull'ultima; `vw_saldi_rate` coincide col nucleo e legge con i diritti di chi
  la interroga.

---

### Note di migrazione

* 2026-09-17 — nasce come nucleo set-based dei saldi delle rate, e `fn_get_saldo_rata` ne
  diventa la porta a un elemento. Fino ad
  allora il saldo di una rata aveva una porta sola, per rata, in plpgsql a tre letture.
* 2026-09-17 — lo stesso giorno arriva l'imputazione derivata dei movimenti e delle righe senza
  rata. Prima la rata contava solo i movimenti che la
  nominavano, e la rata di una nota di credito avrebbe contato due volte il credito riportato.

---

{% include-markdown "signature-core.md" %}
