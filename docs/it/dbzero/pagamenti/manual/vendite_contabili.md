## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile**
per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per
centro riscossione e data contabile, con eventuale dettaglio del canale
(`ente_incasso`) e stato operativo della testata.

---

### Campi chiave (semantica)

* `codice`: identificativo testata contabile. ⭐ **Dal 2026-09-15 è un numero
  di registro** — `DIS-<SIGLA>-<ANNO>-<7 cifre>` — non più un'etichetta da
  DEFAULT (`VC_…`): vedi la sezione «Il codice viene dal registro» qui sotto.
* `emittente_soggetto_ruolo_id` (`NOT NULL`, dal 2026-09-15): **di chi è** la
  distinta. È l'input del numeratore e la colonna su cui passa la RLS.
* `registro_id` / `anno`: il sezionale e l'anno su cui il codice è stato
  numerato, scritti insieme al codice; `NULL` sul pregresso `VC_…`.
* `centro_riscossione_id`: riferimento principale al centro riscossione.
* `ente_incasso_id`: ente/canale specifico (opzionale).
* `stato_id`: stato della testata contabile.
* `data_contabile`: data contabile di riferimento.
* `data_conferma` / `user_conferma`: tracciamento conferma testata. ⭐ **Dal
  2026-08-22 le scrive `pagamenti.fn_posta_contabile`**: prima esistevano e
  restavano vuote. La conferma è l'atto di **registrare**, e il `COALESCE` tiene
  la prima volta che è successo.

---

### Regole principali

* `codice` univoco: l'identità della distinta è la **stringa nuda**, come per la
  commessa (sigla e anno stanno dentro il codice).
* Ogni testata e` collegata a un solo centro riscossione.
* Se `ente_incasso_id` e` valorizzato, deve essere coerente con
  `centro_riscossione_id` della testata (guard applicativa).
* ⚠️ Una distinta **nata da una sistemazione** non si collega a un lotto di
  fatturazione. ⭐ Dal 2026-08-22 la regola non vive più qui: girato il verso del
  legame (D15-e), **la contabile non sa più di essere nata da un atto** — lo sa
  l'atto. Il presidio è rimasto **uno solo**, e sulla porta che conta:
  `trgfn_vendite_contabili_lotti_guard_sistemazione`. E la regola *«una
  compensazione sta sul centro dedicato»* è passata a
  [trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati),
  dove il dato che la rende decidibile esiste davvero.
