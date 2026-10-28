# Brief DB — la riga manuale nasce con la destinazione, e in bozza si elimina

> **Cos'è.** Il seguito del **primo collaudo in-app** del giro incassi (Tid,
> 2026-09-14, caricando la prima contabile). Tre rilievi, e il modello li aveva
> già scritti — era l'interfaccia a dire il contrario:
>
> - **§1 · l'inserimento della riga è «libero»**, mentre la norma è che chi digita
>   un incasso **sa chi ha pagato**: la riga deve nascere già associata al
>   documento, e la riga senza destinazione dev'essere l'**eccezione dichiarata**,
>   con la coda «da abbinare» come recupero;
> - **§2 · una riga di una bozza non si può eliminare**: l'unico gesto offerto è
>   «scarta», che vuol dire un'altra cosa e — sulla manuale — **rompe la
>   quadratura**;
> - **§3 · «il pagamento si scrive con la validazione?»** — no: con la
>   **registrazione**. La risposta è nel modello e va solo resa leggibile.
>
> **Sede.** Le **decisioni di dominio** (D16, D17, D18) stanno qui e sono
> riportate in sintesi nel brief madre
> ([brief-incassi-riconciliazione-rate-promemoria.md](../work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis), che resta la sede unica. Il **piano DB** è qui (§4). Per BE e FE
> qui c'è **solo l'elenco di cosa fare** (§5, §6): il piano lo scrivono loro
> in [brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md).
>
> ✅ **Applicato su dev il 2026-09-14 alle 15:49** (`databasechangelog`:
> `20260914-04`, `-05`, `-06`), pgTAP verdi col runner come applicazione
> (Tid). Il brief era stato scritto la mattina misurando contro il modello vivo
> (doc auto-gen), non contro i dati: `pagamenti` aveva ancora zero righe di
> esercizio. **La parte DB è chiusa**; BE (§5), FE (§6) e il copione (§7)
> sono stati scritti la sera stessa (riquadro sotto). Il seed P-8 è **scritto
> il 15/09** (CSV, prova in transazione annullata: riquadro sotto) e aspetta
> il migrate di Tid; la doc auto-gen, P-9, è entrata con `84f1b3fd7`.
>
> ✅ **BE e FE scritti il 2026-09-14 (sera)** su «procedi» di Tid, e **riletti
> criticamente** la sera stessa (registro §9): il piano sta in §10 col terreno
> misurato sul codice e lo stato per voce in §10.1. La decisione emersa alla
> rilettura (**Q-H**, il PATCH di `importo` e la capienza) è stata **presa il
> 15/09** (strada A, §10.4). La prova in-app (**C-2**) **esce dal brief** e vive
> nel copione di collaudo (riquadro «CHIUSO», residuo 1). Il solo
> prerequisito al team DB, il seed **P-8**, è **scritto il 15/09** (riquadro
> sotto) e aspetta il migrate; P-9 risulta **già fatta** (doc auto-gen in
> `84f1b3fd7` del 14/09, `check_i18n_keys` la legge). Nessun commit.
>
> ✅ **Sviluppo DB scritto il 2026-09-14** (stessa giornata): tre changeSet
> `20260914-04/05/06`, il seed, un pgTAP nuovo da 30 asserzioni, sei pgTAP
> adeguati, sei documenti. Provato con l'**SQL estratto** dagli YAML in
> `BEGIN … ROLLBACK` su dbdev, seed compreso: 30/30 il nuovo, 110/110 i sei
> adeguati, 168 verdi sugli altri diciassette candidati (i soli rossi sono le
> asserzioni RLS di `test-rls-pagamenti-perimetro`, girato da owner nella
> prova: come app non si possono fare finché non è applicato). **L'apply e il
> lancio col runner sono di Tid** — fatti alle 15:49, verdi. Due decisioni
> prese durante lo sviluppo — la porta `DELETE` del giro dei fondi e D18
> confermata — stanno in §4 e §9.
>
> ✅ **P-8 scritto il 2026-09-15** (DB): `meta.nessuna_azione_key` sulle cinque
> righe di `pagamenti/vendite_contabili_stati.csv`, **solo il CSV** — i mirror
> sono due (`20260213-04` e il ri-ancorato `20260821-30`, quello che porta
> tutte le colonne), entrambi `runOnChange` + `ANY` e già risvegliati
> (`RERAN`/`EXECUTED` il 21-08), quindi rileggono il file al prossimo
> migrate. Provato su dbdev in `BEGIN … ROLLBACK` con l'upsert di **tutte**
> le righe (le due specie di mina): `UPDATE 5`, `lock_columns` muto, e la
> colonna che legge `_DISTINTA_SELECT` risponde con le cinque chiavi;
> `check_i18n_keys.py` verde (controllo 4 le trova nei locales `it`/`en`).
> Scheda manuale del catalogo aggiornata (rimanda allo standard `infoKey`).
> **L'apply è di Tid**: fino a lì `stato_info_key` resta `NULL` e la barra è
> muta, non rotta.
>
> **Stato:** ✅ **CHIUSO il 2026-09-15** — riquadro «CHIUSO» qui sotto: che cosa
> è consegnato, come è stato provato, e le **otto** cose che escono dal brief
> con la loro destinazione — la prima è **C-2**, che vive nel copione. La
> storia passo per passo è in §9.

---

> ## ✅ CHIUSO — 2026-09-15 · DB P-0 → P-9 · BE-1…8 · FE-1…9 · C-1 · archiviato in `work-done/`
>
> **Lato DB**: `20260914-04/05/06` `EXECUTED` su dev il 14-09 alle 15:49; pgTAP
> nuovo (30 asserzioni) e i sei adeguati lanciati col runner come applicazione
> da Tid; committati con `7598dce86` e **verdi in CI** — la `CI-Validate` su
> `Tito-dev` del 15-09 alle 09:30 (`8b42e2807`) li contiene, e
> `test-righe-contabili-eliminazione-v1.sql` non compare in nessuna delle due
> baseline dei rossi. P-9 è entrata con `84f1b3fd7`. Il seed **P-8** è scritto
> il 15-09 (CSV in albero, provato con l'upsert di tutte le righe in transazione
> annullata, `check_i18n_keys.py` verde) e **aspetta il migrate di Tid**: è
> stato di macchina, non di progetto — in CI il mirror ri-esegue da solo. I file
> sono **immutabili**: un cambio va in un changeSet nuovo.
>
> **Lato BE/FE**: BE-1…BE-8, FE-1…FE-9 e la Q-H (strada A) sono **mergiati** su
> `Tito-dev` (`3fd99cc0b` → PR #1589, `62426b8c7`), `api_pagamenti.md` compresa;
> al consuntivo 217 test backend verdi (DB e2e compresi), build · lint · i18n
> verdi. Il consuntivo per voce sta in
> [brief-be-fe §10.12](brief-be-fe-posting-e-abbinamento-rata.md).
>
> **Il copione (C-1) è riscritto. C-2 — la prova a video — ESCE dal brief** e
> vive nel documento che si tiene aperto accanto all'applicazione:
> [collaudo-in-app-incassi-distinte-e-sistemazioni.md](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md),
> riquadro «C-2». ⚠️ Non è una chiusura «col test verde perché nessuno l'ha
> guardato»: i tre rilievi che hanno generato questo brief li ha trovati un giro
> a video, e il secondo giro è scritto lì punto per punto — cosa fare, cosa deve
> succedere, cosa fare se non succede.
>
> ⚠️ **Che cosa ESCE dal brief, e dove va** — censito alla chiusura, perché un
> residuo senza destinazione è un residuo che nessuno rilegge:
>
> | # | Residuo | Dove va | Perché non resta qui |
> | --- | --- | --- | --- |
> | 1 | 🔴 **C-2**, la prova in-app di D16/D17/D18: §2.6–2.9, §3.1–3.3-bis, §4.0 del copione, più la riga di stato del drawer (dopo l'apply di P-8) | [copione](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md), riquadro «C-2» | il copione è il documento che si **spunta** accanto all'app; un brief chiuso non si tiene aperto |
> | 2 | **Apply di P-8** (il seed è in albero, provato) + commit del CSV e delle due schede | `db-migrate` di Tid | stato di macchina: in CI il mirror ri-esegue da solo |
> | 3 | §8: i **fatti** di una riga sotto una distinta **finale** restano modificabili da SQL — sotto `CHIUSA` la porta 2 tace di proposito (la sede è `guard_distinta_finale`, che lascia «le altre scritture su una riga già lì»); nessun verbo BE lo fa | **DB**, decisione — brief madre [§2-bis D16-D18, «residui di modello»](../work-in-progress/brief-incassi-riconciliazione-rate-promemoria.md) | è una decisione (fatti immutabili sotto una finale, per ogni origine), non un passo |
> | 4 | §10.2-2: sulle due matrici `meta` è `{"manuale": false}` ovunque (`20260821-31`) e «chi può chiedere» vive nel BE (`STATI_*_RICHIEDIBILI`); seminare `manuale`/`action_key`/`label_key` porterebbe il vocabolario dove il modello l'ha previsto | **DB**, decisione — brief madre §2-bis | è il modello della matrice, non di questo giro; BE-5 legge la matrice così com'è |
> | 5 | A-5: `contenuto_modificabile` è una **copia dichiarata** del motivo 3, scritto tre volte (check, guard porta 2 sull'`INSERT`, BE) e legato da test; una `fn_check_contabile_contenuto_modificabile(p_contabile_id)` darebbe una sede sola | **DB**, decisione — brief madre §2-bis | BE-7 è deciso come derivata; cambiarlo è un giro suo |
> | 6 | Q-G: la `LATERAL` «primo motivo» è scritta in **quattro** repository nella stessa forma (`registri` ×2, `vendite` ×1, `pagamenti` ×1) | **BE**, «in un giro suo» — [brief BE/FE §10.12](brief-be-fe-posting-e-abbinamento-rata.md) | estrarre un BB `core/db` è trasversale ai domini |
> | 7 | Q-C: il markup «richiesta di conferma» della forzatura (Message + motivo + «Forza») è alla **seconda** occorrenza, dichiarata e non estratta | **FE** — brief BE/FE §10.12 | il composable è già condiviso; il markup nel dialogo sta nel footer, nel form è inline |
> | 8 | La `DataTable` grezza delle righe nel drawer (eccezione ammessa: righe di un documento nel suo master; debito verso `RigheMasterDetailTable`) | `frontend/scripts/datatable.baseline.json` + il commento sopra l'import | debito pre-esistente (28/08), dichiarato dove il presidio lo conta |
>
> Nessun residuo resta senza casa. Il trasloco in `work-done/` chiude il brief:
> i link relativi ai documenti ancora in `work-in-progress/` sono riscritti, le
> due schede manuali (`script/manual/fn_check_riga_contabile_eliminabile`,
> `pagamenti/manual/trgfn_vendite_contabili_righe_guard_contenuto`) puntano alla
> sede nuova, e i residui 1 e 3-7 sono scritti **nei documenti che li ricevono**,
> non solo qui. ⚠️ `mappa-concentrica-changelog.md`: l'ultima voce copre
> l'11–14/09 e non nomina questo cantiere — entra nella voce del periodo
> successivo, quando si scriverà.

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| **D16** | La riga **manuale** nasce con **fattura, cliente e (facoltativa) rata**, direttamente `ABBINATA`; la riga **senza destinazione** è un'eccezione che l'operatore **dichiara**, nasce `DA_ABBINARE` e si recupera dalla coda. ⭐ **Il DB non cambia**: i guard girano già sull'`INSERT`, la matrice è solo su `UPDATE`, e il pgTAP dell'abbinamento inserisce già righe in `ABBINATA` | §2.1 · §4 P-0 |
| **D17** | **Elimina riga** = `attivo = false`, ammesso **solo** su distinta `MANUALE` in `BOZZA`. Un predicato `script.fn_check_riga_contabile_eliminabile` (tre motivi ordinati), un guard che lo chiama su `attivo → false` **e** su `DELETE`, due codici nuovi + uno riusato. ⚠️ `SCARTATA` resta, ma **non è un'eliminazione**: conta nella quadratura (D12-e). 🔴 Il `DELETE` ha **un** passaggio legittimo — il giro dei fondi — che il brief non aveva visto: §4 P-2 | §2.2 · §4 P-1…P-4 |
| **D18** ✅ | *(confermata da Tid il 2026-09-14)* Sotto `VALIDATA` il **contenuto** della manuale si congela: né righe nuove, né fatti modificati, né eliminazioni — finché non torna in bozza. Fino a quel giorno **niente lo impediva**, contro D14-a-bis | §2.3 · §4 P-5 |
| **§3** | Validare ≠ registrare: i movimenti nascono in `fn_posta_contabile`, solo da `VALIDATA`. 🔴 Il copione di collaudo **saltava il passo** «Porta a VALIDATA» (§4.1) e fallirebbe per costruzione — ✅ riscritto il 14/09 (§7, C-1) | §3 · §7 |
| **BE** ✅ | `crea_riga` accetta la destinazione e nasce `ABBINATA`; `DELETE /righe/{id}/`; le quattro colonne `elimina_blocco_*`/`can_eliminare` in lista; le transizioni offerte **dalla matrice**, non dal solo vocabolario | §5 |
| **FE** ✅ | il form riga parte dal **documento** (lookup → rate col saldo → **importo proposto dal residuo**), «non identificato» è un gesto esplicito; il **cestino** diventa «elimina» e smette di essere l'icona di «scarta» | §6 |

---

## 1. Cosa dice il modello, verificato

Le tre cose che il collaudo ha messo in discussione stanno nei documenti e nel
database così:

| Domanda | Risposta del modello | Dove è scritto |
| --- | --- | --- |
| Quando il denaro **conta** nei saldi? | Alla **registrazione** (`fn_posta_contabile`): nascono i movimenti, le righe vanno a `POSTATA`, la distinta a `CHIUSA`. Si registra **solo da `VALIDATA`** (`E_CONTABILE_NON_REGISTRABILE`). Fino a lì il denaro è «dichiarato», e le righe `ABBINATA` compaiono nel saldo fattura come **in lavorazione** | [fn_posta_contabile](/dbzero/pagamenti/manual/fn_posta_contabile), D3, D14-a-bis |
| Che cos'è `VALIDATA`? | *«ho finito di inserire, è pronta da registrare»* + la quadratura col totale dichiarato. **Non** muove denaro. `VALIDATA → BOZZA` esiste apposta *«per aggiungere o togliere una riga»*, solo sulla manuale | D14-a-bis, [guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) |
| Che cos'è `DA_ABBINARE`? | *«va attribuita, **non so ancora a chi**»*: lo stato di un importo arrivato **senza nome** — la forma dell'import (D6), che non esiste ancora | D14-a, D4 |
| Come si scrive una riga a mano? | *«chi lavora a mano scrive già le righe giuste»*: la destinazione si **digita**, non si ricava dopo | **D1-ter** |
| Che cos'è `SCARTATA`? | *«non è nostra»*: denaro **arrivato** che non ci appartiene. Conta nella quadratura, *«quel denaro è arrivato»* | D14-a, **D12-e** |
| Cosa succede a un foglio non ancora registrato? | *«prima della conferma si annulla: è ancora un foglio di lavoro, non ha toccato niente»* | **D9-c** |

⭐ **Nessuna delle tre richieste di Tid contraddice il modello.** Contraddice il
modo in cui BE e FE lo hanno reso: la riga nasce `DA_ABBINARE` per costruzione
(`STATO_RIGA_INIZIALE`, [pagamenti_service.py](../../../../backend/apps/pagamenti/services/pagamenti_service.py#L121)),
il form tiene i soli fatti (R-6 del piano BE/FE), e l'unico modo di togliere una
riga è lo stato `SCARTATA` — disegnato **col cestino**.

---

## 2. Le decisioni

### 2.1 ✅ D16 — La riga manuale nasce **con la destinazione**; «non identificata» è l'eccezione dichiarata

**Cosa si fa.** Nel giro manuale la riga si crea **in un gesto solo**: importo,
date e riferimento (i fatti) **più** fattura, cliente e — se c'è — la rata (la
destinazione). Nasce `ABBINATA`. Se l'operatore, cercato il documento, **non lo
trova**, lo **dichiara** («non identificato») e la riga nasce `DA_ABBINARE` coi
soli fatti: comparirà nella coda «Da abbinare» (Q-4), da cui si recupera col
verbo `abbina`.

**Perché.** Tre ragioni, tutte già scritte:

- `DA_ABBINARE` significa *«non so a chi»*. Chi digita da una contabile
  bancaria **lo sa**: farlo passare per lo stato dell'ignoto e chiedergli di
  «abbinare» in un secondo tempo è il flusso dell'import applicato a una persona
  che ha il nome sotto gli occhi;
- **D1-ter**: le righe si scrivono giuste **fin dall'inizio**. La sequenza
  «crea → abbina» ricava la riga giusta da una riga incompleta, che è il
  contrario;
- la mancata associazione **è un'eccezione** (parole di Tid), e un'eccezione si
  **dichiara**: la riga senza destinazione esce da un gesto esplicito, non dal
  default di un form.

**Cosa NON cambia**, ed è la parte da tenere ferma:

| | Resta | Perché |
| --- | --- | --- |
| **R-6 per la modifica** | il `PATCH` della riga tocca i **soli fatti**; ri-abbinare resta il **verbo** `abbina` | la ragione di R-6 — *«mescolarli farebbe cambiare stato a una riga mentre si corregge un importo»* — vale per una riga che uno stato ce l'ha già. Una riga che **nasce** non ha uno stato da proteggere |
| **Il doppio tempo della capienza** | identico: primo tentativo senza `forzata`, rifiuto confermabile (`confirm_and_retry`), secondo con `forzata` + motivo | il guard è `BEFORE INSERT OR UPDATE`: sull'`INSERT` fa esattamente ciò che fa sull'`UPDATE` |
| **La rata facoltativa** | anche alla nascita | è il caso del fondo fattura, e di un pagamento su un documento senza rate (a credito) |
| **La coda «Da abbinare»** | è il recupero dell'eccezione | esiste già (A-9) |

⚠️ **Nessuna colonna «non identificata».** La dichiarazione è **lo stato**
(`DA_ABBINARE`) su una distinta `origine = MANUALE`: con l'import (D6) le due
provenienze si distingueranno dall'`origine` della testata, non da un flag sulla
riga. Un motivo obbligatorio **non** si chiede: «non ho trovato il documento»
è già tutto ciò che c'è da dire, e `SOSPESA` col suo `motivo_sospeso` resta il
posto per «l'ho guardata e c'è un problema» — che è un'altra cosa (D14-a).

⭐ **Il DB non cambia**, ed è misurato:

| Cosa serve all'`INSERT` diretto in `ABBINATA` | C'è già |
| --- | --- |
| fattura + cliente obbligatori | `trgfn_vendite_contabili_righe_guard_stato_dati`, `BEFORE INSERT OR UPDATE`, legge `richiede_abbinamento` |
| coerenza rata ↔ fattura (rifiuta) e capienza (segnala, forzabile) | `trgfn_vendite_contabili_righe_guard_rata`, `BEFORE INSERT OR UPDATE`; la capienza si valuta se la riga è attiva, postabile e non forzata — sull'`INSERT` come sull'`UPDATE` |
| perimetro emittente sulla fattura | `script.trgfn_guard_emittente_scope('fattura','fattura_id')`, `BEFORE INSERT OR UPDATE` |
| la matrice **non** vincola l'`INSERT` | `trg_…_guard_transizione_upd` è **solo `UPDATE`**, per la regola generale (linee-guida §7c punto 6: *«non vincolare l'INSERT con la matrice»*) |
| il contratto è già pinnato | `db/pgtap/pagamenti/test-abbinamento-rata.sql` **inserisce** righe con fattura, cliente, rata e `stato = ABBINATA` (test 2 e seguenti) |

**Cosa la ribalterebbe.** Che la riga manuale debba **sempre** passare da una
persona diversa da chi la digita (separazione digitazione/abbinamento). Escluso:
la distinta manuale è **per operatore** (D12-a), e il gesto irreversibile — la
registrazione — ha già la sua porta (`registra_distinta`, azione pericolosa).

---

### 2.2 ✅ D17 — Una riga di una bozza manuale **si elimina**; «scarta» non è un'eliminazione

**Il rilievo, misurato.** Non esiste **nessun** verbo di eliminazione: nessuna
rotta `DELETE`, nessuna azione FE, nessun trigger di `DELETE`. L'unico modo di
togliere una riga è portarla a `SCARTATA`, che il drawer disegna con
**`MANAGE_ICONS.DELETE`** — il cestino — e che la matrice ammette **solo** da
`DA_ABBINARE` e `SOSPESA`. Il drawer però la **propone su ogni riga** (offre
tutti i richiedibili meno lo stato corrente): su una riga `ABBINATA` il DB
rifiuta con `E_RIGA_CONTABILE_TRANSIZIONE_NON_AMMESSA`. È il «vincolo troppo
stretto» del collaudo — e un difetto §12 (*si propone ciò che verrà rifiutato*).

**Ma il punto è di modello, non di matrice.** Una riga digitata male su una
manuale in bozza **non è un fatto**: non è denaro arrivato, è un errore di
battitura. `SCARTATA` racconta il contrario — *«denaro arrivato, non nostro»* —
e ha una conseguenza concreta: la quadratura **conta anche le scartate**
(D12-e, [guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) riga 48):

```text
dichiaro 400  →  digito 400 (sbagliata) + 400 (giusta)  →  «scarto» la sbagliata
somma delle righe attive = 800  ≠  400   →   la distinta NON si valida più
```

⇒ Oggi un errore di digitazione su una manuale con totale dichiarato **non ha
via d'uscita**. D9-c dà la regola al livello sopra — *prima della conferma si
cancella, perché non è successo niente* — e vale identica per la riga.

**Cosa si fa.**

| | Decisione | Perché |
| --- | --- | --- |
| **a** | Il verbo è **«elimina riga»** e scrive **`attivo = false`** | è la porta che il modello ha **già** aperto: `trgfn_prevent_deactivate_if_children` sui movimenti presidia proprio la disattivazione, e **tutti** i lettori — `fn_get_saldo_fattura_contabili`, `fn_get_saldo_rata`, `fn_posta_contabile` (quadratura e selezione), `guard_chiusura`, `vw_rate_fuori_capienza`, `vw_eccedenze_da_sistemare`, e nel BE `list_righe` e i contatori del dettaglio — filtrano **già** `attivo IS TRUE`. Resta la traccia di chi ha tolto cosa (`user_update`/`data_update`), senza storicizzazione |
| **b** | Ammesso **solo** se: la distinta è **`MANUALE`**, è in **`BOZZA`**, e non è finale | `AUTOMATICA` è immutabile su tutte e tre le porte (D12-d); `GENERATA` la governa il sync dei fondi, che le sue righe le rifà; `VALIDATA` è *«ho finito»*: si **riapre** per togliere (D14-a-bis) — ed è esattamente il confine detto da Tid, *«fino a quando la contabile non è validata»* |
| **c** | Il predicato è **una `script.fn_check_*`** con i motivi **ordinati**, e la madre — qui il guard — la **chiama** | §12.5.2: il tooltip del cestino spento e il rifiuto del database escono dalla stessa funzione, quindi **non possono divergere** |
| **d** | Il guard chiude **anche il `DELETE` fisico**, con lo stesso predicato | D12-d: *«immutabile ha tre porte, chiuderne una sola non serve a niente»*. Oggi il `DELETE` è aperto a chiunque abbia il privilegio (l'app ce l'ha): una riga `POSTATA` la ferma solo la FK `NO ACTION` del movimento, le altre niente |
| **e** | `SCARTATA` **resta** con il suo significato, e la sua icona **non è più il cestino** | è lo stato dell'import: una riga arrivata da un file che non ci appartiene. Sulla manuale in bozza il gesto giusto è eliminare; scartare tornerà utile con D6 |

**I tre motivi**, nell'ordine in cui la check li nomina (lo specifico batte il
generico; l'ordine è il contratto):

| # | `reason` | Quando | Codice sollevato | Soluzione (a catalogo) |
| --- | --- | --- | --- | --- |
| 1 | `DISTINTA_FINALE` | la testata è `CHIUSA` o `ANNULLATA` | **riuso** `E_RIGA_CONTABILE_DISTINTA_FINALE` — il messaggio dice già *«quelle che ha non si lavorano più»*, valori `(codice, chiusa\|annullata)` | il registrato si corregge con una distinta di segno opposto |
| 2 | `DISTINTA_NON_MANUALE` | `origine <> 'MANUALE'` | 🆕 `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` (`CONFLITTO_STATO`) | generata: si rigenera dal giro che l'ha prodotta; automatica: si scarta o si sospende |
| 3 | `DISTINTA_VALIDATA` | stato `VALIDATA` (o comunque non `BOZZA`) | 🆕 `E_RIGA_CONTABILE_DISTINTA_VALIDATA` (`CONFLITTO_STATO`) | riportare la distinta in bozza, eliminare, rivalidare |

⚠️ **Nessun motivo «riga registrata»**, ed è voluto: una riga `POSTATA` sta per
costruzione sotto una distinta `CHIUSA` (la chiusura è la conseguenza del
posting), quindi la ferma il motivo 1 — e dietro c'è comunque la rete di
`prevent_deactivate_if_children` sul movimento. Un motivo irraggiungibile
insegnerebbe un caso che non esiste (la lezione di `STORNATA`).

⚠️ **Il codice riusato e il rubinetto degli accumulatori.** Sollevare
`E_RIGA_CONTABILE_DISTINTA_FINALE` da un secondo punto — via
`fn_raise_primo_motivo_se_presente`, quindi famiglia `IGNOTO` — può fermare
`codici-errore-baseline.sh`. Non è un accumulo: è **la stessa condizione**
(«sotto una distinta finale non si lavora») da una porta in più, ed è la ragione
scritta per la ri-base, se serve.

**Cosa la ribalterebbe.** Una regola di revisione che pretenda la traccia di
ogni riga **mai digitata**, anche in bozza. Allora `attivo = false` sarebbe
comunque la forma giusta (la riga resta), e cambierebbe solo la lettura: un
interruttore «mostra le eliminate» che oggi il BE dichiara di **non** avere
apposta (*«un parametro che nessuno passa è superficie che invecchia»*).

---

### 2.3 ✅ D18 — Sotto `VALIDATA` il contenuto della manuale si congela *(confermata da Tid il 2026-09-14)*

**Il rilievo.** D14-a-bis dice *«finché è validata il contenuto non cambia»* e
motiva così la stabilità della quadratura. Ma **niente lo impedisce**: il
drawer rende le righe modificabili su ogni stato non finale (`modificabile`), e
il DB non ha alcun guard sulle righe che guardi `VALIDATA` — i soli guard di
testata sono su `is_final`. Una distinta validata a 400 può ricevere una riga in
più un minuto dopo. Il posting **ri-quadra** (passo 3 della madre), quindi non
si registra mai un totale sbagliato; ma il gesto «ho finito» non è un
congelamento, e la quadratura fatta *«mentre l'operatore è ancora nel flusso»*
può essere rifatta a sorpresa al momento di registrare.

**Cosa si propone.** Sotto una distinta `MANUALE` in `VALIDATA`:

| Si rifiuta | Resta permesso |
| --- | --- |
| `INSERT` di una riga; `UPDATE` dei **fatti** (`importo`, `data_pagamento`, `data_valuta`, `data_operazione`, `riferimento_ente`); `attivo → false` (che è D17, stesso motivo 3) | ogni **decisione**: `stato_id`, `fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`, `motivo_forzatura`, `motivo_sospeso`, `meta` |

Il criterio è quello di D12-d — **fatti contro decisioni** — e ha due ragioni:
l'abbinamento **non tocca la quadratura** (D12-e punto 2), quindi si può fare
anche a distinta validata; e la madre del posting **muove lo stato** delle righe
mentre la distinta è ancora `VALIDATA` — un congelamento dello stato la
romperebbe.

⛔ **Solo su `MANUALE`.** Le distinte `GENERATA` **nascono già `VALIDATA`** e il
sync inserisce le righe **dopo** la testata: un guard sull'`INSERT` che non
guardasse l'`origine` fermerebbe il giro dei fondi al primo passaggio.
L'immutabilità di `AUTOMATICA` e `GENERATA` è di D12-d e arriva **con
l'import**, come già deciso.

Stesso codice del motivo 3 di D17 (`E_RIGA_CONTABILE_DISTINTA_VALIDATA`): il
messaggio è scritto per coprire tutti e tre i gesti — *«le sue righe non si
aggiungono, non si modificano e non si eliminano finché non torna in bozza»*.

⚠️ **Conseguenza FE**: `modificabile` = stato **`BOZZA`**, non «non finale». E
la voce «Porta a VALIDATA» smette di essere una transizione fra le altre: è il
momento in cui il foglio si chiude alla digitazione.

~~**Se non si conferma**: D17 resta intero (il motivo 3 blocca l'eliminazione
sotto `VALIDATA` per la ragione di D14-a-bis), e P-5 non si scrive.~~
✅ **Confermata** il 2026-09-14, e scritta nello stesso changeSet di P-2.

⭐ **Due mosse in più rispetto alla tabella qui sopra**, viste scrivendo il guard
e trattate come contenuto per la stessa ragione (cambiano la somma delle righe
di una distinta che l'operatore ha dichiarato finita): la **riattivazione** di
una riga (`attivo` da falso a vero) e lo **spostamento** di una riga da o verso
un'altra distinta (`contabile_id`). Il trigger è `UPDATE OF attivo,
contabile_id, importo, data_pagamento, data_valuta, data_operazione,
riferimento_ente`: sulle decisioni non scatta nemmeno.

---

## 3. Validare non è registrare — e il copione lo dà per scontato

La domanda di Tid — *«la scrittura dell'effettivo pagamento avviene con la
validazione?»* — ha una risposta sola nel modello, e vale la pena scriverla
dove si legge:

```text
BOZZA ──(Porta a VALIDATA)──► VALIDATA ──(Registra)──► CHIUSA
  digito, correggo,             «ho finito»,            fn_posta_contabile:
  elimino (D17)                 quadratura,             nascono i MOVIMENTI,
                                contenuto fermo (D18)   righe POSTATA, data_conferma
                                                        ⛔ irreversibile
saldo fattura: invariato ─────► «in lavorazione» ─────► residuo che CAMBIA
```

🔴 **Il copione** ([collaudo-in-app-incassi-distinte-e-sistemazioni.md](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md))
passava da §2.7 a §4.1 «Sul drawer → Registra» **senza** il passo «Porta a
VALIDATA»: la madre rifiuta da bozza (`E_CONTABILE_NON_REGISTRABILE`), e il
punto 4.1 sarebbe fallito per costruzione. ✅ **Riscritto il 14/09** (C-1)
insieme a §2.6 e §3.1 (D16) e con la prova nuova per D17 — la tabella è in §7;
la **prova in-app** (C-2) resta da fare.

ℹ️ Se i due clic (validare, poi registrare) sembrano ridondanti sulla manuale
per-operatore, è una **decisione di Tid**, non un difetto: la madre motiva il
vincolo con *«da bozza la distinta potrebbe cambiare mentre la si registra»*, e
D14-a-bis colloca lì la quadratura *«mentre sei ancora nel flusso»*. Con D18 il
primo dei due gesti acquista un mestiere in più (congelare), e la ridondanza si
riduce da sé.

---

## 4. Piano DB

Regole di lavorazione: corpo di ogni oggetto esistente **dalla doc auto-gen**;
un changeSet per file, `runOnChange: false`; codici errore **in coda al CSV**
con la loro classe; numerazione `NN` assegnata **al momento della scrittura**
(quella «libera» scade nel minuto); `security_invoker`/`SECURITY INVOKER`
espliciti; la prova è **l'SQL estratto** in `BEGIN … ROLLBACK`, poi il pgTAP
concatenato nella stessa transazione. L'apply e il lancio col runner sono di
Tid.

| Passo | Cosa | Fase | Note |
| --- | --- | --- | --- |
| **P-0** ✅ | **D16: nessun changeSet.** ⚠️ **Il caso non mancava**: i test **5 e 6** di `test-abbinamento-rata.sql` fanno *già* un `INSERT` diretto in `ABBINATA` con capienza superata (rifiuto *«non ci rientra»*) e lo stesso `INSERT` con `forzata = true` (passa). La riga «oggi il doppio tempo è provato solo sull'`UPDATE`» era **falsa**, e si è vista rileggendo il file. Aggiunta una nota nello *Scopo* del file che dichiara i due test come contratto di D16, perché chi cerca «dove è pinnata la nascita abbinata» li trovi | pgTAP | fatto datato: 2026-09-14 |
| **P-1** ✅ | `script.fn_check_riga_contabile_eliminabile(p_riga_id bigint) RETURNS jsonb` — `[]` se ammesso, altrimenti l'array **ordinato** dei tre motivi di §2.2, forma `{codice, reason, reason_key, dettaglio, valori}` (modello: `script.fn_check_ordine_annullabile`). `SECURITY INVOKER`, `STABLE`; guard `p_riga_id IS NULL OR <= 0` su **`E_PAGAMENTI_CHIAMATA_NON_VALIDA`** (TECNICO — non `E_PARAMETRO_INVALIDO`, che è uno split rimandato). ⚠️ Legge la testata (`vendite_contabili`, che ha la RLS): chi vede la riga vede la testata per la stessa catena di scope (`…_via_contabile`), come già fa `guard_distinta_finale`; **riga non leggibile ⇒ `E_RIGA_CONTABILE_NON_TROVATA`** (404, no-leak), non `[]` — che sarebbe «si può eliminare» detto di una cosa che non si vede. `valori` del motivo 1 = `(codice distinta, 'chiusa'\|'annullata')`, per riusare il messaggio esistente. ⭐ Il motivo 3 è scritto **solo per la manuale**: su una generata «torna in bozza» non è un rimedio, e un tooltip che lo suggerisse manderebbe a un gesto destinato a fallire | `20_code/script/20260914-04` | `reason_key`: `pagamenti.righe.elimina_reason.{distinta_finale, distinta_non_manuale, distinta_validata}` |
| **P-2** ✅ | ⚠️ **Rinominato**: `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto()` + trigger `trg_vendite_contabili_righe_a10_guard_contenuto_ins_upd_dlt` — con D18 confermata la stessa funzione rifiuta anche un `INSERT`, e un guard che si chiama *eliminazione* e rifiuta un inserimento si legge male esattamente quando conta (la regola dell'icona con due sensi, §8, applicata a un nome). Porta 1: `attivo` `true → false` **e `DELETE`**, chiama la check di P-1 e solleva con `script.fn_raise_primo_motivo_se_presente` (il codice si **legge** dall'array, mai ricopiato). ⚠️ Ordine alfabetico dei `BEFORE ROW`: parla **prima** di tutti gli altri guard di riga (`c` < `d`), non «dopo `guard_distinta_finale`» come scritto qui in prima stesura — e va bene: sotto una finale la porta 2 tace e lascia il messaggio a `guard_distinta_finale`; sulla disattivazione `guard_rata` esce da sé e `guard_distinta_finale` non guarda — verificato leggendo i corpi e provato (test 24-25). 🔴 **La porta `DELETE` ha un passaggio legittimo che il brief non aveva visto**: `vendite.fn_cancella_fondo_fattura` — sede unica dei tre `DELETE` del giro dei fondi, chiamata da `fn_reset_fondi_fattura`, `fn_annulla_sistemazione` e `DELETE /vendite/fondi-fattura/{id}/` — cancella **fisicamente** le righe del suo atto sotto una `GENERATA`, dove la check risponde `DISTINTA_NON_MANUALE`. «Stesso predicato» avrebbe ucciso il giro al primo atto cancellato, e con lui tre pgTAP di `vendite`. ⭐ **Decisione di Tid (2026-09-14), fra tre strade**: la madre del giro **apre la porta per il proprio `DELETE`** con la GUC transazionale `zeroerp.allow_contabile_riga_delete_override` (`SET LOCAL 'on'` prima, `''` dopo) e il guard la onora **solo sul `DELETE`** — precedente identico e in servizio, `script.fn_change_user_emittenti_scope` su `trgfn_user_emittenti_fiscali_guard_delete`. Non è un permesso: è la madre che dichiara «sono io» dopo aver letto il **suo** criterio (`fn_check_fondo_cancellabile`). Le alternative scartate: lasciare il `DELETE` aperto (contraddice D17-d) e saltare le righe con `fondo_source_id` (un ramo scelto dal valore di una colonna) | `20_code/pagamenti/20260914-05` | il `DELETE` di una `POSTATA` era già fermato dalla FK: adesso parla **prima**, col messaggio giusto (test 25) |
| **P-2 bis** ✅ | 🆕 `vendite.fn_cancella_fondo_fattura` rev: `SET LOCAL zeroerp.allow_contabile_riga_delete_override = 'on'` prima del `DELETE` delle righe, `''` subito dopo. Corpo **dalla doc auto-gen** (rev `20260831-64`), le sole righe nuove sono le due `SET LOCAL` e il commento. Nessun predicato, conteggio o codice cambia; firma invariata | `20_code/vendite/20260914-06` | i tre pgTAP dei fondi passano (110/110 nella prova) |
| **P-3** ✅ | Seed: 2 righe in `config/codici_errore.csv` (`E_RIGA_CONTABILE_DISTINTA_NON_MANUALE`, `E_RIGA_CONTABILE_DISTINTA_VALIDATA`, classe `CONFLITTO_STATO`, note col nome della funzione che li solleva) + 2 righe `it` in `config/messaggi_errore.csv` (**id 1063, 1064**) con `causa` e `soluzione` (§2.2). ⭐ Anche le **note** dei due codici riusati (`E_RIGA_CONTABILE_DISTINTA_FINALE`, `E_RIGA_CONTABILE_NON_TROVATA`) dichiarano il secondo punto di sollevamento. ⚠️ «Apostrofi raddoppiati» era **sbagliato**: nel CSV l'apostrofo è singolo (`e'`), il loader lo passa come parametro — il raddoppio vale nei letterali SQL dei changeSet. Verificato **rieseguendo l'upsert di tutte le 857 + 852 righe** in transazione annullata (le due specie di mina, stantìa e irriscrivibile): passa; segnaposto controllati. ⚠️ I due codici sono `IGNOTO` per il rubinetto degli accumulatori (sollevati via helper), quindi la baseline B-7 non si muove | `80_data` | il BE rigenera `error_policies_generated.py` e scrive i due ripieghi in `error_messages_fallback.py` (§5) |
| **P-4** ✅ | pgTAP nuovo `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql`, **30 asserzioni** (runner **app**; fixture **costruita**: `fn_pgtap_crea_emittente_operatore` + `fn_pgtap_crea_cliente_ba` + una fattura; le distinte si **inseriscono dirette** e non con `fn_get_or_create_vendite_contabile`, la cui chiave di riuso potrebbe restituire una distinta già esistente della giornata). Copre tutto l'elenco previsto — i tre motivi nell'ordine (4, 7, 23), lo scenario di §2.2 (15-20: «scartare» rompe la quadratura, eliminare la ripara), il `DELETE` fisico (22, 25, 26), la riattivazione in bozza (21), il saldo «in lavorazione» (16, 19) — più i casi di P-5, la porta della GUC aperta e **richiusa** (27-28) e i due guard di chiamata (29-30). ⚠️ Il saldo si asserisce come **delta**, non come valore assoluto: la fattura ha già righe pronte sotto le altre distinte della fixture, e `800`/`400` erano la fotografia — la prima stesura è caduta lì | pgTAP | `throws_like` sulla frase dove la frase è la posta (lo è quasi ovunque: il punto è *quale* guard parla) |
| **P-5** ✅ | *(D18 confermata)* la stessa funzione di P-2 prende la **terza mossa** (porta 2): `INSERT`, `UPDATE` di uno dei cinque fatti, **riattivazione** e **spostamento** (§2.3) sotto una testata `MANUALE` non più in `BOZZA` e non finale → `E_RIGA_CONTABILE_DISTINTA_VALIDATA`. ⛔ Filtro `origine = 'MANUALE'` **prima** di tutto: il sync dei fondi inserisce e aggiorna righe sotto testate già `VALIDATA`, la sistemazione sotto una `GENERATA` in `BOZZA`. ⚠️ La condizione è il **motivo 3 della check scritto due volte** (sull'`INSERT` non c'è una riga da passare): copia dichiarata, legata dal pgTAP (test 7 vs 9-10, stesso codice). Test: riga nuova (9), importo (10), spostamento (11) rifiutati; `abbina` nella forma del BE **passa** (12); `UPDATE OF` a valore invariato passa (13); i pgTAP dei fondi restano verdi | `20_code/pagamenti/20260914-05` + pgTAP | il codice è lo stesso di P-3: nessun seed in più |
| **P-6** ✅ | Doc manuale: `docs/it/dbzero/script/manual/fn_check_riga_contabile_eliminabile.md`, `docs/it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_contenuto.md` (nuove); aggiornati `pagamenti/manual/vendite_contabili_righe.md` (sezione «Eliminare una riga, e quando il contenuto si ferma»), `vendite/manual/fn_cancella_fondo_fattura.md` (la porta del `DELETE`) e la guida [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) — §«Righe contabili», §«Trigger di guardia» (voce nuova che rimanda), §«Flusso logico» (validare ≠ registrare, in un paragrafo), regola di dominio 8. ⛔ Le doc auto-gen non si editano: le due schede nuove entrano nel sito alla prossima rigenerazione | docs | rimando al meccanismo, non copia |
| **P-7** ✅ | 🆕 **Adeguamento dei pgTAP esistenti**, nello stesso giro (memoria: un guard restrittivo si grepa prima). Il `DELETE` di cleanup di **cinque** file cancella righe sotto distinte `CHIUSA` o `GENERATA` — `test-abbinamento-rata`, `test-fn-posta-contabile`, `test-fondi-fattura`, `test-fondi-fattura-governo`, `test-fondo-fattura-eseguito` — e ora lo dichiara con la stessa GUC della madre del giro (il ROLLBACK farebbe comunque il lavoro). `script/test-rubinetto-primo-motivo-v1.sql` test 5: da **16 a 17** funzioni che chiamano l'helper (un sito nuovo nato già sull'helper, non una bonifica). Nessun altro pgTAP scrive fatti sotto una manuale validata o disattiva righe: censiti 24 file che nominano gli oggetti toccati, tutti provati | pgTAP | 110/110 sui sei adeguati, 168 verdi sugli altri |

| ✅ **P-8** *(scritto 15/09, apply di Tid)* | 🆕 *(richiesta dal lato BE/FE, 2026-09-14 sera — per FE-9, §10.2-3)* **Seed `meta.nessuna_azione_key` sui cinque stati della distinta**, in `80_data/sql/pagamenti/vendite_contabili_stati.csv` (⚠️ i mirror sono **due**, non uno: `20260213-04` e il ri-ancorato `20260821-30` con la lista completa delle colonne — entrambi `runOnChange` + `ANY`, entrambi già risvegliati; si edita il CSV, mai un `UPDATE`): `BOZZA` → `pagamenti.distinte.stato_info.bozza` · `IMPORTATA` → `…importata` · `VALIDATA` → `…validata` · `CHIUSA` → `…chiusa` · `ANNULLATA` → `…annullata`. Forma del valore: `"{""nessuna_azione_key"":""pagamenti.distinte.stato_info.bozza""}"` (come `config/stati_doc_ordini.csv`). ⭐ **BE e FE sono già pronti**: `_DISTINTA_SELECT` legge `st.meta ->> 'nessuna_azione_key' AS stato_info_key` (oggi `NULL`), il drawer lo passa a `DrawerActionsBar :info-key`, e le **cinque chiavi sono già nei locales** `it`/`en` — quindi `check_i18n_keys.py` (controllo 4, che scandisce ogni CSV di `80_data/sql`) le troverà. Nessun altro oggetto. ✅ **Fatto il 15/09**: prova su dbdev in `BEGIN … ROLLBACK` con l'upsert di tutte le righe (CSV = DB prima dell'edit, nessuna riga irriscrivibile, `UPDATE 5`), `stato_info_key` letto come lo legge il BE, `check_i18n_keys.py` verde; scheda `pagamenti/manual/vendite_contabili_stati.md` aggiornata sul `meta` | `80_data` | il testo compare a video all'apply; fino a lì la barra è muta, non rotta |
| ✅ **P-9** *(fatta: `84f1b3fd7`, 14/09)* | 🆕 Rigenerazione della **doc auto-gen** (`docs/it/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile.md`, `pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto.md`, `vendite/funzioni/fn_cancella_fondo_fattura.md`): le due schede manuali nuove entrano nel sito da lì, e il controllo 4 di `check_i18n_keys.py` legge le `reason_key` dal corpo delle funzioni — le tre `pagamenti.righe.elimina_reason.*` sono già nei locales | docs | già previsto in testa al brief; qui solo per completezza dell'elenco |

**Cosa il DB NON fa, e perché**

| | |
| --- | --- |
| Nessuna vista `vw_distinta_righe` | le righe le serve il BE con SQL proprio (`list_righe`): la colonna del motivo la aggiunge **lui** con una `LATERAL` sulla check (§5). Una vista nuova per una colonna sarebbe un oggetto in più con la RLS da armare |
| Nessun lookup «fatture con residuo per cliente» | i saldi hanno **una sede sola** nel BE (`saldi_service`, §2.7 del piano BE/FE) sopra `fn_get_saldo_fattura`: una `LATERAL` per riga su venti risultati non chiede una funzione set-based. Se il BE la vuole, la chiede |
| Nessuna colonna sulla riga per «non identificata» | è lo stato su una distinta `MANUALE` (§2.1) |
| Nessuna modifica alla matrice | `SCARTATA` resta dov'è, per D6 |

---

## 5. Cosa deve fare il backend *(solo l'elenco: il piano è loro)*

| | Cosa | Perché / vincolo |
| --- | --- | --- |
| **BE-1** ✅ | `POST /pagamenti/distinte/{id}/righe/` accetta anche `fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`, `motivo_forzatura`. Con `fattura_id` la riga nasce **`ABBINATA`** — **un solo `INSERT`**, atomico per costruzione; senza, nasce `DA_ABBINARE` come oggi | D16. ⛔ Non due scritture (`create` + `abbina`): i guard fanno tutto sull'`INSERT`. `billing_account_id`: se manca, si deriva dalla fattura (come già fa il dialog dell'abbinamento) |
| **BE-2** ✅ | Il doppio tempo della capienza vale anche alla creazione: il 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` risale con `confirm_and_retry`, come per `abbina` | il BE **trasporta**, non decide che cosa sia forzabile |
| **BE-3** ✅ | `DELETE /pagamenti/righe/{id}/` → `UPDATE … SET attivo = false`. Il metodo dice il verbo (api.md §Grammatica URL); i motivi li dà il DB (409 `E_RIGA_CONTABILE_DISTINTA_*`), il BE traduce e passa | D17. Nessuna copia del predicato in Python |
| **BE-4** ✅ | La lista righe (`list_righe`) e la coda (`GET /pagamenti/righe/`) espongono `elimina_blocco_reason` e `elimina_blocco_reason_key` da `script.fn_check_riga_contabile_eliminabile(r.id) -> 0` in `LATERAL` (`NULL` = ammesso). ⚠️ **Sono quattro, non due** — vedi §10.2-1: anche `elimina_blocco_dettaglio` e il flag `can_eliminare`, perché il BB FE che compone la frase legge la terna e il flag | §12.5: **un verbo, una colonna**, col nome del verbo. Non riusare una colonna di un altro blocco |
| **BE-5** ✅ | Le transizioni di riga offerte al FE si derivano **dalla matrice** (`pagamenti.transizioni_stati_contabile_riga`) per lo stato corrente, non dal solo vocabolario `stati_richiedibili.riga`. ⭐ **Anche per la testata** (§10.2-2): oggi coincide con la matrice per caso | oggi il FE propone `SCARTATA` su una riga `ABBINATA` e il DB la rifiuta: difetto §12 emerso al collaudo |
| **BE-6** ✅ | `genera_error_policies` + ripieghi in `error_messages_fallback.py` per i due codici nuovi; test `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | ✅ **Già fatto** (misurato il 14/09 sera): rigenerato e ripieghi scritti con `eeed40be8` da un altro cantiere lo stesso giorno; `--check` risponde «allineato al catalogo», presidio verde — §10.1 |
| **BE-7** ✅ | *(D18 confermata)* `aggiorna_riga` e `crea_riga` non hanno nulla da cambiare — il rifiuto arriva dal DB come 409 `E_RIGA_CONTABILE_DISTINTA_VALIDATA` — ma il dettaglio distinta espone un `contenuto_modificabile` derivato (`stato_codice_interno = 'BOZZA' AND origine = 'MANUALE'`) così il FE non ricalcola la regola. ⚠️ Anche la **riattivazione** e lo **spostamento** di una riga sono contenuto (§2.3): se il BE avesse un verbo per l'una o per l'altro, sotto una validata prende lo stesso 409 | una sede sola |
| **BE-8** | Il `DELETE /vendite/fondi-fattura/{id}/` **non cambia**: `fn_cancella_fondo_fattura` apre da sé la porta del `DELETE` delle righe (P-2 bis). ⛔ Il BE **non deve** impostare `zeroerp.allow_contabile_riga_delete_override` da nessuna parte: è una dichiarazione della madre, non un parametro di sessione — e una GUC lasciata aperta renderebbe verdi per sottrazione tutti i `DELETE` della richiesta | non è un permesso |

---

## 6. Cosa deve fare il frontend *(solo l'elenco)*

| | Cosa | Perché / vincolo |
| --- | --- | --- |
| **FE-1** ✅ | `DistintaRigaForm` in **creazione** parte dal **documento**: `FatturaLookup` (cerca già per numero, ragione sociale, codice BA, CF/P.IVA) → **rate col saldo** (lo stesso lettore di `AbbinaRigaDialog`, rata facoltativa) → ⭐ **importo proposto** = residuo della rata scelta (o della fattura, senza rata), modificabile → fatti (date, riferimento) | D16. La risposta alla domanda «quanto?» la dà il documento, e l'operatore corregge solo se l'importo arrivato è diverso |
| **FE-2** ✅ | «**Non riesco ad associarlo**» è un gesto esplicito (toggle/pulsante) che **scopre** i soli fatti e fa nascere la riga `DA_ABBINARE`; la riga in elenco e la coda «Da abbinare» la fanno vedere come eccezione | l'eccezione si dichiara, non è il default |
| **FE-3** ✅ | La capienza alla creazione usa `useForzaturaConfermata` come il dialog di abbinamento | stesso BB, stesso `ui_action` |
| **FE-4** ✅ | In **modifica** il form resta sui fatti (R-6); ri-abbinare resta il verbo `abbina`. ⭐ E dal 15/09 anche la modifica ha il **secondo tempo** (Q-H, strada A): il PATCH accetta `forzata` + `motivo_forzatura`, il form li porta con `extra` come alla nascita | la ragione di R-6 vale per una riga che ha già uno stato — e protegge la destinazione, non la conferma |
| **FE-5** ✅ | Azione di riga **«Elimina»**: cestino (`MANAGE_ICONS.DELETE`), `severity: danger`, conferma con `useConfirmAction`, `disabled` + **`tooltip`** dalla terna via `bloccoMotivo.js` (`motivoBloccoRiga`/`bloccoAttivo`, il BB che già serve registri e tab BA — non `labelOrCode` a mano); tre chiavi `pagamenti.righe.elimina_reason.*` in `it.json` **e** `en.json` nello stesso giro (`check_i18n_keys.py` controllo 4 è rosso finché mancano). ✅ **Le tre chiavi ci sono già** in entrambe le lingue (14/09, `eeed40be8`) — §10.1 | D17, §12.5.5: il campo si chiama `tooltip`, non `motivo` |
| **FE-6** ✅ | `SCARTATA` **non usa più il cestino** (`ICONA_TRANSIZIONE_RIGA`): un'icona di «scarto» (`pi pi-ban` o simile). Il cestino significa «elimina», e da FE-5 lo è | un'icona con due sensi è il difetto che la regola delle icone vieta |
| **FE-7** ✅ | Le voci «Porta a …» di riga si costruiscono dalle transizioni **ammesse dallo stato corrente** (BE-5), non dal vocabolario intero | §12: mai proporre ciò che verrà rifiutato |
| **FE-8** ✅ | *(D18 confermata)* `modificabile` = `BOZZA` e `MANUALE` (BE-7); sotto `VALIDATA` restano i verbi di decisione (abbina, sospendi) e le azioni di testata (riapri, registra) | D18 |
| **FE-9** ✅ *(il testo compare all'apply di P-8)* | Il pannello di stato del drawer dice in una riga **dove si è**: «bozza: si digita» · «validata: pronta da registrare, il denaro non è ancora registrato» · «registrata». ⚠️ **Non è solo FE** (§10.2-3): la chiave viene dal `meta` dello stato (`DrawerActionsBar :info-key`, lo standard degli otto drawer) ⇒ seed **P-8** al team DB; BE e FE si scrivono subito | §3: la domanda di Tid nasce da qui |

---

## 7. Il copione di collaudo — righe da riscrivere

✅ **Riscritte il 2026-09-14 (C-1)** in [collaudo-in-app-incassi-distinte-e-sistemazioni.md](../work-in-progress/collaudo-in-app-incassi-distinte-e-sistemazioni.md):
la colonna «Domani» è ciò che il copione dice adesso; **la prova a video (C-2)
non è ancora stata fatta**.

| Punto | Oggi | Domani |
| --- | --- | --- |
| **§2.6** | «Aggiungi una riga da 400 … stato **DA_ABBINARE**» | la riga si crea **cercando la fattura 103**, scegliendo la rata, con l'importo **proposto** (400,00) → stato **ABBINATA** |
| **§3.1–3.3** | «Azioni della riga → Abbina» come primo abbinamento | diventano la prova del **ri-abbinamento** (riga sbagliata → `DA_ABBINARE` → `abbina` di nuovo) e dell'**eccezione**: una riga «non identificata» compare in **Da abbinare** |
| 🆕 **§2.8** | — | **elimina** una riga sbagliata in bozza: sparisce, la quadratura torna; sotto `VALIDATA` il cestino è **spento col motivo** |
| 🔴 **§4.0** | manca | **Porta a VALIDATA** prima di «Registra»: con un totale dichiarato sbagliato deve fermarsi **qui**, non alla registrazione |

---

## 8. Trappole da non ripagare, viste scrivendo

- ⚠️ **Un'icona con due sensi è una regola scritta a metà.** Il cestino su
  «scarta» ha fatto leggere a Tid uno stato di dominio come un'eliminazione —
  e l'eliminazione non c'era. *Prima di dare a un gesto l'icona di un altro,
  chiedersi che cosa dirà a chi non ha letto il brief.*
- ⚠️ **Un vocabolario offerto per intero non è una matrice.** `stati_richiedibili`
  dice cosa una persona può chiedere **in generale**; da quale stato lo può
  chiedere lo dice la matrice, che sta a DB e nessuno leggeva a video. Il
  risultato è un pulsante che il database rifiuta.
- ⚠️ **«Il contenuto non cambia» va presidiato, o è una frase.** D14-a-bis lo
  dichiarava dal 21/08 e nessun guard lo faceva: la quadratura reggeva perché
  il posting la rifà, non perché fosse congelata. *Una proprietà dichiarata in un
  brief e non scritta in un guard vale finché nessuno la tocca.*
- ⚠️ **Il default di un form è una decisione di dominio.** «La riga nasce
  `DA_ABBINARE`» era scritto nel BE come ovvietà del modello (*«quando il
  denaro arriva non si sa ancora di chi sia»*) — vero per l'import, falso per
  chi digita. Il default aveva scelto il flusso sbagliato senza che nessuno
  l'avesse deciso.
- ⚠️ **Prima di aggiungere un motivo, verificare che sia raggiungibile.** «Riga
  registrata» sembrava il primo motivo da scrivere: è coperto da «distinta
  finale» per costruzione, e un motivo che non scatta mai è un caso finto nel
  tooltip e nel test.
- 🔴 **Prima di chiudere una porta, censire chi ci passa** (2026-09-14, in
  sviluppo). «Il guard chiude anche il `DELETE`, con lo stesso predicato» era
  scritto qui sopra e verificato contro gli altri guard — non contro le
  **madri**: `vendite.fn_cancella_fondo_fattura` cancella fisicamente righe
  sotto una `GENERATA`, e il predicato del cestino dell'operatore l'avrebbe
  fermata. Lo ha trovato un `grep` di `DELETE FROM pagamenti.vendite_contabili_righe`
  sulla doc auto-gen delle funzioni, prima di scrivere il trigger. *Un
  predicato scritto per un verbo (eliminare a mano) applicato a una porta
  (il `DELETE`) incontra anche gli altri verbi che passano da quella porta.*
- ⚠️ **Il nome di un guard è una promessa come un'icona.** `guard_eliminazione`
  che rifiuta un `INSERT` è lo stesso difetto del cestino su «scarta»: rinominato
  `guard_contenuto` quando D18 gli ha dato la seconda porta.
- ⚠️ **Un valore assoluto in un test è una fotografia della fixture.** Il saldo
  «in lavorazione» della fattura contava anche le righe delle altre distinte
  costruite dallo stesso file: `800` e `400` erano veri per caso, e la prima
  corsa li ha smentiti. Si asserisce il **delta** (la riga entra, la riga esce).
- ⚠️ **Provare un changeSet con l'SQL estratto e il seed nella stessa
  transazione ha una trappola sua**: un upsert di *tutte* le righe di
  `messaggi_errore` prende lock `FOR UPDATE` (la chiave `codice` è in un indice
  unico), e il primo errore di dominio su un codice **esistente** fa aspettare
  la sessione `dblink` di `fn_log_error_only` sulla FK di `error_log` — che
  aspetta la transazione, che aspetta il dblink. Un deadlock fra due sessioni
  che PostgreSQL non vede. La prova inserisce **solo** le righe nuove; l'upsert
  completo si prova **a parte**.
- 🔵 **Residuo dichiarato, non di questo cantiere**: sotto una distinta
  **finale** la porta 2 tace di proposito (la sede è `guard_distinta_finale`,
  che lascia «le altre scritture su una riga già lì»), quindi l'**importo** di
  una riga sotto una `CHIUSA` — anche `POSTATA`, col suo movimento — resta
  modificabile da SQL. Nessun verbo del BE lo fa; è un buco del modello che
  questo cantiere ha visto e non chiude, perché chiuderlo è un'altra decisione
  (fatti immutabili sotto una finale, per ogni origine).

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-14 | Stesura, dal primo collaudo in-app di Tid (prima contabile caricata). Tre rilievi letti sul modello: **D16** (la riga manuale nasce con la destinazione, l'eccezione si dichiara — DB invariato, contratto già pinnato), **D17** (elimina riga = `attivo=false` su manuale in bozza; check + guard su disattivazione **e** `DELETE`; `SCARTATA` non è un'eliminazione e rompe la quadratura), **D18** proposta (congelamento del contenuto sotto `VALIDATA`, solo `MANUALE`). Chiarito che validare ≠ registrare e che il copione salta il passo di validazione. Piano DB in sei passi; a BE e FE l'elenco di cosa fare. Niente applicato |
| 2026-09-14 (sera) | **Sviluppo DB scritto**, nessun apply. Due decisioni di Tid durante il lavoro: **D18 confermata** (P-5 nello stesso changeSet di P-2) e la **porta `DELETE`** — il giro dei fondi (`fn_cancella_fondo_fattura`) cancella fisicamente righe sotto una `GENERATA`, e «stesso predicato» l'avrebbe fermato: la madre apre la porta con la GUC `zeroerp.allow_contabile_riga_delete_override` e la richiude (P-2 bis, precedente `fn_change_user_emittenti_scope`). Il guard si chiama **`guard_contenuto`** (due porte). P-0 era già coperto dai test 5-6 di `test-abbinamento-rata` (la riga del brief era falsa). Scritti: `20260914-04` (check), `-05` (guard + trigger, porte 1 e 2), `-06` (rev madre del giro); seed id 1063-1064 + due note; pgTAP nuovo 30/30; cinque cleanup e il rubinetto (16→17) adeguati; sei documenti. Provato con l'SQL estratto in `BEGIN … ROLLBACK`: 30/30 + 110/110 + 168 verdi. **Da fare dopo l'apply**: il runner come app sul nuovo test e su `pagamenti`/`vendite`; BE-6 (`genera_error_policies` + ripieghi); FE-5 (le tre `reason_key` in `it.json`/`en.json`, `check_i18n_keys.py` controllo 4 è rosso finché mancano, dalla rigenerazione della doc) |
| 2026-09-14 15:49 | **Applicato su dev** (`20260914-04/05/06`), seed compreso; pgTAP verdi col runner come applicazione — quindi anche la lettura sotto RLS della check e del guard, che la prova da owner non poteva esercitare. **DB chiuso.** Da qui: BE-1…BE-8 e FE-1…FE-9 (piano in `brief-be-fe-posting-e-abbinamento-rata.md`), il copione §7, la rigenerazione della doc auto-gen (le due schede manuali nuove entrano nel sito da lì), e la baseline CI al primo giro verde. Resta dichiarato e **non pianificato** il residuo di §8 (fatti modificabili sotto una distinta finale): è una decisione, non un passo |
| 2026-09-14 (sera, dopo) | ✅ **Sviluppo BE/FE scritto** (su «procedi» di Tid; Q-A sì, Q-D strada B, le altre come proposte). BE: `crea_riga` con la destinazione (un `INSERT`, `ABBINATA`/`DA_ABBINARE` dalla presenza della fattura, BA letto dal documento se assente, lettura unica `_destinazione_da_payload` condivisa con `abbina`), `DELETE /righe/{id}/` → `attivo = false`, le **quattro** colonne `elimina_blocco_*`/`can_eliminare` in LATERAL sul frammento condiviso (misurato con EXPLAIN: Function Scan sotto la WindowAgg, accanto ai predicati RLS — resta), `transizioni.{distinta,riga}` dalle due matrici al posto di `stati_richiedibili`, `contenuto_modificabile`, `stato_info_key` dal `meta`; e **`get_riga` filtra `attivo`** (il buco). FE: `RataSelect` estratto (dialogo + form), form riga documento-first con importo proposto e toggle «non riesco ad associarlo», forzatura a due tempi alla nascita, «Elimina» col cestino e il motivo dal DB (`bloccoMotivo`), `SCARTATA` con icona sua, transizioni e `modificabile` dal dettaglio, `:info-key`, chiavi i18n (compresi i cinque `stato_info.*`). Copione §7 riscritto (§2.6–2.9, §3.1–3.3, §4.0). 📮 Al DB: **P-8** seed `nessuna_azione_key` (righe esatte in §4) e **P-9** doc auto-gen. Nessun commit |
| 2026-09-15 | ✅ **Q-H decisa: strada A** (Tid). Il PATCH della riga accetta `forzata` + `motivo_forzatura` come secondo tempo della capienza, con la stessa regola della nascita e di `abbina` (una funzione: `_guard_motivo_con_forzatura`); R-6 resta intero sulla destinazione. Schema OpenAPI, `api_pagamenti.md` §PATCH, client `aggiornaRiga`, form riga a un handler solo con `extra` in entrambi i modi. Test: +5 a mock (`ModificaTests`), **+2 sul DB provvisto** con fixture costruita (`ModificaSecondoTempoTests`: 400→900 rifiutato `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`/`confirm_and_retry` e riga intatta; con `forzata` passa e resta scritto). Resta aperto **C-2**. Verificato a repo lo stato DB: **P-9 già fatta** (`84f1b3fd7`), **P-8 no** (`meta = {}` sulle cinque righe del CSV) |
| 2026-09-15 (DB) | ✅ **P-8 scritto**: `meta.nessuna_azione_key` sulle cinque righe di `pagamenti/vendite_contabili_stati.csv`, forma dei CSV gemelli (`"{""nessuna_azione_key"":""pagamenti.distinte.stato_info.bozza""}"`). Solo il CSV: i mirror sono **due** (`20260213-04` + ri-ancorato `20260821-30`), `runOnChange` + `ANY`, già `RERAN`/`EXECUTED` — rileggono il file al prossimo migrate. Prova su dbdev in `BEGIN … ROLLBACK`: CSV = DB prima dell'edit (nessuna mina stantìa), upsert di **tutte** le righe passato (`UPDATE 5`, nessuna irriscrivibile, `lock_columns` non si oppone), `meta ->> 'nessuna_azione_key'` risponde con le cinque chiavi; `check_i18n_keys.py` verde. Scheda `pagamenti/manual/vendite_contabili_stati.md`: il `meta` dichiara la chiave e rimanda allo standard `infoKey` (e il codice d'esempio smette di dire `DRAFT`). **Apply e runner di Tid**; nessun commit. Resta aperto C-2 |
| 2026-09-15 (chiusura) | ✅ **CHIUSO e archiviato in `work-done/`** (riquadro in testa). C-2 esce dal brief e vive nel copione di collaudo, riquadro «C-2»; i residui di modello (fatti sotto una finale, `meta` delle matrici, sede unica del motivo 3) vanno al brief madre §2-bis; Q-C e Q-G al brief BE/FE §10.12; l'apply di P-8 resta a Tid come stato di macchina. Link relativi riscritti, schede manuali ri-puntate |
| 2026-09-14 (sera, rilettura critica) | 🔍 **Rilettura del BE/FE scritto**, sul non committato. Un **difetto** corretto: in **modifica** il form riga passava da `useForzaturaConfermata` e sul 409 di capienza (che `guard_rata` solleva anche sull'`UPDATE` di `importo`) offriva un «Forza» che ripeteva lo stesso PATCH senza `forzata` — un pulsante che il DB rifiuta; ora la modifica usa un handler suo e il 409 è un toast, come prima. Il buco di modello che ci sta sotto è **Q-H** (§10.4). Un **codice fragile** chiuso nel BB: `useLetturaTreStati` non aveva guard di versione, e due letture in volo (cambio fattura in `RataSelect`, saldo in `useSaldi`) potevano lasciare a video il documento sbagliato — `useFetchVersion` dentro, 6 test costruiti (`useLetturaTreStati.spec.js`). **Duplicati** tolti: il predicato «stato vivo» scritto sei volte nel repository (`_sql_stato_vivo`), la whitelist di `crea_riga` che ricopiava `_CAMPI_RIGA_PATCH`, `E_FATTURA_NON_TROVATA` dichiarato in tre service (ora in `_helpers`). Doc `api_pagamenti.md` §abbina allineata (il cliente si deriva). Registro `datatable.baseline.json` abbassato (il commento sopra l'import era arrivato senza il verso). 4800 BE + 50 FE verdi, lint, build, guards, i18n |
| 2026-09-14 (sera) | 📋 **Analisi e piano BE/FE scritti in §10**, fermo al piano (Tid). Misurato sul codice: **BE-6 e la metà i18n di FE-5 erano già chiusi** (`eeed40be8`, altro cantiere, stesso giorno); BE-2 e BE-8 non hanno lavoro; tutto il resto è 🔴. Tre correzioni a §5/§6: BE-4 porta **quattro** colonne (terna + flag, perché `bloccoMotivo.js` le legge così), BE-5 vale **anche per la testata** (oggi coincide con la matrice per caso; e la matrice ha `meta.manuale = false` ovunque — residuo di modello per il DB), FE-9 a standard passa da un **seed** `nessuna_azione_key` sugli stati (P-8) e non da un `v-if`. 🔴 **Un buco che nasce con D17**: `get_riga` non filtra `attivo`, quindi `PATCH`/`stato`/`abbina` passerebbero su una riga eliminata che nessuna lista mostra — si chiude in A-3. Regola del 2 da dichiarare: `RataSelect` (seconda occorrenza del giro fattura → rate col saldo) e `_destinazione_da_payload`. Sette decisioni in §10.4. Nessun codice scritto |

---

## 10. Analisi e piano BE/FE *(2026-09-14, scritto dal lato BE/FE; eseguito la sera stessa — stato per voce in §10.1 e per passo in §10.3)*

> **Perché sta qui e non nel piano BE/FE.** La sede naturale sarebbe
> [brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md)
> (la sua riga di registro del 14/09 dice *«il piano lo scrive questo
> documento»*): Tid ha chiesto di scriverlo **qui**, accanto alle decisioni. Il
> consuntivo, quando si costruirà, andrà nel §10 di quel documento — questa
> sezione è il piano e resta il piano.
>
> ⛔ **Niente è stato scritto in codice.** Ogni riga qui sotto è misurata sul
> codice e sul database vivo del 2026-09-14 (dopo l'apply delle 15:49), e la
> misura serve a trovare dove il brief e il codice non si parlano — non a
> decidere la forma di ciò che si costruisce.

> ✅ **Sviluppo BE/FE scritto il 2026-09-14 (sera), su «procedi» di Tid** —
> Q-A estrazione **sì**, Q-D **strada B**, le altre cinque come proposte in
> §10.4. Consuntivo nel piano BE/FE
> ([§10.12](brief-be-fe-posting-e-abbinamento-rata.md)); qui resta il piano e
> lo stato per voce. Verdi: **217** test backend (DB e2e compresi, 11 nuovi sul
> DB provvisto + 25 a mock), build · eslint · oxlint · `check_i18n_keys.py`.
> 📮 Al team DB restava **P-8** (seed, per FE-9): ✅ **scritto il 15/09**,
> aspetta il migrate; **P-9** è entrata con `84f1b3fd7`. Nessun commit.

### 10.1 Il terreno, misurato sul codice

| Voce | Stato | Dove, verificato |
| --- | --- | --- |
| **BE-6** | ✅ **già chiuso, e §5 non lo sa** | `error_policies_generated.py` ha i due codici con classe `CONFLITTO_STATO`, `manage.py genera_error_policies --check` risponde *«allineato al catalogo»*, e `error_messages_fallback.py` porta i due ripieghi senza `%s`. Entrati con `eeed40be8` (14/09, il cantiere «modifiche certe ciclo vendita» ha rigenerato e li ha raccolti). `test_error_policies_classi` verde |
| **FE-5**, la metà i18n | ✅ **già fatta** | le tre `pagamenti.righe.elimina_reason.{distinta_finale, distinta_non_manuale, distinta_validata}` sono in `it.json` **e** `en.json` (stesso commit). ⚠️ Il controllo 4 di `check_i18n_keys.py` legge la **doc auto-gen** delle funzioni: fino al `84f1b3fd7` la scheda di `fn_check_riga_contabile_eliminabile` non c'era e il cancello non le cercava; ✅ ora c'è, **le cerca e le trova** (verde il 15/09) |
| **BE-2** | ✅ **per costruzione** | `confirm_and_retry` è dichiarato sul **codice** `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` in `error_ui_overrides.py`, non sull'endpoint: il 409 di un `INSERT` lo porta come quello di un `UPDATE`. Resta da **provare**, non da scrivere |
| **BE-8** | ✅ niente da fare | zero occorrenze di `allow_contabile_riga_delete_override` in `backend/` |
| **BE-1** | ✅ A-1 | ~~`crea_riga` ammette i soli fatti~~ *(era così al piano)*: `crea_riga` ammette i soli fatti (`validate_allowed_keys`), `create_riga` non ha i parametri di destinazione — **tolti** dalla revisione del 24/08 come *«seconda porta per scrivere l'abbinamento»* — e `STATO_RIGA_INIZIALE = "DA_ABBINARE"` è cablato col commento *«quando il denaro arriva non si sa ancora di chi sia»*: è esattamente il default di §8. ⭐ La ragione del 24/08 **decade con D16**: la porta non aggira il verbo, è il verbo alla nascita, e i guard sull'`INSERT` sono gli stessi dell'`UPDATE` |
| **BE-3** | ✅ A-3 | *(al piano)* `ApiRigaDetail` ha il solo `patch`. Precedente per la forma: `DELETE /vendite/fondi-fattura/{id}/` — `handle_post_json` con `require_idempotency_key=True` e payload ignorato |
| **BE-4** | ✅ A-2 | *(al piano)* `_RIGA_COLONNE`/`_RIGA_FROM` non hanno la LATERAL. Precedente: `registri_repository._LATERAL_BLOCCHI` (terna `reason/reason_key/dettaglio` + flag `can_*`). 🔴 **Il brief dice due colonne; il BB FE ne legge tre più il flag** — §10.2 |
| **BE-5** | ✅ A-4 | *(al piano)* `stati_richiedibili.riga` è il vocabolario intero; il FE toglie solo lo stato corrente e `ABBINATA`. Nessun lettore delle due matrici in tutto `backend/`. ⚠️ **E la matrice ha `meta = {"manuale": false}` su tutte le righe** (seed `20260821-31`): il campo previsto per «chi può chiedere» (col suo `CHECK` su `action_key`/`label_key`) non è usato — il vocabolario vive nel BE (`STATI_*_RICHIEDIBILI`) |
| **BE-7** | ✅ A-5 | *(al piano)* nessun `contenuto_modificabile`; il FE ha `modificabile = !stato_is_final` ⇒ **sotto `VALIDATA` il form si apre e il DB rifiuta** (dal 14/09): un difetto §12 nato con l'apply, non col collaudo |
| **FE-1…4** | ✅ B-1 · B-2 | *(al piano)* `DistintaRigaForm` = soli fatti in entrambi i modi. ⭐ `AbbinaRigaDialog` ha **già tutto il giro**: `FatturaLookup` → rate col saldo (`useLetturaTreStati` + `listRateFattura`) → forzatura (`useForzaturaConfermata`). Il form in creazione è la **seconda occorrenza** — §10.4 Q-A |
| **FE-5**, l'azione | ✅ B-3 | *(al piano)* `buildRowActions` offre `abbina` + le transizioni; nessun «elimina» |
| **FE-6** | ✅ B-3 | *(al piano)* `ICONA_TRANSIZIONE_RIGA.SCARTATA = MANAGE_ICONS.DELETE` (`DistintaDrawer.vue`). ⭐ Il precedente è **scritto in `constants.js` accanto a `UNDO`**: il 19/08 il cestino sull'annullo dell'accredito era già stato letto come «elimina» |
| **FE-7 · FE-8** | ✅ B-4 | dipendevano da BE-5 e BE-7 |
| **FE-9** | ✅ B-5 *(testo all'apply di P-8)* | *(al piano)* nessun pannello. ⭐ Il BB esiste — `DrawerActionsBar :info-key` — ed è in servizio su **otto** drawer; ma lo standard vuole la chiave **dal `meta` dello stato** e `vendite_contabili_stati.meta` è `{}` su tutte le righe — §10.2 |
| **§7 copione** | ✅ C-1 · 🔴 C-2 | riscritto (§2.6–2.9, §3.1–3.3, §4.0); **la prova in-app resta da fare** |
| 🆕 **Un buco che nasce con D17** | ✅ A-3 | *(al piano)* `get_riga` **non filtra `attivo`**: `_riga_o_404` trova una riga eliminata, e `PATCH`, `stato/` e `abbina/` passerebbero su una riga che nessuna lista mostra. Prima di D17 non c'era modo di produrla dall'app; adesso c'è. Si chiude nello stesso giro (A-3) |
| Baseline | ✅ | `apps.pagamenti.tests` + `test_error_policies_classi`: **156 verdi**, 1 skip, prima di toccare qualcosa. **Dopo**: 179 in `pagamenti` (DB e2e compresi), 4800 sull'intera suite BE, 50 FE — alla rilettura del 14/09 sera |

### 10.2 Tre cose che il piano cambia rispetto a §5/§6, e perché

| | Cosa | Perché |
| --- | --- | --- |
| **1 · BE-4 porta QUATTRO colonne** | `elimina_blocco_reason` · `elimina_blocco_reason_key` · `elimina_blocco_dettaglio` (jsonb **decodificato**) · `can_eliminare` (`reason IS NULL`) | il BB FE che compone la frase — `core/utils/bloccoMotivo.js` — legge la **terna** `<verbo>_reason/_reason_key/_dettaglio` (i parametri della chiave i18n stanno in `dettaglio`, non in `valori`) e `bloccoAttivo` legge il **flag** quando c'è. È la famiglia dei registri (`can_disattivare` + `rimozione_blocco_*`), che api.md §capability dice di seguire *«invece di coniarne una quarta»*. Con due colonne sole la frase uscirebbe senza parametri e il blocco si dedurrebbe dal testo |
| **2 · BE-5 vale anche per la TESTATA** | `get_distinta` espone `transizioni: {distinta: {stato: [stati_a…]}, riga: {…}}`, lette dalle **due** matrici e ristrette ai richiedibili | oggi le due liste della testata coincidono con la matrice **per caso** (`BOZZA→VALIDATA/ANNULLATA`, `VALIDATA→BOZZA/ANNULLATA`): un'asimmetria fra testata e riga si chiude subito, non in fase due — e la lettura è una sola. ⚠️ **Residuo di modello, per il team DB, non di questo giro**: con `meta.manuale` a `false` ovunque, «chi può chiedere» vive nel BE e non nella matrice. Spostarlo (seminare `manuale`, `action_key`, `label_key`) è una decisione DB; qui si legge la matrice così com'è |
| **3 · FE-9 non è solo FE** | la chiave dello stato arriva dal **`meta` del catalogo** (`nessuna_azione_key`, lo stesso campo degli otto domini), il BE la trasporta come `stato_info_key`, il FE la passa a `:info-key` | frontend-standards §`infoKey`: *«un `v-if` su `stato_codice_interno` nel drawer sarebbe la stessa regola scritta due volte»*. ⇒ serve un **seed** (P-8, DB) su `pagamenti.vendite_contabili_stati`: `BOZZA` → `pagamenti.distinte.stato_info.bozza`, `VALIDATA` → `…validata`, `CHIUSA` → `…chiusa`, `ANNULLATA` → `…annullata`, `IMPORTATA` → `…importata`. ⭐ BE e FE **non aspettano**: la colonna si legge (oggi `NULL`) e le chiavi entrano nei locales; il testo compare all'apply del seed. ⚠️ Le chiavi vanno nei locales **prima** del seed, o `check_i18n_keys.py` (controllo 4, che scandisce ogni CSV) è rosso fra i due branch |

### 10.3 Il piano

Ordine: **BE prima** (il FE legge colonne che oggi non esistono), con ogni SQL
provato con `EXPLAIN` sul database vero e ogni contratto dichiarato provato per
intero; poi FE; poi il copione. Nessun commit di iniziativa; nessuna estrazione
prima dell'ok (§10.4).

#### Slice A — Backend

| | Passo | Cosa | Note |
| --- | --- | --- | --- |
| ✅ **A-1** | BE-1 + BE-2 | `crea_riga` ammette anche `fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`, `motivo_forzatura`. Con `fattura_id` lo stato è `ABBINATA`, senza è `DA_ABBINARE` — **un solo `INSERT`** (`create_riga` riprende i parametri, e il commento del 24/08 si riscrive: la porta è dichiarata). `billing_account_id` assente ⇒ derivato con `get_riferimenti_fattura` (già esiste, porta il 404 `E_FATTURA_NON_TROVATA`). Rifiuti 400 (`E_PAGAMENTI_VALIDATION`, con `field`): `scadenza_id`/`forzata`/`motivo_forzatura` **senza** `fattura_id`; `motivo_forzatura` senza `forzata` (regola già in `abbina_riga`) | `STATO_RIGA_INIZIALE` sparisce: nascono `STATO_RIGA_SENZA_DESTINAZIONE` e resta `STATO_RIGA_ABBINATA`, con la ragione di D16 nel commento. ⛔ Il service **non nomina** capienza né saldo (il presidio statico esistente si estende a `crea_riga`). La lettura della destinazione dal payload diventa **una** (`_destinazione_da_payload`, Q-B) |
| ✅ **A-2** | BE-4 | `_RIGA_FROM` prende la `LEFT JOIN LATERAL … ON TRUE` sulla check (`ORDER BY ord LIMIT 1`, forma di `_LATERAL_BLOCCHI`), `_RIGA_COLONNE` le quattro colonne di §10.2-1; `_shape` decodifica `elimina_blocco_dettaglio` con `jsonb_out`; `RigaContabileRow` in `types.py` le dichiara | ⭐ Il frammento è **condiviso** fra `list_righe`, `get_riga` e la coda: una sede, e la coda le porta per costruzione (BE-4 come scritto). ⚠️ **Costo, letto sul piano**: nella coda `_lista_paginata` avvolge la `SELECT` in `COUNT(*) OVER()`, quindi la LATERAL gira per ogni riga **filtrata**, non per riga di pagina (stessa trappola annotata sul tab BA). Si misura con `EXPLAIN`; se pesa, la coda si ristruttura **pagina prima, motivo dopo** (LATERAL sul risultato paginato) — decisione da prendere col piano in mano, non prima |
| ✅ **A-3** | BE-3 + il buco | `ApiRigaDetail.delete` → `handle_post_json(…, require_idempotency_key=True)` con payload ignorato → `pagamenti_service.elimina_riga(riga_id)` → `repository.disattiva_riga`: `UPDATE … SET attivo = false WHERE id = %s AND attivo IS TRUE`. Il DB rifiuta con `E_RIGA_CONTABILE_DISTINTA_*` (409), il traduttore li estrae dal testo come oggi. ⭐ **`get_riga` filtra `attivo IS TRUE`**: una riga eliminata non è raggiungibile da nessun verbo (`PATCH`, `stato/`, `abbina/`, un secondo `DELETE`) e risponde `E_RIGA_CONTABILE_NON_TROVATA` — la stessa risposta di «non la vedi», no-leak, coerente con `list_righe` che non la mostra | risposta `{"riga_id", "eliminata": true}`. Un doppio invio lo copre l'`Idempotency-Key`, non un ramo «già eliminata». ⛔ Nessuna copia del predicato in Python |
| ✅ **A-4** | BE-5 (+ testata) | `repository.list_transizioni()` legge le **due** matrici (`attivo IS TRUE`, codici via JOIN sui cataloghi, stati ritirati esclusi) in una query; il service le restringe a `STATI_*_RICHIEDIBILI` sullo stato di arrivo e le espone in `get_distinta` come `transizioni.{distinta, riga}` — mappa `stato_da → [stato_a…]`. `stati_richiedibili` **esce** dal dettaglio nello stesso giro (B-4 lo sostituisce): un vocabolario senza lo stato di partenza è esattamente *«il vocabolario offerto per intero»* di §8, e lasciarlo accanto alle transizioni sarebbe una seconda lista da tenere allineata | ⭐ Presidio contro il DB vero: **ogni** richiedibile compare come `stato_a` in matrice (vocabolario ⊆ grafo) — un richiedibile irraggiungibile è un pulsante che il DB rifiuta, ed è il difetto del collaudo |
| ✅ **A-5** | BE-7 + BE di FE-9 | `get_distinta` espone `contenuto_modificabile = (stato_codice_interno == BOZZA and origine == MANUALE)` — **copia dichiarata** del motivo 3 (il DB stesso lo scrive due volte, §4 P-5), con un presidio che la lega ai codici a catalogo; e `stato_info_key` da `st.meta ->> 'nessuna_azione_key'` nella `_DISTINTA_SELECT` (il JOIN su `vendite_contabili_stati` c'è già) | 🔵 residuo per il team DB: con una `fn_check_contabile_contenuto_modificabile(p_contabile_id)` il BE **leggerebbe** invece di derivare, e anche il guard avrebbe una sede sola. Non si chiede in questo giro: BE-7 è deciso così |
| ✅ **A-6** | Test | service (mock): destinazione → `ABBINATA` e i cinque campi passano **intatti**; senza → `DA_ABBINARE`; i quattro rifiuti 400 di A-1; BA derivato se assente; il primo tentativo non è forzato; `elimina_riga` 404 su riga assente/inattiva e 409 tradotto dal marker DB; `contenuto_modificabile` sulle quattro combinazioni; `transizioni` ristrette ai richiedibili. API: `DELETE` senza `Idempotency-Key` = 400, con = 200; `POST righe/` con destinazione passa al service. DB vero (`richiedi_db_provvisto`): le quattro colonne esistono (`cursor.description`, anche a lista vuota); `script.fn_check_riga_contabile_eliminabile` esiste con arità 1; `EXPLAIN` su `_RIGA_SELECT`, `get_riga`, coda (ogni ordinamento dichiarato — il presidio esistente si estende da sé) e `list_transizioni`; vocabolario ⊆ matrice (A-4); i cinque `stato_info_key` **non** si asseriscono valorizzati finché P-8 non è applicato — si asserisce che la colonna c'è | ⛔ Le madri non si chiamano. ⚠️ Un test che asserisca «`stato_info_key` è `NULL`» sarebbe il test che tiene fuori il numero il giorno che arriva (§10.10 del piano BE/FE): non si scrive |

> ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_shape` di `pagamenti_repository` è ritirato. `elimina_blocco_dettaglio` arriva decodificato dal lettore comune (`rows_to_list` / `fetch_paged_with_total`, dal tipo della colonna).

#### Slice B — Frontend

| | Passo | Cosa | Note |
| --- | --- | --- | --- |
| ✅ **B-1** | estrazione *(dopo l'ok, Q-A)* | `RataSelect.vue` in `pagamenti/components/`: prende `fatturaId`, tiene `scadenza_id` in `v-model`, emette `select` con la rata **intera** (serve il residuo), dentro ha il terzetto «rate · nessuna · non lette» (`useLetturaTreStati`), `etichettaRata` col residuo negativo detto a parole e la nota «facoltativa». `AbbinaRigaDialog` lo adotta nello stesso giro | è la seconda occorrenza, dichiarata già in §5.3 del piano BE/FE come *«aspetta la seconda»* |
| ✅ **B-2** | FE-1 · FE-2 · FE-3 · FE-4 | `DistintaRigaForm` in **creazione** parte dal documento: `FatturaLookup` → `RataSelect` → **importo proposto** (residuo della rata scelta; senza rata, residuo del documento da `useSaldi(LIVELLO.DOCUMENTO)`, la base unica) → fatti. La proposta riempie l'importo solo se **vuoto o ancora proposto**, mai sopra un valore digitato. Toggle «**Non riesco ad associarlo**»: scopre i soli fatti, azzera fattura e rata, la riga nasce `DA_ABBINARE`. Il salvataggio passa da `useForzaturaConfermata` come il dialogo (primo tentativo **senza** `forzata`; sul 409 confermabile: messaggio del DB coi numeri + motivo + «Forza»). In **modifica** il form resta sui fatti (R-6) | ⚠️ `billing_account_id` si manda dal lookup quando c'è (il BE deriva se manca). ⚠️ Il blocco «richiesta di conferma» (Message + motivo + pulsanti) è la seconda occorrenza di un markup che nel dialogo vive nel footer: si dichiara (Q-C), non si estrae senza ok |
| ✅ **B-3** | FE-5 · FE-6 | azione di riga **«Elimina»**: `MANAGE_ICONS.DELETE`, `severity: 'danger'`, `disabled: bloccoAttivo(riga, 'elimina_blocco', 'can_eliminare')`, `tooltip: motivoBloccoRiga(t, te, riga, 'elimina_blocco')`, `confirmAction` rossa → `eliminaRiga(id)` (`api.delete` + `Idempotency-Key`) → `ricarica`. `SCARTATA` prende un'icona **sua** nella mappa locale (`'pi pi-ban'`, letterale: un lettore solo, frontend-standards §«dove vive il nome di un'icona») | chiavi nuove `pagamenti.righe.{elimina, conferma_elimina, eliminata}` in `it` e `en` |
| ✅ **B-4** | FE-7 · FE-8 | le voci «Porta a …» — testata **e** riga — si costruiscono da `transizioni.<x>[stato_corrente]` (meno `ABBINATA`, che ha il verbo), non più da `stati_richiedibili`; `modificabile = !isReadonly && distinta.contenuto_modificabile` (governa «Nuova riga», il click di modifica e la sezione form). Le **decisioni** (abbina, porta a) restano governate da `finale \|\| foglioChiuso` come oggi: sotto `VALIDATA` si abbina, non si digita | ⛔ nessun `if stato === 'BOZZA'` nel FE: il flag viaggia |
| ✅ **B-5** | FE-9 | `<DrawerActionsBar :actions="drawerActions" :info-key="distinta?.stato_info_key \|\| ''" />` + le cinque chiavi `pagamenti.distinte.stato_info.*` in `it` e `en` (BOZZA *«bozza: si digita»* · VALIDATA *«pronta da registrare: il denaro non è ancora registrato»* · CHIUSA *«registrata»* · ANNULLATA · IMPORTATA) | il testo compare quando P-8 è applicato; fino a lì la barra è come oggi |
| ✅ **B-6** | Verifiche | build · eslint · `check_i18n_keys.py` · `check_license.py` · il grep delle `DataTable` grezze **non sale** | il drawer usa già una `DataTable` grezza per le righe (eccezione ammessa: righe di un documento nel suo master) senza il commento sopra l'import: si aggiunge il commento, non si migra a `RigheMasterDetailTable` in questo giro |

#### Slice C — Il copione e la prova a video

| | Passo | Cosa |
| --- | --- | --- |
| ✅ **C-1** | §7 di questo brief | riscrivere `collaudo-in-app-incassi-distinte-e-sistemazioni.md`: **§2.6** (la riga nasce cercando la fattura 103, rata scelta, importo **proposto** 400,00 → `ABBINATA`), 🆕 **§2.8** (elimina una riga sbagliata in bozza: sparisce e la quadratura torna; sotto `VALIDATA` il cestino è **spento col motivo**), **§3.1–3.3** (ri-abbinamento: `ABBINATA → DA_ABBINARE → abbina`; e l'eccezione: una riga «non identificata» compare in **Da abbinare**), 🆕 **§4.0** («Porta a VALIDATA» prima di «Registra»: con un dichiarato sbagliato si ferma **qui**), e la riga di stato del drawer (§FE-9) come cosa da leggere in §2.4 |
| 🔴 **C-2** | in-app | il giro intero con un operatore **dentro** il perimetro, e la lista con uno **fuori** |

#### 📮 Al team DB *(prerequisiti, nessuno bloccante per iniziare)*

| | Cosa | Serve a |
| --- | --- | --- |
| ✅ **P-8** *(scritto 15/09, apply di Tid)* | seed `meta.nessuna_azione_key` sulle cinque righe di `pagamenti/vendite_contabili_stati.csv` (chiavi in §10.2-3) — §4 P-8 | FE-9 a standard |
| ✅ **P-9** | rigenerazione della doc auto-gen (le due schede nuove + il corpo della check, che il controllo 4 di `check_i18n_keys.py` legge) — **fatta** con `84f1b3fd7` (14/09) | chiudere il cerchio i18n |
| 🔵 | *(residuo, decisione)* `meta.manuale`/`action_key`/`label_key` sulle matrici, per portare «chi può chiedere» dove il modello l'ha previsto | BE-5 senza vocabolario in Python |

### 10.4 Decisioni da prendere prima di scrivere *(Tid)*

| | Domanda | Proposta |
| --- | --- | --- |
| **Q-A** | Estrarre `RataSelect` (rate col saldo, alimentate da una fattura) alla seconda occorrenza? | **sì**, in `pagamenti/components/` — entrambi i consumatori sono del dominio; passa in `core/` solo se ne nasce uno in `vendite` |
| **Q-B** | Un helper `_destinazione_da_payload(payload, *, obbligatoria)` condiviso fra `crea_riga` e `abbina_riga`? | **sì**, interno al service: la regola «motivo solo con forzatura» esiste già lì, e la seconda copia divergerebbe |
| **Q-C** | Il blocco «richiesta di conferma» della forzatura (Message + motivo + «Forza») diventa componente alla seconda occorrenza? | **non ora**: nel dialogo sta nel footer, nel form è inline — il composable è già condiviso, il markup no. Dichiarato |
| **Q-D** | FE-9 via seed `meta` + `:info-key` (P-8) o `v-if` sui flag nel drawer? | **seed**: è lo standard e il BB c'è; il `v-if` è la regola scritta due volte |
| **Q-E** | BE-5 esteso alla testata? | **sì**: simmetria, una lettura sola, stesso costo |
| **Q-F** | `billing_account_id` assente alla creazione ⇒ derivato dalla fattura (come scritto in BE-1)? | **sì**; il guard `guard_stato_dati` lo pretende comunque su `ABBINATA` |
| **Q-G** | La LATERAL «primo motivo» come BB `core/db` (oggi in `registri_repository` ×2, `vendite_repository` ×1, +questa)? | **dopo**, in un giro suo: qui si scrive nella forma dei precedenti, così l'estrazione — se si fa — trova quattro copie identiche |
| ✅ **Q-H** *(dalla rilettura critica del 14/09 sera; decisa il 15/09: **strada A**)* | Il **PATCH di `importo`** su una riga `ABBINATA` con rata incontra `guard_rata` come l'`INSERT` (la capienza si valuta a ogni `UPDATE` di `importo`) e riceve `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con `confirm_and_retry` — ma il PATCH **non porta `forzata`** (R-6), quindi il secondo tempo su quella rotta **non c'è**: il codice promette una conferma che il verbo non sa raccogliere. La prima stesura del form faceva passare anche la modifica da `useForzaturaConfermata`, e offriva un «Forza» che ripeteva lo stesso PATCH (rifiutato di nuovo): **corretto** — in modifica il 409 è un toast, come prima del 14/09. Resta la domanda di modello | **Proposta**: ammettere `forzata` + `motivo_forzatura` sul PATCH come secondo tempo (stessa forma dell'`INSERT`: sono la conferma di *questa* scrittura, non la destinazione — R-6 protegge `fattura_id`/`billing_account_id`/`scadenza_id`, e resterebbe intero). L'alternativa era tenere R-6 così com'è e dichiarare il rimedio «elimina e ricrea» (D17, solo in bozza). ✅ **Tid ha scelto A** (15/09): `_CAMPI_FORZATURA` nel PATCH con la regola «motivo solo con forzatura» in una funzione sola (`_guard_motivo_con_forzatura`, usata da nascita, abbinamento e modifica); il form torna a un handler solo e passa `extra` anche ad `aggiornaRiga`. Provato per intero sul DB vero (fixture costruita: rata piena, PATCH 400→900 rifiutato confermabile, con `forzata` passa e resta scritto) |

### 10.5 Cosa il piano NON fa, e perché

| Non fa | Perché |
| --- | --- |
| Non migra il drawer a `RigheMasterDetailTable` | debito pre-esistente (la `DataTable` grezza con macchina a stati propria è del 28/08), non di questo giro; si dichiara col commento sopra l'import |
| Non sposta il vocabolario dei richiedibili nella matrice | è una decisione DB (§10.2-2), e il BE deve comunque saper leggere la matrice così com'è |
| Non chiede `fn_check_contabile_contenuto_modificabile` | BE-7 è deciso come derivata; il residuo è scritto in A-5 per quando il DB vorrà una sede sola |
| Non chiude il residuo di §8 (fatti modificabili sotto una finale) | è una decisione di modello, dichiarata lì |
| Non rigenera la doc auto-gen | è del team DB (P-9) |
| Non riabilita una riga eliminata | D18 chiama la riattivazione «contenuto» e nessun verbo la offre: un `DELETE` è definitivo per l'app, e la traccia resta a DB |
