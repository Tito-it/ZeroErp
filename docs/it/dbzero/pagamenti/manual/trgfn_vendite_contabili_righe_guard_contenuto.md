## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la tabella che custodisce
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta di cui legge origine e stato
>
> Approfondimento funzioni:
>
> * [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile) — il predicato dell'eliminazione, che il guard chiama
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo della check
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — il guard vicino: ingresso sotto una distinta finale, sola lettura sotto un'annullata
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — la quadratura, e la riapertura della sola manuale
> * [vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura) — la madre che apre la porta del `DELETE`
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il precedente della stessa forma di porta
> * [script.fn_get_contabile_stato_origine](/dbzero/script/funzioni/fn_get_contabile_stato_origine) — origine e stato della distinta, letti fuori dalla row security
>
> Guide:
>
> * [Linee guida trigger](/linee-guida-trigger) — l'ordine alfabetico dei `BEFORE ROW`

---

### 🎯 Scopo Principale

Custodisce il **contenuto** di una distinta contabile: chi può togliere, aggiungere o cambiare
una riga, e quando. Ha due porte, che rispondono a due domande.

| Porta | Quando scatta | Chi decide |
| --- | --- | --- |
| **1 — eliminazione** | `attivo` da vero a falso, e `DELETE` | la check `fn_check_riga_contabile_eliminabile`, **chiamata**: il guard solleva il **primo** motivo e non contiene il predicato |
| **2 — congelamento** | `INSERT`; modifica di un **fatto** (importo, data di pagamento, di valuta, di operazione, riferimento dell'ente); riattivazione; spostamento da o verso un'altra distinta | sotto una **`MANUALE`** che non è più in `BOZZA` (e non è finale) il rifiuto è `E_RIGA_CONTABILE_DISTINTA_VALIDATA` |

⚠️ **Il nome dice «contenuto», non «eliminazione»**: la stessa funzione rifiuta anche un
`INSERT`, e un guard che si chiamasse *eliminazione* e rifiutasse un inserimento si leggerebbe
male esattamente quando conta.

---

### ⭐ Fatti contro decisioni

Le **decisioni** restano libere anche a distinta validata (stato, fattura, cliente, rata,
forzatura e suo motivo, motivo della sospensione, `meta`), e non è una concessione:
l'abbinamento **non tocca la quadratura**, e la madre del posting **muove lo stato** delle
righe mentre la distinta è ancora `VALIDATA`. Congelare lo stato romperebbe la registrazione.

Per questo il trigger scatta solo sull'aggiornamento dei fatti, di `attivo` e della distinta:
sulle decisioni **non scatta nemmeno**. E un aggiornamento che riscrive un fatto col valore che
aveva (il backend scrive più colonne in un colpo) passa: nessun contenuto si muove.

---

### ⛔ La porta 2 è solo della `MANUALE`


[vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) **inserisce** righe sotto una `GENERATA` che nasce già `VALIDATA`, e le aggiorna (fatti
compresi) a ogni giro; [pagamenti.fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione)
inserisce sotto una `GENERATA` in `BOZZA`. Un guard che non guardasse l'origine fermerebbe il
giro dei fondi al primo passaggio. L'immutabilità di `GENERATA` e `AUTOMATICA` arriverà con
l'import.

⚠️ **La condizione della porta 2 è il motivo «distinta validata» della check**, scritta due
volte (nella check e qui) perché sull'`INSERT` non c'è una riga da passare alla check. È una
copia **dichiarata**, e il pgTAP la lega: sotto la stessa distinta validata pretende il rifiuto
da entrambe le porte con lo stesso codice.

---

### ⭐ Il `DELETE` fisico passa dalla stessa check

Un `DELETE` è una delle tre porte dell'immutabilità, e chiuderne una sola non serve a niente:
il `DELETE` passa dalla **stessa check** della disattivazione, e una riga `POSTATA` riceve il
messaggio giusto **prima** che parli la chiave esterna del movimento.

🔴 **Ma un `DELETE` legittimo esiste, ed è del giro dei fondi.**
[vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura), sede
unica dei `DELETE` del giro (chiamata dal reset dei fondi, dall'annullo di una sistemazione e
dall'endpoint che cancella un fondo), cancella **fisicamente** le righe di un atto sotto una
`GENERATA`, dove la check risponde `DISTINTA_NON_MANUALE`: quel predicato è il cestino
dell'**operatore**, e lì non c'è un operatore.

La madre del giro **apre la porta per il proprio `DELETE`** con la GUC transazionale
`zeroerp.allow_contabile_riga_delete_override` (accesa prima, svuotata dopo), e questo guard la
onora **solo sul `DELETE`**. È la stessa forma con cui
[script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope)
attraversa il guard sul `DELETE` delle associazioni utente-emittente.

⚠️ **Non è un permesso: è la madre che dichiara «sono io»** dopo aver letto il *suo* criterio
([vendite.fn_check_fondo_cancellabile](/dbzero/vendite/funzioni/fn_check_fondo_cancellabile)).
E si **richiude**: lasciata aperta renderebbe verdi per sottrazione tutti i `DELETE` successivi
della transazione. I pgTAP che cancellano righe nel cleanup la impostano allo stesso modo.

---

### ⚠️ Parla per primo fra i guard di riga, e nessuno lo contraddice

I `BEFORE ROW` girano in ordine alfabetico, e questo guard viene prima degli altri. Verificato
sui corpi, non c'è conflitto:

* `attivo` verso falso: il guard della rata non guarda la capienza di una riga non attiva, il
  guard della distinta finale non lo tratta come una riattivazione, e il blocco sulla
  disattivazione con movimenti arriverebbe dopo; ma la riga con movimento è `POSTATA` sotto una
  `CHIUSA`, e qui parla il motivo «distinta finale» col messaggio giusto;
* `INSERT` o riattivazione sotto una **finale**: la porta 2 tace (esclude le distinte finali) e
  lascia il messaggio al guard della distinta finale, che è la sua sede;
* il posting cambia solo lo stato: il trigger non scatta.

---

### 🔴 La porta 2 legge la distinta fuori dalla row security

Una riga contabile si vede anche dalla **fattura**: chi la vede così non vede la sua distinta.
Per questo la porta 2 chiede origine e stato della distinta a
[script.fn_get_contabile_stato_origine](/dbzero/script/funzioni/fn_get_contabile_stato_origine),
che legge fuori dalla row security. Letta sotto RLS, per quell'operatore l'origine non c'era, la
condizione «manuale e non in bozza» risultava falsa e l'importo si cambiava sotto una distinta
validata. Il numero della distinta, che serve solo al messaggio, resta letto sotto RLS.

La porta 1 non ne ha bisogno: la check dell'eliminazione, se non vede la riga o la sua distinta,
rifiuta (`E_RIGA_CONTABILE_NON_TROVATA`).

---

### ⚠️ Sotto una distinta chiusa l'importo resta modificabile

Sotto una distinta **annullata** nessuna scrittura passa: ogni aggiornamento lo rifiuta il guard
della distinta finale, e su disattivazione e `DELETE` parla qui la check, col motivo
`DISTINTA_ANNULLATA`.

Sotto una **chiusa**, invece, la porta 2 tace e il guard della distinta finale lascia di
proposito le altre scritture su una riga già lì, perché le righe si lavorano ancora (la
registrazione tardiva, «Riprendi»). Ne segue che l'**importo** di una riga sotto una `CHIUSA`,
anche `POSTATA` col suo movimento, resta modificabile da SQL. È un buco del modello visto e non
chiuso: chiuderlo è una decisione.

---

### Codici errore

* Porta 1, il primo motivo della check:
  * `E_RIGA_CONTABILE_DISTINTA_ANNULLATA` — la distinta è annullata: le sue righe si leggono
    soltanto;
  * `E_RIGA_CONTABILE_DISTINTA_FINALE` — la distinta è chiusa;
  * `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` — la distinta non è compilata a mano;
  * `E_RIGA_CONTABILE_DISTINTA_VALIDATA` — la manuale non è più in bozza;
  * i codici della check stessa, se la riga non si legge.
* Porta 2: `E_RIGA_CONTABILE_DISTINTA_VALIDATA` — lo stesso codice della porta 1, per tre gesti
  (aggiungere, cambiare un fatto, spostare).

---

### Test

* `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` — il trigger montato sui soli
  fatti, la check su bozza, generata e validata, il congelamento di inserimento, importo e
  spostamento, l'abbinamento che passa a distinta validata, l'aggiornamento a valore invariato,
  la porta del `DELETE` del giro.
* `db/pgtap/pagamenti/test-righe-distinta-annullata-congelate-v1.sql` — sotto un'annullata il
  `DELETE` e la disattivazione rifiutati col motivo `DISTINTA_ANNULLATA`, e uno solo.
* `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — il guard fra i chiamanti del rubinetto
  del primo motivo.
* `db/pgtap/pagamenti/test-righe-guard-distinta-vista-dalla-fattura-v1.sql` — la porta 2 sulla
  riga vista dalla fattura: l'importo non si cambia sotto la manuale validata di un'altra
  azienda, e si cambia sotto la sua bozza.

---

### Note di migrazione

* 2026-09-14 — nasce. Nel progetto si chiamava `guard_eliminazione`, poi ha preso
  il nome attuale. Fino a quel giorno il `DELETE` era aperto a chiunque avesse il privilegio, e
  una riga `POSTATA` la fermava solo la chiave esterna del movimento. Lo stesso giorno
  `vendite.fn_cancella_fondo_fattura` prende la GUC che apre la porta.
* 2026-09-30 — il residuo sotto le distinte finali si restringe: sotto un'annullata nessuna
  scrittura passa; resta l'importo sotto una chiusa.
* 2026-11-03 — la porta 2 legge origine e stato della distinta fuori dalla row security. Prima li
  leggeva con i diritti di chi scrive, e la riga vista dalla fattura passava senza controllo.

---

{% include-markdown "signature-core.md" %}
