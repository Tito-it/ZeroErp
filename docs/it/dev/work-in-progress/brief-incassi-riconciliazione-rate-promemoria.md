# Promemoria — Incassi e riconciliazione rata ↔ incasso

> **Cos'è.** Un promemoria delle attività **rimaste aperte** e collegate fra loro
> dal medesimo pezzo mancante: l'aggancio fra una **rata** e un **incasso**.
> Non è un piano e non contiene decisioni: serve a ritrovare, a distanza di
> tempo, cosa era stato lasciato indietro e **perché stava insieme**.
>
> **Scritto il 2026-08-02**, alla chiusura del cantiere satelliti della fattura,
> dove queste voci erano elencate come «fuori scope» in tre documenti diversi.
> Ordine di lavorazione deciso da Tid: **1) incassi/riconciliazione → 2) blocco
> `2.4 DatiPagamento` → 3) SDI**.
>
> **Fonti**: `brief-db-generazione-scadenze-fattura.md` §6 e §7 (chiuso),
> `dbzero/vendite/manual/fatture_scadenze.md`, `guide/gestione-dei-pagamenti.md`.

---

## 1. Il pezzo mancante, in una frase

**Un incasso è agganciato alla fattura, non alla rata.**

Verificato sul DB il 2026-08-02: nell'intero database **non esiste alcuna
colonna `scadenza_id`**. `pagamenti.vendite_movimenti` porta `fattura_id` e
`billing_account_id`, e si ferma lì.

Da questo singolo fatto discendono **tutte** le voci aperte qui sotto. Non sono
quattro lavori indipendenti che per caso si somigliano: sono quattro conseguenze
dello stesso anello mancante, ed è la ragione per cui vanno riprese insieme e in
quest'ordine.

---

## 2. Stato di partenza, misurato

Da rileggere prima di stimare qualsiasi cosa: il terreno è **più vuoto** di
quanto la presenza degli schemi suggerisca.

| Cosa | Stato al 2026-08-02 |
|---|---|
| Colonna di aggancio rata → incasso | **non esiste** (nessun `scadenza_id` nel DB) |
| `pagamenti.vendite_movimenti` | tabella presente, **0 righe** |
| Le altre 9 tabelle di `pagamenti` | presenti, **tutte a 0 righe** |
| Schema `contabilita` | **nessuna tabella** |
| `vendite.fatture_scadenze` | **si popola da oggi**: il generatore è entrato con la Fase 4 |

⚠️ **La riga più importante è l'ultima.** Fino al 2026-08-02 le rate non
esistevano affatto: il piano rate è appena stato acceso. Qualsiasi analisi fatta
prima di quella data ha guardato una tabella vuota, e le sue conclusioni vanno
riverificate sui dati veri.

**Cosa invece esiste già** e non va riscritto: `fn_get_saldo_fattura` (residuo =
`totale_a_pagare` − movimenti attivi, con flag di presenza), la testata contabile
`vendite_contabili` con righe e stati, i centri di riscossione, gli enti di
incasso, i mandati SEPA e le compensazioni. La guida
[gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) descrive il modello.
Il saldo, insomma, c'è — **ma è per fattura**, non per rata.

---

## 3. Le attività aperte

### 3.1 🔴 Riconciliazione rata ↔ incasso — è il prerequisito di tutto il resto

L'unico lavoro **strutturale** dell'elenco. Le altre tre voci si sbloccano da
sola quando questa atterra.

Da decidere (nessuna decisione è stata presa, sono qui solo le domande):

- l'aggancio è **una FK** `vendite_movimenti → fatture_scadenze` o una tabella di
  **allocazione N:N**? Un incasso può coprire più rate e una rata può essere
  coperta da più incassi: la FK singola è più semplice ma decide subito che quel
  caso non esiste;
- che cosa succede a un incasso **parziale** su una rata;
- l'imputazione è **manuale, automatica o mista** (per data, per importo esatto,
  a saldo progressivo);
- lo stato della rata è **derivato** dagli incassi o **materializzato** in
  colonna. ⚠️ Il modello ha già una preferenza in casi analoghi: derivare, e
  materializzare solo quando il costo di ricalcolo lo impone.

### 3.2 ⏸️ Blocco `2.4 DatiPagamento` del payload FatturaPA

**Ora possibile**, perché le rate esistono. Verificato: `fn_prepare_sdi_payload`
**non nomina mai** né `DatiPagamento` né le scadenze — il blocco non è generato.

