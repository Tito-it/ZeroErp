# Brief BE/FE — il CRUD dei registri di numerazione

> **Destinatario:** backend + frontend (`dev/backend-tid`).
>
> **In una riga:** `vendite.registri_fatturazione` **non ha nessun CRUD** — né
> rotta, né lista, né maschera. Le 14 righe di oggi nascono da changeSet di seed
> e dal provisioning automatico; per farne una a mano serve una migrazione.
>
> ⭐ **Un solo prerequisito DB, e non blocca la partenza.** Verificato il
> 2026-08-31: i codici errore che servono sono tutti a catalogo e con la loro
> policy (`E_VENDITE_DUPLICATO`, `E_VENDITE_VALIDATION`, `E_VENDITE_NOT_FOUND`,
> `E_ATTIVO_BLOCK_CHILDREN_EXIST`, `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`), la
> configurazione della lista è **dato** e si crea in-app o con
> `scripts/gen_seed_lista.py`, e il gate è quello che già protegge l'emittente.
>
> ⇒ **I passi 1-4 del §5 partono subito.** Aspettano solo il 5 e il 6 — il
> cestino col motivo — che vogliono `script.fn_check_registro_disattivabile`,
> chiesta come **voce 2** di
> [richieste aperte dal backend — elenco 2](brief-db-richieste-aperte-dal-backend-2.md).
> ⭐ È chiesta **prima** di scrivere il codice che ne dipende, non dopo.
>
> **Origine.** Domanda di Tid, 2026-08-31: *«non ricordo dove si trova il CRUD
> per la tabella numeratori»*. Non si trovava perché non c'è.
>
> **Correlati:**
> [brief-db-registri-di-numerazione-emittente-e-trasloco](../work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md) (il cantiere che ha reso questa tabella centrale) ·
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione) ·
> [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento)

---

## 0. ⛔ La cosa che rende questo CRUD diverso da tutti gli altri

**Creare e disattivare NON sono simmetrici**, e una maschera che li presenta
come le due facce di un interruttore mente.

L'indice `uq_registri_fatturazione_famiglia_emittente_utility` — un **UNIQUE
parziale**, `NULLS NOT DISTINCT`, sulle sole famiglie non-`FATTURA` — **non
filtra su `attivo`**. Ne discende che *un registro spento continua a occupare lo
slot* `(famiglia, emittente, utility)`.

⇒ **«Spegni e rifai» non è una strada.** Per la stessa terna si **riattiva**
quello che c'è. Chi ci prova prende un `23505` che parla di una riga che non
vede più.

⭐ **Ed è giusto così, non è una svista da correggere allargando il predicato**:
se lo slot si liberasse spegnendo, resterebbero due registri storici della
stessa famiglia per lo stesso emittente e nessuno saprebbe più **quale ha
numerato cosa**. La regola è scritta nel `COMMENT` dell'indice (changeSet
`20260831-37`) — questo brief la eredita, non la decide.

⛔ **Quindi la UI non può limitarsi a mostrare l'errore**: deve **non far
arrivare** l'operatore lì. Vedi `FE-3`.

---

## 1. Cosa esiste oggi — struttura, non fotografia

| Superficie | Stato |
| --- | --- |
| rotte `urls_v1.py` | **nessuna** |
| whitelist del lookup generico (`rel=`) | **assente** |
| `ui.lista_definizione` | **nessuna riga** (chiesto al DB, non ai seed) |
| viste/drawer FE | **nessuno** |
| voce di menu (`navigation.js`) | **nessuna** |

Il backend nomina la tabella in **due** file soltanto, entrambi in sola lettura:

* `VenditeRepository.get_registro_codice(registro_id)` — l'etichetta del filtro
  nell'export dei cruscotti;
* il filtro sezionale della dashboard competenza (`?registro_id=`).

**Come si gestiscono oggi**, e sono due strade:

1. **changeSet di seed** — `20260127-57`, `20260819-05`, `20260825-05`,
   `20260831-03`;
2. ⭐ **automaticamente**: `vendite.fn_provision_registri_emittente` +
   `trgfn_emittenti_fiscali_provision_registri` — un emittente **nuovo o
   riattivato** si prende da sé i registri delle quattro famiglie non fiscali.

⚠️ **Il punto 2 cambia il perimetro di questo CRUD, e va letto prima di
disegnarlo**: per DDT/ordini/commesse/resi il registro **non si crea a mano nel
caso normale**, arriva da sé. Il CRUD serve a *correggere*, *rinominare*,
*disattivare* e a coprire il caso non automatico — non a fare il lavoro
ordinario. Una maschera che mette «Nuovo» in cima suggerisce il contrario.

---

## 2. ⭐ Le due specie di registro, e perché la maschera non è una sola

| | `FATTURA` | `DDT` · `ORDINE` · `COMMESSA` · `RESO` |
| --- | --- | --- |
| quanti per emittente | **N** (oggi 3: Back-office, Front-office, NC) | **uno** per (emittente, utility) — lo impone l'UNIQUE parziale |
| chi sceglie il registro | la mappa `tipi_doc_fiscale_registri` per (tipo doc, natura) | la terna (famiglia, emittente, utility) |
| campi del limite di emissione | **ammessi** | ⛔ **vietati dal `CHECK`** `chk_registri_fatturazione_famiglia_regole_fattura` |
| `politica_data_documento` diversa da neutra | ammessa | ⛔ vietata dallo stesso `CHECK` |
| provisioning automatico | no | **sì** |

⛔ **Non è una differenza cosmetica da risolvere con un `v-if`**: sono due
regole di configurazione diverse. Un form che mostra i campi del limite su un
registro `DDT` offre caselle che il `CHECK` rifiuta — lo stesso difetto per cui
i codici CIG restavano nascosti in creazione finché il DB non li ammetteva.

⚠️ **E `reset_policy` non è una scelta**: `chk_registri_fatturazione_reset` la
inchioda ad `ANNUALE`. Va mostrata come **fatto**, non come campo — o non
mostrata affatto.

---

## 3. Backend

### BE-1 · Repository + service

Sede: `apps/vendite/db/` e `apps/vendite/services/`. ⚠️ **Non** in
`vendite_repository.py`, che è già il generico dello schema: i registri hanno
regole proprie (le due specie, i tre guard di disattivazione) e sono un
sottodominio — vale la regola di naming di AGENTS.md.

| Metodo | Note |
| --- | --- |
| `list_registri(...)` | Paginata, filtri `famiglia_documento` / `emittente` / `attivo`, con i **display field** via JOIN (descrizione famiglia dal catalogo, codice emittente) — mai lookup client-side |
| `get_registro(id)` | Dettaglio + i **contatori** di `registri_fatturazione_progressivi` (sola lettura, vedi BE-4) |
| `create_registro` / `update_registro` | Whitelist colonne esplicita. ⛔ `uid`, `id`, `reset_policy` fuori |
| `set_attivo(id, attivo)` | Un verbo suo, non un PATCH generico: vedi BE-3 |

⛔ **Lo scope emittente è a carico del BACKEND, e non è gratis**: verificato il
2026-08-31, **`registri_fatturazione` NON ha la RLS**. Chi legge senza filtrare
vede i registri di tutti gli emittenti. Si usa
`PermissionResolver.get_emittenti_sr_ids` (la colonna è
`emittente_soggetto_ruolo_id`, convenzione SR — **non** la PK: vedi
`feedback_emittente_pk_vs_soggetto_ruolo`).

### BE-2 · La traduzione del `23505`, ed è il pezzo che vale il cantiere

`map_integrity_error` con la mappa dei vincoli. ⛔ **La voce che conta è
`uq_registri_fatturazione_famiglia_emittente_utility`**, e il messaggio non può
essere «esiste già»: deve dire **che potrebbe essere spento**.