* `stato_id` punta al lookup `pagamenti.vendite_contabili_stati`.

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_contabili
WHERE data_contabile = current_date;
```

---

### 🎯 Che cos'è davvero: una **distinta**, non un movimento bancario

L'evidenza è nelle colonne: qui non c'è **nessun importo** e **nessun riferimento
bancario** (CRO, TRN, numero operazione). Il riferimento della banca sta **sulla
riga**. Questa testata non modella *un* bonifico: modella il **documento che
raccoglie N importi arrivati insieme** e li prepara.

⭐ È ciò che rende sensata la registrazione «per testata»: le righe dubbie restano
`SOSPESA` e non si registrano, quindi *«registra la distinta»* significa
naturalmente **registra tutto il pronto, lascia lì il resto**. Con una testata per
bonifico non ci sarebbe nessun «resto» da lasciare.

### `origine` — il cardine da cui pendono le altre regole (2026-08-21)

| Valore | Che cos'è | Chi la crea |
| --- | --- | --- |
| `MANUALE` | il **lotto di lavoro di un operatore** | una persona, digitando |
| `AUTOMATICA` | il **file** arrivato dal canale | l'import *(non ancora costruito)* |
| `GENERATA` | la produce **il sistema** | il giro dei fondi fattura, le compensazioni |

⭐ **Il terzo valore è nato da una misura**, non da una simmetria: l'unico creatore
di distinte esistente è il giro dei fondi, che **non è né l'uno né l'altro** — non
la digita una persona e non arriva da un file. Con due soli valori, il 100% delle
distinte di oggi avrebbe portato una parola falsa.

Tre regole pendono da questa colonna:

* **`importo_dichiarato`** è obbligatorio su `AUTOMATICA`, facoltativo su
  `MANUALE`, **vietato** su `GENERATA` *(due CHECK)*;
* il **raggruppamento per operatore** vale solo su `MANUALE`;
* la **riapertura** `VALIDATA → BOZZA` vale solo su `MANUALE`.

### `importo_dichiarato` — non è il totale delle righe

È **ciò che la sorgente dichiara di aver mandato**. Sull'automatica è
l'**autocontrollo dell'import**: se abbiamo letto male il file la somma non torna e
non nasce niente. Sul manuale è il classico controllo da inserimento dati, e
**scatta al passaggio a `VALIDATA`** — cioè al gesto «ho finito», mentre
l'operatore è ancora nel flusso.

⚠️ La quadratura conta **tutte** le righe attive, `SCARTATA` comprese: quel denaro
è arrivato comunque. Dice *«abbiamo letto tutto ciò che c'era»*, non *«tutto è
nostro»*.

### ⭐ La distinta manuale è **per operatore**, e con ciò il lock sparisce

Il riuso della testata, sul ramo manuale, comprende **chi sta lavorando**. Il
raggruppamento «giornata + canale» non ha un referente nel mondo — nessun
documento reale corrisponde a *«tutti gli incassi banca di lunedì digitati a
mano»* — mentre il lotto di lavoro di una persona ce l'ha.

⭐ Era stata chiesta una funzione di **blocco** perché due operatori non si
pestassero i piedi: con questo raggruppamento **la contesa non esiste**, quindi
non servono colonne di blocco, scadenze, sblocco d'emergenza. *Il presidio più
economico è quello che il modello rende inutile.*

### `stato_id` è obbligatorio, ed è un cancello

Da quando lo stato divide il **brogliaccio** dal **registro** — prima della
conferma la distinta si annulla, dopo no — una testata *senza* stato non sarebbe
né l'uno né l'altro, e passerebbe i filtri di entrambi. Dal 2026-08-21 la colonna
è `NOT NULL` con default `BOZZA`.

### 🔢 Il codice viene dal registro, e la distinta sa di chi è (2026-09-15)

Fino al 2026-09-15 il `codice` nasceva da un **DEFAULT di colonna**
(`VC_<timestamp>_<md5>`) e, sulla strada delle sistemazioni, da una seconda
composizione (`SIS_<atto>_<timestamp>`): un'etichetta unica, non un numero.
Da quel giorno la distinta entra nella **numerazione standard** — il meccanismo
è quello della [guida](/guide/numerazione-documenti-e-codici): famiglia
`DISTINTA` in `vendite.famiglie_documento`, **un registro per emittente**
(`DIS-<sr>`, prefisso `DIS-`, 7 cifre, reset annuale, anno nel numero), e il
trigger `trg_vendite_contabili_a10_gen_codice_ins` che chiama
`vendite.fn_assegna_numero_documento` **alla creazione**, come ordine e commessa.

| Cosa | Com'è |
| --- | --- |
| forma | `DIS-<SIGLA>-<ANNO>-<NNNNNNN>`, es. `DIS-ACME-2026-0000001` — la sigla è `emittenti_fiscali.codice`, passata come corpo (come la commessa) |
| identità | la stringa nuda: `uq_vendite_contabili_codice` resta com'è; con un registro per emittente la sigla è ciò che distingue due `…-2026-0000001` |
| momento | `BEFORE INSERT`: il codice è la maniglia con cui si lavora la distinta da subito; i buchi da bozza annullata sono accettati, come per l'ordine |
| anno | da `data_contabile`: una distinta datata 31/12 e inserita il 2/1 è dell'anno vecchio. `presidia_data_documento = false`: la distinta di ieri inserita oggi è un caso normale |
| codice fornito | rispettato (no-op), per le fixture. ⛔ Non è una porta per le madri: `test-distinta-numerazione-registro-v1` (test 12/13) pretende che nessuna funzione viva passi `codice` |
| pregresso | le righe `VC_…` restano così, con `registro_id` e `anno` `NULL` (guida §6.6): forma diversa, non collidono |

⭐ **Un registro appartiene a un emittente, e la distinta era l'unico documento
numerabile che non dichiarava il proprio.** Da qui le tre colonne: l'emittente
(l'input), `registro_id` e `anno` (l'output). L'emittente si risolve in **una
sede sola**, `pagamenti.fn_get_emittente_distinta`, applicata dal trigger
`trg_vendite_contabili_a10_emittente_ins_upd` a ogni INSERT e chiamata dalla
madre `fn_get_or_create_vendite_contabile` per la **chiave di riuso** (che ora
comprende l'emittente):

| Livello | Se… | Allora |
| --- | --- | --- |
| 0 | l'emittente dato non è un emittente fiscale | `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (TECNICO) |
| 1 | è dato; se c'è anche il canale, deve essere il suo | altrimenti `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` (campo `ente_incasso_id`) |
| 2 | c'è solo il canale | il suo emittente (canale → conto → soggetto-ruolo → emittente); un canale che non porta a un emittente è `E_CONFIG_MANCANTE` |
| 3 | c'è un operatore in sessione | `script.fn_resolve_emittente_for_user` (la riserva è di chi agisce; legge prima l'emittente attivo) |
| 4 | niente | `E_CONTABILE_EMITTENTE_OBBLIGATORIO` (campo `emittente_fiscale_id`): il super admin sceglie nel form |

