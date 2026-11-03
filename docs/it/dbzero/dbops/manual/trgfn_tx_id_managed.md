## 📘 Documentazione Concettuale – Trigger function `dbops.trgfn_tx_id_managed`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids) — il registro in cui si verifica l'id della sessione
> * [config.parameters](/dbzero/config/tabelle/parameters) — il parametro `tx_id_bypass_enabled`
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — dà l'id quando la sessione non ne ha
> * [dbops.fn_run_automations_tx_id](/dbzero/dbops/funzioni/fn_run_automations_tx_id) — monta questo trigger sulle tabelle
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — registra gli avvisi senza sollevare
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori veri
> * [script.uuid_nil](/dbzero/script/funzioni/uuid_nil) — la sentinella
>
> Guide:
>
> * [Transaction ID](/guide/tx_id_implementation_guide) — il disegno completo del `tx_id`
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — la convenzione `E_` / `W_`

---

### 🎯 Scopo Principale

Il trigger `BEFORE INSERT OR UPDATE` che dà a ogni riga di una tabella tracciata il **`tx_id`
della transazione**: se la riga ne porta già uno lo lascia com'è, altrimenti prende quello della
sessione, verificato nel registro, o ne fa generare uno.

Lo monta l'automazione dei transaction id su ogni tabella con una colonna `tx_id` di tipo UUID; il
nome del trigger viene dal modello della regola.

---

### ⭐ Una riga che porta il suo `tx_id` esce subito

Se `NEW.tx_id` è valorizzato, la funzione esce senza leggere il parametro del bypass né toccare le
funzioni di `script`: tutto il resto serve solo a calcolare il valore quando manca. È anche ciò che
permette al canale di log, che scrive sempre il proprio `tx_id` e ha diritti sul solo schema
`dbops`, di scrivere senza fallire per permessi.

La normalizzazione della stringa vuota sta prima dell'uscita, ed è un ordine vincolante.

---

### Quando la riga non ha `tx_id`

1. **Il bypass.** Si legge `tx_id_bypass_enabled` in `config.parameters`; se non è attivo, si
   legge l'override di sessione `myapp.bypass_tx_id_check`. Con il bypass attivo nessun id si
   genera né si verifica: vale quello della sessione, o la sentinella nulla.
2. **L'id della sessione.** Se il GUC `dbops.tx_id` è pubblicato, deve esistere in
   `dbops.transaction_ids`: se c'è si usa.
3. **Nessun id in sessione.** Lo chiede a `dbops.fn_get_or_create_session_tx_id`, che lo genera e
   lo registra fuori transazione, o restituisce la sentinella se il canale non c'è.

⚠️ Se il parametro `tx_id_bypass_enabled` manca dalla tabella dei parametri, la funzione registra
`E_ERRORE_PARAMETRI_TABELLA` senza sollevare, ma il bypass resta **indefinito**, non spento: in
quel caso anche l'override di sessione viene ignorato, e il bypass non scatta.

---

### ⚠️ L'id non registrato avverte, e non blocca

Se il GUC contiene un id che il registro non conosce, la funzione registra `W_TXID_NOT_REGISTERED`
e prosegue: è un avviso, come dice il prefisso. Il caso non dovrebbe presentarsi, perché
`dbops.fn_get_or_create_session_tx_id` pubblica solo id registrati: succede se qualcuno imposta il
GUC a mano.

⚠️ Il valore che la riga riceve, alla fine, è comunque quello del GUC: l'assegnazione dà la
precedenza al GUC sul valore calcolato, quindi in questo ramo la riga porta l'id non registrato,
non la sentinella. Lo stesso vale con il bypass: se il GUC è pubblicato, vince lui.

---

### Codici errore

* `E_SQL_READ_TABLE` — la lettura di `config.parameters` fallisce (per esempio per permessi): è
  bloccante, e la scrittura della riga si ferma.
* `E_ERRORE_PARAMETRI_TABELLA` — il parametro del bypass non c'è: registrato, non sollevato.
* `W_TXID_NOT_REGISTERED` — l'id pubblicato nella sessione non è nel registro: registrato, non
  sollevato.
* `E_TXID_GENERATION` — la generazione dell'id fallisce con un errore: è bloccante.

---

### Test

* `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` — senza canale una scrittura tracciata
  riesce con la sentinella; un GUC forzato a un id non registrato non blocca la scrittura; con il
  bypass la scrittura riesce; un `tx_id` esplicito si conserva tale e quale, anche con il GUC
  avvelenato; l'uscita anticipata sta prima della lettura dei parametri.

---

### Note di migrazione

* 2026-07-22 — il ramo dell'id non registrato avverte e prosegue: prima sollevava, perché usava la
  funzione che registra e solleva al posto di quella che registra soltanto, e la riga che assegnava
  la sentinella era irraggiungibile. La discrepanza c'era fin dalla prima versione
  (`brief-db-coerenza-tx-id-non-registrato`).
* 2026-07-24 — l'uscita anticipata sale in testa: prima la funzione faceva tutto il giro anche per
  le righe che portavano il proprio `tx_id` (`brief-db-tx-id-uscita-anticipata`).

---

{% include-markdown "signature-core.md" %}
