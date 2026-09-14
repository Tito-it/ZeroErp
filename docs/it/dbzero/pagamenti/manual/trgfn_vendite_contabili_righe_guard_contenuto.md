## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_contenuto`

> 👀 **Vedi anche**
>
> **Il predicato, che sta altrove:**
>
> • [script.fn_check_riga_contabile_eliminabile](/dbzero/script/funzioni/fn_check_riga_contabile_eliminabile)
>
> **I guard vicini, sulla stessa tabella:**
>
> • [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — l'ingresso sotto una distinta finale
> • [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — la quadratura, e la riapertura solo della manuale
>
> **Chi apre la porta del `DELETE`:**
>
> • [vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura)
>
> **Piano:** [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga](/dev/work-in-progress/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga) §2.2 (D17), §2.3 (D18), §4 P-2/P-5

---

### 🎯 Scopo Principale
(scritto il 14-09-2026)

Custodire il **contenuto** di una distinta contabile: chi può togliere,
aggiungere o cambiare una riga, e quando. Due porte, due domande.

| Porta | Quando scatta | Chi decide |
| --- | --- | --- |
| **1 — eliminazione** (D17) | `attivo` da vero a falso, e `DELETE` | la check `fn_check_riga_contabile_eliminabile`, **chiamata**: il guard solleva il **primo** motivo e non contiene il predicato |
| **2 — congelamento** (D18) | `INSERT`; `UPDATE` di un **fatto** (`importo`, `data_pagamento`, `data_valuta`, `data_operazione`, `riferimento_ente`); riattivazione; spostamento da/verso un'altra distinta | sotto una **`MANUALE`** che non è più in `BOZZA` (e non è finale) → `E_RIGA_CONTABILE_DISTINTA_VALIDATA` |

> ⚠️ **Il nome dice «contenuto», non «eliminazione».** Il brief lo aveva
> battezzato `guard_eliminazione`; con D18 confermata la stessa funzione rifiuta
> anche un `INSERT`, e un guard che si chiama *eliminazione* e rifiuta un
> inserimento si legge male esattamente quando conta.

---

### ⭐ Fatti contro decisioni

Le **decisioni** restano libere anche a distinta validata — `stato_id`,
`fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`,
`motivo_forzatura`, `motivo_sospeso`, `meta` — e non è una concessione:
l'abbinamento **non tocca la quadratura** (D12-e), e la madre del posting
**muove lo stato** delle righe mentre la distinta è ancora `VALIDATA`.
Congelare lo stato romperebbe la registrazione.

Per questo il trigger è `UPDATE OF <fatti, attivo, contabile_id>` e non `UPDATE`
nudo: sulle decisioni **non scatta nemmeno**. E un `UPDATE OF` a valore
invariato — il backend scrive più colonne in una `SET` — passa: nessun contenuto
si muove.

---

### ⛔ La porta 2 è solo della `MANUALE`

`vendite.fn_sync_contabili_fondo_fattura` **inserisce** righe sotto una
`GENERATA` che nasce già `VALIDATA`, e le aggiorna (fatti compresi) a ogni
giro; `pagamenti.fn_conferma_sistemazione` inserisce sotto una `GENERATA` in
`BOZZA`. Un guard che non guardasse l'origine fermerebbe il giro dei fondi al
primo passaggio. L'immutabilità di `GENERATA` e `AUTOMATICA` è di D12-d e
arriva con l'import.

> ⚠️ **La condizione della porta 2 è il motivo 3 della check**, scritta due
> volte — nella check e qui — perché sull'`INSERT` non c'è una riga da passare.
> È una copia **dichiarata**, e il pgTAP la lega: sotto la stessa distinta
> validata pretende il rifiuto da entrambe le porte con lo stesso codice.

---

### ⭐ Il `DELETE` fisico, e chi può passare

Fino a questo guard il `DELETE` era aperto a chiunque avesse il privilegio
(l'applicazione ce l'ha): una riga `POSTATA` la fermava solo la FK `NO ACTION`
del movimento, le altre niente. D12-d dice *«immutabile ha tre porte, chiuderne
una sola non serve a niente»*: adesso il `DELETE` passa dalla **stessa check**
della disattivazione, e la riga registrata riceve il messaggio giusto **prima**
della FK.

🔴 **Ma un `DELETE` legittimo esiste, ed è del giro dei fondi.**
`vendite.fn_cancella_fondo_fattura` — sede unica dei tre `DELETE` del giro,
chiamata dal reset, dall'annullo di una sistemazione e dall'endpoint
`DELETE /vendite/fondi-fattura/{id}/` — cancella **fisicamente** le righe di un
atto sotto una `GENERATA`, dove la check risponde `DISTINTA_NON_MANUALE`: quel
predicato è il cestino dell'**operatore**, e lì non c'è un operatore.

⇒ La madre del giro **apre la porta per il proprio `DELETE`** con la GUC
transazionale `zeroerp.allow_contabile_riga_delete_override` (`SET LOCAL 'on'`
prima, `''` dopo), e questo guard la onora **solo sul `DELETE`**. Precedente
identico e in servizio: `script.fn_change_user_emittenti_scope` attraversa
`config.trgfn_user_emittenti_fiscali_guard_delete` con
`zeroerp.allow_user_emittente_delete_override`.

> ⚠️ **Non è un permesso: è la madre che dichiara «sono io»** dopo aver letto il
> *suo* criterio (`vendite.fn_check_fondo_cancellabile`: atto eseguito, riga
> registrata, distinta chiusa, figlia congelata, sistemazione attiva). E si
> **richiude**: lasciata aperta renderebbe verdi per sottrazione tutti i
> `DELETE` successivi della transazione. I pgTAP che cancellano righe nel
> cleanup la impostano allo stesso modo.

---

### ⚠️ Ordine dei `BEFORE ROW` (alfabetico), verificato leggendo i corpi

`a10_guard_contenuto` parla **prima** degli altri guard di riga. Nessun
conflitto:

* `attivo → false`: `guard_rata` esce (riga non attiva), `guard_distinta_finale`
  non guarda (non è una riattivazione), `prevent_deactivate_if_children` sui
  movimenti arriverebbe dopo — ma la riga con movimento è `POSTATA` sotto una
  `CHIUSA`, e qui parla il motivo 1 col messaggio giusto;
* `INSERT` o riattivazione sotto una **finale**: la porta 2 tace (esclude
  `is_final`) e lascia il messaggio a `guard_distinta_finale`, che è la sua sede;
* il posting (`UPDATE stato_id`) non entra nell'`UPDATE OF`: il trigger non
  scatta.

---

### ⚠️ Residuo dichiarato, non di questo cantiere

Sotto una distinta **finale** la porta 2 tace di proposito, e
`guard_distinta_finale` lascia *«le altre scritture su una riga già lì»*: quindi
l'**importo** di una riga sotto una `CHIUSA` — anche `POSTATA`, col suo
movimento — resta modificabile da SQL. È un buco del modello che questo cantiere
ha **visto** e non chiude: è una decisione (§8 del brief).

---

### Quando si attiva

* `BEFORE INSERT OR UPDATE OF attivo, contabile_id, importo, data_pagamento,
  data_valuta, data_operazione, riferimento_ente OR DELETE` su
  `pagamenti.vendite_contabili_righe`.

### ⚠️ Error handling

| Codice | Classe | Porta |
| --- | --- | --- |
| `E_RIGA_CONTABILE_DISTINTA_FINALE` | `CONFLITTO_STATO` | 1 — il primo motivo della check (riusato) |
| `E_RIGA_CONTABILE_DISTINTA_NON_MANUALE` | `CONFLITTO_STATO` | 1 |
| `E_RIGA_CONTABILE_DISTINTA_VALIDATA` | `CONFLITTO_STATO` | 1 **e** 2: un codice per tre gesti |

Presidio: `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql`.

{% include-markdown "signature-core.md" %}
