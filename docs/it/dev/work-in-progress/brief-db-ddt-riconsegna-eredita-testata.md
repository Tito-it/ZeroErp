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
> ⭐ **Revisione 2026-08-28 — il documento ha adesso un piano.** Sono entrati due
> capitoli nuovi: il **§8**, cosa dice la struttura letta oggi (contratti: corpi
> di funzione, definizioni di vista, nullabilità) e come cambia l'ordine del
> lavoro; il **§9**, il **piano di sviluppo** vero e proprio — fasi, changeSet,
> pgTAP, decisioni aperte.
>
> ✅ **Rev. 2026-08-28, seconda passata — le due domande a Tid sono chiuse.**
> **R5**: il vettore **eredita** (§3.2 — l'ha decisa un fatto che il documento non
> aveva: un vettore vuoto si stampa «Mezzo proprio», quindi non ereditare non
> taceva, *affermava*). **R4-ter**: una riga di DDT senza `iva_id` è
> **impossibile** → nasce la **Fase C** (§9.3), e con essa la correzione §9.3.1,
> dove ritiro l'obiezione sbagliata che avevo scritto contro il `NOT NULL`.
> ⭐ **Precisato subito dopo da Tid**: *«impossibile si traduce in **non
> emittibile**»* — quindi la Fase C è **un passo solo**, il gate all'emissione,
> e la riga resta lecita in bozza come per la causale (§9.3.2).
> ⭐ **E il §9.4.1 risolve D-2**: l'arco `RESO → DDT` è un **avanzamento**, per la
> ragione già scritta nel corpo della vista per l'arco S.
> ⭐ **Nessuna fase ha più decisioni davanti**: resta una verifica (§9.4.1) e un
> coordinamento col FE (la `reason_key` di C-1).
>
> 📍 **Rev. 2026-08-28 sera, quinta passata — MIGRAZIONE APPLICATA, doc auto-gen
> rigenerata, NESSUNA REGRESSIONE** (baseline `vendite`: 5 rossi, tutti gia'
> noti). Il test nuovo gira **sotto RLS**: 17/17. Chiusa anche la verifica del
> §9.4.1, e **sulla struttura**: `DDT_VENDITA` ha `pipeline_rank` 3 e `FATTURA`
> 5, quindi i due figli in avanti di un reso non pareggiano mai.
> ⛔ **Ma la parte DB NON e' finita e NON passa tutto al frontend**: restano la
> **doc manuale** di 5 oggetti (perimetro DB), una **rigenerazione lato BE**
> (`manage.py genera_error_policies` — emersa solo dopo l'apply) e la chiave
> i18n del FE, che e' l'unica a **bloccare la CI adesso**. Dettaglio: **§12**.
>
> 🔴 **Rev. 2026-08-28, quarta passata — UNA REGRESSIONE, trovata da Tid**
> subito dopo l'apply: l'arco T ha rotto il pgTAP che enumera il **vocabolario
> chiuso** degli archi. Era un cricchetto che ha fatto il suo mestiere, non una
> fixture stantia. Chiusa, con un'asserzione **in piu'** invece che con un
> elenco piu' largo — **§11**. Suite `vendite` ricontrollata: nessuna
> regressione. ⛔ La ricaduta era mia: avevo grepato i pgTAP per la **funzione**
> e non per le **due viste** dello stesso changeSet.
>
> ✅ **Rev. 2026-08-28, terza passata — LO SVILUPPO E' FATTO.** Le Fasi A, B, C
> e D sono scritte: 6 changeSet, 2 append ai CSV dei codici errore, 1 file pgTAP
> da 17 asserzioni. ⛔ **Niente e' applicato.** Elenco dei file, cosa e' stato
> trovato scrivendo e come e' stato verificato: **§10**.
> ⚠️ Il §10.5 e' l'unica cosa che serve da un altro perimetro: due righe di
> testo nei locales del frontend, da chiedere **adesso** — il cancello i18n
> diventa rosso al primo migrate, non prima.
>
> ⛔ **Da leggere per primo, prima di scrivere una riga: il §8.1 e il §8.2.**
> Le richieste del §6 **non sono indipendenti**: consegnare R1 senza R4 trasforma
> un documento muto in un documento che **non si emette**, e consegnare R4 senza
> R4-quater produce un **riepilogo IVA sbagliato in silenzio**. Il §6 le elencava
> come voci separabili; la struttura dice che tre di esse sono **una consegna
> sola**.
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

> ⚠️ **Rev. 2026-08-28 — quella frase resta vera per le voci 1, 2 e 3, e va
> ristretta.** «Una funzione, un changeSet» descrive bene la **Fase A** del §9.1,
> che è dove sta il grosso. Ma il §8.2 mostra che la voce **2** (la riga)
> trascina una domanda che vive **fuori** dalla funzione — se una riga di DDT
> possa avere un prezzo e nessuna aliquota — e il §8.5 che la voce **3** (la
> sorgente), da sola, riempie una colonna senza far comparire il documento nel
> grafo. Le due code sono le Fasi C e D. Il perimetro «nessun BE, nessun FE»
> invece **regge intero**: nessuna delle fasi chiede una riga a quei due lati.

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
| `vettore_soggetto_ruolo_id` | ⭐ **entrato il 2026-08-28** su decisione di Tid (§3.2): *chi* spedisce è una scelta commerciale, e un `NULL` non tace — la stampa scrive «Mezzo proprio» |
| `fatturazione_immediata` | corsia di instradamento, non cancello: è un patto commerciale come le altre (§4.3) |
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

### 3.2 ✅ `vettore_soggetto_ruolo_id` — RISPOSTO: eredita (Tid, 2026-08-28)

È il caso di confine, e per questo **non lo decido qui**: il vettore è insieme
una scelta (l'accordo con quel corriere) e un fatto del viaggio. Se eredita, sono
coerenti `targa`/`autista` che **non** ereditano — chi spedisce è una scelta,
quale furgone parte è una misura. Se non eredita, la testata resta più vuota ma
non dice mai niente di non verificato.

> ⛔ **L'ultima frase era sbagliata, ed è il fatto che ha deciso la domanda.**
> Non ereditare **non** lascia la testata «più vuota»: `template-ddt-vendita.html`
> rende il vettore con
> `{{ trasporto.vettore_denominazione or "Mezzo proprio" }}` — un `NULL` si stampa
> **«Mezzo proprio»**, con sotto il riquadro «Firma vettore». Cioè il documento
> *afferma* che la merce viaggia col mezzo del venditore.
>
> ⭐ È l'unica colonna del §2/§3 dove **non decidere produce comunque una frase**:
> `targa`, `autista` e `tracking_code`, se vuoti, semplicemente non si stampano
> (`{% if %}` nel template). Il confronto giusto non era «campo pieno contro campo
> vuoto», era **«corriere dell'andata contro "Mezzo proprio"»** — e fra due
> affermazioni non verificate vince quella che nel caso ordinario è vera.

**Decisione di Tid (2026-08-28): il vettore EREDITA.** Rientra quindi nel blocco
«relazione» del §2, e il §3.1 lo spiega senza eccezioni: *chi spedisce* è una
scelta commerciale, *quale furgone parte* è una misura.

⚠️ **Il campo resta modificabile in qualunque stato**: sul vettore non c'è nessun
guard di immutabilità (a differenza della causale, `trgfn_ddt_guard_causale_immutabile`).
Un corriere ereditato e sbagliato si corregge; una causale no. È la ragione per
cui l'eredità qui costa meno che altrove.

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

1. ~~il seed di `RESO_VENDITA` porta `key_selector = 'id'` mentre `PREVENTIVO`
   porta `'uid'`: se il puntatore diventa `resi.uid`, i due vanno riconciliati o
   il selettore mente;~~
   ✅ **ALLARME RIENTRATO il 2026-08-28 — vedi §8.4.** `key_selector` non governa
   la colonna tipizzata `ddt.sorgente_uid`: `ORDINE_VENDITA` è **già** a
   `key_selector = 'id'` e quella colonna ci mette da sempre `ordini.uid`. Non
   c'è niente da riconciliare e `config.sorgenti` non si tocca;
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
| **R4-ter** | ~~❓ Una riga di DDT **senza `iva_id`** è ammessa a regime?~~ ✅ **RISPOSTO da Tid il 2026-08-28: NO, è impossibile.** Il vincolo va quindi nel DB, non nel pulsante Salva — come questa riga già anticipava. La forma del vincolo, e perché non può essere un `NOT NULL` di colonna oggi, nel **§9.3** riscritto | no |
| **R5** | ~~Decisione di Tid sul vettore (§3.2)~~ ✅ **RISPOSTO da Tid il 2026-08-28: il vettore EREDITA.** Vedi §3.2, che ora porta anche il fatto che ha deciso: un vettore vuoto **non è un silenzio**, la stampa scrive «Mezzo proprio» | no — sbloccata la Fase A |
| ~~R-fatt~~ | ✅ ~~`fatturazione_immediata`~~ — **ritirata**, §4 | — |
| **R6** | Sorgente `RESO_VENDITA` sulla ri-consegna standalone (§5) | no — cantiere suo, se il team DB preferisce |

> ⭐ **Rev. 2026-08-28 — dove finisce ciascuna richiesta.** La tabella qui sopra
> resta l'elenco di *cosa* va fatto; il **§9** dice *in che ordine* e *insieme a
> cosa*, e le due letture non coincidono:
>
> | Richiesta | Fase (§9) | Perché lì |
> | --- | --- | --- |
> | R1, R2, R3, R4, R4-quater | **A** — un solo changeSet | si trascinano a vicenda: §8.1 e §8.2 |
> | i pgTAP del §6 | **B** | il perimetro si legge dai test, e la Fase A senza di essi è una promessa |
> | R4-ter | **C** | ✅ risposto «no» — e «impossibile» **si traduce in non emittibile**: un gate in più all'emissione, un passo solo (§9.3) |
> | R6 | **D** | da sola riempie una colonna e non fa comparire il documento nel grafo (§8.5) |
> | R5 (vettore) | **A** | ✅ risposto «eredita»: è una colonna della stessa `INSERT`, non un lavoro a parte |
> | ~~R4-bis~~, ~~R-fatt~~ | — | chiuse |

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

---

## 8. ⭐ Cosa dice la struttura, e perché cambia l'ordine del lavoro

> **Cos'è questo capitolo.** Non porta misure sui dati: porta letture di
> **contratto** — corpi di funzione, definizioni di vista, nullabilità di colonne,
> seed di catalogo — fatte il **2026-08-28** sulla doc auto-gen. È la sorgente
> giusta per decidere (`AGENTS.md` §«struttura contro popolazione»), e serve
> perché il §6 elenca sei richieste come se fossero **separabili**: tre di esse
> non lo sono, e consegnarne una senza l'altra **peggiora** ciò che c'è oggi.

### 8.1 ⛔ R1 senza R4 non è «metà cura»: è un blocco all'emissione

`script.fn_check_ddt_emittibile` — la single source che alimenta i quattro guard
di emissione **e** `fn_available_actions_ddt` — ha un punto 3 che dice questo:

```sql
-- se la causale e' fatturabile, ogni riga attiva deve avere un prezzo
-- RISOLVIBILE: proprio o ereditato dalla riga d'ordine via fulfillment
WHERE dr.attivo IS TRUE
  AND COALESCE(dr.prezzo_unitario, src.prezzo_unitario) IS NULL
```

dove `src` è un `LEFT JOIN LATERAL` su `ordini_righe_fulfillment`. E
`config.causali_trasporto` dichiara **`fatturabile = t` sulla sola VENDITA**;
tutte le altre sette (`CONTO_VISIONE`, `RESO`, `RIPARAZIONE`, `CAMPIONATURA`,
`TRASFERIMENTO`, `CONTO_LAVORO`, `OMAGGIO`) sono a `f`.

Componendo le due letture con il §3-bis.2 — nel ramo **standalone** la funzione
**non scrive nessun fulfillment**, quindi `src.prezzo_unitario` è `NULL` per
costruzione — esce la catena:

> R1 eredita la causale dal DDT origine → nel caso ordinario quella causale è
> **VENDITA**, cioè `fatturabile` → il punto 3 si accende → la riga standalone
> non ha né prezzo proprio né fulfillment → **`E_DDT_PREZZO_NON_RISOLVIBILE`**,
> e il DDT non si emette.

⭐ **Il documento cambierebbe difetto, non ne perderebbe uno.** Oggi la
ri-consegna standalone arriva muta e si emette solo dopo che l'operatore ha
digitato la causale a mano (prova 9). Con R1 da sola arriverebbe parlante e
**non si emetterebbe affatto**, e il messaggio nominerebbe un prezzo che
l'operatore non sa da dove prendere.

⚠️ **E non è un caso di nicchia mascherato**: non dipende da quale causale abbia
il DDT di oggi. Dipende dal fatto che il modello **ammette** la causale
fatturabile su un DDT che genera una ri-consegna — ed è anzi il caso *normale*,
perché quella causale è la stessa del viaggio di andata di una vendita. Se
domani il DDT origine avesse `CONTO_VISIONE`, il punto 3 tacerebbe: il ramo
resterebbe comunque raggiungibile, e un ramo raggiungibile va coperto.

**Conseguenza sul piano**: R1 e R4 **si consegnano insieme**. Non è una
preferenza di comodo — è che l'una arma un guard che solo l'altra disarma.

### 8.2 ⛔ R4 senza R4-quater produce un riepilogo IVA sbagliato **in silenzio**

Il §6 marca `R4-quater` (l'`iva_id`) come *«🟠 da coordinare coi due cantieri»*,
cioè rinviabile. La definizione delle due viste dice il contrario.

`vendite.vw_ddt_righe_iva_base` filtra così:

```sql
WHERE r.attivo IS TRUE AND r.quantita > 0 AND r.prezzo_unitario IS NOT NULL
```

— e **non filtra `iva_id`**. Anzi lo ammette esplicitamente:

```sql
CASE WHEN r.iva_id IS NOT NULL THEN config.fn_get_aliquota_iva(...)
     ELSE NULL::numeric END AS aliquota_effettiva
```

`vendite.vw_ddt_riepilogo_iva_dettaglio` aggrega su `(ddt_id, iva_id,
aliquota_effettiva)` e calcola l'imposta con
`COALESCE(a.aliquota_effettiva, 0)`.

Mettendo insieme le tre letture, ecco cosa succede **oggi** e cosa succederebbe
**con R4 da sola**:

| | riga di ri-consegna standalone | cosa fa il riepilogo IVA |
| --- | --- | --- |
| **oggi** | `prezzo_unitario` NULL | la riga **non entra** nella base: il riepilogo tace |
| **con R4 sola** | prezzo valorizzato, `iva_id` NULL | la riga **entra**, e produce una riga di riepilogo con **imponibile pieno**, `iva_codice` **vuoto** e `imposta = 0` |
| **con R4 + R4-quater** | prezzo e aliquota valorizzati | riga corretta, come ogni altra |

⛔ **La riga di mezzo è peggio della prima.** Un prezzo assente è un documento che
non si emette — rumoroso, e chiunque se ne accorge. Un imponibile senza aliquota
è un documento che **si emette e si stampa** con una riga di IVA anonima a
imposta zero. Nessun guard lo ferma: `fn_check_ddt_emittibile` non guarda
`iva_id` in nessuno dei suoi cinque punti, e su `vendite.ddt_righe` non c'è
**nessun trigger di default IVA** (l'unico che nomina `iva_id` è
`trgfn_child_requires_active_parent`, che verifica solo che l'aliquota citata sia
attiva — non che ci sia).

⭐ **È la forma di `feedback_bug_logici_modello` un piano più in là**: il §3-bis.4
raccontava un percorso che il DB apre e che a valle non ha uscita. Qui il
percorso l'uscita ce l'ha, e porta fuori un numero sbagliato.

**Conseguenza sul piano**: R4 e R4-quater sono **la stessa consegna**. Il
carattere «provvisorio» della copia dell'IVA, che il §6 descrive bene e che resta
vero, riguarda **quanto a lungo** quella riga di codice vivrà — non se possa
mancare al momento del rilascio.

> ✅ **Rev. 2026-08-28 — R4-ter è stato risposto, e conferma questa lettura da
> sopra.** Tid: *una riga di DDT senza `iva_id` è **impossibile**.* Quindi il caso
> descritto nella riga di mezzo della tabella non è «un difetto da evitare»: è uno
> stato che il modello **non ammette**, e che oggi esiste solo perché nessuno ha
> ancora messo il vincolo. La Fase C (§9.3) lo mette — e la §9.3.1 spiega perché
> non può essere un `NOT NULL` di colonna in un colpo solo.

### 8.3 🟠 L'order-backed ha già un buco, ed è lo stesso di forma opposta

Il §3-bis.1 conclude, correttamente, che nel ramo order-backed il prezzo **non va
copiato** perché `fn_list_ddt_da_pushare` lo risale via `ordini_righe_fulfillment`
al momento della lettura. Quell'argomento vale per il **lister della
fatturazione**, e `fn_check_ddt_emittibile` è stata scritta per essere d'accordo:
il suo punto 3 fa lo stesso `COALESCE`, con lo stesso `LEFT JOIN LATERAL`.

⚠️ **`vw_ddt_righe_iva_base` invece no.** Non conosce il fulfillment: legge solo
`r.prezzo_unitario`, e scarta la riga se è `NULL`. È l'unica vista di righe DDT
del progetto (verificato il 2026-08-28: nessun'altra `vw_ddt_*righe*` esiste, e
delle quattro viste che nominano `ordini_righe_fulfillment` nessuna è una vista
di righe DDT).

Ne segue una cosa che **non dipende da questo cantiere e c'era già**:

> una ri-consegna **order-backed** supera il gate di emissione — il prezzo è
> risolvibile via fulfillment — e stampa un **riepilogo IVA vuoto**, perché per
> la vista quella riga non esiste.

⭐ Vale la pena vederlo per quello che è: due consumatori della stessa domanda
(«questa riga ha un prezzo?») rispondono in modo diverso, e uno dei due è quello
che finisce sul foglio consegnato al cliente. Il `COALESCE` è la sorgente giusta;
è la vista a non averlo imparato.

⛔ **Non lo si risolve dentro `fn_genera_ddt_riconsegna`**, ed è il motivo per cui
sta qui e non nel §9.1: copiare il prezzo anche nell'order-backed farebbe sparire
il sintomo creando la seconda copia che il §3-bis.1 rifiuta con ragione. La cura,
se si decide di farla, è **insegnare il `COALESCE` alla vista** — ed è un cantiere
suo, che tocca ogni DDT da evasione ordine, non solo le ri-consegne.

**Conseguenza sul piano**: nessuna, per le Fasi A-D. È una **voce da aprire
altrove**, e il §9.5 la registra come tale perché non si perda.

### 8.4 ✅ `key_selector`: l'allarme del §5 è rientrato

Il §5 chiedeva di riconciliare `config.sorgenti.key_selector` prima di puntare
`ddt.sorgente_uid` a `resi.uid`. **Non serve**, e le ragioni sono tre, tutte di
contratto:

1. **Il precedente esiste già ed è quello accanto.** `ORDINE_VENDITA` ha
   `key_selector = 'id'` nel seed, e `ddt.sorgente_uid` ci mette da sempre
   `ordini.uid` — lo scrive `fn_genera_ddt_da_ordine` al passo 4. Se il selettore
   «mentisse», mentirebbe già su tutti i DDT da evasione.
2. **Sono due meccanismi distinti.** `key_selector` governa la **chiave polimorfa
   testuale** (`commesse_sorgenti`, `pratiche_sorgenti`, le `vw_stato_sorgente_*`);
   `vendite.ddt.sorgente_uid` è una **colonna tipizzata `uuid`**, fuori dal
   polimorfo. Lo dice per esteso la descrizione di `vw_stato_sorgente_ddt`:
   *«Chiave = ddt.id::text, come dichiara key_selector per DDT_VENDITA (NON
   l'uid: quello è la colonna tipizzata diretta resi.sorgente_uid, meccanismo
   diverso)»*.
3. **Il resolver prova la via uuid per prima, qualunque sia il selettore.**
   `vendite.fn_get_sorgente_documento_ref` — quello che accende l'azione «apri
   documento sorgente» e compone l'etichetta — testa il valore contro la regex
   uuid **prima** di guardare `key_selector`, e in quel ramo fa
   `SELECT t.id, t.<label_selector> FROM <target_table> t WHERE t.uid = $1`.
   Con `RESO_VENDITA` a `target_table = vendite.resi` e `label_selector = numero`,
   e `vendite.resi.uid uuid NOT NULL DEFAULT uuidv7()`, la traduzione **riesce**:
   l'operatore vedrebbe `RESO0005122` e il pulsante «apri».

⛔ **Corollario: `config.sorgenti` non si tocca.** Sarebbe un `UPDATE` su una
tabella la cui sede è il CSV (`80_data/sql/config/sorgenti.csv`) — e cambiare
`key_selector` per RESO_VENDITA cambierebbe il comportamento di **tutti** i
consumatori polimorfi di quel tipo, per risolvere un problema che non c'è.

### 8.5 🟠 R6 senza l'arco di lineage riempie una colonna e non fa comparire niente

Il §5 chiede che la ri-consegna standalone **dichiari** la propria sorgente.
Giusto — ma il posto in cui quella dichiarazione si vede è il grafo, e il grafo
non la leggerebbe.

`vendite.vw_documento_lineage_archi` costruisce gli archi **uno per uno, con il
tipo sorgente cablato in join**. L'arco che porta a un DDT è questo:

```sql
JOIN config.sorgenti s_from ON s_from.id = d.sorgente_tipo_id
                           AND s_from.codice_interno = 'ORDINE_VENDITA'
JOIN vendite.ordini  o      ON o.uid = d.sorgente_uid
```

Un DDT con `sorgente_tipo_id = RESO_VENDITA` **non produce nessun arco**: il join
lo scarta, in silenzio e correttamente. Il grafo ha già un arco `DDT → RESO`
(`s_from = DDT_VENDITA` su `resi.sorgente_uid`) e un arco `RESO → nota di
credito` (l'arco S, 2026-08-25) — ma **non** l'arco di ritorno `RESO → DDT di
ri-consegna`, perché finora non c'era niente da leggere.

⭐ **Quindi R6 è due cose, non una**: scrivere la sorgente sulla testata *e*
aggiungere l'arco che la rende visibile. Consegnare solo la prima produce una
colonna valorizzata e un «Transito/Passaggi» identico a prima — cioè
esattamente il sintomo che il §5 vuole togliere, con in più la falsa impressione
che sia stato curato.

⚠️ **E l'arco ha una natura da dichiarare, non da indovinare.** La descrizione di
`vw_documento_lineage_archi` è esplicita sul criterio: *«"inverso" vuol dire ramo
di RITORNO, un verso che il grafo forward non percorre»*, e l'arco S **non** è
inverso perché è l'*avanzamento* del reso. La ri-consegna è nella stessa
famiglia: la merce è tornata e adesso riparte. Se sia un avanzamento del reso o
un ramo inverso è una **decisione di quel cantiere**, e va presa lì — motivo per
cui la Fase D si coordina con
[brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md),
come il §5 già suggeriva.

⚠️ Una cosa da guardare quando si scriverà: `vw_ddt_lista` fa
`LEFT JOIN vendite.ordini o_src ON o_src.uid = d.sorgente_uid` **senza
qualificare il tipo sorgente**. Con una sorgente RESO il join non trova nulla e
la colonna resta vuota — che è l'esito giusto — ma ci arriva **per assenza di
collisioni fra spazi di uuid**, non perché qualcuno l'abbia deciso. Non blocca
R6; è una riga da irrobustire mentre si è lì.

### 8.6 ⚠️ Due eredità, due strade — e una delle due può mancare

La testata e la riga non pescano dallo stesso posto, e la differenza è di
**nullabilità**:

| | da dove | il modello garantisce l'origine? |
| --- | --- | --- |
| **testata** (§2) e **indirizzi** | `vendite.resi.sorgente_uid` → `vendite.ddt` | ⛔ **no**: la `SELECT` del passo 2 usa un `LEFT JOIN vendite.ddt d ON d.uid = r.sorgente_uid`. `resi.sorgente_tipo_id`/`sorgente_uid` sono `NOT NULL`, ma **nulla impone che il tipo sia `DDT_VENDITA`**: il join può non trovare niente e `v_orig.*` resta tutto `NULL` |
| **riga** (R4) | `vendite.resi_righe.ddt_riga_id` → `vendite.ddt_righe` | ✅ **sì**: la colonna è `NOT NULL` |

Due conseguenze per chi scrive la Fase A:

1. **L'eredità di testata deve tollerare il `NULL`**, senza guard nuovi: se il
   DDT origine non c'è, le colonne restano vuote **come oggi** e l'emissione
   resta bloccata dai guard che già ci sono. È il comportamento corrente, non una
   regressione — e sollevare lì sarebbe rompere un percorso che oggi funziona per
   i resi che un DDT ce l'hanno.
2. **L'eredità di riga non ne è toccata**: passa da `resi_righe`, e funziona anche
   nel caso in cui la testata non erediti niente.

⚠️ **E le due possono puntare a DDT diversi.** `trgfn_resi_righe_guard_origine_coerente`
verifica la coerenza fra `ordine_riga_id` e il fulfillment della riga di DDT —
**non** che `resi_righe.ddt_riga_id` appartenga al DDT citato da
`resi.sorgente_uid`. Il modello lo ammette. Non è un problema da risolvere qui,
ma è il motivo per cui la Fase A **non** deve «semplificare» leggendo il prezzo
dal DDT di testata invece che dalla riga di reso: sarebbe una scorciatoia che
funziona finché nessuno costruisce il caso che il modello permette.

### 8.7 ✅ Il kit composito: perché copiare il prezzo del padre è comunque corretto

`fn_genera_ddt_riconsegna` non copia `vendite.ddt_righe_componenti` — il gemello
da ordine sì (passo 5, ramo `is_composito`). Quindi una ri-consegna di un kit
produce **una riga padre senza componenti**. Non lo vieta nessuno: i guard di
coerenza BoM e di prezzo obbligatorio stanno su `ddt_righe_componenti`, e su zero
righe non scattano.

⭐ **R4 in quel caso fa la cosa giusta per costruzione.** Sul DDT d'origine il
prezzo della riga padre **è già** la somma dei componenti: ce lo ha scritto
`trg_ddt_righe_componenti_z90_ricalcola_padre_ins_upd_dlt`. Copiarlo trasporta un
totale corretto, e sulla ri-consegna **niente lo sovrascrive**, perché quel
trigger vive sui componenti e componenti non ce ne sono.

⚠️ Resta un fatto da sapere, non da curare adesso: la ri-consegna di un kit è un
documento che dichiara un totale e non mostra il dettaglio di cosa lo compone.
Va **detto nel corpo della funzione** insieme al resto (R3), non lasciato dedurre.

### 8.8 ⭐ Un effetto collaterale buono: l'eredità evita l'antipattern §6d

`config.causali_trasporto` ha `codice` e **non ha `codice_interno`**: è un caso
`CANDIDATE_ADD_CI` delle linee guida SQL (§6d). Cablare `WHERE codice = 'VENDITA'`
dentro la madre — che è quello che la lettura affrettata del §1.2 suggerirebbe,
visto che il design-of-record nomina VENDITA — sarebbe **esattamente il BUG_DUAL**
descritto lì: funziona finché nessuno rinomina il codice, poi il lookup torna zero
righe e il documento nasce di nuovo muto, **in silenzio**.

R1 come è scritta — **eredita l'id dal DDT origine** — non contiene nessun
letterale e non ha bisogno della colonna che manca. Nel caso ordinario ottiene
VENDITA perché VENDITA è ciò che il padre dichiara, e nei casi non ordinari
ottiene la causale giusta invece di una sbagliata.

⚠️ Questo **non chiude** il debito di `causali_trasporto` (una tabella di catalogo
referenziata da logica senza chiave stabile), ma lo lascia dov'era: questo
cantiere non ne aggiunge.

---

## 9. 🛠️ Piano di sviluppo

> **Perimetro.** Solo DB (`dev/db-tid`). Nessuna modifica sotto `backend/` e
> nessuna sotto `frontend/`: le Fasi A-D non ne hanno bisogno (§7), e se ne
> emergesse una si scrive **qui**, come richiesta, non la si esegue.
>
> ⛔ **Nessuna migrazione si applica.** Il piano si ferma ai file scritti e alla
> verifica in transazione annullata. L'`update` lo autorizza Tid, a voce, per
> quel comando.

### 9.0 Il principio d'ordine, in una riga

> **Ogni fase deve lasciare il sistema in uno stato che si può emettere.**

È il criterio che ha prodotto la Fase A così grossa: il §8.1 e il §8.2 mostrano
due tagli che *sembrano* naturali — «prima la testata, poi la riga», «prima il
prezzo, poi l'IVA» — e che entrambi lasciano in mezzo un documento peggiore di
quello di oggi. Una fase non è un'unità di lavoro: è un punto in cui ci si può
fermare.

### 9.1 Fase A — la madre. Un changeSet, una funzione

**File**: `db/changelog/migrations_v2/20_code/vendite/20260828-NN-update-fn-genera-ddt-riconsegna-eredita-testata-mctit.yaml`

⚠️ `NN` è la **numerazione globale per data**, non per cartella: si prende il
primo libero guardando *tutte* le sottocartelle di `migrations_v2` con prefisso
`20260828-`.

**Forma del changeSet** — le regole che si applicano qui, tutte già costate:

* `CREATE OR REPLACE FUNCTION` — la **firma non cambia**
  (`p_reso_id bigint, p_righe jsonb, p_data date`), quindi niente `DROP` e nessun
  rischio di overload;
* corpo **copiato dalla doc auto-gen**
  ([fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna)),
  non da uno YAML: ci sono revisioni intermedie che uno YAML non conosce;
  ⚠️ e la doc auto-gen **perde il `;` dopo `$function$`**: va rimesso;
* `runOnChange: false` — è `20_code`, dove `true` è **vietato** e presidiato in CI;
* `logicalFilePath` valorizzato, **un solo changeSet nel file**, header GPL dal
  template;
* nel `COMMENT ON FUNCTION` si cita il **nome** del brief, **mai** il path
  `work-in-progress/`: quel testo vive nel database e sopravvive alla cartella;
* apostrofi **raddoppiati** in tutto ciò che è dentro un letterale — `COMMENT`
  compreso, che è dove il difetto vive quasi sempre.

**Le sette modifiche al corpo**, in ordine di passo:

| # | Passo | Cosa cambia | Richiesta |
| --- | --- | --- | --- |
| A-1 | 2 | La `SELECT` di `v_orig` legge anche `d.id`, `d.causale_trasporto_id`, `d.aspetto_bene_id`, `d.modalita_addebito_trasporto_id`, `d.mittente_soggetto_ruolo_id`, `d.vettore_soggetto_ruolo_id`, `d.fatturazione_immediata` | R1, R5, §4.3 |
| A-2 | 4 | La `INSERT` di testata passa da **nove** colonne a **sedici**: le sette sopra in più. ⛔ Nessuna del blocco «viaggio» del §3 | R1, R5, R3 |
| A-3 | 4-bis **(nuovo)** | Cascata indirizzi da `vendite.ddt_indirizzi` del DDT origine, filtrata su `config.tipi_indirizzi_allowed` ambito `DDT` e `attivo`, con `origine_*` propagati e `ON CONFLICT (ddt_id, tipo_indirizzo_id) DO NOTHING` | R2 |
| A-4 | 5 | Il `FOR` legge anche dalla riga di DDT d'origine (`resi_righe.ddt_riga_id` → `vendite.ddt_righe`): `prezzo_unitario`, `sconto_percentuale`, `iva_id` | R4, R4-quater |
| A-5 | 5 | La `INSERT` di riga passa da **sette** colonne a **dieci** — e le tre in più si valorizzano **solo nel ramo standalone** (`v_riga.ordine_riga_id IS NULL`) | R4 |
| A-6 | — | I commenti che dicono **perché** il blocco «viaggio» non si copia, riga per riga: senza il motivo, il prossimo che allarga la `INSERT` li rimette dentro | R3 |
| A-7 | — | `COMMENT ON FUNCTION` aggiornato: cosa eredita, cosa **non** eredita e perché, e che la copia dell'`iva_id` è **provvisoria** e va tolta quando arriva il risolutore | R4-quater |

**Le tre cose che è facile sbagliare**, e che valgono più dell'elenco:

1. ⛔ **A-5 è condizionale, A-4 no.** Leggere il prezzo dalla riga d'origine si fa
   sempre (costa un join che c'è già); **scriverlo** si fa solo se
   `ordine_riga_id IS NULL`. Nell'order-backed la colonna resta `NULL` di
   proposito — il `COALESCE` di `fn_list_ddt_da_pushare` è la sorgente, e una
   copia la peggiora (§3-bis.1). Un `COALESCE` di comodo qui cancellerebbe la
   decisione senza che nessuno se ne accorga.
2. ⚠️ **A-1/A-2 devono sopravvivere al `LEFT JOIN` che non trova** (§8.6): niente
   guard nuovi, niente `NOT FOUND`. Se il DDT origine manca, le sei colonne
   restano `NULL` — cioè lo stato di oggi.
3. ⚠️ **A-3 filtra su `tipi_indirizzi_allowed` anche se la sorgente è già un
   DDT.** Sembra ridondante — le righe di `ddt_indirizzi` sono già passate da
   `trgfn_tipi_indirizzi_only_allowed('DDT')` — e non lo è: un tipo **ritirato
   dopo** (`attivo = false`) resterebbe sulle righe vecchie e farebbe **fallire
   l'INSERT** sulla ri-consegna, contro lo stesso trigger. Il filtro è ciò che
   rende la copia tollerante al ritiro di un tipo, e va scritto con il suo
   perché accanto.

**Cosa la Fase A NON tocca**: nessuna colonna nuova, nessuna vista, nessun
trigger, nessun codice errore nuovo, nessun seed. Se durante la scrittura
servisse un codice errore nuovo, è il segnale che si sta rifiutando qualcosa che
la funzione dovrebbe invece **ereditare**.

### 9.2 Fase B — i pgTAP, che sono il perimetro

**File**: `db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql`, dal
template (`cp db/pgtap/_TEMPLATE.sql.txt`).

⚠️ **Il preambolo è obbligatorio e presidiato** (`BEGIN;`, riga di contesto
operatore, `SET CONSTRAINTS ALL IMMEDIATE`): senza, il file diventa verde per
sottrazione. E il test gira come **l'applicazione** (`zeroerp_app` + RLS attiva),
quindi le fixture devono scrivere dove l'applicazione scrive.

⛔ **Tutti i soggetti si costruiscono.** Nessun test cerca «una ri-consegna che
c'è»: su un database ricostruito da zero non ce n'è nessuna, e il file passerebbe
a vuoto proprio in CI. È il corollario sui test della Regola zero.

I sette casi, e cosa prova ciascuno:

| # | Caso | Perché esiste |
| --- | --- | --- |
| B-1 | **order-backed**, testata: causale, aspetto, modalità addebito, mittente, **vettore** e `fatturazione_immediata` **uguali** al DDT origine | R1, R5, §4.3 — il ramo che oggi c'è |
| B-2 | **order-backed**, indirizzi ambito DDT copiati 1:1, `origine_*` propagati | R2 |
| B-3 | **standalone**, testata: idem B-1 — ed è il caso della prova 9, **costruito** | R1, il ramo che si rompe |
| B-4 | **standalone**, riga: `prezzo_unitario`, `sconto_percentuale` e `iva_id` **uguali alla riga di DDT d'origine** | R4, R4-quater |
| B-5 | **order-backed**, riga: `ddt_righe.prezzo_unitario` resta **`NULL`** | ⭐ prova che la copia **non c'è** — è l'unico modo di presidiare una decisione di *non* fare |
| B-6 | ⛔ **il blocco «viaggio» resta a `NULL`** — `num_colli`, `peso_lordo`, `peso_netto`, `volume`, `targa`, `autista`, `tracking_code`, `data_ora_partenza`, `data_ora_consegna_prev` — **anche quando il DDT origine li ha valorizzati** | senza, «non copiare» è un commento e il prossimo `INSERT` allargato non accende niente |
| B-7 | ⭐ **il freno della fatturazione non si è allentato**: la riga di ri-consegna senza nota di credito ha `vw_partite_merce.stato = 'RICONSEGNA'` e `differenza IS NULL`, e **non compare** in `fn_list_ddt_da_pushare` — **anche ora che un prezzo ce l'ha** | è la non-regressione che il §4 rende necessaria: prima il prezzo assente **nascondeva** l'esito, quindi un verde di ieri non prova niente su oggi |

⭐ **Due casi che il §6 non chiedeva e che il §8 ha reso necessari**:

| # | Caso | Perché |
| --- | --- | --- |
| B-8 | **standalone**, il documento **si emette**: DRAFT → EMESSO passa, con la causale ereditata fatturabile e la riga valorizzata | è la prova che A-1..A-5 **insieme** disarmano il punto 3 di `fn_check_ddt_emittibile` (§8.1). Provare le colonne una per una non lo dimostra |
| B-9 | **standalone**, il riepilogo: `vw_ddt_riepilogo_iva_dettaglio` sul DDT generato **non ha righe con `iva_id IS NULL`** | è il presidio del §8.2 — l'unico che si accorge se un domani qualcuno toglie la copia dell'`iva_id` credendo di togliere una ridondanza |

⚠️ **`throws_ok` sempre con lo SQLSTATE** (`'P0001'` per un errore di dominio),
o `throws_like` sulla frase dove la frase è la posta in gioco. E ⚠️ **niente
`LIMIT 1` senza `ORDER BY`**: verificherebbe una riga a caso.

⚠️ Prima di aggiungere il file, `grep` sui pgTAP che già toccano questa madre —
`test-ponte-riconsegna-copre-riga-v1.sql`, `test-resi-motore-v1.sql`,
`test-resi-rinunce-scenario-v1.sql`,
`test-fn-list-ddt-da-pushare-contatore-v1.sql`,
`test-vw-partite-merce-riconsegna-dopo-nc-v1.sql` — perché B-4 e B-5 cambiano
ciò che quelle fixture producono, e un rosso lì sarebbe **nostro**.
Confronto con la baseline: `scripts/pgtap-baseline.sh vendite`.

### 9.3 Fase C — R4-ter: ✅ RISPOSTO «no, impossibile» (Tid, 2026-08-28)

**La domanda era**: una riga di DDT senza `iva_id` è ammessa a regime?
**La risposta è no.** Il vincolo va quindi nel DB — come R4-ter già scriveva
(*«il posto del vincolo è il DB, non il pulsante Salva»*).

Resta da scegliere **la forma**, e qui c'è una correzione da fare a questo stesso
documento.

#### 9.3.1 ⛔ Correzione: l'obiezione che avevo scritto contro `NOT NULL` era la sbagliata

La tabella precedente bocciava `iva_id NOT NULL` dicendo che *«rompe il DDT di
solo trasporto»*. **È falso, e l'errore è mio**: il DDT di solo trasporto è fatto
di righe **senza prezzo**, non senza aliquota — lo dice testualmente il punto 1 di
`fn_check_ddt_emittibile` (*«quello è righe SENZA PREZZO, non zero righe»*). Una
riga senza valore può benissimo dichiarare l'aliquota del suo articolo, e
`vw_ddt_righe_iva_base` la scarterebbe comunque, perché filtra sul prezzo.

⭐ **Il vero ostacolo è un altro, ed è più serio** (letto il 2026-08-28 sulla doc
auto-gen): **`vendite.ordini_righe.iva_id` è nullable.**

E `fn_genera_ddt_da_ordine`, al passo 5, scrive `orr.iva_id` **tale e quale**
nella riga di DDT. Quindi:

> un `NOT NULL` su `vendite.ddt_righe.iva_id` farebbe **fallire l'evasione di un
> ordine** ogni volta che la riga d'ordine non ha l'aliquota — con un `23502`,
> cioè un errore tecnico muto, su un percorso che oggi funziona.

⚠️ E il NULL è ammesso lungo **tutta la catena**, non solo lì: `ordini_righe.iva_id`
nullable, `ddt_righe_componenti.iva_id` nullable, `ddt_righe.iva_id` nullable.
Chiudere l'ultimo anello senza chiudere i primi due non rende il dato obbligatorio:
sposta il punto di rottura su chi non c'entra.

⭐ È la stessa forma del §8.1, un piano più su: **un vincolo si mette dove il dato
si può fornire, non dove il difetto si vede.**

#### 9.3.2 ✅ La forma: il gate all'emissione, e basta

> ⭐ **Precisazione di Tid, 2026-08-28** (chiude un dubbio che avevo lasciato
> aperto in questa stessa sezione): *«il mio "impossibile" si traduce in **non
> emittibile**»*.
>
> Quindi **C-1 è la risposta piena a R4-ter**, non metà. La riga senza aliquota
> resta ammessa **in bozza** — dove ogni documento è ancora incompleto per
> definizione, come già lo è per la causale (*«in bozza il NULL resta legittimo:
> il vincolo è qui, non sul salvataggio»*, punto 2 di `fn_check_ddt_emittibile`)
> — e diventa impossibile **sul documento che esce**.
>
> ⭐ Ed è coerente col resto del gate: **nessuno** dei sei punti vieta uno stato
> in bozza. Il DDT dichiara la causale, il prezzo, gli indirizzi e ora l'aliquota
> **quando si emette**, perché è lì che il documento smette di essere una
> lavorazione e diventa un foglio consegnato.

**Un passo solo, in questo cantiere.**

| | Cosa | Dove | Quando |
| --- | --- | --- | --- |
| **C-1** | Una riga **con prezzo** e senza aliquota **non si emette** | sesto punto in `script.fn_check_ddt_emittibile` + il guard che lo solleva | ⭐ **questo cantiere**, dopo la Fase B |

⭐ **Perché C-1 si aggancia al prezzo e non alla sola presenza della riga**: è lo
stesso discrimine che il progetto ha già scelto per il punto 3 — *c'è un prezzo,
quindi c'è un valore, quindi serve un'aliquota*. Inventarne un secondo vorrebbe
dire che due punti della stessa funzione decidono con criteri diversi cosa sia
una riga «valorizzata». ⚠️ Ed è anche ciò che tiene in piedi il **DDT di solo
trasporto**: righe senza prezzo, quindi senza obbligo di aliquota.

> ~~⚠️ C-1 non è la risposta piena a R4-ter…~~ ⛔ **Paragrafo RITIRATO il
> 2026-08-28**, vedi il riquadro qui sopra. Sosteneva che servisse un secondo
> passo (`iva_id NOT NULL` sulla colonna) per rendere la riga impossibile «sulla
> tabella», e che fra i due restasse una finestra aperta. Con «impossibile =
> non emittibile» quella finestra **non è una finestra**: è la bozza, ed è dove
> il documento si lavora. Il §9.3.1 resta valido come **lettura** — la catena a
> monte ammette il `NULL` e un `NOT NULL` sull'anello finale romperebbe
> l'evasione ordine con un `23502` muto — ma non descrive più un lavoro da fare:
> descrive perché quel lavoro **non serve**.

**Cosa comporta C-1, in concreto:**

* ⛔ **un codice errore NUOVO, ed è inevitabile**: verificato il 2026-08-28 sul
  catalogo (`80_data/sql/config/messaggi_errore.csv`), **non esiste** nessun
  codice che dica «riga senza aliquota». I candidati che sembrano tali non lo
  sono — `E_BOM_IVA_DISCORDANTE` parla di due aliquote che non coincidono,
  `E_PERC_IVA_NO_MOD` di una modifica. Si conia;
* **classe `DATO_ERRATO` (400)**: il dato lo fornisce una persona in un form, e
  l'operatore può rimediare da solo scegliendo l'aliquota sulla riga. Nel
  `context` va `campo` (il nome della colonna) e il **bersaglio** sul documento —
  con `tipo` preso da `config.tipi_entita`, non inventato;
* ⛔ **nel `VARIADIC` non entra `iva_id`**: quella è la frase che legge una
  persona. Ci va il numero della riga, non il nome della colonna;
* **si appende al CSV** — `messaggi_errore.csv`, niente loader nuovo, niente
  `INSERT` SQL a parte;
* ⚠️ **è una richiesta al frontend nello stesso giro** — e non è una decisione,
  è un coordinamento. Il DB non scrive la frase: emette `enabled: false`, un
  `reason` (codice macchina, per i log e per chi diagnostica) e una `reason_key`,
  che è **una chiave, non un testo**. Il FE la cerca in
  `frontend/src/locales/it.json` e `en.json` e la mostra come tooltip sul
  pulsante grigio.
  ⛔ Chiave emessa + chiave assente dai due JSON = pulsante grigio col tooltip
  **vuoto**, cioè il difetto che la regola «disabilita col motivo» esisteva per
  evitare, in forma peggiore — sembra presidiato e non lo è.
  ✅ Il cancello c'è: `scripts/check_i18n_keys.py` (controllo 4) legge le
  `reason_key` emesse dalle funzioni DB nella doc auto-gen e **fa fallire la CI**
  se non le trova nei locales. Se il DB va per primo, la build è rossa.
  ⭐ **Il nome è già deciso dalla convenzione**: `fn_check_ddt_emittibile` emette
  già `vendite.ddt.azione_reason.causale_mancante`, `.prezzo_non_risolvibile`,
  `.componenti_prezzo_pendente`, `.componenti_non_valorizzati` — la quinta è
  **`vendite.ddt.azione_reason.iva_mancante`**. Le due righe di testo (it + en)
  le mette il FE, nello stesso giro del changeSet;
* ✅ **si specchia da sé nella capability**: `fn_check_ddt_emittibile` è la single
  source di `fn_available_actions_ddt` e dei quattro guard, quindi il pulsante
  «Emetti» diventa grigio **col motivo** senza scrivere una seconda regola.

⭐ **E C-1 non tocca la ri-consegna**: dopo la Fase A quelle righe l'aliquota ce
l'hanno. C-1 chiude il caso generale — la riga digitata a mano, l'evasione di un
ordine con la riga senza IVA — che è dove la finestra resta davvero aperta.

**pgTAP di C-1** (file suo, `db/pgtap/script/test-fn-check-ddt-emittibile-iva-v1.sql`):

| # | Caso |
| --- | --- |
| C-1a | riga **con prezzo, senza `iva_id`** → l'emissione **rifiuta**, con `throws_ok(..., 'P0001')` |
| C-1b | riga **senza prezzo, senza `iva_id`** (DDT di solo trasporto) → l'emissione **passa**: è il ramo che non va rotto |
| C-1c | `fn_available_actions_ddt` sullo stesso DDT di C-1a espone «Emetti» **`enabled = false`** con `reason` e `reason_key` valorizzati — non assente, non acceso |

### 9.4 Fase D — R6: la sorgente **e** l'arco

Due changeSet, e il secondo è quello che si dimentica (§8.5).

| # | Cosa | File |
| --- | --- | --- |
| D-1 | `fn_genera_ddt_riconsegna`: nel ramo standalone valorizza `sorgente_tipo_id = RESO_VENDITA` (lookup per `codice_interno`, come già si fa per `ORDINE_VENDITA` e `DRAFT`) e `sorgente_uid = resi.uid` | `20_code/vendite/20260828-NN-update-fn-genera-ddt-riconsegna-sorgente-reso-mctit.yaml` |
| D-2 | `vw_documento_lineage_archi`: arco nuovo `RESO → DDT`, con la sua natura **dichiarata** (avanzamento come l'arco S, o ramo inverso) | `20_code/vendite/20260828-NN-update-vw-documento-lineage-archi-riconsegna-mctit.yaml` |

**Le cose da guardare, e sono contratti già scritti:**

* ⚠️ **`security_invoker=on` va ri-specificata** nel `CREATE OR REPLACE VIEW`:
  PostgreSQL la **azzera** se non la si ripete, e la vista diventa
  `SECURITY DEFINER` di fatto — cioè scavalca la RLS senza dirlo;
* ⚠️ **la regola di perimetro della vista**: *«ogni ramo passa dalle
  TABELLE-TESTATA dei due documenti che collega, perché sono quelle che portano
  la RLS»*. L'arco nuovo unisce `vendite.resi` e `vendite.ddt` — entrambe
  testate, entrambe con RLS. Va scritto così e non passando da `resi_righe`;
* ✅ **l'order-backing non si perde**, e va **detto** invece che dedotto (lo
  chiedeva già il §5): la ri-consegna order-backed continua a dichiarare
  `ORDINE_VENDITA`, e il legame con l'ordine resta comunque su
  `ordini_righe_fulfillment` (passo 5). Cambia **solo** il ramo standalone, che
  oggi non dichiara niente;
* ⚠️ mentre si è lì, `vw_ddt_lista` (§8.5): il `LEFT JOIN` all'ordine va
  qualificato sul tipo sorgente. Oggi funziona per assenza di collisioni, non per
  decisione.

#### 9.4.1 ⭐ D-2 — la natura dell'arco: **avanzamento**, e la ragione è già scritta

Il grafo marchia ogni collegamento in un modo solo, e il marchio è una riga:
`is_ramo_inverso = arco IN ('R','N')`. Letti insieme, i quattro archi che
riguardano il ritorno merce dicono già la regola:

| arco | da → a | natura |
| --- | --- | --- |
| **H** | ordine → DDT | avanzamento |
| **R** | DDT → reso | 🔙 **ritorno** — la **merce** torna indietro |
| **N** | fattura → nota di credito | 🔙 **ritorno** — il **valore** torna indietro |
| **S** | reso → nota di credito | avanzamento |

⭐ **S è il precedente, e porta la sua ragione scritta nel corpo della vista**:
*«"inverso" vuol dire ramo di RITORNO, un verso che il grafo forward non
percorre; S invece è l'AVANZAMENTO del reso — la merce è tornata, adesso si
accredita»*.

**L'arco della ri-consegna è la gemella di S**: la merce è tornata, adesso
**riparte**. Il ritorno è già avvenuto, ed è l'arco R; da lì in poi il reso ha
**due modi di andare avanti** — accreditare la merce (S) o ri-consegnarla (il
nuovo). Nessuno dei due è il grafo che cammina all'indietro.

**Effetto voluto**, lo stesso che S ha prodotto: il reso **smette di essere una
foglia** e prende il DDT di ri-consegna come **frontiera**. Oggi un reso
ri-consegnato, nel grafo, è un vicolo cieco.

⚠️ **L'unica cosa da verificare scrivendolo**, e la nota dell'arco S la segnala
per il caso analogo: un reso può essere **in parte accreditato e in parte
ri-consegnato**, quindi avere **due figli in avanti**. Con S il pericolo era che
i due figli fossero **dello stesso tipo** (due nodi FATTURA allo stesso livello,
stesso `pipeline_rank`, e la frontiera decisa sul confronto lessicografico fra
due uid testuali). Qui i due figli sono di **tipo diverso** — una FATTURA e un
DDT — quindi il rango li separa e il caso è sicuro. ⛔ Ma va **guardato**, non
dato per buono: è esattamente quella differenza a renderlo sicuro, e se un domani
non ci fosse più, il difetto tornerebbe silenzioso.

**Coordinamento**: la stesura dell'arco si fa insieme a
[brief-db-lineage-residui-root-e-sorgente-ddt.md](brief-db-lineage-residui-root-e-sorgente-ddt.md)
§2 — è lo stesso nervo, «documenti che dichiarano di non avere origine».

### 9.5 Decisioni — chiuse il 2026-08-28, e quel che resta

**Chiuse da Tid**, e la Fase A è sbloccata:

| # | Domanda | Risposta | Effetto |
| --- | --- | --- | --- |
| **R5** | `vettore_soggetto_ruolo_id` eredita? (§3.2) | ✅ **sì, eredita** | entra in A-1/A-2. La testata passa a **sedici** colonne |
| **R4-ter** | Una riga di DDT senza `iva_id` è ammessa? (§9.3) | ✅ **no** — e «impossibile» **si traduce in non emittibile** (precisazione di Tid, stesso giorno) | nasce la **Fase C**, ⭐ in **un passo solo**: C-1. La riga resta ammessa in bozza, come per la causale |

⭐ **Il fatto che ha deciso R5, e che non era nel documento**: il template di
stampa rende il vettore con `or "Mezzo proprio"`. Non ereditare non lasciava un
campo vuoto — faceva **affermare** al documento che la merce viaggia col mezzo
del venditore. Fra due affermazioni non verificate vince quella che nel caso
ordinario è vera. *Una colonna non si giudica dal suo nome né dalla sua
nullabilità: si giudica dal percorso che la legge* — la stessa lezione del §4.3,
qui applicata alla stampa invece che al lister.

**Aperte, e nessuna blocca le Fasi A e B:**

| # | Domanda | Chi | Blocca |
| --- | --- | --- | --- |
| **D-2** | L'arco `RESO → DDT` è un avanzamento o un ramo inverso? | ✅ **risolta nel §9.4.1: avanzamento**, per la stessa ragione scritta nel corpo della vista per l'arco S. Resta **una verifica**, non una decisione: il reso in parte accreditato e in parte ri-consegnato ha due figli in avanti, e vanno di rango diverso | nulla — si scrive |
| **C-1-key** | `vendite.ddt.azione_reason.iva_mancante` — il **testo** (it + en) nei locales | ⚠️ **non è una decisione, è un coordinamento**: lo mette il FE nello stesso giro, o `check_i18n_keys.py` fa fallire la CI | la consegna di C-1 |

**Cantieri che questo brief apre e non esegue** — registrati perché non si
perdano, non perché siano piccoli:

| # | Cosa | Perché è fuori da qui |
| --- | --- | --- |
| ~~**C-2**~~ | ~~`iva_id NOT NULL` lungo la catena~~ | ⛔ **RITIRATO il 2026-08-28**: con «impossibile = non emittibile» non serve più. Il §9.3.1 resta perché spiega **perché non serve** — la catena a monte ammette il `NULL` e un `NOT NULL` sull'anello finale romperebbe l'evasione ordine con un `23502` muto |
| **§8.3** | Insegnare il `COALESCE` del fulfillment a `vw_ddt_righe_iva_base` | riguarda **ogni** DDT da evasione ordine, non le ri-consegne: oggi una riga col prezzo solo derivato supera il gate di emissione e sparisce dal riepilogo IVA stampato |
| **§8.5** | `vw_ddt_lista`: qualificare sul tipo sorgente il `LEFT JOIN` all'ordine | funziona per assenza di collisioni fra spazi di uuid, non per decisione. Da fare mentre si è lì con la Fase D |
| **§8.7** | I componenti BoM non si copiano sulla ri-consegna: un kit ri-consegnato dichiara un totale senza il dettaglio | il prezzo del padre è comunque corretto (§8.7): è una scelta di completezza del documento, non un difetto di calcolo |
| **§8.8** | `config.causali_trasporto` non ha `codice_interno` (`CANDIDATE_ADD_CI`, linee guida §6d) | questo cantiere **non lo aggrava** — eredita l'id e non scrive nessun letterale — ma il debito resta |

### 9.6 La verifica prima dell'apply — cosa si può fare senza migrare

L'hook blocca `liquibase update`, e giustamente. Resta però **tutto ciò che
serve** per sapere se il changeSet è sano:

1. ⛔ **Si estraggono i blocchi `changes[].sql.sql` dallo YAML e si eseguono
   INTERI**, con `ON_ERROR_STOP=1`, dentro una transazione che si annulla.
   ⚠️ **Riscrivere a mano l'SQL non prova il changeSet**: si ricopia sempre la
   DDL e si saltano proprio `COMMENT` e `GRANT`, che è dove vive il difetto
   dell'apostrofo. Il `BEGIN`/`ROLLBACK` dev'essere **nel file eseguito**, non
   nella testa di chi lancia.
2. `liquibase status` e `validate` sono liberi. `updateSQL` pure — non applica.
3. I **pgTAP** girano in transazione e sono liberi:
   `scripts/testpgtap.sh db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql`.
   ⚠️ Lanciati **prima** del migrate girano per forza da **owner**, perché la
   funzione nuova nel database non c'è ancora: un verde lì **non prova** che
   passi sotto RLS. Va ripetuto dopo l'apply.
4. `scripts/guardrail_sql_letterali.py` e `guardrail_run_on_change.py` sono i
   cancelli statici: si lanciano a mano, non si aspetta la CI.
5. ⚠️ **«Applicato?» si chiede a `databasechangelog`**, non al brief.

### 9.7 ⛔ Cosa questo piano NON fa

* **non applica migrazioni** — nemmeno dopo un «procedi»: l'autorizzazione si
  chiede per quel comando;
* **non tocca `backend/` né `frontend/`** — le eventuali richieste si scrivono
  qui;
* **non tocca `config.sorgenti`** (§8.4) né `config.causali_trasporto` (§8.8);
* **non aggiunge colonne** a `vendite.ddt` né a `vendite.ddt_righe`;
* **non conia codici errore nuovi** — se servissero, il difetto è a monte;
* **non copia i componenti BoM** sulla ri-consegna (§8.7): sarebbe un cantiere
  suo, e il prezzo del padre è già corretto senza;
* **non insegna il `COALESCE` a `vw_ddt_righe_iva_base`** (§8.3): è una voce
  aperta, registrata, di un altro perimetro;
* **non commette** senza che Tid lo chieda.

### 9.8 Il residuo del §3-bis.4-bis, che non è di questo piano

Il §3-bis.4-bis registra che l'unificazione dei tre form di riga
(`OrdiniRigaForm`, `PreventiviRigaForm`, e il gemello dei DDT) in
`useRigaArticoloComposito` è **proposta a Tid e in attesa di ok**. Resta lì: è
frontend, ha una sua regola (quella del 2) e non dipende da nessuna delle quattro
fasi.

⚠️ Una cosa però la Fase A la cambia, e va detta al FE quando si consegna: con
R4-quater la riga di ri-consegna **avrà** un'aliquota, quindi il select IVA
`:disabled` in EDIT smette di essere un vicolo cieco e torna a essere una scelta
di interfaccia normale. La domanda che il §6 poneva in coda a R4-bis — *«se il
team DB decide di non ereditare `iva_id`, allora quel campo va sbloccato»* —
**decade**: il team DB eredita.

---

## 10. ✅ Sviluppo eseguito — 2026-08-28

> **Stato: i file ci sono tutti, niente è applicato.** Il piano del §9 è stato
> scritto per intero, Fasi A → D. L'`update` lo autorizza Tid, a voce, per
> quel comando: «procedi allo sviluppo» ha autorizzato il **lavoro**.

### 10.1 I file

| # | File | Cosa |
| --- | --- | --- |
| **A** | `20_code/vendite/20260828-01-update-fn-genera-ddt-riconsegna-eredita-testata-mctit.yaml` | R1+R2+R3+R4+R4-quater+R5 — la madre eredita testata, indirizzi e (standalone) valore di riga |
| **C-1a** | `20_code/script/20260828-02-update-fn-check-ddt-emittibile-iva-mancante-mctit.yaml` | sesto motivo: riga **con prezzo** e senza aliquota |
| **C-1b** | `20_code/vendite/20260828-03-update-trgfn-ddt-guard-causale-emissione-iva-mctit.yaml` | il guard solleva `E_DDT_RIGA_IVA_MANCANTE` |
| **C-1c** | `80_data/sql/config/codici_errore.csv` · `messaggi_errore.csv` | il codice nuovo, **append** — nessun loader nuovo |
| **D-1** | `20_code/vendite/20260828-04-update-fn-genera-ddt-riconsegna-sorgente-reso-mctit.yaml` | R6 — la standalone dichiara `RESO_VENDITA` + `resi.uid` |
| **D-2** | `20_code/vendite/20260828-05-update-vw-documento-lineage-archi-riconsegna-mctit.yaml` | **arco T**, reso → DDT di ri-consegna |
| **D-3** | `20_code/vendite/20260828-06-update-vw-ddt-lista-sorgente-qualificata-mctit.yaml` | §8.5 — il join all'ordine si qualifica sul tipo sorgente |
| **B** | `db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql` | 17 asserzioni, Fase B + C-1 |

### 10.2 ⭐ Tre cose trovate scrivendo, che il piano non aveva

**10.2.1 ⛔ L'eredità di catalogo poteva impedire la generazione.** `vendite.ddt`
ha tre trigger `dbops.trgfn_child_requires_active_parent` — su
`causale_trasporto_id`, `aspetto_bene_id`, `modalita_addebito_trasporto_id` — e
`vendite.ddt_righe` ne ha uno su `iva_id`. Ereditare alla cieca da un DDT vecchio
che cita un elemento **ritirato dopo** avrebbe fatto **fallire** la
`fn_genera_ddt_riconsegna`: un errore duro al posto di un campo vuoto.

Ogni eredità di catalogo passa quindi da un `LEFT JOIN` filtrato su `attivo`: se
l'elemento non è più valido la colonna resta `NULL`, cioè lo stato di prima, e il
documento si genera lo stesso.

> ⭐ **La regola generale**: *un'eredità che può impedire la generazione non è una
> comodità, è un guasto nuovo.* È la stessa forma del filtro su
> `tipi_indirizzi_allowed` che il §9.1 già prescriveva per gli indirizzi — solo
> che lì l'avevo visto, e sulle tre colonne di testata no.

**10.2.2 ⚠️ `fatturazione_immediata` è `NOT NULL`.** Ereditarla da una testata
d'origine non trovata (§8.6) avrebbe violato il vincolo. Va con `COALESCE(…, false)`.
È l'unica delle sette colonne ereditate a non essere nullable.

**10.2.3 ⭐ D-2 non dipende da D-1, e questo cambia il §8.5.** L'arco si
costruisce da **`vendite.resi_righe_riconsegne`** — il ponte duro che la madre
popola per **entrambi** i rami dal 2026-07 — non da `ddt.sorgente_*`. Due
conseguenze:

* l'arco copre anche le ri-consegne **order-backed**, che dichiarano
  `ORDINE_VENDITA` e il reso non lo nominerebbero mai;
* i due changeSet sono **indipendenti**: si può consegnare l'uno senza l'altro.

> ⚠️ Il §8.5 diceva *«R6 è due cose, non una»* e resta vero come **descrizione del
> risultato** — una colonna riempita non fa comparire niente nel grafo. Ma la
> conclusione operativa era sbagliata: non sono due metà della stessa cosa, sono
> **due cose diverse**. D-1 dice *chi è il padre* sul documento (il campo
> «Origine», l'azione «apri sorgente»); D-2 lo fa *comparire nel grafo*.
> ⭐ Il ponte era la sorgente giusta e nessuno l'aveva guardato: si era guardata
> la colonna che il §5 aveva messo sotto accusa.

### 10.3 ⚠️ E una mina l'ho piantata io — vale la pena scriverla

Il primo append ai due CSV è stato fatto con `csv.writer` di Python, che ha
`lineterminator='\r\n'` **di default**. Le due righe nuove sono nate con il
ritorno carrello, in due file che il resto lo scrive con `\n`.

⛔ **Non se ne sarebbe accorto nessuno guardando il diff**, e il migrate sarebbe
morto sul `COPY` del mirror con *«"ritorno carrello" non quotato trovato nei
dati»* — su un file di 800 righe, indicando la riga giusta ma non la causa.
L'ha trovata la verifica del §9.6 punto 1, rieseguendo l'upsert su **tutte** le
righe.

⭐ È la conferma che quella verifica non è cerimoniale: ha trovato un difetto
introdotto **in questa stessa sessione**, non un debito storico.

### 10.4 Cosa è stato verificato, e come

Tutto in **transazioni annullate**: nessun `liquibase update`, nessun `make db-*`.

| # | Verifica | Esito |
| --- | --- | --- |
| 1 | `guardrail_sql_letterali.py` — 3022 changelog | ✅ nessun letterale aperto |
| 2 | `guardrail_run_on_change.py` | ✅ nessun `runOnChange: true` in `20_code` |
| 3 | `guardrail_pgtap_preambolo.py` — 518 file | ✅ invarianti rispettate; il debito `throws_ok` resta **131 su 131** (il file nuovo passa sempre lo SQLSTATE) |
| 4 | ⭐ I sei blocchi `changes[].sql.sql` **estratti dagli YAML** ed eseguiti **interi**, `ON_ERROR_STOP=1`, in transazione annullata | ✅ 4 `CREATE FUNCTION` + 4 `COMMENT` + 2 `CREATE VIEW`, poi `ROLLBACK` |
| 5 | ⭐ DDL **+ il pgTAP nuovo** nella **stessa** transazione annullata | ✅ **17 su 17** |
| 6 | ⭐ Mirror CSV: upsert rifatto su **tutte** le righe dei due file (800 + 797) in transazione annullata | ✅ dopo la correzione del §10.3 |
| 7 | ⭐ Non-regressione: i 5 pgTAP che già toccano questa madre, eseguiti **prima e dopo** il DDL | ✅ 0 rossi in entrambi i casi — e le asserzioni girano davvero (27 e 7, non zero per fixture morta) |

⚠️ **Cosa questa verifica NON prova**, ed è la parte da non dimenticare: girando
**prima** del migrate, il psql si connette come **owner**, quindi la **RLS non è
stata esercitata**. Un verde qui non è un verde sotto le policy. Dopo l'apply va
rilanciato dal runner vero:

```bash
scripts/testpgtap.sh db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql
scripts/pgtap-baseline.sh vendite
```

### 10.5 ⚠️ Il debito verso il frontend, e QUANDO diventa rosso

`scripts/check_i18n_keys.py` oggi passa, e non è una buona notizia: il controllo 4
legge le `reason_key` dalla **doc auto-gen** (`docs/it/dbzero/`), che riflette
l'oggetto **vivo**. Finché il changeSet non è applicato e la doc non è
rigenerata, la chiave nuova lì non c'è e il cancello non la cerca.

> **Diventa rosso al primo migrate + rigenerazione della doc.** Quindi la riga
> nei locales va chiesta **adesso**, non quando la build si accende.

| Chiave | it | en |
| --- | --- | --- |
| `vendite.ddt.azione_reason.iva_mancante` | *(da scrivere — FE)* | *(da scrivere — FE)* |

Il senso da rendere: **la riga ha un prezzo ma nessuna aliquota IVA, e il
documento non si emette finché non la si sceglie.** Sta accanto alle quattro
sorelle che la stessa funzione già emette (`causale_mancante`,
`prezzo_non_risolvibile`, `componenti_prezzo_pendente`,
`componenti_non_valorizzati`).

### 10.6 ⭐ Un test che vale più degli altri, e perché sta scritto qui

Il **16)** del file pgTAP: *causale **non** fatturabile, riga **con** prezzo e
senza aliquota → l'emissione **rifiuta lo stesso**.*

Presidia la sola decisione discutibile della Fase C: il punto 3-bis sta **fuori**
dal ramo `IF COALESCE(v_fatturabile, false)`, dove invece stanno i punti 3, 5 e 6.
Metterlo dentro è la cosa che **sembra ordinata**, e sarebbe sbagliata:
`vw_ddt_righe_iva_base` la causale non la guarda affatto, quindi la riga
entrerebbe comunque nel riepilogo con l'imposta a zero.

> ⛔ Senza quel test, il giorno in cui qualcuno «uniforma» i sei punti nessuno se
> ne accorge. È il gemello del 6) e del 7), che presidiano le altre due decisioni
> di **non** fare.

⚠️ E un test l'ho scritto sbagliato io, prima: toglieva il solo prezzo lasciando
la causale VENDITA, e prendeva un rosso che *sembrava* del punto 3-bis ed era del
punto 3. Il «DDT di solo trasporto» sono **due** condizioni — causale non
fatturabile **e** righe senza prezzo — non una. Sta scritto nel corpo del test.

### 10.7 Cosa resta

| # | Cosa | Chi |
| --- | --- | --- |
| 1 | ⛔ **L'apply** — `liquibase update`, con l'autorizzazione a voce | Tid |
| 2 | Ri-lanciare il pgTAP **dal runner** (sotto RLS) + `pgtap-baseline.sh vendite` | dopo l'apply |
| 3 | Le due righe di testo per `vendite.ddt.azione_reason.iva_mancante` | **FE**, §10.5 |
| 4 | La verifica del §9.4.1: due figli in avanti di tipo diverso, ranghi diversi | col cantiere lineage |
| 5 | Le voci aperte del §9.5 (`vw_ddt_righe_iva_base` e il `COALESCE`, i componenti BoM, il debito `codice_interno` di `causali_trasporto`) | cantieri loro |
| 6 | Il commit | Tid — nessun commit autonomo |

---

## 11. 🔴 La regressione del 2026-08-28, e cosa insegna

> **Trovata da Tid subito dopo l'apply**, lanciando
> `scripts/testpgtap.sh db/pgtap/vendite/test-documento-lineage-v1.sql`:
>
> ```
> # Failed test 13: "archi: arco sempre in A..H,R,N,S"
> #         have: 7   want: 0
> ```

### 11.1 Cos'era

L'arco **T** del §9.4.1 ha aggiunto una lettera a un **vocabolario chiuso** che
un pgTAP enumera:

```sql
WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R','N','S')
```

Sette archi T generati, sette righe fuori elenco. ⭐ **Il test ha fatto
esattamente il suo mestiere**: non è una fixture stantia, è un **cricchetto** —
ogni arco nuovo lo rompe **apposta**, per costringere chi lo aggiunge a
dichiararlo.

### 11.2 ⛔ Perché non l'avevo vista, ed è una ricaduta

Il §9.2 prescriveva di fare `grep` sui pgTAP che toccano l'oggetto modificato, e
l'ho fatto — **per la funzione** (`fn_genera_ddt_riconsegna`, cinque file, tutti
verdi prima e dopo). Non l'ho fatto **per le due viste**, che pure erano nello
stesso lavoro.

```bash
grep -rl "vw_documento_lineage_archi" db/pgtap/   # l'avrebbe trovato in un secondo
```

> **Il perimetro del grep è OGNI oggetto toccato dal changeSet, non il più
> importante.** È la stessa regola che avevo applicato bene una riga sopra, su
> un oggetto diverso.

⚠️ E la verifica pre-apply del §10.4 non poteva vederlo: girava i **cinque file
che conoscevo**, non la suite.

### 11.3 ✅ Come è stato chiuso — e perché non basta allargare l'elenco

`db/pgtap/vendite/test-documento-lineage-v1.sql`, plan da 38 a **39**:

1. **elenco allargato** a `('A'…'S','T')`, con accanto il perché la lettera è
   entrata e la data;
2. ⭐ **asserzione nuova (39)**, ed è la parte che conta:

   ```sql
   WHERE a.arco = 'T'
     AND (a.from_tipo_id <> <RESO_VENDITA>
       OR a.to_tipo_id   <> <DDT_VENDITA>
       OR a.is_ramo_inverso)
   ```

   cioè: T parte da un reso, arriva a un DDT, e **non è un ramo di ritorno**.

> ⛔ **Allargare e basta trasforma un cricchetto in una formalità**, e il valore
> successivo passerebbe senza che nessuno lo guardi. Chi allarga l'elenco
> aggiunge anche l'asserzione che dice **cosa significa** il valore nuovo — come
> il file già fa per R (`punta sempre a un RESO_VENDITA`), per N (`sta fra due
> FATTURA`, `non è mai un cappio`) e per S.

⚠️ **E la 39 non è coperta dalla 29.** La 29 verifica che `is_ramo_inverso`
coincida con `arco IN ('R','N')` — confronta la **proprietà con l'elenco**, e se
un domani cambiassero **insieme** resterebbe verde. La 39 àncora T
all'*avanzamento* in modo indipendente: se finisse fra i rami inversi, il reso
tornerebbe a essere una foglia e la frontiera cambierebbe in ogni lista, **senza
errori e senza log**.

### 11.4 ⭐ I gemelli: cercati, e non ce n'erano

Prima di allargare, chi altro enumera quel vocabolario (verificato il
2026-08-28 su `db/`, `backend/`, `frontend/src`):

| Consumatore | Cosa legge | Esito |
| --- | --- | --- |
| `LineagePassaggiContenuto.vue` | `is_ramo_inverso` | ✅ una **proprietà derivata**, non la lettera |
| `fn_documento_lineage` | `a.is_ramo_inverso` dalla vista | ✅ dal 2026-08-20 non ricalcola più `arco = 'R'` |
| `vw_documento_lineage` (summary) | `is_ramo_inverso` | ✅ idem |
| `backend/apps/vendite/types.py` | `arco: str` | ✅ un tipo, non un elenco |
| `test-documento-lineage-v1.sql` | l'elenco delle lettere | 🔴 **l'unico**, ed è quello che si è rotto |

⭐ **La forma giusta è quella del frontend**: un consumatore che legge la
**lettera** è un secondo elenco da tenere allineato a mano. Il progetto ci era
già arrivato — la rev 2026-08-20 della vista dice per esteso *«prima la lettera
R era ripetuta in tre posti e il terzo dimenticato non avrebbe rotto niente di
visibile»* — e infatti l'unico punto rimasto a enumerare è il **presidio**, che
è il posto giusto per farlo.

### 11.5 Lo stato dopo la correzione

| Verifica | Esito |
| --- | --- |
| `testpgtap.sh test-documento-lineage-v1.sql` | ✅ **39/39** |
| `testpgtap.sh test-fn-genera-ddt-riconsegna-eredita-v1.sql` — dal runner vero, **sotto RLS** | ✅ **17/17** (chiude il punto 2 del §10.7) |
| `pgtap-baseline.sh vendite` — 237 file | ✅ **5 rossi, tutti già noti in baseline: nessuna regressione** |

⚠️ **I sei changeSet risultano applicati** (`databasechangelog`, 2026-08-28
12:21). Il §10 è stato scritto prima dell'apply e lo dice ancora al futuro:
resta com'è, come storia del momento in cui i file sono stati consegnati.

Del §10.7 restano quindi: la riga i18n del **frontend** (§10.5), la verifica
del §9.4.1 col cantiere lineage, le voci aperte del §9.5 e il commit.

---

## 12. 📍 Stato al 2026-08-28 sera — cosa è chiuso e a chi passa

### 12.1 ✅ Fatto

| | |
| --- | --- |
| **Migrazione** | ✅ **applicata** — i sei changeSet `20260828-01…06` sono in `databasechangelog`, 12:21 |
| **Doc auto-gen** | ✅ **rigenerata** — verificato: la doc di `fn_genera_ddt_riconsegna` porta la rev Fase A, `vw_documento_lineage_archi` l'arco `'T'`, `fn_check_ddt_emittibile` la `reason_key` nuova |
| **Regressioni** | ✅ **nessuna** — `pgtap-baseline.sh vendite`, 237 file: 5 rossi, **tutti già noti in baseline** |
| **Il test nuovo, sotto RLS** | ✅ **17/17** dal runner vero (`testpgtap.sh`), non più solo da owner |
| **Il presidio del lineage** | ✅ **39/39** dopo la correzione del §11 |
| **Bersagli non dichiarati** | ✅ **0** (`dbops.vw_bersagli_non_dichiarati`) |
| **Codice errore a catalogo** | ✅ `E_DDT_RIGA_IVA_MANCANTE` → `CONFLITTO_STATO`, messaggio e `causa`/`soluzione` in `config.messaggi_errore` |

### 12.2 ✅ La verifica del §9.4.1 è chiusa — e sulla struttura, non sui dati

Restava da guardare il caso dei **due figli in avanti** di un reso in parte
accreditato e in parte ri-consegnato. Misurato il 2026-08-28 su
`vw_documento_lineage_nodi`:

| tipo | `pipeline_rank` |
| --- | ---: |
| `RESO_VENDITA` | 0 |
| `DDT_VENDITA` | **3** |
| `FATTURA` | **5** |

I due figli **non possono finire allo stesso livello**, quindi il tie-break
lessicografico su due uid — il pericolo che la nota dell'arco S segnalava — qui
non entra mai in gioco. ✅ La verifica è chiusa.

> ⭐ **E va chiusa così, non con l'altro numero.** Oggi **nessun reso ha
> entrambi i figli** (zero righe con archi `S` e `T` insieme). Quello è un
> **fatto datato e non prova niente**: zero occorrenze non significa che il caso
> non esiste, significa che non c'è ancora un controesempio. A rispondere è il
> `pipeline_rank`, che è **struttura** — cioè il progetto, scritto.

### 12.3 ⛔ NO: la parte DB non è finita, e non passa tutto al frontend

Ci sono **tre** destinatari, non uno.

#### 🔴 FRONTEND — una riga, e blocca la CI *adesso*

`scripts/check_i18n_keys.py` è **rosso**, exit **1** (verificato dopo la
rigenerazione della doc auto-gen — prima taceva, ed è esattamente il momento che
il §10.5 aveva previsto):

```
[X] 1 CHIAVI EMESSE DAL DB e assenti dai locales
    vendite.ddt.azione_reason.iva_mancante
```

Serve la voce in `frontend/src/locales/it.json` **e** `en.json`. Senso da
rendere: *la riga ha un prezzo ma nessuna aliquota IVA, e il documento non si
emette finché non la si sceglie.* Sta accanto alle quattro sorelle che la stessa
funzione già emette.

#### 🟠 BACKEND — una rigenerazione, e non è opzionale

⚠️ **Questo non era nel piano, ed è emerso solo dopo l'apply.**
`E_DDT_RIGA_IVA_MANCANTE` **non è** in
`backend/apps/core/services/error_policies_generated.py` (verificato: 0
occorrenze su 782 codici). Quel file è **generato**, non si edita a mano:

```bash
cd backend && ./manage.py genera_error_policies
```

Senza, il backend non sa mappare il codice a **HTTP 409** + `show_error_banner`
— che la classe `CONFLITTO_STATO` in `error_policies.py` già definisce, ma solo
per i codici che il file generato conosce. Ed è il **terzo lato** del presidio:
il cancello `apps/core/tests/test_error_codes_db_policy_guardrail.py` confronta
il censimento del DB (`dbops.vw_codici_errore_da_dichiarare`, dove il codice
**c'è**, portato da `fn_check_ddt_emittibile` e dal guard) contro le policy del
backend.

⚠️ **Non l'ho potuto eseguire da qui**: il server DB non ha l'ambiente Django
(`.env.systemd` assente). Va lanciato dal server backend, e il cancello va
riguardato lì.

> ⭐ **La lezione, e vale oltre questo cantiere**: un codice errore nuovo ha
> **tre** sedi, non due — il catalogo DB (fatto), il file generato del backend
> (da fare), i locales del frontend (da fare). Il piano ne aveva previste due.

#### 🟡 DATABASE — resta la doc MANUALE, ed è perimetro nostro

La doc **auto-gen** è a posto perché si rigenera. La doc **manuale** no: si
scrive a mano, è la sede della documentazione concettuale
(`AGENTS.md` § Regole Documentazione), e i cinque oggetti toccati ce l'hanno
tutti — **ora stantia in modo sostanziale**, non cosmetico:

| File | Cosa dice oggi, e non è più vero |
| --- | --- |
| `script/manual/fn_check_ddt_emittibile.md` | ⛔ una **tabella numerata dei 5 motivi**: ora sono **6**, e il nuovo sta fra il 3 e il 4 — cioè cambia anche la numerazione di quelli dopo |
| `vendite/manual/fn_genera_ddt_riconsegna.md` | ⛔ *«crea la `ddt_righe` (copia articolo/UoM/qta)»* — ora copia anche prezzo/sconto/aliquota, eredita sette colonne di testata e fa cascadere gli indirizzi. E il passo 2 descrive la sorgente **senza** il ramo `RESO_VENDITA` |
| `vendite/manual/trgfn_ddt_guard_causale_emissione.md` | i motivi sollevati sono tre, non due |
| `vendite/manual/vw_documento_lineage_archi.md` | l'elenco degli archi non ha `T` |
| `vendite/manual/vw_ddt_lista.md` | il join alla sorgente è ora qualificato |

⚠️ **Non è un dettaglio di forma.** La doc manuale è ciò che
[AGENTS.md](.codex/AGENTS.md) indica come da leggere *prima di strutturare una
soluzione*: una tabella dei motivi ferma a cinque manderà il prossimo a
cercare un sesto motivo che «non c'è».

### 12.4 In una riga

> **DB: manca la doc manuale (5 file). BE: una rigenerazione. FE: una chiave.**
> Le tre cose sono indipendenti e si possono fare in parallelo; la sola che
> **blocca la CI adesso** è quella del frontend.

E resta, come sempre, il **commit** — che non è stato fatto.

➡️ **BE e FE sono stati chiusi il 2026-08-28 pomeriggio: §13.** Lì c'è anche
ciò che questa conta non aveva — il lato BE era di **due** pezzi, non di uno —
e due cose che tornano al DB.


---

## 13. ✅ BE e FE chiusi — 2026-08-28 pomeriggio

> **Chi**: ramo `dev/backend-tid`, dopo il merge #1416 che ha portato in `main`
> i sei changeSet. Il §12.3 assegnava tre destinatari; qui si chiudono i due che
> non sono il DB — e si scopre che uno dei due era di **due** pezzi.

### 13.1 ⛔ Il lato BE non era «una rigenerazione»: erano due file

Il §12.3 chiedeva `manage.py genera_error_policies` e si fermava lì. **Non
basta**, e il motivo è che quel comando *accende un cancello che oggi tace*:

* `error_policies_generated.py` mette il codice in `CLASSE_PER_CODICE`;
* `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`
  (`apps/core/tests/services/test_error_policies_classi.py`) confronta quel
  dizionario con `USER_MESSAGE_FALLBACK` e **fallisce** per ogni codice vivo
  che non abbia la sua frase in `error_messages_fallback.py`.

Finché il codice non è nel file generato il test non lo cerca. Rigenerare senza
scrivere il ripiego avrebbe quindi consegnato un ramo **rosso**, e rosso su un
test che prima del proprio intervento era verde: la forma peggiore, perché
sembra una regressione altrui.

> ⭐ **La lezione del §12.3 era giusta e va allungata di uno.** Un codice errore
> nuovo ha **quattro** sedi, non tre: il catalogo DB, il file **generato** del
> backend, il **ripiego** del backend, i locales del frontend. La quarta non è
> una dimenticanza di chi ha scritto il brief — è che le prime due si vedono da
> un `--check`, e la terza si vede solo dal **test**, cioè dopo aver fatto la
> seconda.
>
> ⚠️ Il ripiego va **senza `%s`**: si mostra proprio quando gli argomenti non
> arrivano, e un segnaposto finirebbe a video in chiaro
> (`test_i_messaggi_di_ripiego_non_hanno_segnaposto`).

### 13.2 Cosa è stato scritto

| Lato | File | Cosa |
| --- | --- | --- |
| **BE** | `apps/core/services/error_policies_generated.py` | rigenerato: `E_DDT_RIGA_IVA_MANCANTE` → `CONFLITTO_STATO` |
| **BE** | `apps/core/services/error_messages_fallback.py` | la frase di ripiego, argument-free |
| **FE** | `src/locales/it.json` · `en.json` | `vendite.ddt.azione_reason.iva_mancante`, inserita **fra `prezzo_non_risolvibile` e `componenti_prezzo_pendente`** — lo stesso posto che il motivo ha nella funzione, fra il 3 e il 4 |
| **doc** | `docs/it/dev/api.md` · `catalogo-building-block-backend.md` | il conteggio delle voci del file generato era fermo a **689 (79 ritirate)**, ora **800 (88)** — era già stantio prima di questo cantiere |

⭐ **Il testo dei due locales dice anche la via d'uscita**, non solo il divieto:
*«scegli l'aliquota, oppure togli il prezzo se la merce non si valorizza»*. È la
`soluzione` che il catalogo già scriveva, e senza di essa il motivo lascia
l'operatore davanti a una riga che non sa come sbloccare — il DDT di solo
trasporto è una risposta legittima, non un ripiego.

### 13.3 La verifica prima di dire che è finita

| # | Cosa | Esito |
| --- | --- | --- |
| 1 | **Il DB non è avanti rispetto a git** — la condizione che vieterebbe di rigenerare: confrontato il CSV in git col file generato **prima** di toccare niente | ✅ 744 codici a catalogo, **uno solo** assente: quello nuovo |
| 2 | ⭐ **Il diff della rigenerazione**: una riga aggiunta, **zero classi spostate** — una classe che si muove cambia lo status HTTP di una risposta esistente | ✅ +1 voce, +1 sul conteggio in testata, nient'altro |
| 3 | `genera_error_policies --check` | ✅ *«allineato al catalogo»* |
| 4 | `scripts/check_i18n_keys.py` | ✅ exit **0**, *«tutto pulito»* — era exit 1 |
| 5 | I tre cancelli dei codici errore (`test_error_codes_db_policy_guardrail`, `..._declared_guardrail`, `test_error_policies_divergenza_db`) **con `ZEROERP_TEST_DB_E2E=1`**, cioè contro il DB vero | ✅ 9/9 |
| 6 | `test_error_policies_classi` — dove vive il cancello del ripiego | ✅ 17/17 |
| 7 | Non-regressione: `apps.core` + `apps.vendite` | ✅ **2587 test**, 0 rossi |
| 8 | `vite build` | ✅ verde |

⛔ **Il punto 1 non è cerimoniale**: rigenerare mentre il DB locale è avanti
rispetto a git aggancia il modulo BE a un changeSet non mergiato, e in CI il
cancello diventa rosso **al contrario** — la CI ricostruisce il DB dal changelog
e quei codici non li trova. La condizione va **misurata ogni volta**, non
ereditata da un handoff: qui i sei changeSet erano in `HEAD` (merge #1416,
verificato con `git merge-base --is-ancestor`).

### 13.4 ✅ Cosa NON serviva — verificato, non assunto

Tre cose che sembravano lavoro e non lo erano. Le scrivo perché il prossimo che
legge il §12.3 non le rifaccia:

* **L'arco `T` non chiede niente al frontend.** Il FE non mappa le lettere degli
  archi: decide per **direzione** (`is_ramo_inverso`, calcolato nella vista) ed
  etichetta i **nodi** per tipo. `vendite.lineage.tipo_reso_vendita` e
  `tipo_ddt_vendita` esistono entrambe dal loro cantiere. Il reso comparirà nella
  barra collegamenti del DDT di ri-consegna da sé.
* **La sorgente `RESO_VENDITA` sul DDT non chiede niente al backend.** La colonna
  `ordine_origine_numero` di `vw_ddt_lista` resta vuota, ed è **corretto**: il
  join a `vendite.ordini` è ora qualificato su `ORDINE_VENDITA` (changeSet 06).
  Il drawer sa già aprire un `RESO_VENDITA` (`DOCUMENTO_DRAWER_TIPI`).
* **Nessun override di UI per il codice nuovo.** `CONFLITTO_STATO` dà già 409 +
  banner, e `test_nessun_override_ripete_il_default_della_classe` **vieta** un
  override che ripeta il default.

### 13.5 ➡️ Due cose che tornano al DB

**1 · Le cinque doc manuali del §12.3 non sono nel push.** Verificato sul commit
`05c61d1b1`: tocca `docs/it/dbzero/**/funzioni/` e `**/views/` — cioè la doc
**auto-gen** — e mai `**/manual/`. Restano stantie tutte e cinque, come il §12.3
le elenca.

**2 · ⚠️ E ce n'è una sesta che il §12.3 non elenca: il `COMMENT ON VIEW` di
`vw_documento_lineage_archi`.** Il changeSet `20260828-05` non contiene nessuno
`COMMENT`, quindi la descrizione della vista — quella che finisce in cima alla
doc auto-gen — dice ancora:

> *«grafo archi normalizzato A-H + R e N (rami di ritorno) + S»*

**Senza `T`.** È la stessa classe di difetto della tabella dei motivi ferma a
cinque, e in un posto che pesa di più: il §11 racconta che quel vocabolario è
presidiato **come chiuso** da un pgTAP: il prossimo che allarga l'elenco legge la
descrizione per sapere quali lettere esistono, e ne trova una in meno di quante
il `WHERE` ne produce.

### 13.6 Cosa resta

| # | Cosa | Chi |
| --- | --- | --- |
| 1 | La doc manuale dei 5 oggetti **+ il `COMMENT` della vista** (§13.5) | **DB** |
| 2 | Il collaudo in-app della ri-consegna: generare un reso da DDT, generarne la ri-consegna, e guardare che testata, indirizzi e valore di riga **ci siano** — è la prova 9 che ha aperto questo cantiere | **Tid** |
| 3 | Il commit | **Tid** — nessun commit autonomo |

⚠️ **Il punto 2 non è una formalità**, ed è la stessa lezione del cantiere
gemello «Rendi definitive»: qui è stato provato il **percorso** (17 asserzioni
pgTAP sotto RLS, i cancelli dei codici, la chiave che risolve) ma non
l'**esito a video** — che il drawer del DDT nuovo mostri davvero la causale, gli
indirizzi e il prezzo. La classe di difetto che nessun test prende — il DB
scrive in un modo e l'interfaccia legge in un altro — si vede solo guardando lo
schermo.
