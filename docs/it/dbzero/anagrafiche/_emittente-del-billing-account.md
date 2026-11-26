### 🏢 L'azienda di un billing account

> **Ultimo aggiornamento**: 26 novembre 2026
>
> **Vedi anche**
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento di ogni billing account alla sua azienda, e la riga dell'azienda predefinita
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto che fattura; non si cancella
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — il cliente del billing account: si chiude annullandolo
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il collegamento che nasce col billing account
> * [anagrafiche.fn_crea_billing_account](/dbzero/anagrafiche/funzioni/fn_crea_billing_account) — la creazione con un'azienda chiesta
> * [script.fn_utente_di_sessione](/dbzero/script/funzioni/fn_utente_di_sessione) — l'utente di chi agisce, letto senza ingoiarne il rifiuto
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — l'azienda di chi agisce
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'azienda di un billing account, per chi agisce
> * [script.fn_get_ba_emittente_sr_id_installazione](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id_installazione) — l'azienda di un billing account, per l'installazione
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) e [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — i risolutori che sollevano `E_EMITTENTE_DEFAULT_MISSING`
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il rifiuto della cancellazione e dello spostamento
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente), [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente), [script.fn_check_ba_cambio_emittente](/dbzero/script/funzioni/fn_check_ba_cambio_emittente) — il cambio d'azienda e la storia
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) e [anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/funzioni/fn_get_storia_emittente_ba) — che cosa è la storia, e la frase del rifiuto
> * [anagrafiche.trgfn_efba_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_albero_emittente), [anagrafiche.trgfn_billing_account_guard_albero_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_albero_emittente), [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — padre e figli su un'azienda sola
> * [anagrafiche.trgfn_efba_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_istanza_emittente), [anagrafiche.trgfn_billing_account_guard_istanza_emittente](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_istanza_emittente), [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — i billing account di un'istanza su un'azienda sola
> * [anagrafiche.fn_check_ba_coppia_emittente_omogenea](/dbzero/anagrafiche/funzioni/fn_check_ba_coppia_emittente_omogenea) — il confronto di due billing account, comune ai due guard qui sopra
> * [anagrafiche.trgfn_efba_guard_clienti_chiave](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_clienti_chiave) e [anagrafiche.fn_guard_clienti_chiave_unica_di](/dbzero/anagrafiche/funzioni/fn_guard_clienti_chiave_unica_di) — l'azienda nella chiave del cliente manuale
> * [anagrafiche.fn_check_ba_padre](/dbzero/anagrafiche/funzioni/fn_check_ba_padre) — un solo padre per cliente e per azienda
> * [script.trgfn_doc_guard_emittente_ba](/dbzero/script/funzioni/trgfn_doc_guard_emittente_ba) — il documento di vendita, fattura compresa, è dell'azienda del suo billing account
> * [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento) — le famiglie di documenti che fanno storia

Ogni billing account fattura per un'azienda (l'emittente fiscale), e lo dice il suo **collegamento** in
`anagrafiche.emittenti_fiscali_billing_account`: **una riga per ogni billing account, sempre**. La tabella ha
in più una riga senza billing account, `is_default`, che è l'**azienda predefinita** dell'installazione, una
sola.

#### Il collegamento nasce col billing account

Il billing account nasce già collegato: lo scrive `anagrafiche.trgfn_billing_account_link_ef` subito dopo la
nascita, con

* l'azienda di **chi agisce**, se l'utente di sessione ne ha una;
* l'azienda **predefinita**, senza sessione (batch, import, manutenzione) o se chi agisce non ha un'azienda;
* nessuna: senza nessuna azienda nell'installazione il billing account **non nasce**
  (`E_EMITTENTE_DEFAULT_MISSING`). Un cliente fattura sempre per qualcuno.

L'utente si legge con `script.fn_utente_di_sessione`: un `app.current_user_id` che non è l'id di un utente è
rifiutato, e il rifiuto sale fino a chi scrive. Non diventa «nessun utente», che porterebbe il billing account
alla predefinita senza i controlli di chi agisce.

Chi crea il billing account con `anagrafiche.fn_crea_billing_account` e chiede un'azienda precisa la ottiene
così: senza sessione la funzione **modifica** il collegamento appena nato verso l'azienda chiesta; con un
operatore in sessione il billing account è dell'azienda di chi agisce, e chiederne un'altra è una chiamata
sbagliata. ⚠️ I controlli di albero e istanza giudicano il billing account quando nasce, cioè sul collegamento
alla predefinita, prima della modifica: senza sessione un billing account con un'azienda chiesta diversa
dalla predefinita, e un padre o un'istanza su quell'azienda, non passa.

#### Di quale azienda è un billing account

Del suo collegamento. Le due letture, `script.fn_get_ba_emittente_sr_id` (per chi agisce) e
`script.fn_get_ba_emittente_sr_id_installazione` (per l'installazione), rispondono col collegamento, e con
ogni billing account collegato danno sempre la stessa risposta. I loro livelli successivi (l'azienda di chi
agisce, poi la predefinita, oppure soltanto la predefinita) riguardano solo l'istante della nascita, prima che
il collegamento sia scritto, e ripetono la scelta del trigger di nascita. `anagrafiche.fn_get_emittente_fiscale_id`
e `anagrafiche.fn_get_emittente_fiscale_pk` usano la prima lettura e trasformano un'azienda non risolta in
`E_EMITTENTE_DEFAULT_MISSING`.

#### L'azienda predefinita decide solo i billing account che nasceranno

La predefinita serve al trigger di nascita, quando chi agisce non porta un'azienda. Non è l'azienda di nessun
billing account già nato: spostarla (si modifica la sua riga, che non si cancella e non si sostituisce) non
cambia l'azienda di nessun cliente, e per questo nessun controllo del collegamento la giudica.

#### Come cambia l'azienda di un billing account

| Movimento | Che cosa succede |
| --- | --- |
| nasce il billing account, e con lui il collegamento | l'azienda di nascita; si giudicano albero, istanza e chiave del cliente, non la storia: non ce n'è |
| si **modifica** l'azienda sul collegamento | il billing account passa all'altra azienda, solo se non ha nessun documento |
| si cancella il collegamento | rifiutato (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`), anche la riga della predefinita |
| il collegamento passa a un altro billing account, o diventa la riga predefinita, o smette di esserlo | rifiutato (`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`) |
| si cancella il billing account | rifiutato (`E_BA_NON_SI_CANCELLA`): il cliente si chiude annullandolo (`anagrafiche.clienti`, stato «AN annulla servizio») |

I due rifiuti del collegamento e quello del billing account non hanno porte, nemmeno per il proprietario:
nessuna scrittura legittima li attraversa. Il collegamento appartiene al suo billing account per sempre, e
spostare un cliente vuol dire **modificare** l'azienda sul suo collegamento.

Il cambio d'azienda passa da quattro cancelli, che giudicano solo il collegamento di un billing account che
nasce o cambia azienda:

| Domanda | Controllo | Trigger |
| --- | --- | --- |
| Il billing account ha già documenti? | `anagrafiche.fn_guard_ba_cambio_emittente` (la regola è `script.fn_check_ba_cambio_emittente`) | `anagrafiche.trgfn_efba_guard_storia_emittente`, prima della scrittura, solo sulla modifica |
| L'albero padre/figli diventa misto? | `anagrafiche.fn_guard_albero_ba_emittente` | `anagrafiche.trgfn_efba_guard_albero_emittente`, dopo |
| L'istanza finisce su due aziende? | `anagrafiche.fn_guard_istanza_ba_emittente` | `anagrafiche.trgfn_efba_guard_istanza_emittente`, dopo |
| Un cliente manuale trova un doppione nella nuova azienda? | `anagrafiche.fn_guard_clienti_chiave_unica_di` | `anagrafiche.trgfn_efba_guard_clienti_chiave`, alla conferma |

Albero e istanza si giudicano anche dal lato del billing account, quando prende un padre o nasce su
un'istanza (`anagrafiche.trgfn_billing_account_guard_albero_emittente`,
`anagrafiche.trgfn_billing_account_guard_istanza_emittente`); i due guard confrontano le coppie con
`anagrafiche.fn_check_ba_coppia_emittente_omogenea`. Il limite dell'albero a un livello e del padre unico per
cliente e azienda lo tiene `anagrafiche.fn_check_ba_padre`.

#### Che cosa è la «storia» che ferma un cambio

**Qualunque documento**, di qualunque famiglia e in qualunque stato, **anche in bozza**: le famiglie attive di
`vendite.famiglie_documento` che dichiarano la colonna del billing account. La domanda la fa
`anagrafiche.fn_ba_ha_storia_emittente`; `anagrafiche.fn_get_storia_emittente_ba` conta i documenti per
famiglia e compone la frase di `E_BA_EMITTENTE_CON_STORIA`. L'elenco non è scritto nei controlli: una famiglia
nuova entra nella regola quando si registra.

⭐ Anche una bozza conta perché è già un documento di quell'azienda: ogni documento di vendita, fattura
compresa, è emesso dall'azienda del suo billing account (`script.trgfn_doc_guard_emittente_ba`). Spostare il
cliente lascerebbe i suoi documenti a un'azienda che non lo vede più.

La **finestra di correzione** resta, finché il billing account non ha nessun documento: il collegamento nasce
da solo con l'azienda di chi crea il cliente, e un cliente nato sotto l'azienda sbagliata si corregge
modificandolo. Chi ha già scritto documenti e ha sbagliato azienda li cancella prima. Un cliente che passa
davvero a un'altra azienda non si sposta: presso la nuova si apre una fornitura nuova, e i documenti già
scritti restano a chi li ha scritti.
