# Brief DB — il DDT di ri-consegna nasce nudo: testata e riga che non ereditano, e le cose che NON vanno copiate

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Collaudo in-app di Tid del 2026-08-27, prova **9** di
> [collaudo-in-app-ddt-righe-senza-prezzo.md](../work-done/collaudo-in-app-ddt-righe-senza-prezzo.md)
> (ri-consegna standalone, casella **6** del §19 di
> [brief-ddt-righe-senza-prezzo.md](../work-done/brief-ddt-righe-senza-prezzo.md)):
> reso generato dal DDT `DDT0023451`, ri-consegna generata → il DDT nuovo arriva
> **senza causale di trasporto e senza indirizzi**, e l'operatore li deve
> ridigitare a mano su un documento che il DB ha generato da sé.
>
> **Stato.** 2026-08-27 — analisi sulla **struttura** (corpo delle due funzioni
> madri, colonne di `vendite.ddt`, seed di `config.sorgenti`). Nessun file
> scritto, nessuna migrazione. **Una domanda di modello** prima di qualunque riga
> di SQL (§3.2, il vettore).
>
> ⚠️ **Revisione 2026-08-27, stessa giornata**: la voce su `fatturazione_immediata`
> era **mia e sbagliata** — nasceva dall'aver guardato la colonna senza seguire il
> percorso che la consuma. Ritirata e riscritta nel §4, che ora dice il contrario.
> Al suo posto è entrata una voce vera, il §3-bis, sollevata da una domanda di Tid
> sul prezzo della riga.
>
> **Correlati:**
> [fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) ·
> [fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) ·
> [trgfn_ddt_normalize](/dbzero/vendite/funzioni/trgfn_ddt_normalize) ·
> [brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md)

---

## 0. Le voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | **Testata**: il generatore che parte dalla sorgente **più ricca** (un DDT) copia **meno** di quello che parte dalla più povera (un ordine): niente indirizzi, niente blocco trasporto | 🔴 asimmetria del modello, già incontrata in-app | ogni operatore che genera una ri-consegna |
| **2** | **Riga**: né prezzo né IVA né sconto. Nel caso **standalone** non c'è nessun `COALESCE` a valle che li recuperi — e la riga generata **non si poteva salvare affatto** dalla UI, nemmeno per correggere la quantità | 🔴 vicolo cieco chiuso | chi apre una riga di ri-consegna: prova 9 |
| **3** | La ri-consegna **standalone** non dichiara nessuna sorgente: nasce orfana, mentre `RESO_VENDITA` esiste a catalogo e `vendite.resi` ha lo `uid` | 🟠 dato vero non rappresentato | chi guarda «Transito»/«Passaggi» su quel DDT |
| **4** | ✅ ~~`fatturazione_immediata` ri-fattura merce già fatturata~~ — **rilievo mio RITIRATO il 2026-08-27**, vedi §4: la doppia fatturazione è già impedita a monte, e il flag sceglie solo la corsia | 🟢 nessuna | — |

⭐ **Cosa hanno in comune**: la cura sta tutta dentro **`fn_genera_ddt_riconsegna`**
— una funzione, un changeSet. Nessuna vista, nessun trigger, nessun BE, nessun
FE: il drawer del DDT mostra già tutti i campi in questione, sono vuoti perché
nessuno li scrive.

---

## 1. Il fatto, letto dal contratto

`vendite.fn_genera_ddt_riconsegna`, passo 4, inserisce la testata con **nove**
colonne:

```sql
INSERT INTO vendite.ddt (
    data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
    sorgente_tipo_id, sorgente_uid, billing_account_id,
    utility_id, valuta_id, emittente_fiscale_id)
```

`vendite.ddt` ne ha **quaranta**. Restano fuori, fra le altre:
`causale_trasporto_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id`,
`mittente_soggetto_ruolo_id`, `vettore_soggetto_ruolo_id`,
`fatturazione_immediata`. E **non c'è nessun `INSERT INTO vendite.ddt_indirizzi`**.

`trgfn_ddt_normalize` non tappa il buco e non è pensato per farlo: eredita
`billing/utility/valuta/emittente` e **solo** da una sorgente `ORDINE_VENDITA`.

### 1.1 ⭐ L'argomento non è la comodità, è la simmetria

La funzione gemella `fn_genera_ddt_da_ordine`, al passo **4-bis**, fa questo:

```sql
-- 4-bis) Cascata indirizzi (D-1): copia 1:1 gli snapshot dell'ordine
--   filtrati sui tipi ammessi in ambito DDT (di fatto solo CON).
INSERT INTO vendite.ddt_indirizzi (
    ddt_id, tipo_indirizzo_id, snapshot,
    origine_indirizzo_id, origine_soggetto_ruolo_id)
SELECT ... FROM vendite.ordini_indirizzi oi
  JOIN config.tipi_indirizzi_allowed a
    ON a.tipo_indirizzo_id = oi.tipo_indirizzo_id AND a.ambito = 'DDT'
 WHERE oi.ordine_id = p_ordine_id
ON CONFLICT (ddt_id, tipo_indirizzo_id) DO NOTHING;
```

Un **ordine** non ha nessun blocco trasporto — causale, aspetto, addebito non
esistono proprio su `vendite.ordini` — e ciononostante il generatore da ordine
fa cascadere gli indirizzi. Il generatore da **reso** parte da un `vendite.ddt`,
cioè dall'unico documento che il blocco trasporto ce l'ha **tutto**, e non copia
né quello né gli indirizzi.

> Non è «una dimenticanza in un caso di nicchia»: è che la stessa cosa — «il
> documento figlio eredita la testata del padre» — è scritta in un posto e non
> nell'altro. Il modello la ammette in entrambi. Va resa **simmetrica subito**,
> non rinviata (`feedback_simmetria_modello_no_meta_scope`).

### 1.2 ⚠️ E il design-of-record la causale l'aveva già nominata

Il **§R-3** di `brief-ddt-righe-senza-prezzo.md` scrive, testualmente:

> *«E la causale giusta per quel documento è **VENDITA**: il §N7 di
> `vw_partite_merce` dice che la quota accreditata torna ri-fatturabile, quindi
> quella ri-consegna si vende.»*

La causale era **già decisa** sul modello. Non è mai stata cablata: la funzione
lascia `causale_trasporto_id` a `NULL` e il documento arriva all'operatore muto.

⭐ **Corollario sul collaudo**: la prova 9 chiede oggi di *impostare* VENDITA a
mano prima di verificare che l'emissione blocchi in modo parlante. Con l'eredità,
quella casella si accende da sé — e la prova diventa fedele a com'è il processo
invece che a com'è il rimedio manuale.

---

## 2. ✅ Cosa va ereditato — «la relazione»

Colonne che descrivono **con chi e perché** la merce si muove. Sono le stesse per
il viaggio di andata e per la ri-consegna, perché è la stessa relazione
commerciale eseguita una seconda volta.

| Colonna | Perché eredita |
| --- | --- |
| `causale_trasporto_id` | il *perché* del movimento non cambia. ⚠️ È **immutabile dopo l'emissione** (`trgfn_ddt_guard_causale_immutabile`) e **obbligatoria** all'emissione: lasciarla nulla non rimanda una scelta, la sposta su un operatore che non ha il contesto |
| `aspetto_bene_id` | la merce è **la stessa merce**, tornata indietro |
| `modalita_addebito_trasporto_id` | patto sulle spese, non fatto del viaggio |
| `mittente_soggetto_ruolo_id` | spedisce lo stesso soggetto |
| **indirizzi** (`ddt_indirizzi`, ambito `DDT`) | cascata 1:1 come al passo 4-bis del gemello, `origine_*` propagati, `ON CONFLICT DO NOTHING`. È il pezzo che oggi **blocca l'emissione**: `trgfn_ddt_guard_indirizzi_obbligatori` alza `E_INDIRIZZO_DOC_OBBLIGATORIO` su un documento generato dal DB |

---

## 3. ⛔ Cosa NON va ereditato — «il viaggio»

Qui la richiesta *«tutte le informazioni duplicate dal DDT da cui è nato»* va
ristretta, e non per prudenza: **copiare queste colonne scrive fatti falsi su un
documento fiscale di trasporto.**

