## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_movimenti`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — il documento che il movimento paga
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — la rata a cui il movimento è imputato
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'intestatario
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — da dove è arrivato il denaro
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la riga contabile da cui il movimento nasce
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — dove sono tracciate le compensazioni
>
> Approfondimento viste:
>
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — le rate uscite dalla banda, calcolate sui movimenti
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga) — copia i riferimenti dalla riga contabile
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — il posting che scrive i movimenti
> * [pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva) — il posting di una riga arrivata dopo
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — il saldo del documento, sommato sui movimenti
> * [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) — il saldo delle rate, sommato sui movimenti

---

### 🎯 Scopo Principale

La tabella **`pagamenti.vendite_movimenti`** registra i movimenti di incasso e di rimborso sulle
fatture: il **fatto** che il denaro è stato attribuito a un documento, con la sua provenienza
(centro di riscossione) e i dati per il calcolo degli interessi e la contabilizzazione.

I movimenti sono il risultato del posting contabile: li scrivono
[fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) e
[fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva), un movimento per
riga contabile.

---

### Le colonne che non si capiscono dal nome

* `importo` — positivo o negativo: un rimborso è un movimento col segno opposto.
* `centro_riscossione_id` — l'origine del denaro. Facoltativo; un movimento **senza centro** non
  conta come incassato nelle funzioni dei saldi.
* `contabile_riga_id` — la riga contabile da cui il movimento nasce. È univoca quando c'è: una
  riga produce al più un movimento.
* `fattura_id`, `billing_account_id`, `contabile_id`, `scadenza_id` — quando c'è la riga, sono
  **copiati** dalla riga, non scritti dal chiamante.
* `data_per_calcolo_interessi` ed `escluso_da_interessi` — la data di riferimento per gli
  interessi, e il flag che toglie il movimento da quel calcolo.
* `data_contabilizzazione` — quando il movimento è stato inviato o registrato in contabilità.

---

### ⭐ La rata sta anche sul movimento, perché il movimento è il fatto

Il movimento porta la rata a cui è imputato anche se la stessa rata è già sulla riga contabile.
Il **movimento è il fatto**, e i fatti si leggono da soli: chi somma gli incassi di una rata deve
poterlo fare **senza passare dalla riga**, che può essere disattivata, spostata, o vivere sotto
una distinta annullata.

⚠️ E non è una seconda sorgente di verità: quando il movimento nomina una riga, i quattro
riferimenti (`contabile_id`, `fattura_id`, `billing_account_id`, `scadenza_id`) **non li scrive
il chiamante**, li copia il trigger di mirror
[trgfn_vendite_movimenti_sync_contabile_from_riga](/dbzero/pagamenti/funzioni/trgfn_vendite_movimenti_sync_contabile_from_riga).
Chi ne passa uno diverso da quello della riga viene rifiutato.

Un movimento con `scadenza_id` vuoto è un incasso «sulla fattura, senza rata»: le funzioni dei
saldi lo imputano alle rate del documento in ordine di scadenza.

---

### Le compensazioni non stanno sul movimento

Un movimento non sa di essere nato da una compensazione o da un'altra sistemazione: il legame va
dall'atto alla contabile, ed è [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni)
a puntare la testata contabile che ha prodotto. Il movimento porta solo il centro, che per una
compensazione è il centro di compensazione.

---

### 🔒 Chi li vede: il perimetro passa dalla fattura, e basta

La policy `rls_vendite_movimenti_ef_whitelist` è **`FOR ALL`**, con il cancello del ruolo
`OPERATORE` fail-closed e il predicato **via fattura**: l'operatore vede e scrive i movimenti
delle fatture di un emittente del suo perimetro.

⭐ La ragione è nel modello: `fattura_id` è obbligatorio, perché un movimento nasce solo quando il
denaro è **già attribuito a un documento**. Prima è una riga contabile, e le righe hanno la loro
policy. Il guard di scrittura sull'emittente, montato sulla stessa colonna, dice la stessa cosa:
scrittura e lettura coincidono, e non si dà il caso di poter leggere un movimento che non si
potrebbe scrivere.

⚠️ **L'asimmetria con la riga contabile, che di strade per il perimetro ne ha tre, è voluta.**
Un movimento appartiene al **documento che paga**. Il conto racconta *da dove* il denaro è
arrivato, e quella è una domanda sulla **lavorazione**, che si fa sulla riga contabile dove la
lavorazione vive. A saldo fatto, l'unica proprietà che conta è del documento.

⭐ Il `WITH CHECK` è il predicato intero, senza sconti, perché la fattura del movimento **esiste
già** quando il movimento nasce; sulle altre due tabelle del perimetro incassi c'è un istante in
cui il perimetro non è ancora risolvibile.

⚠️ I saldi (`fn_get_saldo_fattura`, `fn_get_saldo_rata`,
[vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza)) sommano i
movimenti **che l'utente può vedere**. Chi legge un saldo a zero deve poter distinguere «non è arrivato
niente» da «non è roba mia»: la distinzione la fa il cancello `OPERATORE`, fail-closed per
costruzione, e il fatto che un saldo si chieda sempre **partendo da un documento** che il
perimetro ha già filtrato.

---

### Test

* `db/pgtap/pagamenti/test-vendite-movimenti-contabile-riga.sql` — i riferimenti derivati dalla
  riga contabile, il rifiuto di un riferimento incoerente, l'unicità della riga.
* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — il mirror copia la rata sul movimento e
  rifiuta un movimento che ne nomina un'altra.
* `db/pgtap/pagamenti/test-fn-posta-contabile.sql` — il posting che scrive i movimenti.

---

### Note di migrazione

* 2026-08-22 — `scadenza_id` entra fra i riferimenti copiati dalla riga: erano tre, diventano
  quattro.
* 2026-08-22 — si accende la row security, via fattura. Il guard di scrittura sull'emittente
  c'era già da giugno 2026: fino ad allora si poteva non poter scrivere un movimento e poterlo
  leggere.
* 2026-08-22 — il legame con le compensazioni gira verso: la testata contabile perde
  `compensazione_id`, ed è l'atto di sistemazione a puntare la contabile.

---

{% include-markdown "signature-core.md" %}