⛔ **Nessun «default dell'installazione»**: dichiarare di un emittente il denaro
di un altro è l'attribuzione che la numerazione per emittente esiste per
impedire. La madre `fn_get_or_create_vendite_contabile` ha un parametro in coda
`p_emittente_fiscale_id` (la PK, ciò che backend e frontend conoscono) e, se
manca, deriva l'emittente dal **lotto** — la distinta di un fondo è
dell'emittente del lotto, chiunque lanci il giro; un lotto invisibile è TECNICO,
non si cade sulla sessione. La sistemazione lo prende dall'**atto**, la
correzione lo **copia** dalla distinta corretta (stesso registro, progressivo
successivo). Su `UPDATE … SET emittente = NULL` il trigger **non** ri-riempie
dalla sessione: parla il vincolo.

⚠️ **L'ordine dei `BEFORE ROW` regge sul nome**: `a10_emittente` (risolve) <
`a10_gen_codice` (numera) < `a10_guard_emittente_scope` (giudica). Chi rinomina
uno dei tre sposta la risoluzione dopo chi la usa.

⚠️ **E la FK sul registro ha un effetto nell'altro verso** (2026-09-18): una
distinta numerata **blocca la disattivazione del suo registro** `DIS-<sr>`. Il
guard lo monta l'automazione ATTIVO da sola sulla FK, e — non avendo la distinta
una colonna `attivo` ma uno `stato_id` — blocca sull'**esistenza**: una distinta
annullata pesa come una confermata, e una distinta non si cancella. È l'ottavo
guard su `registri_fatturazione` e il primo fuori da `vendite`;
`script.fn_check_registro_disattivabile` lo anticipa col motivo `HA_DISTINTE`,
così il cestino del registro si spegne prima del click (pgTAP
`script/test-fn-check-registro-disattivabile-v1`, test 6-9). Il perché e il
meccanismo stanno nella scheda del
[registro](/dbzero/vendite/manual/registri_fatturazione), non qui.

Brief: [brief-db-distinta-numerata-sul-registro](/dev/work-done/brief-db-distinta-numerata-sul-registro).

### 🔒 Chi la vede — la RLS del perimetro incassi (2026-08-22, corretta il 2026-09-15)

> ⭐ **Dal 2026-09-15 il perimetro è la colonna `emittente_soggetto_ruolo_id`**
> (`20260915-31`), nella forma di `rls_fatturazione_lotti_ef_whitelist`: il
> ramo «senza canale = di tutti» descritto qui sotto **non esiste più**, né
> sulla testata né sui satelliti (`20260915-32`: righe `20260822-24` e
> manifesto dei lotti `20260910-18`, che portavano lo stesso ramo). Una
> distinta interna è del suo emittente, come il lotto o l'atto da cui nasce;
> le sue righe la seguono per la sola testata, senza bisogno della fattura. Il
> guard di scrittura è in modo `soggetto_ruolo` sulla stessa colonna. Il testo
> del 22-08 resta sotto perché spiega **perché** il perimetro nacque dal conto
> e perché è `FOR ALL`: quelle due ragioni valgono ancora.


Policy `rls_vendite_contabili_perimetro_incasso`, **`FOR ALL`**, gate
`OPERATORE` fail-closed. Il perimetro viene dal **conto di incasso** e non dalla
fattura (**D5**): una distinta è un estratto conto e la fattura non ce l'ha — un
predicato «via fattura» avrebbe reso la coda «da abbinare» invisibile **a
tutti**, che è peggio di visibile a chi non dovrebbe.

