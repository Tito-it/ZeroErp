# Brief DB — i riferimenti dell'atto in fattura: un satellite, non tre colonne

> **Destinatario:** team DB (`dev/db-tid`). **Voce unica**, e chiude la coda di
> `D9` / `I8` lasciata aperta dal brief madre
> [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md)
> (§8-nonies, punto 2: *«si porta dietro la colonna `fatture_righe.contratto`»*).
>
> 📌 **La richiesta operativa è raccolta con le altre** in
> [brief-db-richieste-aperte-dal-backend.md](brief-db-richieste-aperte-dal-backend.md):
> quello è l'ordine di lavoro, questo è il ragionamento. ⛔ Se le due divergono,
> vale questo — l'elenco rimanda, non ricopia.
>
> **Origine.** Decisione di Tid del 2026-08-31, presa rispondendo a una domanda
> sua: *«la fattura elettronica lo richiede per riga?»*. La risposta ha rovesciato
> una scelta fatta poche ore prima — testata — e ha portato alla forma (b) qui
> sotto.
>
> **Stato.** 2026-08-31 — verificato sulla **struttura** (doc auto-generata di
> `vendite.fatture_righe`, `vendite.contratti`, `vendite.attivita_fatturabili`;
> sorgente di `fatture_righe_service.py`). **Nessuna misura sui dati.** Nessun
> file scritto lato DB.
>
> **Correlati:**
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) ·
> [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva) ·
> [vendite.contratti](/dbzero/vendite/manual/contratti) ·
> [trgfn_fattura_satellite_guard_congelamento](/dbzero/vendite/funzioni/trgfn_fattura_satellite_guard_congelamento)

---

## 1. Il fatto: la FatturaPA non chiede né una testata né una colonna di riga

`CIG`, `CUP` e commessa vivono nel blocco `DatiContratto` (e nei gemelli
`DatiOrdineAcquisto`, `DatiConvenzione`) dentro `DatiGenerali`. Il blocco è
**ripetibile `0..N`**, e ogni occorrenza porta:

```text
RiferimentoNumeroLinea    0..N   ← i numeri di DettaglioLinee a cui il blocco si riferisce
IdDocumento               1      ← il numero del contratto
Data · NumItem
CodiceCommessaConvenzione
CodiceCUP
CodiceCIG
```

⇒ **Non è «testata» e non è «una colonna sulla riga»: sono N blocchi di
documento, ognuno agganciato alle sue righe.** Una fattura con righe di due
contratti produce **due** blocchi, ciascuno con la propria lista di numeri di
linea. Col contratto unico `RiferimentoNumeroLinea` si omette e il blocco vale
per tutto il documento.

⭐ **Il manual di `vendite.contratti` lo dice già** (§«Riferimenti dell'atto»,
scritto dal team DB il 2026-08-29): *«la sede giusta è la riga di fattura, non la
testata … È anche ciò che la FatturaPA prevede, con `RiferimentoNumeroLinea`»*.
Questo brief non scopre niente: **costruisce ciò che quella riga aveva già
deciso**, e aggiunge la forma.

---

## 2. La forma decisa: un satellite che **è** il blocco XML

Le due strade erano:

| | Forma | Verdetto |
| --- | --- | --- |
| **(a)** | i codici snapshottati **su `fatture_righe`** | ⛔ **scartata** |
| **(b)** | un satellite `vendite.fatture_atti` + FK sulla riga | ✅ **decisa (Tid, 2026-08-31)** |

**Perché la (a) è stata scartata**, e non è una preferenza di stile:

* servirebbe snapshottare anche `IdDocumento` (il numero del contratto) e la sua
  data — quindi **cinque** colonne di riga, non tre;
* il generatore XML dovrebbe ricostruire i blocchi con un `GROUP BY` su **testo**.
  Due atti che condividono un codice ma non la data si fondono o si spezzano a
  seconda di cosa entra nel raggruppamento, **e nessun vincolo se ne accorge**. È
  la specie di difetto muto che questo cantiere esiste per togliere.

⭐ **La (b) non assomiglia al blocco XML: lo è.** Una riga = un blocco;
`RiferimentoNumeroLinea` è la lista delle righe che ci puntano; il generatore
diventa una `SELECT`.

⭐ **E il precedente è sulla stessa tabella**: `vendite.fatture_riepiloghi_iva` è
già esattamente un satellite che aggrega righe per produrre un blocco XML
(`DatiRiepilogo`). Non si introduce un pattern nuovo, se ne riusa uno in
servizio.

