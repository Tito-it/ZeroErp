## 📘 Documentazione Concettuale – Funzione `vendite.fn_ritira_commessa_attivita_da_sorgente`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe che si ritirano
> * [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log) — il registro, una riga per riga ritirata
>
> Approfondimento funzioni:
>
> * [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile) — ferma la chiusura se ci sono righe in volo
> * [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — chi la chiama, dopo la conferma dell'annullo
> * [vendite.fn_annulla_commessa_attivita](/dbzero/vendite/funzioni/fn_annulla_commessa_attivita) — la complementare, per le righe manuali
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

**Il ritiro: il documento riprende ciò che aveva spinto.** Porta ad `ANNULLATA`
le sole righe di commessa in **`NON_EMESSA`** della sorgente indicata, e lascia
una riga di registro **per ciascuna**. Restituisce **quante** ne ha ritirate.

---

### ⭐ È l'oggetto di una promessa che il modello faceva già per iscritto

Il guard d'origine di
[`fn_annulla_commessa_attivita`](/dbzero/vendite/funzioni/fn_annulla_commessa_attivita)
dice:

> *«per una riga da push il rimedio è **SEMPRE a monte, sul documento**»*

Questa funzione è quel rimedio: annullare il documento non ferma solo i push **futuri**, ritira
anche ciò che era già passato e non è ancora emesso. Senza, il lavoro resterebbe in commessa,
fatturabile, e l'unico modo di uscirne sarebbe **essere fatturato**.

---

### ⭐ Le due funzioni sono complementari, non in contraddizione

| | perimetro |
| --- | --- |
| `fn_annulla_commessa_attivita` | **rifiuta** le righe con sorgente, e lavora sulle **sourceless** |
| **questa** | lavora **solo** su quelle **con** sorgente |

Insieme coprono il piano, e nessuna delle due invade l'altra.

⚠️ Le righe **sourceless** — `ONERE` e `RETTIFICA` — non hanno sorgente e il
ritiro per sorgente **non le trova**. È corretto: per l'onere la via è
`fn_annulla_commessa_attivita`, per la rettifica
`fn_annulla_accredito_riga_reso`. È la stessa distinzione **origine / natura**
dell'annullo manuale.

---

### ⛔ La chiave, e sbagliarla non dà errore

Il documento si passa con le colonne del modello della provenienza: il tipo, `p_sorgente_id` e
`p_sorgente_uid` (uuid). La ricerca segue la **regola d'incontro**: una riga combacia se il suo
`sorgente_id` è quello passato **o** il suo `sorgente_uid` è quello passato. Chi ha il documento
passa il suo id **e** il suo uid, senza leggere il `key_selector`: nella riga la colonna che il
tipo non usa è vuota, e non incontra niente. Serve almeno una delle due chiavi (altrimenti
`E_RITIRO_SORGENTE_PARAMETRO_MANCANTE`).

⚠️ Una chiave sbagliata (l'id di un altro documento, un tipo che non è quello) non solleva
niente: **ritira zero righe**, cioè un ritiro che non ritira.

⭐ È il motivo per cui la funzione restituisce un **conteggio** invece di `void`,
e per cui c'è un test apposta.

---

### ⚠️ Il motivo è obbligatorio, come per l'annullamento manuale

`ANNULLATA` è **irreversibile**: `fn_approva_commessa_attivita` la filtra e non
esiste ripristino. L'unica traccia del *perché* è l'evento di registro, e a mesi
di distanza un importo sparito senza spiegazione è indistinguibile da un difetto.

⭐ **Qui vale il doppio**: chi chiude il documento non sta guardando la commessa,
e il ritiro è per lui un **effetto a distanza**.

---

### ⚠️ Un ritiro è una cascata silenziosa, e si paga col registro

Una riga di `vendite.commesse_attivita_log` — evento
**`RIGA_RITIRATA_DA_SORGENTE`** — **per riga ritirata**, con il motivo, lo stato
precedente, la sorgente, il `segment_key`, il prezzo e il tipo movimento.

Senza, «il lavoro è sparito» diventa indistinguibile da un difetto — che è
esattamente il male da cui nasce il cantiere.

ℹ️ La colonna `evento` non ha `CHECK` né tabella-vocabolario: **nessun seed da
estendere**.

---

### Cosa scrive, e in che ordine

1. **fotografa** le righe `NON_EMESSA` della sorgente — *prima* di annullarle:
   lo stato precedente è ciò che il registro deve raccontare, e l'`UPDATE` lo
   sovrascrive. È la stessa disciplina del riordino di
   `fn_cleanup_fatture_by_ids`: **si legge il dato finché è vivo**;
2. **porta ad `ANNULLATA`** le sole `NON_EMESSA`;
3. **scrive il registro**, riga per riga.

⚠️ `FOR UPDATE` con `ORDER BY id`: serializza i concorrenti ed evita il deadlock
fra due chiusure che si intersecano in ordine opposto.

⚠️ Il predicato è scritto **in positivo** (`= 'NON_EMESSA'`) e non come
`<> 'EMESSA'`: se domani il `CHECK` ammettesse un quarto stato, il default resta
il **non toccarlo** — fail-closed su un verbo irreversibile.

---

### ⭐ Una sorgente, una commessa: `p_commessa_id`

Ultimo parametro, in coda e `DEFAULT NULL`:

| `p_commessa_id` | Chi lo usa | Cosa ritira |
| --- | --- | --- |
| `NULL` | l'annullo di un **documento** | le righe della sorgente in tutte le commesse: il documento riprende tutto ciò che ha spinto |
| valorizzato | l'annullo di una **commessa** | le sole righe di quella commessa: la stessa sorgente può avere righe vive in un'altra commessa, che non c'entra |

Il filtro è residuo: l'accesso resta dalla provenienza.

---

### Note operative

* **`SECURITY INVOKER`**: `commesse_attivita` ha la RLS, e lo scope resta quello
  del chiamante. ⚠️ Chi non vede le righe ne ritira **zero**, e il conteggio è
  l'unico modo di accorgersene.
* `stato_approvazione` resta com'è: sono due assi distinti, e una riga ritirata
  conserva la memoria di essere stata approvata.
* `data_update` / `user_update` / `tx_id` / storico: li mettono i trigger.
* Non è raggiungibile dall'interfaccia: la chiama il BB
  [`fn_documento_ritira_legami`](/dbzero/vendite/funzioni/fn_documento_ritira_legami)
  dentro i verbi di annullo (`fn_annulla_ddt`, `fn_annulla_ordine`,
  `fn_annulla_preventivo`, `fn_annulla_contratto`), **dopo la conferma** di chi
  annulla. Il motivo registrato è «Ritiro all'annullo confermato del documento di
  origine (…)».
* Test: `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql`.
  ⭐ Il **7** è quello che vale: con la chiave sbagliata ritira zero e non solleva.

---

### Note di migrazione

* 2026-08-26 — nasce la funzione: fino ad allora annullare l'ordine fermava i push futuri e non
  ritirava niente di ciò che era già passato (brief-db-lavoro-che-non-torna-indietro, lotto L7).
* 2026-10-11 — non la chiama più un trigger `_z90_` all'ingresso in uno stato abortito, ma il BB
  `fn_documento_ritira_legami` dopo la conferma dell'annullo
  (brief-db-annullo-documento-con-legami, D-5).
* 2026-10-12 — arriva `p_commessa_id` (brief-db-annullo-a-valle-riapre-a-monte, D-1).
* 2026-11-07 — il documento si passa con le colonne tipizzate (`p_sorgente_id` e `p_sorgente_uid`
  uuid) e si cerca con la regola d'incontro, al posto della chiave testuale `p_sorgente_uid`, che
  era l'uid della testata in testo per ogni tipo (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