```text
vendite_contabili.ente_incasso_id
    → enti_incasso.soggetto_ruolo_conto_bancario_id
        → soggetti_ruoli_conti_bancari.soggetto_ruolo_id
            → emittenti_fiscali → whitelist dell'operatore
```

⭐ **La distinta senza canale (`ente_incasso_id IS NULL`) resta visibile a tutti**
*(⚠️ vero fino al 2026-09-15: vedi il riquadro in testa alla sezione)*,
e la condizione sta **in chiaro nel predicato**, non dentro una funzione: chi
legge la policy deve vedere l'eccezione. Non è generosità, è la **verità del
modello** — le distinte interne (fondo fattura, compensazione) le fabbrica il
sistema e la chiave di riuso non nomina l'emittente, quindi ne raccolgono di
tutti: dichiararle «di qualcuno» sarebbe una bugia, nasconderle a tutti
spegnerebbe la pipeline. ⚠️ Le sue **righe** non ereditano niente: la loro policy
le filtra una per una sulla fattura che portano.

> 🔴 **Perché `FOR ALL` e non `FOR SELECT`** — misurato, non supposto:
> 1. la RLS **nega ciò che nessuna policy permette**: con la sola `FOR SELECT` la
>    tabella diventa **di sola lettura** per l'applicazione;
> 2. **`INSERT ... RETURNING` passa dalla `USING`**: una riga che la `USING` non
>    copre fa fallire l'`INSERT` con *«la nuova riga viola la regola di sicurezza
>    per riga»* — e `fn_get_or_create_vendite_contabile` restituisce l'id proprio
>    con un `RETURNING`.
>
> ⭐ Ne segue una regola che vale oltre questo caso: **ciò che l'applicazione
> scrive e poi rilegge deve essere visibile a chi l'ha scritto, nello stesso
> istante.** Un perimetro che si chiude su una riga appena creata non nasconde:
> **rompe**.

⚠️ `ENABLE` ma **non** `FORCE`, a parità col resto del database — e qui il `FORCE`
non è solo «più avanti»: il risolutore che regge il predicato è `SECURITY
DEFINER` e gira come proprietario, quindi con il `FORCE` rientrerebbe sotto la
policy della tabella che sta leggendo e nascerebbe una **ricorsione**.

⚠️ `zeroerp_batch_fatturazione` ha `BYPASSRLS`, ma dal 2026-09-05 nessun
processo lo usa: ogni giro corre con un utente tecnico per (processo × azienda),
dentro il proprio perimetro — il livello 3 della sede unica risolve anche per lui.

⭐ **La policy nasconde, il trigger rifiuta.** Il guard di scrittura
`trg_vendite_contabili_a10_guard_emittente_scope_ins_upd` (modo `ente_incasso`
fino al 2026-09-15, poi `soggetto_ruolo` sulla colonna emittente)
impedisce di **aprire una distinta sul canale di un altro emittente** e lo
**spiega**; un `WITH CHECK` da solo direbbe «new row violates row-level security
policy», che è vero e inservibile.

---

### I guard che la difendono

| Guard | Impedisce |
| --- | --- |
| `trgfn_vendite_contabili_emittente` *(2026-09-15)* | che una distinta nasca **senza sapere di chi è**, o con un canale di un altro emittente: applica la sede unica `fn_get_emittente_distinta` |
| `trgfn_vendite_contabili_gen_codice` *(2026-09-15)* | non un guard: il **numeratore** sul registro `DISTINTA` dell'emittente |
| `trgfn_vendite_contabili_guard_transizione` | i salti di stato che la matrice non ammette |
| `trgfn_vendite_contabili_guard_chiusura` | di **chiudere** una distinta che ha ancora righe pronte |
| `trgfn_vendite_contabili_guard_validazione` | di validare con un totale che non quadra, e di riaprire una distinta non manuale |
| `trgfn_vendite_contabili_guard_ente_centro` | le incoerenze fra **centro** ed **ente** *(dal 2026-08-22 non guarda più le sistemazioni: la colonna che le nominava non esiste)* |
| `script.trgfn_guard_emittente_scope('soggetto_ruolo','emittente_soggetto_ruolo_id')` | di **scrivere una distinta di un emittente fuori dal proprio perimetro** *(dal 2026-09-15; fino ad allora in modo `ente_incasso` sul canale)* |

---

{% include-markdown "signature-core.md" %}