📌 **`D9` non viene contraddetta**, viene presa alla lettera: diceva *«tutti e
tre insieme, perché stanno nello stesso blocco»*. Qui **una riga è un blocco**.

---

## 3. La richiesta

### 3.1 La tabella nuova — `vendite.fatture_atti`

Snapshot dei riferimenti dell'atto, **una riga per (fattura, contratto)**.

| Colonna | Note |
| --- | --- |
| `id` | chiave tecnica (identity), come `fatture_riepiloghi_iva` |
| `fattura_id` | `bigint NOT NULL`, FK → `vendite.fatture` |
| `contratto_id` | FK → `vendite.contratti` (PK `bigint`). ⚠️ è il **chi**, non lo snapshot: serve a ricostruire il legame, non a stampare |
| `id_documento` | `NOT NULL` — snapshot di `contratti.numero` (→ `IdDocumento`) |
| `data_documento` | snapshot di `contratti.data` (→ `Data`) |
| `codice_cig` · `codice_cup` · `codice_commessa` | nullable, snapshot delle tre colonne del contratto |
| audit + `tx_id` + `storicizza` | convenzione di progetto |

**Vincoli**: `UNIQUE (fattura_id, contratto_id)` — un blocco per atto, per
fattura.

⛔ **Perché lo snapshot e non un `JOIN` al contratto**: è la ragione di `D9`. Un
CIG corretto in anagrafica domani **non deve cambiare** su una fattura già
emessa. Il puntatore `contratto_id` c'è per il lineage, non per la stampa: chi
genera l'XML legge le colonne snapshottate, sempre.

### 3.2 La FK sulla riga

`vendite.fatture_righe.fattura_atto_id`, **nullable**, FK → `fatture_atti`.

⚠️ **Nullable per forza**: `fatture_righe` porta una sorgente fra **quindici**
tipi (`config.sorgenti`), e la maggior parte non nasce da un contratto. Una riga
senza atto è il caso ordinario, non l'eccezione.

### 3.3 Gli agganci obbligatori, che si vedono solo conoscendo il progetto

Sono quattro, e nessuno è opzionale:

| # | Cosa | Perché |
| --- | --- | --- |
| **1** | montare `trgfn_fattura_satellite_guard_congelamento` su `fatture_atti` | ⭐ **È già parametrica**: `D34` (`20260830-08`) le ha insegnato `TG_ARGV[1]` = codice errore, opzionale. Qui basta `TG_ARGV = ('fattura_id')` e il codice generico `E_FATTURA_SATELLITE_CONGELATO` — **nessun codice errore nuovo**. Un satellite di fattura che non è protetto dal congelamento è un buco nella soglia unica appena costruita da `D33` |
| **2** | classificare la tabella in `db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` | ⛔ Quel file **diventerà rosso e farà il nome della tabella**: è il suo mestiere. ⚠️ E la sua intestazione lo dice: *«non si aggiunge la tabella all'inventario per far tornare il verde, si DECIDE a quale categoria appartiene»*. Qui la categoria sembra `CASCADE_DB` — il blocco è uno snapshot di **quella** fattura e muore con lei — ma la decisione va scritta con la sua motivazione, non dedotta da questo brief |
| **3** | nessuna policy RLS sul satellite, e il cancello resta la **testata** | Stessa forma di `fatture_righe` e `fatture_riepiloghi_iva`: `vendite.fatture` ha la RLS, i satelliti no. Chi legge parte dalla testata, sempre — è la regola già scritta in `api_fattura_dettaglio.md` |
| **4** | indici FK **non a mano** | Policy di progetto: `dbops.apply_fk_index_policy()` in `90_end`, e le celle si registrano in `dbops.fk_index_policy` |

⚠️ **Sull'ordine delle `ON DELETE`** non mi pronuncio: con due figlie della stessa
fattura che devono morire insieme, e una FK fra loro, l'ordine di cascata è una
scelta di DDL che è vostra. La segnalo perché è il punto in cui una `DELETE` di
fattura può esplodere con una violazione grezza a runtime.

---

## 4. ⛔ La metà BE, e va detta qui perché senza di essa il satellite non funziona

**`contratto_id` non entra nella chiave di aggregazione delle righe di fattura.**
Verificato in `apps/vendite/services/fatture_righe_service.py`
(`_build_group_key`, ~148): la chiave è
`(articolo, dest_BA, uom, prezzo, iva, competenza, arrotondamenti, rettifica)` —
**zero occorrenze** di `contratto` in tutto il file.