| Colonna | Perché **non** eredita |
| --- | --- |
| `num_colli`, `peso_lordo`, `peso_netto`, `volume` | ⛔ **sbagliati per costruzione, non «stantii»**: la ri-consegna porta un **sottoinsieme** delle righe del DDT origine, e su quelle righe una **frazione** della quantità (il residuo di ri-consegna, `fn_resi_riga_residuo_riconsegna`). Un peso copiato è il peso di un collo che non è quello che parte |
| `targa`, `autista` | il mezzo e la persona di un viaggio **già avvenuto**. Sono una misura, non una scelta |
| `data_ora_partenza`, `data_ora_consegna_prev` | date di un viaggio concluso su un documento ancora in `DRAFT` |
| `tracking_code` | ⛔ il peggiore: punta il cliente al **collo precedente**. Un codice di tracciamento copiato non è un campo vuoto, è un'informazione sbagliata data a un terzo |

### 3.1 Il criterio, in una riga

> **Eredita ciò che è una scelta; non ereditare ciò che è una misura.**
> Una scelta vale finché non la si cambia; una misura vale per il viaggio in cui
> è stata presa.

### 3.2 ❓ Domanda di modello — `vettore_soggetto_ruolo_id`

È il caso di confine, e per questo **non lo decido qui**: il vettore è insieme
una scelta (l'accordo con quel corriere) e un fatto del viaggio. Se eredita, sono
coerenti `targa`/`autista` che **non** ereditano — chi spedisce è una scelta,
quale furgone parte è una misura. Se non eredita, la testata resta più vuota ma
non dice mai niente di non verificato.

**Serve la risposta di Tid**, non del DB: è una convenzione di processo.

---

## 3-bis. 🔴 La riga: prezzo, IVA e sconto — e il vicolo cieco dello standalone

Domanda di Tid del 2026-08-27: *«il prezzo della riga non dovrebbe essere
ereditato? oppure essendo una ri-consegna potrebbe essere lasciato vuoto?»*.
La risposta è **diversa nei due rami**, e il ramo standalone è un vicolo cieco.

### 3-bis.1 Order-backed: il prezzo eredita già, e NON va copiato

`fn_list_ddt_da_pushare` proietta il prezzo così:

```sql
COALESCE(x.dr_prezzo, x.src_prezzo_unitario)   -- src = riga d'ordine via fulfillment
```

Il prezzo della ri-consegna order-backed **c'è già**, e non perché qualcuno
l'abbia copiato: si risale a `ordini_righe_fulfillment` al momento della lettura.
È lo stesso meccanismo che il §R-3 di `brief-ddt-righe-senza-prezzo.md` descrive
(«tutte ereditano il prezzo dalla riga d'ordine via `ordini_righe_fulfillment`»).

⛔ **Copiarlo dentro `ddt_righe.prezzo_unitario` sarebbe un peggioramento**: si
creerebbe una **seconda copia di un numero che ha già una sorgente**, e le due
divergono al primo cambio di prezzo sull'ordine (`feedback_duplicazione_nasconde_il_bug`).

### 3-bis.2 Standalone: non c'è nessun secondo termine del `COALESCE`

Nel caso standalone `fn_genera_ddt_riconsegna` **non scrive nessun fulfillment**
(passo 5, ramo `ordine_riga_id IS NOT NULL`). Quindi `src_prezzo_unitario` è
`NULL`, `dr_prezzo` è `NULL`, e non c'è niente da cui ereditare.

⭐ **Ma la sorgente esiste, ed è a un salto solo**: `vendite.resi_righe.ddt_riga_id`
è **`NOT NULL`** — ogni riga di reso punta alla riga del DDT d'origine, che il
prezzo, lo sconto e l'IVA ce li ha. È la stessa relazione che il generatore usa
già per articolo, descrizione e UoM.

⚠️ **Non è `resi_righe` la sorgente**: quella tabella il prezzo **non ce l'ha**
(articolo, descrizione, quantità, UoM, tipo, motivo — nessuna colonna di valore).
Il reso è uno snapshot di **quantità**, non di **valore**. Chi cercasse il prezzo
lì non lo trova e concluderebbe che «non c'è», mentre è sulla riga a monte.

### 3-bis.3 ⛔ E non è solo il prezzo: mancano anche IVA e sconto

Il generatore inserisce la riga con **sette** colonne:

```sql
INSERT INTO vendite.ddt_righe (
    ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, uom_operativa_id, factor_to_base)
```

Il gemello `fn_genera_ddt_da_ordine` ne scrive **dieci**, e le tre in più sono
esattamente `prezzo_unitario, sconto_percentuale, iva_id`. Stessa asimmetria del
§1, un piano più in basso.

`vendite.ddt_righe.iva_id` è nullable e **non ha nessun trigger di default**: la
riga nasce senza aliquota.

### 3-bis.4 ⛔ Perché è un vicolo cieco e non un fastidio

Rilievo in-app di Tid, in due tempi: prima *«la riga dell'articolo non è
comunque modificabile»*, poi — ed è la frase che ha aperto il caso —
*«il pulsante salva risulta disabilitato, e la combo IVA è vuota»*.

Il contratto dice questo:

* `script.fn_available_actions_ddt` → `can_edit_righe = (stato = 'DRAFT')`: in
  bozza la riga **si apre**;
* nel form di riga, in EDIT, `ArticoloLookup` e il select **IVA** sono
  `:disabled="isEdit"`, mentre `prezzo_unitario` resta editabile;
* ⛔ ma `canSave` pretendeva `iva_id` **anche in EDIT** — e `iva_id` su quelle
  righe è `NULL`.

Quindi non era «monco», era **chiuso**: il form si apriva e il pulsante Salva era
morto per sempre. Non solo il prezzo — nemmeno la quantità si poteva correggere.
E l'auto-fill dell'IVA dall'articolo non poteva soccorrere: passa da
`onArticoloSelect`, che in EDIT non si può invocare perché il lookup è disabilitato.

> ⭐ È il caso di `feedback_bug_logici_modello`: non manca un default comodo — il
> percorso che il DB apre **non ha un'uscita a valle**.

#### 3-bis.4-bis ✅ Il lato FE è già corretto (2026-08-27)

`canSave` valida ora **solo ciò che l'EDIT invia**. Il ramo `isEdit` di
`buildRigaPayload` manda `{qta_operativa, sconto_percentuale, descrizione}` più
il prezzo: articolo, UoM e IVA non viaggiano, quindi non si validano.

⚠️ **Sono due difetti distinti e servono entrambe le cure.** Il gate era
sbagliato *a prescindere* dalle righe di ri-consegna — validava campi non
trasmessi; le righe nude sono solo ciò che l'ha reso visibile. Con R4 il gate
resterebbe sbagliato e nessuno se ne accorgerebbe più.

⚠️ **La stessa forma è in `OrdiniRigaForm` e `PreventiviRigaForm`** (tre copie,
payload di UPDATE identico: `articolo_id`/`uom_operativa_id`/`iva_id` non inviati
in nessuna delle tre). Lì è **latente** — nessun generatore produce righe senza
IVA su ordini e preventivi — ma è lo stesso difetto. L'unificazione in
`useRigaArticoloComposito` (che già possiede `isEdit`/`isCasoA`/`submitRiga`) è
**proposta a Tid, in attesa di ok**: regola del 2.

### 3-bis.5 «Lasciarlo vuoto aiuta a non ri-fatturare?»

**No** — ed è la parte da sfatare. Il prezzo non ha **nessun ruolo** nel decidere
se una riga va in fatturazione: quel freno è altrove ed è già montato (§4). Un
prezzo assente non protegge da niente; produce solo un documento che non si
emette. I due piani sono indipendenti.

---

## 4. ✅ `fatturazione_immediata` — rilievo RITIRATO, e il perché conta

> ⚠️ **Questa sezione diceva il contrario fino a poche ore fa.** Sosteneva che
> ereditare il flag da un DDT a fatturazione immediata avrebbe emesso *«una
> seconda fattura sulla stessa merce»*. **È falso**, e l'errore è stato mio: avevo
> guardato la **colonna** senza seguire il **percorso che la consuma**. Lo lascio
> scritto invece di cancellarlo, perché è il rilievo che avrebbe mandato il team
> DB a mettere in sicurezza una porta già chiusa.

### 4.1 La doppia fatturazione è già impedita, e per nome

`vendite.vw_partite_merce` classifica ogni riga di DDT:

```sql
CASE WHEN r.e_riconsegna AND r.quota_nuova <= 0 THEN 'RICONSEGNA' ... END AS stato
CASE WHEN w.conta_fatturazione AND v.misurabile
      AND ((NOT r.e_riconsegna) OR (r.quota_nuova > 0)) THEN w.saldo
     ELSE NULL END AS differenza
```

e `fn_list_ddt_da_pushare` sbarra la porta con un predicato esplicito, commentato
per esteso nel corpo della funzione:

```sql
--   - riga di RI-CONSEGNA: merce gia' contata sulla partita
--     d'origine. Fatturarla di nuovo sarebbe il «bug 1a».
AND pm.differenza IS NOT NULL
```

Una riga di ri-consegna ha `differenza` **vuota** e non entra nella lista, **a
prescindere** da `fatturazione_immediata`, dallo stato del DDT e dal prezzo.

### 4.2 L'unico caso in cui la ri-consegna SI fattura è quello giusto

`riconsegna_quota_nuova > 0`, cioè quando una **nota di credito** ha accreditato
la quantità sulla partita d'origine (N7 / D-NC-4: *«una ri-consegna è merce nuova
SOLO per la parte accreditata»*). Lì la merce è **uscita** dal fatturato, quindi
ri-consegnarla è una vendita nuova e va fatturata — per quella quota sola.

### 4.3 Cosa resta del flag

`fatturazione_immediata` è una **corsia di instradamento**, non un cancello:
`fn_list_ddt_da_pushare` la proietta (`x.d_fatt_immediata`) per decidere *dove*
va una riga già dichiarata eleggibile. Quindi eredita insieme al blocco
«relazione» del §2, come le altre colonne di patto commerciale, e la domanda che
avevo posto **non esiste**.

⭐ **La lezione operativa, che vale oltre questa riga**: *una colonna non si giudica
dal suo nome, si giudica dal percorso che la legge.* La stessa forma di
`feedback_whitelist_dal_percorso_reale`.

---

## 5. 🟠 La ri-consegna standalone nasce senza sorgente

Al passo 3 la funzione cerca un ordine dietro le righe di reso; **solo** se lo
trova valorizza `sorgente_tipo_id`/`sorgente_uid` (a `ORDINE_VENDITA` + `uid`
dell'ordine). Nel caso **standalone** — quello della prova 9 — restano entrambi
`NULL`: il DDT dichiara di non venire da nessuna parte, mentre viene da un reso.

Il materiale per dirlo c'è già, e non va inventato:

* `config.sorgenti` ha `RESO_VENDITA` (id 15, `categoria = DOCUMENTO`,
  `scope = REVERSE_FLOW`, attivo);
* `vendite.resi` ha `uid uuid NOT NULL DEFAULT uuidv7()`, cioè la forma che
  `ddt.sorgente_uid` si aspetta.

⚠️ Due cose da guardare prima di scrivere, e le lascio al team DB perché toccano
un contratto pubblicato:

1. il seed di `RESO_VENDITA` porta `key_selector = 'id'` mentre `PREVENTIVO`
   porta `'uid'`: se il puntatore diventa `resi.uid`, i due vanno riconciliati o
   il selettore mente;
2. l'order-backing esistente **non va perso**: oggi la sorgente `ORDINE_VENDITA`
   è ciò che tiene insieme la ri-consegna e il residuo d'ordine. Se la sorgente
   diventa il reso, il legame con l'ordine resta comunque su
   `ordini_righe_fulfillment` (passo 5) — ma va **detto**, non dedotto.

Questa voce tocca lo stesso nervo di
[brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md)
§2 («commesse che dichiarano di non avere origine»): vale la pena che i due
cantieri si guardino prima di scrivere.

---

## 6. La richiesta, in ordine

| # | Cosa | Blocca il collaudo? |
| --- | --- | --- |
| **R1** | `fn_genera_ddt_riconsegna` eredita dal DDT origine il blocco «relazione» del §2 — causale, aspetto, modalità addebito, mittente | 🔴 sì — prova 9 |
| **R2** | Cascata indirizzi ambito `DDT`, modellata sul passo 4-bis di `fn_genera_ddt_da_ordine` | 🔴 sì — senza, l'emissione è bloccata dal guard |
| **R3** | ⛔ **Nessuna** eredità del blocco «viaggio» del §3 — e scritto nel corpo della funzione **perché** (un `-- non si copia` senza motivo lo rimette dentro il prossimo che passa) | — |
| **R4** | **Riga**: `prezzo_unitario` e `sconto_percentuale` dalla riga di DDT d'origine (`resi_righe.ddt_riga_id`, `NOT NULL`) **solo nel ramo standalone** — nell'order-backed il `COALESCE` a valle fa già il lavoro e una copia lo peggiora (§3-bis) | 🔴 sì — oggi lo standalone non ha uscita |
| **R4-quater** | ⚠️ **`iva_id`: la copia è una misura di attesa, non la sede.** Con il risolutore IVA la riga di ri-consegna prende l'aliquota **da lì**, come ogni altra riga — e la decisione **P1** di Tid (2026-08-27) dice perché: *il documento a monte proietta, la fattura decide*, quindi l'IVA del DDT è una **proiezione** e si ri-risolve, non si trasporta. Finché il risolutore non c'è, copiarla dalla riga d'origine è meglio del `NULL` di oggi; quando ci sarà, questa copia **va tolta** o saranno due meccanismi per lo stesso campo. Vedi [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md) §2.6.2 | 🟠 da coordinare coi due cantieri |
| ~~R4-bis~~ | ✅ **FATTO lato FE il 2026-08-27**: `canSave` non pretende più in EDIT i campi che l'EDIT non invia — la riga di ri-consegna ora si salva. ⚠️ **Non sostituisce R4**: resta una riga **senza aliquota**, e il select IVA in EDIT resta `:disabled`. Se il team DB decide di non ereditare `iva_id`, allora quel campo va sbloccato | — |
| **R4-ter** | ❓ Una riga di DDT **senza `iva_id`** è ammessa a regime? La colonna è nullable e nessuna guard la pretende all'emissione, ma il riepilogo IVA (`vw_ddt_riepilogo_iva_dettaglio`) e la stampa la usano. Se la risposta è no, il posto del vincolo è il DB, non il pulsante Salva | no |
| **R5** | Decisione di Tid sul vettore (§3.2) | no |
| ~~R-fatt~~ | ✅ ~~`fatturazione_immediata`~~ — **ritirata**, §4 | — |
| **R6** | Sorgente `RESO_VENDITA` sulla ri-consegna standalone (§5) | no — cantiere suo, se il team DB preferisce |

**pgTAP attesi** (il perimetro si legge dai test, non dalla descrizione della
funzione — `feedback_ripiego_ogni_codice_vivo`):

* ri-consegna **order-backed**: la testata generata ha causale/aspetto/addebito/
  mittente **uguali** al DDT origine, e gli indirizzi ambito DDT copiati;
* ri-consegna **standalone**: idem — è il caso della prova 9, e va **costruito**,
  non cercato fra le righe esistenti;
* ⭐ **standalone, la riga**: prezzo e sconto **uguali alla riga di DDT
  d'origine** (per l'IVA vedi `R4-quater`); e nel ramo **order-backed** `ddt_righe.prezzo_unitario` resta
  `NULL` — la copia non ci deve essere, il `COALESCE` di
  `fn_list_ddt_da_pushare` è la sorgente;
* ⭐ **il freno della fatturazione non si è allentato**: la riga di ri-consegna
  senza nota di credito ha `vw_partite_merce.stato = 'RICONSEGNA'` e
  `differenza IS NULL`, e **non compare** in `fn_list_ddt_da_pushare` — anche
  ora che la riga un prezzo ce l'ha. È la non-regressione che il §4 rende
  necessaria: prima il prezzo assente nascondeva l'esito;
* ⛔ **il test che manca sempre**: la testata generata ha `num_colli`,
  `peso_lordo`, `peso_netto`, `volume`, `targa`, `autista`, `tracking_code`,
  `data_ora_partenza` **a `NULL`** anche quando il DDT origine li ha valorizzati.
  Senza questo, «non copiare» è un commento, e il primo che allarga la `INSERT`
  li porta dentro senza che niente si accenda.

---

## 7. Cosa NON serve

* **niente BE**: `resi_repository.genera_ddt_riconsegna` chiama la madre e ne
  ritorna l'id — la firma non cambia;
* **quasi niente FE**: il drawer DDT rende già causale, aspetto, addebito,
  mittente, vettore e la sezione indirizzi (`DocumentoIndirizziSection`) — oggi
  sono vuoti perché nessuno li scrive, non perché non si vedano. ⚠️ L'unica
  eccezione è **R4-bis**, il select IVA bloccato in EDIT;
* **nessuna colonna nuova**, **nessuna vista**, **nessun trigger**: una funzione,
  un changeSet con numerazione successiva, corpo preso dalla doc auto-gen.
