## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_lotto_segnalazioni_summary`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)   
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)   
>
**Approfondimento funzioni:**
>
• [vendite.fn_log_lotto_esito_fatture](/dbzero/vendite/funzioni/fn_log_lotto_esito_fatture)   
>
### 🎯 Scopo Principale
(latest review 19-09-2026)  
La funzione **`vendite.fn_get_lotto_segnalazioni_summary()`** restituisce
un riepilogo aggregato delle segnalazioni attive (`C`/`W`/`I`) di un lotto,
unificando:

* log fattura (`vendite.fatture_log`) tramite legame lotto-fatture;
* log lotto (`vendite.fatturazione_lotti_log`).
* stato tecnico del ponte lotto-fatture (`vendite.fatturazione_lotti_fatture.stato_esecuzione`).

---

### ⭐⭐ Dal 19-09-2026 è un LETTORE, e porta il verdetto: `fermo` (undicesima colonna)

**La sede degli aggregati non è più qui.** I dieci conteggi si calcolano in
[`vendite.vw_lotti_segnalazioni_summary`](/dbzero/vendite/manual/vw_lotti_segnalazioni_summary)
— una riga per lotto — e questa funzione ne legge **una riga** (`WHERE lotto_id
= p_lotto_id`, spinto dentro le `GROUP BY` della vista). Un addendo nuovo si
aggiunge nella vista, **non** qui: la legge anche il presidio
[`dbops.vw_lotti_fermi_da_guardare`](/dbzero/dbops/manual/vw_lotti_fermi_da_guardare),
ed è la ragione per cui la sede è una.

**`fermo`** — undicesima colonna, in coda — è il verdetto che fino a quel giorno
il backend calcolava da solo (`LottoSegnalazioniService.evaluate_lotto_status`:
`is_error = blocks_next_step`):

```
fermo = (fatture_critical_count + lotto_critical_count) > 0
     OR fatture_stato_esecuzione_errore_count > 0
     OR esiti_stato_esecuzione_errore_count > 0
```

⛔ **Decisione di Tid (D-1, 18-09-2026): «la regola va a DB».** Il backend lo
**legge** e non lo ricalcola; i dieci conteggi restano per la **frase** del
banner. Fino al 19-09 questa pagina — e la `COMMENT` della funzione — dicevano
*«`blocks_next_step` resta in Python»*: non più.

⚠️ **Una riga sempre.** Su un lotto inesistente, o fuori dal perimetro di chi
legge (la vista è `security_invoker`), la risposta è zeri e `fermo = false` —
com'era prima. Il backend legge la testata **prima** e risponde 404: questi zeri
non arrivano a una persona come «tutto a posto».

⚠️ **Finché il backend non legge l'undicesima colonna** (pezzo V del piano
BE/FE), la sua copia in Python e questo valore coincidono per costruzione: la
vista è la trasposizione fedele del predicato Python. È la finestra in cui un
test di parità ha senso — e poi si toglie.

---

### ⭐ I tre conteggi del BANNER — contano GESTI, non allarmi
(dal 2026-09-08)

I sei conteggi storici contano **segnalazioni**. Ma i gesti che l'operatore ha
davanti sono uno per **documento** — «togli questo dal giro» — e un documento
con tre critiche resta un documento solo. Dire *«3 segnalazioni bloccanti»* è un
numero vero che descrive la cosa sbagliata.

| Colonna | Che cosa conta |
| --- | --- |
| `documenti_bloccanti_count` | quanti **documenti** hanno almeno una critica viva (`DISTINCT` sulla chiave) |
| `documenti_presi_in_carico_count` | il **denominatore**: quanti documenti il lotto ha preso in carico |
| `critiche_giro_count` | le critiche che un documento **non ce l'hanno** |

#### ⛔ Il terzo numero non è un di più

Le critiche sono di **due specie**, e una non è un documento:

* di un **documento** (`gruppo_key` valorizzata) → si toglie dal giro;
* del **giro** (`gruppo_key IS NULL`) → emittente non risolto, configurazione
  mancante: blocca e **non c'è niente da togliere**.

Su un lotto fermo per un emittente non risolto, *«N documenti su M»* direbbe
**«0 documenti su 4»** — un banner che dichiara che non c'è niente da fare
mentre il giro è bloccato. Il terzo numero è ciò che rende la frase vera.

#### ⛔ Il denominatore non viene dal perimetro

`M` si conta su `vendite.fatturazione_lotti_esiti` — i documenti **presi in
carico** — e non su `fatturazione_lotti_gruppi`. Il perimetro è **vuoto sui giri
di massa**: è esattamente la ragione per cui la tabella degli esiti è nata il
2026-09-07. Col perimetro il banner direbbe «su 0» su metà dei giri.

#### ⚠️ Descrivono il canale «lotto», e va detto

La `gruppo_key` vive solo lì. Gli altri due canali che bloccano — `fatture_log`
e lo stato della riga di ponte — parlano per **fattura**, e una bozza può
coprire più documenti: i loro conteggi **non sono sommabili** a questi senza
scommettere.

#### ⚠️ Sono in coda, e la posizione è portante

Il backend legge questa riga per **posizione**. Infilare i numeri nuovi in
mezzo farebbe scivolare gli esistenti — e una lettura posizionale sbagliata
**non protesta**: mostrerebbe numeri plausibili e falsi. Per questo `fermo`
(19-09) è l'undicesima, dopo il decimo.