⇒ Ne discende che oggi **due attività di contratti diversi collassano nella
stessa riga di fattura** se hanno lo stesso articolo, prezzo, UoM, IVA e
competenza. E in quel caso `fattura_atto_id` non ha una risposta: la riga
appartiene a due atti.

⭐ **La cura è lato BE e sta in `I4`**: `contratto_id` entra nella group key. Le
attività senza contratto lo hanno `NULL`, quindi **nessun raggruppamento
esistente cambia** — si spezzano solo le righe che oggi mescolano davvero due
atti, cioè quelle che stanno sbagliando in silenzio.

📌 Il dato per farlo **c'è già**: `vendite.attivita_fatturabili.contratto_id`
esiste (verificato sul catalogo). Questa voce non chiede niente al DB — è scritta
qui perché **il satellite senza di essa sarebbe una sede che non si può
riempire**, cioè la voce 2 del brief madre un'altra volta.

---

## 5. Quando

⛔ **Insieme a `I4`, non prima.** La tabella nasce con chi la riempie: costruirla
adesso produrrebbe una sede vuota che nessuno popola, che è esattamente il
difetto da cui questo cantiere è partito.

⚠️ E il generatore XML FatturaPA **non esiste ancora** — verificato: nessun
modulo in `backend/apps`. Il satellite serve comunque prima del builder (è `I4`
che scrive le righe), ma il suo **consumatore finale** arriverà dopo: `IdDocumento`
e `Data` sono snapshottati adesso proprio perché quel giorno non ci sia niente da
ricostruire.

---

## 6. Presidio atteso

⭐ **Il test che discrimina** — e non è «la INSERT riesce», che riesce comunque:

* una fattura con righe di **due** contratti produce **due** righe in
  `fatture_atti`, e ogni riga di fattura punta a quella giusta;
* ⚠️ **il gemello negativo**: una fattura con righe di **un solo** contratto
  produce **una** riga sola. Senza, un'implementazione che scrive un atto per
  riga passerebbe il primo test e sarebbe sbagliata;
* i tre codici in `fatture_atti` **non cambiano** se dopo l'emissione si modifica
  il contratto — è la prova che lo snapshot è uno snapshot, ed è l'unica ragione
  per cui quelle colonne esistono invece di un `JOIN`;
* ⭐ **il congelamento morde**: una scrittura su `fatture_atti` di una fattura
  oltre la soglia viene **rifiutata** con `E_FATTURA_SATELLITE_CONGELATO`. Va
  provata contro la versione **senza** il trigger montato e vista diventare
  verde-per-sbaglio, altrimenti il presidio non prova il montaggio.

---

## 7. Fuori perimetro, dichiarato

* ⛔ **Il generatore XML FatturaPA.** Questo brief prepara il dato, non lo
  stampa;
* 📌 **Gli accordi quadro PA** — contratto con CIG «padre» e ordini attuativi con
  CIG derivato. La forma è già annotata nel manual di `contratti`: gli stessi tre
  campi su `vendite.ordini`, nullable, col contratto come ripiego. Il satellite
  qui proposto **la regge senza modifiche** (cambia solo chi lo alimenta), ed è
  una ragione in più per la forma (b);
* ⛔ **Nessuna misura sui dati.** La domanda «quante fatture mescolano due
  contratti oggi?» non decide niente: decide che il modello lo **ammette** — la
  group key non ha `contratto_id` e `attivita_fatturabili` ce l'ha — e tanto
  basta.

---

## 8. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 | Brief nato da una domanda di Tid — *«la fattura elettronica lo richiede per riga?»* — che ha rovesciato la scelta «testata» presa poche ore prima. ⭐ La risposta era **già in casa**: il manual di `vendite.contratti`, scritto dal team DB il 2026-08-29, cita `RiferimentoNumeroLinea` e indica la riga. Decisa la forma **(b)**: un satellite che *è* il blocco XML, sul modello di `fatture_riepiloghi_iva`, invece di cinque colonne di riga da riaggregare con un `GROUP BY` su testo. ⛔ Trovato costruendo il brief che **`contratto_id` non è nella chiave di aggregazione delle righe di fattura**: due attività di contratti diversi collassano oggi nella stessa riga, quindi il satellite senza la correzione BE (`I4`) sarebbe una sede non riempibile |
