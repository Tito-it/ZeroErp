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
> ([brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis), che resta la sede unica. Il **piano DB** è qui (§4). Per BE e FE
> qui c'è **solo l'elenco di cosa fare** (§5, §6): il piano lo scrivono loro
> in [brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md).
>
> ✅ **Applicato su dev il 2026-09-14 alle 15:49** (`databasechangelog`:
> `20260914-04`, `-05`, `-06`), pgTAP verdi col runner come applicazione
> (Tid). Il brief era stato scritto la mattina misurando contro il modello vivo
> (doc auto-gen), non contro i dati: `pagamenti` aveva ancora zero righe di
> esercizio. **La parte DB è chiusa**; restano BE (§5), FE (§6) e il copione
> (§7), più la rigenerazione della doc auto-gen per le due schede nuove.
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

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| **D16** | La riga **manuale** nasce con **fattura, cliente e (facoltativa) rata**, direttamente `ABBINATA`; la riga **senza destinazione** è un'eccezione che l'operatore **dichiara**, nasce `DA_ABBINARE` e si recupera dalla coda. ⭐ **Il DB non cambia**: i guard girano già sull'`INSERT`, la matrice è solo su `UPDATE`, e il pgTAP dell'abbinamento inserisce già righe in `ABBINATA` | §2.1 · §4 P-0 |
| **D17** | **Elimina riga** = `attivo = false`, ammesso **solo** su distinta `MANUALE` in `BOZZA`. Un predicato `script.fn_check_riga_contabile_eliminabile` (tre motivi ordinati), un guard che lo chiama su `attivo → false` **e** su `DELETE`, due codici nuovi + uno riusato. ⚠️ `SCARTATA` resta, ma **non è un'eliminazione**: conta nella quadratura (D12-e). 🔴 Il `DELETE` ha **un** passaggio legittimo — il giro dei fondi — che il brief non aveva visto: §4 P-2 | §2.2 · §4 P-1…P-4 |
| **D18** ✅ | *(confermata da Tid il 2026-09-14)* Sotto `VALIDATA` il **contenuto** della manuale si congela: né righe nuove, né fatti modificati, né eliminazioni — finché non torna in bozza. Fino a quel giorno **niente lo impediva**, contro D14-a-bis | §2.3 · §4 P-5 |
| **§3** | Validare ≠ registrare: i movimenti nascono in `fn_posta_contabile`, solo da `VALIDATA`. 🔴 Il copione di collaudo **salta il passo** «Porta a VALIDATA» (§4.1) e fallirebbe per costruzione | §3 · §7 |
| **BE** | `crea_riga` accetta la destinazione e nasce `ABBINATA`; `DELETE /righe/{id}/`; la colonna `elimina_blocco_reason` in lista; le transizioni offerte **dalla matrice**, non dal solo vocabolario | §5 |
| **FE** | il form riga parte dal **documento** (lookup → rate col saldo → **importo proposto dal residuo**), «non identificato» è un gesto esplicito; il **cestino** diventa «elimina» e smette di essere l'icona di «scarta» | §6 |

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

🔴 **Il copione** ([collaudo-in-app-incassi-distinte-e-sistemazioni.md](collaudo-in-app-incassi-distinte-e-sistemazioni.md))
passa da §2.7 a §4.1 «Sul drawer → Registra» **senza** il passo «Porta a
VALIDATA»: la madre rifiuta da bozza (`E_CONTABILE_NON_REGISTRABILE`), e il
punto 4.1 fallirebbe per costruzione. Va riscritto insieme a §2.6 e §3.1 (D16)
e con una prova nuova per D17 — è lavoro del piano BE/FE (§7).

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
| **BE-1** | `POST /pagamenti/distinte/{id}/righe/` accetta anche `fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`, `motivo_forzatura`. Con `fattura_id` la riga nasce **`ABBINATA`** — **un solo `INSERT`**, atomico per costruzione; senza, nasce `DA_ABBINARE` come oggi | D16. ⛔ Non due scritture (`create` + `abbina`): i guard fanno tutto sull'`INSERT`. `billing_account_id`: se manca, si deriva dalla fattura (come già fa il dialog dell'abbinamento) |
| **BE-2** | Il doppio tempo della capienza vale anche alla creazione: il 409 `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` risale con `confirm_and_retry`, come per `abbina` | il BE **trasporta**, non decide che cosa sia forzabile |
| **BE-3** | `DELETE /pagamenti/righe/{id}/` → `UPDATE … SET attivo = false`. Il metodo dice il verbo (api.md §Grammatica URL); i motivi li dà il DB (409 `E_RIGA_CONTABILE_DISTINTA_*`), il BE traduce e passa | D17. Nessuna copia del predicato in Python |
| **BE-4** | La lista righe (`list_righe`) e la coda (`GET /pagamenti/righe/`) espongono `elimina_blocco_reason` e `elimina_blocco_reason_key` da `script.fn_check_riga_contabile_eliminabile(r.id) -> 0` in `LATERAL` (`NULL` = ammesso) | §12.5: **un verbo, una colonna**, col nome del verbo. Non riusare una colonna di un altro blocco |
| **BE-5** | Le transizioni di riga offerte al FE si derivano **dalla matrice** (`pagamenti.transizioni_stati_contabile_riga`) per lo stato corrente, non dal solo vocabolario `stati_richiedibili.riga` | oggi il FE propone `SCARTATA` su una riga `ABBINATA` e il DB la rifiuta: difetto §12 emerso al collaudo |
| **BE-6** | `genera_error_policies` + ripieghi in `error_messages_fallback.py` per i due codici nuovi; test `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | dopo l'apply di P-3 |
| **BE-7** ✅ | *(D18 confermata)* `aggiorna_riga` e `crea_riga` non hanno nulla da cambiare — il rifiuto arriva dal DB come 409 `E_RIGA_CONTABILE_DISTINTA_VALIDATA` — ma il dettaglio distinta espone un `contenuto_modificabile` derivato (`stato_codice_interno = 'BOZZA' AND origine = 'MANUALE'`) così il FE non ricalcola la regola. ⚠️ Anche la **riattivazione** e lo **spostamento** di una riga sono contenuto (§2.3): se il BE avesse un verbo per l'una o per l'altro, sotto una validata prende lo stesso 409 | una sede sola |
| **BE-8** | Il `DELETE /vendite/fondi-fattura/{id}/` **non cambia**: `fn_cancella_fondo_fattura` apre da sé la porta del `DELETE` delle righe (P-2 bis). ⛔ Il BE **non deve** impostare `zeroerp.allow_contabile_riga_delete_override` da nessuna parte: è una dichiarazione della madre, non un parametro di sessione — e una GUC lasciata aperta renderebbe verdi per sottrazione tutti i `DELETE` della richiesta | non è un permesso |

---

## 6. Cosa deve fare il frontend *(solo l'elenco)*

| | Cosa | Perché / vincolo |
| --- | --- | --- |
| **FE-1** | `DistintaRigaForm` in **creazione** parte dal **documento**: `FatturaLookup` (cerca già per numero, ragione sociale, codice BA, CF/P.IVA) → **rate col saldo** (lo stesso lettore di `AbbinaRigaDialog`, rata facoltativa) → ⭐ **importo proposto** = residuo della rata scelta (o della fattura, senza rata), modificabile → fatti (date, riferimento) | D16. La risposta alla domanda «quanto?» la dà il documento, e l'operatore corregge solo se l'importo arrivato è diverso |
| **FE-2** | «**Non riesco ad associarlo**» è un gesto esplicito (toggle/pulsante) che **scopre** i soli fatti e fa nascere la riga `DA_ABBINARE`; la riga in elenco e la coda «Da abbinare» la fanno vedere come eccezione | l'eccezione si dichiara, non è il default |
| **FE-3** | La capienza alla creazione usa `useForzaturaConfermata` come il dialog di abbinamento | stesso BB, stesso `ui_action` |
| **FE-4** | In **modifica** il form resta sui fatti (R-6); ri-abbinare resta il verbo `abbina` | la ragione di R-6 vale per una riga che ha già uno stato |
| **FE-5** | Azione di riga **«Elimina»**: cestino (`MANAGE_ICONS.DELETE`), `severity: danger`, conferma con `useConfirmAction`, `disabled` + **`tooltip`** da `elimina_blocco_reason_key` (`labelOrCode`) quando il DB dà un motivo; tre chiavi `pagamenti.righe.elimina_reason.*` in `it.json` **e** `en.json` nello stesso giro (`check_i18n_keys.py` controllo 4 è rosso finché mancano) | D17, §12.5.5: il campo si chiama `tooltip`, non `motivo` |
| **FE-6** | `SCARTATA` **non usa più il cestino** (`ICONA_TRANSIZIONE_RIGA`): un'icona di «scarto» (`pi pi-ban` o simile). Il cestino significa «elimina», e da FE-5 lo è | un'icona con due sensi è il difetto che la regola delle icone vieta |
| **FE-7** | Le voci «Porta a …» di riga si costruiscono dalle transizioni **ammesse dallo stato corrente** (BE-5), non dal vocabolario intero | §12: mai proporre ciò che verrà rifiutato |
| **FE-8** 🟡 | *(se D18)* `modificabile` = `BOZZA` e `MANUALE` (BE-7); sotto `VALIDATA` restano i verbi di decisione (abbina, sospendi) e le azioni di testata (riapri, registra) | D18 |
| **FE-9** | Il pannello di stato del drawer dice in una riga **dove si è**: «bozza: si digita» · «validata: pronta da registrare, il denaro non è ancora registrato» · «registrata» | §3: la domanda di Tid nasce da qui |

---

## 7. Il copione di collaudo — righe da riscrivere

Da rifare nel piano BE/FE, in [collaudo-in-app-incassi-distinte-e-sistemazioni.md](collaudo-in-app-incassi-distinte-e-sistemazioni.md):

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