> *«Esiste già un registro per questa famiglia, questo emittente e questa
> utility — possibilmente disattivato. Un registro spento continua a occupare lo
> slot: per la stessa combinazione si riattiva quello che c'è, non se ne crea un
> altro.»*

⚠️ E la voce porta il **campo** (terzo elemento della tupla, dal 2026-08-08) —
ma solo se un campo del payload lo rappresenta davvero: qui il vincolo è
**composto su tre colonne** che l'operatore sceglie tutte, quindi la tupla resta
**a due**. Dichiarare `famiglia_documento` manderebbe a correggere un campo che
non è più sbagliato degli altri due.

Le altre voci: `uq_registri_fatturazione_codice` → codice duplicato (campo
`codice`, quello sì); `fk_registri_fatturazione_famiglia` / `_emitt` /
`_utility` → `E_VENDITE_FK`.

### BE-3 · La disattivazione ha **tre** guard, non uno

`trg_registri_fatturazione_a10_*` blocca lo spegnimento se il registro ha figli
attivi in **tre** tabelle: `fatture`, `registri_fatturazione_progressivi`,
`tipi_doc_fiscale_registri`. Sollevano `E_ATTIVO_BLOCK_CHILDREN_*`.

⭐ **Il secondo è quello che sorprende**: un registro che ha numerato anche **un
solo** documento ha una riga di contatore viva, quindi **non si spegne più**.
Non è un intralcio: è il presidio che impedisce di ritirare un sezionale con
sotto un contatore vivo.

⇒ ⛔ **Ne discende che «disattiva» è quasi sempre indisponibile**, e la UI deve
dirlo **prima** — non far premere per poi mostrare un errore. Vedi FE-2.

### BE-4 · I progressivi si LEGGONO, non si scrivono

`registri_fatturazione_progressivi` (`anno`, `mese`, `serie`, `last_numero`,
`ultima_data`) va esposto **in sola lettura** nel dettaglio.

⛔ **Nessun endpoint di modifica, e nessuna eccezione «per l'amministratore».**
Cambiare `last_numero` a mano significa riassegnare un numero già uscito, cioè
produrre due documenti con lo stesso numero sullo stesso sezionale — il difetto
che l'intero cantiere del trasloco esiste per rendere impossibile. Se un giorno
servirà, sarà un **verbo di dominio con la sua ragione e il suo audit**, non un
campo editabile in un form.

---

## 4. Frontend

### FE-1 · Dove vive — un tab dell'emittente, non una voce di menu

⭐ **Il registro è per-emittente**, e il progetto ha già il pattern esatto:
`EmittenteFiscaleBillingAccountTab` e `EmittenteFiscaleUtilitiesTab`, tab dentro
il drawer dell'emittente con `<ListaConfigurabile>` + `RowActionsMenu`.

⇒ Un terzo tab, `EmittenteFiscaleRegistriTab`, **non** una schermata di
amministrazione a sé. Motivo: una lista globale dei registri costringerebbe a
mettere l'emittente in colonna e a filtrarci sopra, cioè a ricostruire a mano il
contesto che il drawer dà già.

⛔ **Lista con `<ListaConfigurabile codice="vendite.registri_numerazione">`**,
mai una `DataTable` grezza — regola zero. La configurazione è **dato**: si crea
in-app o con `scripts/gen_seed_lista.py`, e non aspetta il team DB.

### FE-2 · Il cestino spento porta il MOTIVO

Stesso schema già in servizio sul mapping BA: la riga porta `can_remove` +
`rimozione_blocco_reason` + `..._reason_key`, il motivo arriva dal **database**
e non si ricalcola nel frontend.

⚠️ **Ma qui manca il pezzo DB**: per il mapping BA il motivo lo produce
`script.fn_check_ba_cambio_emittente`, che è una `fn_check_*` pura. Per i
registri **non esiste la gemella**. Due strade, e vanno decise prima di
scrivere:

| | Strada | Costo | Effetto |
| --- | --- | --- | --- |
| **a** | Una `script.fn_check_registro_disattivabile` che elenca i motivi (fatture, progressivi, mapping) | un changeSet DB — **questo sì è un prerequisito** | Il tooltip dice *quale* figlio blocca, e non può divergere dal rifiuto |
| **b** | Il BE conta i figli e deriva `can_remove` in Python | zero DB | ⛔ **Regola ricalcolata fuori sede**: il giorno che un quarto guard entra a DB, il tooltip resta indietro e dice «si può» su un gesto che fallisce |

⭐ **La (a) è quella coerente col progetto** (`linee-guida-sql` §12.5.2: il
motivo lo produce la stessa funzione che il database usa per rifiutare). La (b)
è il difetto che il cantiere del mapping BA ha appena finito di chiudere.
⇒ **Decisione a Tid.** Se si sceglie la (a), è l'**unico** prerequisito DB del
cantiere e va chiesto con un brief suo.

### FE-3 · «Nuovo» deve inciampare PRIMA, non dopo

Dal §0: creare un registro su una terna già occupata — anche da uno **spento** —
fallisce. La maschera deve:

* proporre la **riattivazione** quando la terna scelta ha già un registro
  disattivato, invece di lasciar premere Salva;
* ⚠️ e per farlo le serve **vedere anche gli spenti**: la lista deve avere il
  filtro `attivo` con default «tutti» o «attivi», mai «solo attivi» **fisso** —
  una lista che nasconde gli spenti nasconde proprio le righe che spiegano il
  rifiuto.

### FE-4 · I campi che dipendono dalla famiglia

I tre campi fiscali (`limite_emissione_giorni`, `limite_emissione_giorno_mese`,
`politica_data_documento` non neutra) si mostrano **solo** su
`famiglia_documento = 'FATTURA'`. Su una famiglia diversa il `CHECK` li
rifiuta.

⚠️ **Nasconderli non basta: vanno anche non spediti.** Un `null` esplicito
passa, un valore no — e il payload di un form che li tiene in `defaultForm()`
li porta comunque.

---

## 5. L'ordine

1. **BE-1/BE-2** — repository, service, mappa vincoli, scope emittente
2. **BE-4** — i progressivi in lettura nel dettaglio
3. La **configurazione della lista** (dato, in-app)
4. **FE-1/FE-4** — tab + drawer, campi condizionati alla famiglia
5. **BE-3/FE-2** — la disattivazione col motivo ⚠️ *gated sulla decisione (a)/(b)*
6. **FE-3** — la riattivazione proposta al posto del rifiuto

⭐ **I passi 1-4 non dipendono da nessuna decisione aperta**: si possono fare
subito. Il 5 aspetta la scelta fra `fn_check_*` a DB e derivazione in Python.

---

## 6. I presidi

* **Il `23505` sulla terna occupata da uno SPENTO** — è il caso che rompe, e va
  scritto per primo: si crea un registro, lo si disattiva (su una terna **senza**
  documenti, o il guard dei progressivi lo impedisce), si prova a ricrearlo, e
  si verifica che l'errore sia quello **parlante** e non un `IntegrityError` nudo;
* ⛔ **il gemello positivo**: sulla terna **libera** la create passa — senza,
  il test non distingue «respinge il caso giusto» da «respinge tutto»;
* il `CHECK` della famiglia: i campi del limite su un registro `DDT` sono
  rifiutati, e su `FATTURA` passano;
* **lo scope**: un operatore non vede i registri di un altro emittente.
  ⚠️ Su questa tabella **non c'è la RLS**, quindi il presidio non è ridondante —
  è l'unico;
* ⚠️ **Cosa non si prova con un test di servizio**: che i tre guard di
  disattivazione siano montati. Quelli sono trigger, e si presidiano in pgTAP.