È **completezza fiscale, non un abbellimento**: una fattura elettronica senza
condizioni di pagamento è incompleta. Appartiene al cantiere SDI ma dipende da
qui, ed è la ragione per cui Tid l'ha messo **secondo** e non ultimo.

ℹ️ Nota: questo blocco descrive **come si pagherà**, non se è stato pagato —
quindi in teoria non richiede la 3.1. In pratica conviene farlo dopo, per non
scrivere due volte il lettore delle rate.

### 3.3 ⏸️ Portale clienti — `GET /api/portale/scadenze/`

Endpoint previsto e mai scritto. Senza la 3.1 mostrerebbe **il piano rate e
basta**, senza poter dire quali rate siano già pagate: su un portale rivolto al
cliente è un difetto grave, perché la domanda che il cliente si fa è esattamente
quella.

### 3.4 ⏸️ Lista scadenze / scadenzario

Oggi **non esiste** alcuna lista scadenze in `ui.lista_definizione`, e **non
serve**: il piano rate si vede già nel drawer fattura tramite il building block
`ScadenzeSintesi` / `useScadenzeSintesi`, che mostra `—` finché le rate non
arrivano e si accende da sé.

🔴 **Da non confondere**: «elenco del piano rate» e «scadenzario» sono due cose
diverse. Il primo si può fare adesso e aggiungerebbe poco al drawer. Il secondo —
scaduto / insoluto / da incassare, con solleciti e colorazioni — **richiede la
3.1**, perché senza stato di pagamento ogni sua colonna sarebbe falsa su una
fattura già incassata.

Se e quando la lista si farà, valgono i cinque prerequisiti di
[piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md), e il primo è
lavoro BE vero: **non esiste una rotta scadenze paginata**.

---

## 4. Due limiti di dominio da non aggirare

Sopravvivono a questo promemoria e valgono per chiunque tocchi l'area.

**Non esiste uno stato di pagamento della rata.** Finché è così, nessuna colonna
«scaduta / insoluta / da incassare», nessuna colorazione di sollecito, nessun
filtro «da incassare»: su una fattura già incassata sarebbero **tutti falsi**.
Meglio non mostrare un dato che mostrarne uno che mente.

**«Prossima rata» è un concetto temporale, non di pagamento.** La regola vive già
in `useScadenzeSintesi` — la prossima per data, e se sono tutte passate l'ultima —
ed è **una per tutto il prodotto**. Chi la ricalcolasse per conto proprio farebbe
dire a due schermate cose diverse sullo stesso documento.

---

## 5. Trappole già pagate, da non ripagare

- ⚠️ **`AlertScadenzeWidget.vue` non c'entra.** Nonostante il nome, riguarda le
  **versioni di listino** in scadenza senza successore, non le rate di fattura.
  Chi lo trova cercando «scadenze» sta guardando un altro dominio.
- ⚠️ **Il guard D-K presidia già la coerenza rate ↔ totale** in numerazione
  (sei condizioni, `E_FATTURA_NON_NUMERABILE_INCOERENTE`). Chi lavorerà agli
  incassi lo troverà sul percorso: **non è da allentare**: una fattura le cui
  rate non quadrano col totale non deve prendere un numero fiscale, e a maggior
  ragione non deve entrare in riconciliazione.
- ⚠️ **Il piano rate è uno snapshot congelato.** Oltre DRAFT/EMESSA le rate non
  si toccano più (guard satelliti). La riconciliazione deve quindi scrivere
  **altrove** — su una tabella di allocazione o su `vendite_movimenti` — e mai
  «aggiornare la rata come pagata» modificando `fatture_scadenze`.
- ⚠️ **Le tabelle vuote non sono tabelle assenti.** Le 10 tabelle di `pagamenti`
  esistono con vincoli, trigger e manuali: prima di progettare qualcosa di nuovo,
  leggere `guide/gestione-dei-pagamenti.md` — buona parte del modello c'è già e
  aspetta solo di essere usata.

---

## 6. Dove guardare quando si riprende

| Cosa | Dove |
|---|---|
| Il modello pagamenti esistente | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Le rate: struttura, formula, cosa NON sono | [dbzero/vendite/manual/fatture_scadenze.md](/dbzero/vendite/manual/fatture_scadenze) |
| Il catalogo dei termini | [dbzero/config/manual/termini_pagamento.md](/dbzero/config/manual/termini_pagamento) |
| Il residuo per fattura, già pronto | `pagamenti.fn_get_saldo_fattura` |
| Come sono nate le rate (cantiere chiuso) | `work-done/brief-db-generazione-scadenze-fattura.md` |