⛔ ~~`blocks_next_step` resta in Python~~ — **superato il 19-09-2026**: il
verdetto è la colonna `fermo`, a DB. Questi tre restano per la **frase**, non
per la decisione: su questo niente è cambiato.

---

### ⭐⭐ Il decimo numero: gli esiti `ERRORE` entrano nel verdetto (rev 2026-09-12)

`esiti_stato_esecuzione_errore_count` — quanti documenti presi in carico dal
lotto hanno come **ultimo fatto registrato** (`fatturazione_lotti_esiti`) un
`ERRORE`. In coda, decimo, e **questo sì che decide**: il backend lo somma in
`is_error`, quindi in `blocks_next_step`.

**Perché.** Il verdetto contava le bandiere — i log critici, che il runner stesso
abbassa all'avvio di ogni rerun («chi alza la bandiera la abbassa») — e il
gemello a valle (`lotti_fatture.stato_esecuzione`). Gli esiti li usava come
denominatore e per l'`ESCLUSO`, **mai come segnale**. Quindi: pull fallito →
esito `ERRORE`; rerun che **non rivede** quella commessa → bandiere abbassate,
niente le rialza → lotto `COMPLETATO` con un documento preso in carico e ancora
in `ERRORE`, e nessuno lo vede. Provato il 12-09-2026 su LTF-0010972: lotto
`COMPLETATO`, due esiti `ERRORE`, zero fatture.

Un esito è un **fatto** su un documento che il lotto ha preso in carico. Un lotto
che si dichiara a posto con un documento il cui ultimo fatto è `ERRORE` lo fa
**per sottrazione** — la forma fail-open. La via d'uscita c'è già ed è quella
giusta: **«Togli dal giro»** porta l'esito a `ESCLUSO`, cioè l'operatore
**dichiara** che quel documento non fa più parte del lavoro. `ESCLUSO` non conta
in questo numero: è l'altro stato della stessa riga.

✅ Il backend legge il decimo numero dal 12-09-2026
(`LottoSegnalazioniService.evaluate_lotto_status`). Decisione di Tid, 12-09-2026,
brief `brief-db-rilancio-step-non-rivede-le-proprie-commesse` (D2). ⭐ E dal
19-09-2026 quella somma la fa il database: è la colonna `fermo`.

---

### ⭐ Le criticità di un documento **uscito dal giro** non contano più
(dal 2026-09-08)

Quando l'operatore toglie un documento rotto dal giro
([`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)),
la sua segnalazione **smette di fermare il lotto** — così il giro riparte con i
documenti che restano, e riparte da solo quando esce l'ultimo che lo teneva
fermo.

⭐ **Non si ritira niente.** La segnalazione resta scritta e leggibile nella
storia del lotto: cambia soltanto **chi conta** per bloccare. Non è il
messaggio a essere stato messo a tacere, è il suo documento a non essere più in
gioco.

⚠️ **Una segnalazione senza documento continua a contare**, ed è il
comportamento voluto: significa *«questa criticità è del giro»* — un emittente
non risolto, una configurazione mancante — e una criticità del giro deve fermare
il giro, perché non c'è nessun documento da togliere.

#### Dei tre conteggi, uno solo è cambiato

| Conteggio | Da dove legge | Che cosa è cambiato |
| --- | --- | --- |
| **log di lotto** | le segnalazioni del giro | 🔵 **l'unico toccato**: salta quelle dei documenti usciti |
| **log fatture** | attraverso il legame lotto-fatture | ✅ niente |
| **ponte** | lo stato tecnico del legame lotto-fatture | ✅ niente |

⭐ Gli ultimi due **si sistemano da soli**: togliere un documento dal giro
cancella la sua bozza, quindi il legame sparisce e i due conteggi scendono senza
che nessuno li tocchi.

> 🔴 **Finché chi scrive le segnalazioni non dichiara a quale documento
> appartengono, questa regola non sblocca niente**: le criticità nascono senza
> proprietario e contano tutte. È l'ordine dei lavori, non un difetto.

---

### Regole principali

* `p_lotto_id` è obbligatorio e deve essere `> 0`.
* Le conte vengono calcolate solo su record **attivi** (`disabilitato = false`).
* Le severità considerate:
  * `C` = critical
  * `W` = warning
  * `I` = info (solo su log lotto)
* Ritorna anche il conteggio tecnico:
  * `fatture_stato_esecuzione_errore_count` = numero fatture del lotto in stato esecuzione `ERRORE`.
* Output sempre valorizzato con `0` quando non ci sono righe.

---

### Output

La funzione ritorna una sola riga con:

* `fatture_critical_count`
* `fatture_warning_count`
* `lotto_critical_count`
* `lotto_warning_count`
* `lotto_info_count`
* `fatture_stato_esecuzione_errore_count`
* `documenti_bloccanti_count`, `documenti_presi_in_carico_count`, `critiche_giro_count` (banner, 2026-09-08)
* `esiti_stato_esecuzione_errore_count` (verdetto, 2026-09-12) — decimo
* `fermo` (il verdetto stesso, 2026-09-19) — undicesimo e **ultimo**: il backend legge per posizione

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_get_lotto_segnalazioni_summary(
  p_lotto_id => 120
);
```

---

{% include-markdown "signature-core.md" %}
