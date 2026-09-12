## 📘 Documentazione Concettuale – Tabella `dbops.storico_scope_policy`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [dbops.fn_storico_risolvi_scope](/dbzero/dbops/manual/fn_storico_risolvi_scope) — chi legge questa mappa
• [dbops.fn_ensure_storico_table](/dbzero/dbops/manual/fn_ensure_storico_table) — chi crea le tabelle di storico
• [script.trgfn_storico_generic](/dbzero/script/manual/trgfn_storico_generic) — chi le scrive
>
**Guide:**
>
• [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle), sezione *Di chi è una versione*
>

### 🎯 Scopo Principale
(latest review 11-09-2026)

Per ogni tabella che ha uno storico, questa mappa dice **da dove si prende
l'emittente** di una sua riga. Serve al trigger di storico: quando fotografa una
versione, deve scrivere nella tabella di storico *«questa versione appartiene
all'emittente X»*, e quel valore resta lì congelato — è ciò che permette di
mostrare la storia di un documento solo agli operatori che possono vedere il
documento.

Il trigger è uno per tutte le tabelle e non sa nulla della tabella che sta
fotografando: la conoscenza *«per `fatture_righe` risali alla fattura con
`fattura_id`»* sta qui, scritta come dato, non dentro il codice.

Brief: `brief-db-rls-storico-scope-congelato`, §4b (decisione D3).

---

### Le cinque strade, e sono strade verso lo **stesso** fatto

| `modo` | Che cosa dice | Esempio |
| --- | --- | --- |
| `EF` | la riga ha già la colonna dell'emittente fiscale: si copia | `vendite.ddt.emittente_fiscale_id` |
| `SR` | la riga ha il soggetto-ruolo dell'emittente: si converte nel suo emittente fiscale (è 1 a 1) | `vendite.fatture.emittente_soggetto_ruolo_id` |
| `PADRE` | la riga è un satellite: `colonna` è la chiave verso il padre, e si **continua sulla riga di mappa del padre** — anche per più salti | `fatture_righe.fattura_id → fatture` (poi `SR`) |
| `BA` | la riga porta un billing account: un billing account ha **esattamente un** emittente, e lo si prende da lì | `anagrafiche.clienti.billing_account_id` |
| `NESSUNO` | la tabella non è protetta: la sua storia non si arma, e la `ragione` dice perché | `catalogo.articoli` |

⭐ Il valore che si congela è sempre uno solo, un `emittenti_fiscali.id`: i cinque
modi sono cinque **modi di arrivarci**, non cinque cose diverse.

---

### ⭐ Perché è anche un elenco di lavori

Ogni tabella con il trigger di storico deve avere la sua riga qui. Quindi:

* una tabella storicizzata **senza riga** è una tabella che nessuno ha ancora
  guardato — il controllo automatico la segnala;
* una tabella **protetta** dalla row level security ma dichiarata `NESSUNO` è un
  debito: la storia di quelle righe è ancora aperta. Anche questo si segnala;
* una riga `NESSUNO` deve dire **perché** (almeno 40 caratteri): «la tabella non
  ha la row level security», «asse portale, lo storico lo legge solo
  l'operatore». Non «TODO».

Il controllo è `db/pgtap/dbops/test-storico-scope-policy-v1.sql`, che verifica
anche che la mappa **non menta**: la colonna dichiarata esiste davvero, la chiave
verso il padre è davvero una FK verso quel padre, ogni catena arriva davvero a un
emittente e non gira in cerchio.

⭐ **E dal 12-09-2026 gli stessi tre motivi si vedono anche fuori dalla CI**:
[dbops.vw_storico_scope_da_dichiarare](/dbzero/dbops/manual/vw_storico_scope_da_dichiarare)
— `SENZA_RIGA`, `PROTETTA_NESSUNO` (con la ragione dichiarata accanto),
`RIGA_SENZA_MADRE` — è a catalogo in `dbops.presidi` con cadenza settimanale e
deve restare vuota. Il controllo ferma una consegna sbagliata; il digest si
accorge di una mappa invecchiata senza nessuna consegna (una tabella entrata in
RLS con un altro cantiere, una tabella cancellata).

---

### ⚠️ Due cose da sapere

**La chiave porta lo schema.** `acquisti.ddt` e `vendite.ddt` sono due righe
distinte: sono due tabelle che scrivono nella stessa tabella di storico
(`storico.ddt`), e la loro strada verso l'emittente non è la stessa — una ce l'ha
(`EF`), l'altra no (`NESSUNO`, asse fornitore).

**Un padre dichiarato deve esistere nella mappa.** Lo impone una FK della tabella
su se stessa, **differita** al commit: il CSV di seed carica una riga alla volta e
un satellite può venire prima del suo padre. Chi carica un CSV con un padre senza
riga vede fallire il migrate lì.

---

### Come si aggiorna

La sede è il CSV di seed `80_data/sql/dbops/storico_scope_policy.csv` (mirror
`loadUpdateData`): si edita quello, mai con un `UPDATE` a parte. Il CSV originale è
stato **generato dal catalogo** il 2026-09-11 — il modo dalla policy `ef_whitelist`
della tabella, il padre dalla FK reale — quindi dice ciò che il database diceva
quel giorno. Quando una tabella entra in RLS, la sua riga passa da `NESSUNO` al
modo giusto: il controllo automatico è lì per ricordarlo.
