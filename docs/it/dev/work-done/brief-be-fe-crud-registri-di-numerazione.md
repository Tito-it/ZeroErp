# Brief BE/FE — il CRUD dei registri di numerazione

> 🎉 **Stato al 2026-09-02 — CANTIERE CHIUSO, DB e BE/FE.** Spostato in
> `work-done/` il 2026-09-02. Il dettaglio di ciò che è stato scritto è al
> **§13**; le decisioni che l'hanno guidato ai **§11.13** (le sei di Tid) e
> **§12** (le tre della revisione).
>
> ⚠️ **Cosa il cantiere NON chiude, e lo dichiara**: il **collaudo in-app**, che
> è in corso. I rilievi di Tid sono al §13.7, e sono tutti difetti che nessuna
> delle prove scritte aveva preso — è la ragione per cui il collaudo non è
> sostituibile.
>
> **Destinatario:** backend + frontend (`dev/backend-tid`).
>
> **In una riga:** `vendite.registri_fatturazione` **non ha nessun CRUD** — né
> rotta, né lista, né maschera. Le 14 righe di oggi nascono da changeSet di seed
> e dal provisioning automatico; per farne una a mano serve una migrazione.
>
> ⭐ **Nessun prerequisito DB residuo.** Verificato il 2026-09-01: i codici
> errore che servono sono tutti a catalogo e con la loro classe
> (`E_VENDITE_DUPLICATO`, `E_VENDITE_VALIDATION`, `E_VENDITE_NOT_FOUND`,
> `E_ATTIVO_BLOCK_CHILDREN_EXIST`, `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`), la
> configurazione della lista è **dato** e si crea in-app o con
> `scripts/gen_seed_lista.py`, il gate è quello che già protegge l'emittente, e
> `script.fn_check_registro_disattivabile` **è applicata** (`20260831-38`,
> estesa a sei motivi da `20260831-71`).
>
> ⇒ **Tutti e sei i passi del §5 partono subito.**
>
> ~~⇒ I passi 1-4 del §5 partono subito. Aspettano solo il 5 e il 6 — il cestino
> col motivo — che vogliono `script.fn_check_registro_disattivabile`, chiesta
> come **voce 2** di [richieste aperte dal backend — elenco 2](../work-done/brief-db-richieste-aperte-dal-backend-2.md).~~
> 🔴 **Superata il 2026-09-01**: quella voce è **chiusa** e il suo ordine di
> lavoro è archiviato. La riga resta perché dice una cosa che vale ancora — la
> funzione è stata **chiesta prima** di scrivere il codice che ne dipende, non
> dopo.
>
> **Origine.** Domanda di Tid, 2026-08-31: *«non ricordo dove si trova il CRUD
> per la tabella numeratori»*. Non si trovava perché non c'è.
>
> ⭐ **E dal 2026-08-31 c'è una seconda origine, più forte della prima.** Il
> cantiere [il prefisso passa sul registro](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md)
> ha portato `prefisso`, `suffisso` e `lunghezza_numero` **su questa tabella**:
> *«la forma del numero ha ora una sede sola»*, ed è il registro. Le quattro
> righe dei documenti traslocati sono **uscite** da `config.sistema_codici`, che
> un pannello di amministrazione ce l'ha. ⇒ La forma del numero è passata da un
> oggetto con maschera a uno **senza**, e la domanda che ha aperto quel cantiere
> — *«ho visto `ORD0000001`, dov'è fisso `ORD`?»* — oggi ha per risposta un campo
> che nessuno può leggere né correggere da nessuna schermata. Vedi §2-bis.
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

> 🔴 **La RAGIONE di questa riga è scaduta il 2026-09-01, lo stesso giorno in cui
> è stata scritta.** Il changeSet `20260901-06` ha allargato
> `chk_registri_fatturazione_reset` a **`ANNUALE` e `NESSUNA`**, e
> `fn_get_next_progressivo` la legge davvero: sotto `NESSUNA` il secchio del
> contatore è uno solo e la numerazione non riparte fra gli anni.
> ⇒ La **conclusione** regge ancora — oggi non è un campo, perché il backend la
> tiene fuori da entrambe le whitelist — ma non per il motivo scritto qui: non
> c'è più nessun `CHECK` che la inchiodi. Il seguito, con le due mosse da
> decidere, sta in
> [brief-db-registri-numerazione-chiave-del-contatore](brief-db-registri-numerazione-chiave-del-contatore.md)
> §7 e §11.5.
>
> ✅ **Superata il 2026-09-08**: Tid ha deciso che la scelta va in maschera, e
> `reset_policy` è ora un **campo di creazione** — `ANNUALE` (il progressivo
> riparte a ogni anno) o `NESSUNA` (un contatore solo, che non riparte mai).
> ⛔ **In modifica no**, e non è prudenza: è un asse della chiave del contatore,
> e cambiarla su un registro che ha già consegnato numeri fa ripartire il
> progressivo da 1 su un secchio nuovo, contro numeri che esistono già.
> ⚠️ E la riga qui sopra non era l'unica falsa: la stessa affermazione stava
> anche nel messaggio con cui `registri_service.py` traduceva quel `CHECK` —
> cioè in una frase **letta da una persona**, non in un commento. Dettaglio e
> prove in §11.5-bis del brief collegato.

---

## 2-bis. 🔴 La forma del numero — tre campi che questo brief non aveva

> 🔴 **Aggiunta del 2026-09-01.** La prima stesura di questo brief non nomina
> `prefisso`, `suffisso` e `lunghezza_numero` **nemmeno una volta**, e sono
> arrivati sulla tabella lo stesso giorno in cui è stato scritto
> (`20260831-39` → `-56`). Non è un dettaglio dimenticato: è **il pezzo che dà
> più valore al CRUD**, ed era assente dal documento che lo motiva.

| Colonna | Tipo | Cosa decide |
| --- | --- | --- |
| `prefisso` | `varchar` nullable | la parte fissa davanti al numero (`ORD`, `DDT`…) |
| `suffisso` | `varchar` nullable | la parte fissa in coda |
| `lunghezza_numero` | `integer` NOT NULL, default `7` | quante cifre ha il progressivo |

⭐ **Sono l'unico posto in cui la forma del numero si può cambiare.** Prima
vivevano in `config.sistema_codici`, che ha un pannello; ora vivono qui, che non
ce l'ha. ⛔ E `config.sistema_codici` **non si tocca**: le quattro righe dei
documenti traslocati ne sono uscite di proposito.

### ⛔ Il secondo UNIQUE parziale, e ha la stessa trappola del §0

```text
uq_registri_fatturazione_prefisso_suffisso
  ON (emittente_soggetto_ruolo_id, prefisso, suffisso)
  NULLS NOT DISTINCT
  WHERE COALESCE(prefisso,'') <> '' OR COALESCE(suffisso,'') <> ''
```

⚠️ **Anche questo non filtra su `attivo`**: un registro spento continua a
occupare la sua coppia prefisso/suffisso per quell'emittente. È il §0 su un
**secondo asse**.

⛔ **E la differenza che conta è dove si incontra**: quello del §0 si prende
creando, questo si prende anche **modificando** — l'operatore rinomina il
prefisso di un registro e finisce sulla coppia di un altro, magari disattivato,
che nella lista non vede. ⇒ La regola del §0 («la lista deve mostrare anche gli
spenti», FE-3) non è più solo per la creazione: vale per tutta la maschera.

### ⚠️ Cambiare la forma su un registro VIVO — e qui il DB non difende

Verificato il 2026-09-01 sull'auto-gen: sulla tabella **non esiste nessun guard**
oltre ai sei di disattivazione e ai tre di servizio (audit, `tx_id`, storico).
Nessun `lock_columns`, nessun `trgfn_*_guard_*` sulle colonne di forma.

⇒ Un `UPDATE` che cambia `prefisso`, `suffisso`, `lunghezza_numero` o
`serie_default` su un registro **che ha già numerato** passa. Il contatore in
`registri_fatturazione_progressivi` **prosegue**, quindi il documento successivo
esce con una forma nuova e un numero che continua la vecchia serie.

⛔ **È la stessa specie di difetto che il cantiere del prefisso ha appena
riparato, preso dal verso opposto**: là la forma era rimasta identica mentre il
contatore ripartiva da 1; qui la forma cambierebbe mentre il contatore prosegue.
In entrambi i casi il vincolo non se ne accorge, perché la coppia
`(forma, numero)` non è vincolata da nessuna parte.

📌 **Non si risolve in Python.** Il criterio deve stare dove sta il rifiuto,
altrimenti sono due elenchi paralleli — la lezione del §FE-2. È una **richiesta
al team DB**: vedi §7.

---

## 3. Backend

### BE-1 · Repository + service

Sede: `apps/vendite/db/` e `apps/vendite/services/`. ⚠️ **Non** in
`vendite_repository.py`, che è già il generico dello schema: i registri hanno
regole proprie (le due specie, i **sei** guard di disattivazione — vedi BE-3) e
sono un sottodominio — vale la regola di naming di AGENTS.md.

| Metodo | Note |
| --- | --- |
| `list_registri(...)` | Paginata, filtri `famiglia_documento` / `emittente` / `attivo`, con i **display field** via JOIN (descrizione famiglia dal catalogo, codice emittente) — mai lookup client-side |
| `get_registro(id)` | Dettaglio + i **contatori** di `registri_fatturazione_progressivi` (sola lettura, vedi BE-4) |
| `create_registro` / `update_registro` | Whitelist colonne esplicita. ⛔ `uid`, `id`, `reset_policy` fuori. ⚠️ E i **campi di forma** — vedi la riga qui sotto |
| `set_attivo(id, attivo)` | Un verbo suo, non un PATCH generico: vedi BE-3 |

🔴 **La whitelist di `update_registro` non è ancora decidibile** (2026-09-01).
`prefisso`, `suffisso`, `lunghezza_numero` e `serie_default` cambiano la **forma
del numero** di un sezionale che può aver già numerato (§2-bis), e oggi il
database li lascia passare. ⇒ Finché la §7 non è chiusa, `update_registro` li
tiene **fuori**: si può *creare* un registro con la sua forma, non *cambiarla*
sotto un contatore vivo. ⛔ **Non è la regola definitiva** — è il ripiego
prudente in attesa che il criterio nasca dove sta il rifiuto. Un `update` che
ammette il campo prima del guard DB è un permesso che poi va tolto a operatori
che ci hanno già fatto l'abitudine.

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

🔴 **E ne mancava una, aggiunta il 2026-09-01:
`uq_registri_fatturazione_prefisso_suffisso`.** Secondo UNIQUE parziale su
`(emittente, prefisso, suffisso)`, `NULLS NOT DISTINCT` — e **anche lui non
filtra su `attivo`** (§2-bis). Il messaggio deve dire la stessa cosa dell'altro:

> *«Questo emittente ha già un registro con questa coppia prefisso/suffisso —
> possibilmente disattivato. Due sezionali dello stesso emittente non possono
> produrre numeri della stessa forma: si riusa quello che c'è, o si cambia la
> forma.»*

⚠️ **Qui la tupla è a TRE, e la differenza rispetto all'altra voce è reale.** Il
vincolo del §0 è composto su tre colonne che l'operatore sceglie tutte, quindi
nessuna è «più sbagliata» delle altre e il campo non si dichiara. Qui le colonne
in gioco sono **due**, l'emittente non è un campo del form (lo dà il tab), e la
coppia è ciò che l'operatore ha appena scritto ⇒ si dichiara `prefisso`, che è
quello che si corregge per primo.

⛔ **E si raggiunge anche in MODIFICA**, non solo in creazione: è la ragione per
cui il filtro «mostra anche gli spenti» di FE-3 non è un accorgimento della sola
maschera di inserimento.

### BE-3 · La disattivazione ha **sei** guard, non uno

> 🔴 **CORREZIONE 2026-09-01 — questa sezione diceva «tre», e sono sei.**
> Verificato sull'auto-gen di
> [registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione), non
> dedotto. I tre in più — `ddt`, `ordini`, `resi` — hanno guadagnato
> `registro_id` col trasloco, e l'automazione ha montato i loro guard **da sola,
> al migrate**. La riga vecchia è marcata qui sotto perché il modo in cui è
> invecchiata è esattamente il rischio che il §FE-2 descriveva.

`trg_registri_fatturazione_a10_*` blocca lo spegnimento se il registro ha figli
in **sei** tabelle:

| Figlia | La figlia ha `attivo`? | Codice sollevato |
| --- | --- | --- |
| `vendite.ddt` | no | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |
| `vendite.fatture` | no | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |
| `vendite.ordini` | no | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |
| `vendite.registri_fatturazione_progressivi` | **sì** | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE` |
| `vendite.resi` | no | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |
| `vendite.tipi_doc_fiscale_registri` | no | `E_ATTIVO_BLOCK_CHILDREN_EXIST` |

~~Blocca lo spegnimento se il registro ha figli attivi in **tre** tabelle:
`fatture`, `registri_fatturazione_progressivi`, `tipi_doc_fiscale_registri`.~~

⛔ **La colonna di mezzo non è decorativa, ed è il pezzo che si sbaglia
leggendo in fretta.** `dbops.trgfn_prevent_deactivate_if_children` guarda se la
tabella *figlia* ha la colonna `attivo`: se ce l'ha blocca sulle sole righe
**attive**, altrimenti sulla loro **esistenza**. Cinque figlie su sei non ce
l'hanno ⇒ per loro basta che il documento **esista**, anche annullato. Un
servizio che chiedesse «documenti attivi» direbbe «si può disattivare» dove il
trigger rifiuta.

⭐ **Il quarto è quello che sorprende**: un registro che ha numerato anche **un
solo** documento ha una riga di contatore viva, quindi **non si spegne più**.
Non è un intralcio: è il presidio che impedisce di ritirare un sezionale con
sotto un contatore vivo.

⚠️ **E con sei guard, cinque dei quali sull'esistenza, il cestino è spento ancora
più spesso di quanto questa sezione dicesse.** Vale la pena chiederselo prima di
scrivere il passo 5: vedi la nota in coda al §5.

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

### ✅ DECISO E FATTO — `script.fn_check_registro_disattivabile`

> ✅ **Deciso da Tid il 2026-08-31** (la `fn_check_*` a DB, non la derivazione in
> Python) e **applicato lo stesso giorno**: changeSet `20260831-38`.
>
> ⚠️ **Verificato sul database vivo, non sullo YAML**: `SECURITY DEFINER` — serve,
> legge `vendite.fatture` che ha la RLS, e senza contesto emittente la check
> concluderebbe «si può disattivare» **proprio nel caso da bloccare**. Tre
> `reason` — `HA_FATTURE`, `HA_PROGRESSIVI`, `HA_MAPPING_TIPO_DOC` — **nessuno
> col prefisso `E_`**, e **nessun codice errore nuovo**: nomina i due
> `E_ATTIVO_BLOCK_CHILDREN_*` già a catalogo.

⛔ **La strada scartata, e perché**: derivare `can_remove` in Python contando i
figli è il difetto che il cantiere del mapping BA ha appena finito di chiudere —
fino al 2026-08-27 lì `can_remove` era scritto `True` a mano, ed era una
promessa falsa. Qui pesa di più, perché i guard sono **tre** (§BE-3): una
derivazione li ricopia tutti e tre, e al quarto il tooltip dice «si può» su un
gesto che fallisce.

⭐ **E §12.5.2 offre più della disciplina**: la madre non riscrive il predicato,
lo **chiama**. Il presidio da scrivere non è «tooltip e rifiuto coincidono» —
che proverebbe solo l'oggi — ma **«la madre non contiene più il predicato»**.

### ⚠️ Il residuo: il presidio del §12.5.2 NON è raggiunto, e non era raggiungibile

⛔ **Le madri non sono guard scritti a mano.** Sono istanze della stessa
automazione generica, ognuna col proprio figlio negli **argomenti del trigger**:

```text
trg_…_ddt_block_deact_upd            → dbops.trgfn_prevent_deactivate_if_children
   args = vendite \0 ddt                                \0 registro_id \0 id \0 attivo
trg_…_fatture_block_deact_upd        → dbops.trgfn_prevent_deactivate_if_children
   args = vendite \0 fatture                            \0 registro_id \0 id \0 attivo
trg_…_ordini_block_deact_upd         → …                \0 ordini
trg_…_registri_fatturazione_prog_…   → …                \0 registri_fatturazione_progressivi
trg_…_resi_block_deact_upd           → …                \0 resi
trg_…_tipi_doc_fiscale_registri_…    → …                \0 tipi_doc_fiscale_registri
```

> 🔴 **CORREZIONE 2026-09-01 — questo blocco ne elencava TRE.** Erano tre quando
> è stato scritto; alla sera dello stesso giorno erano sei.

Una funzione generica che serve **100 tabelle** non può chiamare una check
specifica. ⇒ Restano **due elenchi paralleli**: i figli stanno nei trigger
montati, e la check li riscrive a mano.

⚠️ **Il rischio ha un nome preciso**: il giorno che si registra un figlio in più,
l'automazione monta il trigger **da sola** e la check resta indietro. Il cestino
sembra acceso, l'operatore preme, fallisce — cioè il difetto che questa funzione
è nata per togliere, spostato di un passo.

### ✅ E il rischio si è avverato lo stesso giorno — poi è stato chiuso

⭐ **Non è più un'ipotesi, ed è la parte da tenere.** I figli nuovi sono arrivati
**tre insieme** — `ddt`, `ordini`, `resi`, traslocati sui registri — e per
qualche ora la check ne copriva **3 su 6**: il tooltip avrebbe detto «si può» su
un registro che il trigger rifiutava.

✅ **Chiuso in serata** dal changeSet `20260831-71`: la check ha ora **sei**
`reason` — `HA_DDT`, `HA_FATTURE`, `HA_ORDINI`, `HA_PROGRESSIVI`, `HA_RESI`,
`HA_MAPPING_TIPO_DOC` — verificate incrociando `pg_trigger` con il corpo vivo
della funzione.

⭐ **E l'ha trovato un presidio, non una rilettura**: il test 6 del pgTAP, scritto
con la frase *«il giorno che ne compare una quarta diventa rosso»*. È ciò che
rende questo un elenco parallelo **tenuto**, che è un'altra cosa da un elenco
parallelo lasciato a sé stesso.

⚠️ **Non blocca il CRUD**: la check com'è **funziona**, e il tooltip dirà la cosa
giusta. ⚠️ **Ma vale per il FE una conseguenza pratica**: i `reason` che il
frontend deve saper tradurre sono **sei**, non tre, e le loro `reason_key` sono
già nei locales `it`/`en` (`check_i18n_keys.py` verde). Chi monta il tooltip non
ne inventi una settima.

### ⭐⭐ E il numero cambia la scala: non è un problema dei registri

Misurato il 2026-08-31 sul database:

| | |
| --- | ---: |
| tabelle protette da `trgfn_prevent_deactivate_if_children` | **100** |
| trigger montati | **363** |
| `fn_check_*` di disattivazione esistenti | **1** (questa) |

E le più vincolate: `catalogo.articoli` **29** figli, `catalogo.unita_misura`
**21**, `config.sorgenti` **18**, `anagrafiche.emittenti_fiscali` **17**.

⛔ **A mano non regge.** Una check per tabella significa firmare 99 volte lo
stesso lavoro, e su `articoli` un elenco di 29 nomi nasce già vecchio. Ogni
maschera di amministrazione con un pulsante «disattiva» ha **esattamente questo
problema**, e oggi lo risolve nessuna.

~~⭐ **La strada giusta è una sola funzione generica** —
`script.fn_check_disattivabile(schema, tabella, id)` — che **legge i trigger
montati** su quella tabella invece di elencarne i figli. Quella dei registri
diventa un involucro di due righe, o sparisce.~~

> 🔴 **DECISA il 2026-08-31, ed è l'OPPOSTO. Questa riga è superata e va letta
> come tale.** L'elenco delle figlie **resta scritto a mano**, e la ragione non
> è la fatica: ogni motivo porta una **`reason_key` da tradurre**, e un elenco
> derivato da `pg_trigger` emetterebbe la chiave di una figlia che nessuno ha
> mai tradotto ⇒ la superficie mostrerebbe la **chiave nuda a video, in
> produzione**, invece di far diventare rosso un test in sviluppo.
>
> ⭐ **Il criterio che ne esce, e vale oltre questo caso**: derivare è meglio
> *quando ciò che si deriva è già completo*. Qui la derivazione produrrebbe solo
> **metà** del motivo — il fatto — e l'altra metà, la frase che una persona
> legge, non si deriva da nessuna parte.
>
> ⇒ **Non è un cantiere da aprire**, e chi legge questo brief non lo proponga
> come tale. La decisione, col suo perché, sta nel `COMMENT` di
> [`script.fn_check_registro_disattivabile`](/dbzero/script/funzioni/fn_check_registro_disattivabile)
> e nella voce 2 di
> [richieste aperte dal backend — elenco 2](../work-done/brief-db-richieste-aperte-dal-backend-2.md).

⭐ **E non si inventa niente: è il principio che questo cantiere ha già usato due
volte**, e che il brief del trasloco elogia con parole sue —
*«ed è **DERIVATA, non elencata**: il sesto documento entra nella regola il
giorno in cui si registra la sua famiglia, e non esiste nessun elenco parallelo
che possa restare indietro»* (`fn_get_storia_emittente_ba`, che deriva da
`famiglie_documento`), e *«è lo stesso principio della primitiva di pulizia che
scopre le figlie da `pg_constraint`»*. Qui si scoprono da `pg_trigger`.

⚠️ **Il limite, dichiarato**: derivare copre i divieti di *quell'automazione*. Un
guard di disattivazione scritto a mano non verrebbe visto — ma è un limite che
ha **anche** l'elenco scritto a mano, con la differenza che oggi l'automazione
copre tutti e 363 i casi. Il buco è teorico, non attuale.

~~📌 **Decisione a Tid, e vale un cantiere suo**: non è di questo brief, e non
blocca i passi 1-4.~~
✅ **Presa il 2026-08-31** (vedi il riquadro rosso qui sopra): l'elenco resta a
mano, tenuto da un presidio. Non c'è nessun cantiere da aprire e non c'è più
nulla in attesa di una decisione.

### ⚠️ Quale forma copiare — lo stato del pattern, misurato

| Grado | Forma | Dove |
| --- | --- | --- |
| ⭐ **pieno** | `reason` **e** `reason_key` viaggiano dal DB; il FE fa `labelOrCode(t, te, riga.reason_key, riga.codice)` | `TitoloIvaDrawer`, `EmittenteFiscaleBillingAccountTab`, azioni di documento (`useDrawerActions`, `useLottoAzioni`) |
| ⚠️ **parziale** | la `fn_check_*` c'è, ma la vista espone **solo il codice** e il FE **costruisce** l'indirizzo i18n con un template literal | `ResiCodaTable`, `ResoRigheTable` |
| ⛔ **fuori** | il motivo lo compone il **frontend** da uno stato | `SistemazioneDrawer`, `DistintaDrawer` |

⛔ **Si copia il grado pieno.** Il parziale non è una variante ammessa: è la
forma **precedente** alla convenzione — verificato sulle viste, `vw_resi_*`
espongono solo `annullo_blocco_codice`, mentre `vw_stiva_movimenti_dettaglio`
porta anche `annullo_blocco_reason_key`. Il `reason_key` è un **indirizzo che
dichiara il database**, non una stringa che il client compone.

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

### FE-5 · 🔴 I campi della forma del numero, e l'anteprima

> 🔴 **Aggiunta del 2026-09-01**: la prima stesura non li nominava. Vedi §2-bis.

`prefisso`, `suffisso` e `lunghezza_numero` valgono per **tutte** le famiglie —
non sono condizionati come i tre campi fiscali. Sono i campi per cui vale la
pena aprire questa maschera.

⭐ **Vanno mostrati con l'anteprima di ciò che producono**, accanto ai tre
campi: *«`ORD` + 7 cifre → `ORD0000001`»*. È l'unica forma in cui un operatore
capisce cosa sta cambiando senza doverlo dedurre — ed è la domanda che ha
originato tutto il cantiere del prefisso. L'anteprima si compone **nel
frontend** da tre valori del form, non si chiede al backend: non è una regola,
è la concatenazione di ciò che l'operatore ha appena scritto.

⛔ **In modifica restano in sola lettura** finché la §7 non è chiusa (vedi BE-1):
si mostrano — servono a capire perché i numeri hanno quella forma — ma non si
toccano su un registro che ha già numerato. ⚠️ E il motivo va **detto**, non
lasciato indovinare: un campo grigio senza spiegazione è la stessa promessa
mancata del cestino spento senza tooltip.

---

## 5. L'ordine

1. **BE-1/BE-2** — repository, service, mappa vincoli, scope emittente
2. **BE-4** — i progressivi in lettura nel dettaglio
3. La **configurazione della lista** (dato, in-app)
4. **FE-1/FE-4/FE-5** — tab + drawer, campi condizionati alla famiglia, forma del numero
5. **BE-3/FE-2** — la disattivazione col motivo ✅ *il prerequisito DB c'è (`20260831-38`, sei motivi da `20260831-71`)*
6. **FE-3** — la riattivazione proposta al posto del rifiuto

✅ **Nessun passo è gated.** Il prerequisito che il 5 aspettava —
`script.fn_check_registro_disattivabile` — è applicato dal 2026-08-31: si può
fare tutto, dall'1 al 6.

*(Superata la riga che diceva «il 5 aspetta la scelta fra `fn_check_*` a DB e
derivazione in Python»: la scelta è stata fatta — la `fn_check_*` — e applicata
in giornata.)*

~~⚠️ **Resta aperta una cosa sola, e non è di questo brief**: se la check debba
**derivare** i figli dai trigger montati invece di elencarli, e soprattutto se
farlo **una volta per tutte e 100 le tabelle** che hanno lo stesso problema
(§FE-2, in coda). Non blocca niente qui.~~
🔴 **Superata il 2026-09-01: quella decisione è stata presa, ed è «no»** —
l'elenco resta a mano, tenuto da un presidio (§FE-2). Al suo posto resta aperta
**un'altra** cosa, che è di questo brief e sta nella §7: chi impedisce di
cambiare la forma del numero sotto un contatore vivo.

### ⚠️ Una domanda di priorità, prima di scrivere il passo 5

Con **sei** guard, cinque dei quali sull'**esistenza** e non sulle righe attive
(BE-3), il cestino è indisponibile su qualunque registro abbia mai visto un
documento — cioè su tutti quelli in servizio. ⇒ Il passo 5 produce quasi sempre
un pulsante spento **con una buona spiegazione**, che è il comportamento
corretto ma non è il valore del cantiere.

⭐ **Il valore sta nei passi 1-4 più la §2-bis**: vedere i registri, correggere
un codice o una descrizione, capire e governare la forma del numero. ⛔ Non è un
motivo per saltare il 5 — un cestino acceso che fallisce sarebbe peggio — ma è
un motivo per **non metterlo per primo**, e per non misurare la riuscita del
cantiere su di lui.

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
  ⚠️ Su questa tabella **non c'è la RLS** (riverificato il 2026-09-01), quindi il
  presidio non è ridondante — è l'unico;
* 🔴 **Il `23505` sulla coppia prefisso/suffisso occupata da uno SPENTO** — stesso
  schema del primo presidio, sul **secondo** UNIQUE parziale (§2-bis), e col suo
  gemello positivo. ⛔ Va provato **in modifica**, non solo in creazione: è lì che
  questo vincolo si incontra, e un test scritto solo sulla create lo mancherebbe;
* ⚠️ **Cosa non si prova con un test di servizio**: che i **sei** guard di
  disattivazione siano montati. Quelli sono trigger, e si presidiano in pgTAP —
  dove il presidio c'è già ed è quello che ha trovato lo scarto da 3 a 6.
  ⛔ **Il test di servizio non lo riscriva**: conterebbe la stessa cosa in un
  posto dove nessuno lo guarda.

---

## 7. 🔴 La richiesta al team DB — chi impedisce di cambiare la forma sotto un contatore vivo

> 🔴 **Aggiunta del 2026-09-01.** È l'unica cosa che questo brief chiede al DB, e
> **non blocca nessuno dei sei passi**: si parte con i campi di forma in sola
> lettura in modifica (BE-1), e il giorno che il guard esiste si aprono.

**Il fatto, verificato — non dedotto.** Sull'auto-gen di
[registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione) i trigger
sono **nove**: sei guard di disattivazione, più audit, `tx_id` e storico.
⛔ **Nessuno presidia le colonne di forma.** Un `UPDATE` che cambia `prefisso`,
`suffisso`, `lunghezza_numero` o `serie_default` su un registro che ha già
numerato **passa**, e il contatore in `registri_fatturazione_progressivi`
prosegue da dov'era.

**Cosa ne discende.** Il documento successivo esce con una forma nuova e un
numero che continua la serie vecchia. Sullo stesso sezionale, nello stesso anno,
convivono due forme — e **nessun vincolo se ne accorge**, perché la coppia
*(forma, numero)* non è vincolata da nessuna parte.

⭐ **È la stessa specie di difetto che il cantiere del prefisso ha appena
riparato, preso dal verso opposto**: là la forma restava identica mentre il
contatore ripartiva da 1
([brief-db-prefisso-sul-registro](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md),
difetto A); qui la forma cambia mentre il contatore prosegue. In entrambi i casi
il danno è **due documenti diversi che si somigliano**, ed è il genere di cosa
che si scopre da un cliente, non da un test.

**La richiesta.** Un guard che rifiuti la modifica delle colonne di forma quando
il registro ha almeno una riga di progressivi — la stessa condizione che già
rende indisponibile la disattivazione, quindi **un criterio solo per due divieti
imparentati**, non uno nuovo.

⚠️ **Tre cose da non dare per scontate**, e sono da decidere al DB, non qui:

1. **`serie_default` sta nello stesso insieme?** Il `COMMENT` della tabella dice
   che cambiarlo su un registro vivo *«SPOSTA il sezionale»*. Sembra lo stesso
   divieto — ma è un'affermazione da **verificare sul comportamento**, non da
   ereditare da una frase. ⚠️ È la forma di premessa che l'elenco 2 delle
   richieste ha visto smentita tre volte: *si misura la cosa, non la parola che
   la nomina.*
2. **Il divieto è categorico, o ha una via d'uscita?** Se un prefisso nasce
   sbagliato e il registro ha già numerato, un divieto senza alternativa lascia
   l'operatore fermo. ⇒ Forse la risposta non è «non si cambia» ma «si apre un
   registro nuovo», che è già la forma che il §0 impone alla creazione.
   ⛔ Se la strada è questa va **detta nel messaggio d'errore**: un rifiuto che
   non nomina l'alternativa la fa cercare a mano.
3. **Serve davvero un codice errore nuovo?** Da valutare prima di coniarlo: la
   famiglia `E_ATTIVO_BLOCK_CHILDREN_*` non calza (non si sta disattivando
   nulla), ma nemmeno si ripiega su un generico. ⭐ La domanda si risponde su
   **chi può rimediare**, non sulla condizione.

⛔ **Non si risolve in Python, e la ragione è già scritta in questo brief.** Un
criterio ricalcolato nel service è un secondo elenco parallelo accanto a quello
del database: il §FE-2 racconta cosa succede quando i due si sfilano — e lì
c'era almeno un presidio a tenerli allineati. Qui non ci sarebbe.

### Cosa blocca — niente, ed è il punto

⭐ Il CRUD parte lo stesso: il backend tiene i campi di forma **fuori dalla
whitelist di `update`** (BE-1), e il FE li mostra in sola lettura in modifica
(FE-5). Si può creare un registro con la sua forma, non cambiarla sotto un
contatore vivo. ⚠️ **È un ripiego prudente, non la regola definitiva** — un
`update` che ammettesse il campo prima del guard sarebbe un permesso da togliere
a operatori che ci hanno già fatto l'abitudine.

### Presidio atteso

Un pgTAP che **costruisce** il caso invece di cercarlo fra i dati: registro nuovo
→ si numera un documento (nasce la riga di progressivi) → si prova a cambiare il
prefisso → **rifiuto**, con lo SQLSTATE e il codice attesi.

⛔ E il **gemello positivo**: sullo stesso registro **prima** di numerare, il
cambio passa. Senza, il test non distingue «rifiuta il caso giusto» da «rifiuta
sempre».

---

## 8. 🛠️ Piano di sviluppo DB — il guard sulla forma del numero

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-01.
> ⭐ È l'esecuzione della §7. Le **tre domande che la §7 lasciava aperte sono
> state chiuse** qui sotto, e ognuna con un fatto verificato sul database vivo —
> non con la frase di un `COMMENT`.

### 8.1 ✅ Le tre decisioni, e su cosa poggiano

#### Q1 · `serie_default` **NON entra** nel guard — due ragioni indipendenti

⭐ **Sul modello.** La chiave del contatore è
`(registro_id, anno, mese, serie)` (`uq_regprog_key`), e `serie` **è dentro la
chiave**. Cambiare `serie_default` non fa proseguire un contatore sotto una
forma nuova: apre un **bucket nuovo** che riparte da 1, sotto una serie che
distingue i documenti da quelli di prima. ⇒ È il modo **legittimo** di aprire una
serie nuova. Il danno che questo guard previene è l'**opposto**: forma diversa
con la **stessa** serie e lo **stesso** contatore.

⛔ **E c'è un fatto strutturale che chiude la questione da solo.**
`db/changelog/migrations_v2/80_data/sql/vendite/registri_fatturazione.csv` è un
**mirror vivo** — `runOnChange: true` + `validCheckSums: ANY` (`20260127-57`) —
e fra le sue colonne c'è `serie_default`. Un `BEFORE UPDATE OF serie_default`
scatta **anche quando il valore non cambia**, perché è lo `UPDATE` a nominare la
colonna. ⇒ Metterla nel guard **farebbe fallire ogni singolo migrate**.

⚠️ **Residuo dichiarato — e il 2026-09-01 ha preso una forma precisa.** Il
`COMMENT` della tabella dice che cambiare `serie_default` su un registro vivo
*«SPOSTA il sezionale»*: vero, ma vago. Guardando **chi registra la serie sul
documento**, il residuo non è uniforme:

* su `fatture`, `ddt` e `ordini` la serie è in colonna **e** dentro il vincolo di
  unicità ⇒ il gesto è **legittimo e innocuo**: si apre una serie nuova;
* su `resi` e `commesse` no ⇒ il contatore riparte da 1 su numeri già usati, il
  vincolo li rifiuta e il documento **non si numera più**.

⇒ È diventato un cantiere suo, con la sua analisi e il suo piano:
[brief-db-registri-numerazione-chiave-del-contatore](brief-db-registri-numerazione-chiave-del-contatore.md).
⭐ Lì la cura è **dare l'asse mancante ai documenti**, non vietare il campo sul
registro — e la colonna `mese` del contatore, dormiente e senza nessun documento
che la porti, **si toglie**.

⭐ **E il CSV dice la cosa che rende il guard possibile**: `prefisso`, `suffisso`
e `lunghezza_numero` **non sono fra le sue colonne**. Il mirror non le tocca,
quindi il guard non lo incontra mai.

#### Q2 · Il divieto è **categorico**, e la frase non inventa una via d'uscita

Per la famiglia `FATTURA` una via d'uscita ci sarebbe — il modello ammette **N**
registri per emittente. ⛔ **Per le altre quattro no**: l'UNIQUE parziale del §0
ne ammette **uno solo** per `(emittente, utility)`, e disattivare quello che c'è
è a sua volta bloccato (BE-3). ⇒ Dire *«apri un registro nuovo»* sarebbe una
strada che per quattro famiglie su cinque **non esiste**.

⇒ **Il messaggio dice che non si può, e perché. Non promette un rimedio.** Una
via d'uscita vera — un verbo di dominio «cambia forma e apri una serie nuova» —
non esiste, e inventarla dentro un guard sarebbe inventarla di nascosto.

⭐ **Ed è il contro-caso di «un cancello su stato persistente blocca per
sempre»**, che qui vale al rovescio: lo stato **dopo** l'azione è
irrecuperabile. Il prefisso si può rimettere com'era, ma i documenti emessi nel
frattempo **non si disfano** — restano con una forma che non è quella del loro
sezionale. Quando il dopo è irrecuperabile, il cancello è la difesa.

#### Q3 · Un codice errore nuovo **serve**, e il §12.5.2 non lo vieta

⚠️ Il §12.5.2 dice *«nessun codice errore nuovo: se per scrivere la check
servisse un codice nuovo, il difetto è a monte — la madre stava rifiutando senza
saper dire perché»*. ⛔ **Quella riga vale quando si retrofitta una check su un
rifiuto che esiste già.** Qui il rifiuto **non esiste**: lo stiamo creando. Non
c'è nessuna madre muta da sanare.

**Codice:** `E_REGISTRO_FORMA_NUMERO_IMMUTABILE`, classe **`CONFLITTO_STATO`**
(409). ⭐ Il nome segue la famiglia già a catalogo — `E_COMMESSA_CHIAVE_IMMUTABILE`,
`E_DDT_CAUSALE_IMMUTABILE`, `E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE` — e la
classe è quella giusta: non è un dato sbagliato, è una richiesta in conflitto con
lo **stato** del registro.

### 8.2 ⭐ Il predicato: «ha già consegnato un numero», non «ha una riga»

`vendite.fn_get_next_progressivo` inserisce la riga di contatore a
`last_numero = 0` e **nella stessa chiamata** la porta a `≥ 1`. ⇒ Una riga ferma
a `0` significa che da quel bucket **non è mai uscito un numero**.

Il predicato è quindi `EXISTS (… WHERE last_numero > 0)`, e **non** «esiste una
riga di progressivi».

⚠️ **È di proposito più stretto di quello della disattivazione**, che guarda
`attivo IS TRUE` a prescindere dal contatore: là il presidio protegge il
contatore *in quanto tale*, qui il danno comincia col **primo numero
consegnato**. Due divieti imparentati, non lo stesso divieto.

⭐ **E il guard confronta i valori, non le colonne**: `IS DISTINCT FROM` su tutte
e tre. Un `UPDATE` che nomina la colonna senza cambiarla passa — così un domani
il mirror CSV può guadagnare quelle colonne senza far fallire il migrate.

### 8.3 I passi

| Passo | Cosa | Dove |
| --- | --- | --- |
| **D-1** | Codice errore + messaggio | append ai due CSV di `80_data` |
| **D-2** | `script.fn_check_registro_forma_modificabile` — la pure check §12.5.1 | `20_code/script/20260901-02` |
| **D-3** | Il guard che **chiama** la check + il trigger | `20_code/vendite/20260901-03` |
| **D-4** | pgTAP | `db/pgtap/vendite/test-registro-forma-numero-immutabile-v1.sql` |
| **D-5** | Doc manuale della funzione | `dbzero/script/manual/` |

⭐ **D-1 non ha un changeSet suo, ed è la regola.** `codici_errore.csv` e
`messaggi_errore.csv` hanno già un **mirror vivo** (`20260614-08`,
`runOnChange: true` + `validCheckSums: ANY`): un codice nuovo è un **append al
CSV**, mai un loader nuovo.

⭐ **D-3 realizza il presidio del §12.5.2, che sulla disattivazione era
irraggiungibile.** Là a rifiutare è un trigger **generico** condiviso da 100
tabelle, che non può chiamare una check specifica. Qui il guard è **nostro**:
non riscrive il predicato, lo **chiama**, e solleva il codice del primo motivo.
⇒ Il presidio da scrivere non è «tooltip e rifiuto coincidono» — che proverebbe
solo l'oggi — ma **«il guard non contiene più il predicato»**.

### 8.4 ⚠️ Cosa NON si tocca

* ⛔ **`config.sistema_codici`**: le quattro righe dei documenti traslocati ne
  sono uscite di proposito (`20260831-53`). Non ci si rientra.
* ⛔ **I sei guard di disattivazione**: sono `BEFORE UPDATE OF attivo`, il nuovo
  è `BEFORE UPDATE OF prefisso, suffisso, lunghezza_numero`. Insiemi di colonne
  disgiunti ⇒ non si oscurano a vicenda, e nessuno dei due scatta in `INSERT`
  (dove oscurerebbe i `CHECK`).
* ⛔ **Nessuna migrazione applicata.** I changeSet si scrivono e si provano
  eseguendo l'SQL **estratto** in transazione; l'apply lo autorizza Tid.

### 8.5 Il debito verso il FE, dichiarato

⚠️ La check emette **una** `reason_key` nuova —
`amministrazione.registri_fatturazione.forma_blocco.ha_numerato` — che va nei
`locales` `it`/`en` **nello stesso giro** del lavoro FE, o
`scripts/check_i18n_keys.py` fallisce (§12.3). ⛔ Il team DB non la scrive: il
perimetro DB non tocca `frontend/`.

⇒ È il campo che dà a **FE-5** il motivo da mostrare accanto ai campi in sola
lettura, invece di lasciarli grigi e muti.

### 8.6 ✅ Stato — **APPLICATO** il 2026-09-01

| Passo | Esito | File |
| --- | --- | --- |
| **D-1** | ✅ scritto | append a `codici_errore.csv` (`E_REGISTRO_FORMA_NUMERO_IMMUTABILE`, `CONFLITTO_STATO`) e a `messaggi_errore.csv` (id 1039) |
| **D-2** | ✅ scritto | `20_code/script/20260901-02-create-fn-check-registro-forma-modificabile-mctit.yaml` |
| **D-3** | ✅ scritto | `20_code/vendite/20260901-03-create-trgfn-registri-guard-forma-numero-mctit.yaml` |
| **D-4** | ✅ **8/8 verdi** | `db/pgtap/vendite/test-registro-forma-numero-immutabile-v1.sql` |
| **D-5** | ✅ scritto | `dbzero/script/manual/fn_check_registro_forma_modificabile.md` |

✅ **Applicato da Tid il 2026-09-01.** Verificato sul `databasechangelog`, non
sul documento: `20260901-02` e `20260901-03` risultano **`EXECUTED`** alle
11:52. Gli oggetti esistono (funzione, guard, trigger montato) e il codice
`E_REGISTRO_FORMA_NUMERO_IMMUTABILE` è a catalogo col suo messaggio.
Doc auto-generata rigenerata.

**Come è stato provato**, e conta più dell'elenco: l'SQL **estratto dai due
YAML** è stato eseguito su una transazione con `ROLLBACK`, insieme al seed del
codice errore — che a catalogo non c'è ancora, perché il mirror di `80_data` gira
al migrate. Poi il pgTAP, nella stessa forma. ⚠️ Pre-apply il test gira
necessariamente da **owner**: gli oggetti non esistono e vanno creati nella
transazione.

Le cinque prove che contano, tutte verdi:

| | Caso | Esito |
| --- | --- | --- |
| 1 | registro che non ha mai numerato → cambio forma | **passa** (il gemello positivo) |
| 2 | registro che ha numerato → cambio `prefisso` | **rifiutato**, `P0001` |
| 3 | stesso caso → cambio `lunghezza_numero` | **rifiutato** |
| 4 | `UPDATE` che nomina la colonna **senza cambiarla** | **passa** (no-op) |
| 5 | `serie_default` su registro che ha numerato | **passa** — fuori dal divieto |

⭐ **E la frase che l'operatore legge è arrivata intera**, coi due segnaposto
riempiti dai `valori` della check:

> *«Registro ZZ-PROVA-FORMA: la forma del numero non si può più cambiare, questo
> sezionale ha già consegnato dei numeri (ultimo: 41).»*

**Guardrail CI, verdi sui file nuovi:** preambolo pgTAP (552 file), `runOnChange`
in `00_schema`/`20_code`, `check_i18n_keys`. ⚠️ Il debito `throws_ok` senza
discriminante **non sale**: il test passa `P0001`.

#### ⚠️ Due cose da sapere prima dell'apply

1. **La chiave di traduzione non esiste ancora**, ed è voluto:
   `amministrazione.registri_fatturazione.forma_blocco.ha_numerato` è **zero
   occorrenze** nei due `locales`. Oggi `check_i18n_keys.py` è verde perché
   guarda la doc auto-generata e la funzione non è applicata. ⛔ **Dopo l'apply e
   la rigenerazione della doc diventerà rosso** finché il FE non la aggiunge —
   ed è il comportamento giusto: è il debito del §12.3 che si fa sentire.
2. **Nel diario l'errore non si è persistito**, durante la prova:
   `fn_log_error_only` scrive via `dblink` e la FK verso `messaggi_errore` non
   risolveva, perché il codice viveva solo dentro la transazione poi annullata.
   ⚠️ È un artefatto della prova, non un difetto del guard — dopo il migrate il
   codice è a catalogo. Va saputo perché a leggere il log della prova sembra un
   fallimento, e non lo è.

#### 🔭 Cosa resta, e non è del team DB

* la **chiave i18n** nei due `locales` (FE, §8.5);
* la lettura della check nella **maschera**, per tenere i tre campi in sola
  lettura **col motivo** invece che grigi e muti (FE-5);
* ⚠️ e il **residuo dichiarato** su `serie_default` (§8.1 Q1), che non è coperto
  da niente e resta una decisione aperta.

---

## 9. ✅ Lato DB chiuso — e cosa trova il backend

> **Verificato sul database vivo il 2026-09-01, dopo l'apply e la rigenerazione
> della doc.** Non sul documento.

### 9.1 Il collaudo post-apply

| Verifica | Esito |
| --- | --- |
| `databasechangelog` | `20260901-02` e `-03` **`EXECUTED`**, 11:52 |
| Oggetti vivi | funzione check, funzione guard, **trigger montato** |
| Catalogo | `E_REGISTRO_FORMA_NUMERO_IMMUTABILE` + messaggio `it` presenti |
| pgTAP dal runner **normale** (`app`, non owner) | **8/8, PASS** |
| `EXECUTE` per `zeroerp_app` | ✅ su entrambe le check e sul guard |
| Doc auto-generata | rigenerata per i due oggetti nuovi |

⭐ **Il pgTAP ora gira come l'applicazione, non da owner.** Pre-apply era
necessariamente owner (gli oggetti andavano creati nella transazione): questa
corsa prova qualcosa in più, cioè che il guard rifiuta e la check risponde **con
i privilegi con cui ci parlerà il backend**.

### 9.2 ⭐ Cosa il backend NON deve costruire — la prova, non l'impressione

⛔ **Non serve nessuna vista nuova**, e non serve chiamare le check riga per
riga. I due motivi si prendono **in una query sola**, con due `LATERAL`:

```sql
SELECT r.id, r.codice, r.famiglia_documento,
       r.prefisso, r.suffisso, r.lunghezza_numero,
       d.motivi -> 0 ->> 'reason'      AS rimozione_blocco_reason,
       d.motivi -> 0 ->> 'reason_key'  AS rimozione_blocco_reason_key,
       f.motivi -> 0 ->> 'reason'      AS forma_blocco_reason,
       f.motivi -> 0 ->> 'reason_key'  AS forma_blocco_reason_key
  FROM vendite.registri_fatturazione r
  CROSS JOIN LATERAL script.fn_check_registro_disattivabile(r.id)      AS d(motivi)
  CROSS JOIN LATERAL script.fn_check_registro_forma_modificabile(r.id) AS f(motivi)
```

**Misurato il 2026-09-01**: sull'intera tabella, `Execution Time: 9,161 ms`.
⚠️ È un **fatto datato**, non una promessa: la lista sarà paginata, quindi le
chiamate saranno quelle della pagina.

⛔ **Due colonne, due verbi, due nomi** — §12.5.4: `rimozione_blocco_*` risponde
a «posso spegnerlo?», `forma_blocco_*` a «posso cambiargli la forma?». Non si
riusa una colonna per l'altra domanda: sono spenti da condizioni diverse, e su
un registro appena creato la prima è vuota e la seconda pure, mentre su uno che
ha numerato lo sono entrambe **per motivi diversi**.

⚠️ **`ui.lista_definizione.vista_sql` è NULLABLE**, e molte liste attive non ce
l'hanno: la configurazione della lista **non pretende una vista**. Il passo 3 del
§5 resta quello che era — dato, in-app o con `gen_seed_lista.py`.

### 9.3 ⇒ Sì, si può passare al BE — con due cose da sapere

✅ **Tutti e sei i passi del §5 sono sbloccati.** Il database non deve più niente
al backend: i vincoli, le due check, i codici errore e il guard ci sono, e sono
raggiungibili dal ruolo applicativo.

⛔ **Ma il repository ha un guardrail ROSSO, e lo chiude solo il FE.**
`scripts/check_i18n_keys.py` esce **1**:

```text
[X] 1 CHIAVI EMESSE DAL DB e assenti dai locales
    amministrazione.registri_fatturazione.forma_blocco.ha_numerato
```

⭐ **È il comportamento voluto, non un incidente.** Prima dell'apply il cancello
era verde perché legge la doc auto-generata e la funzione non esisteva; ora la
funzione c'è, la chiave è dichiarata e **il debito del §12.3 si fa sentire**. Si
chiude aggiungendo la chiave in `it.json` **e** `en.json` — il perimetro DB non
tocca `frontend/`.

⚠️ **Chi apre una PR prima di allora la trova rossa**, e non per colpa sua: va
messo in conto nel primo giro di lavoro FE, non dopo.

⚠️ **E resta il residuo dichiarato su `serie_default`** (§8.1 Q1): non è coperto
da niente, e il `COMMENT` della tabella continua a dire che cambiarla su un
registro vivo sposta il sezionale. Non blocca il CRUD — la colonna non è nella
maschera finché qualcuno non decide che ci vada — ma è una decisione aperta, non
una cosa fatta.

---

## 10. 🛠️ Piano di sviluppo BE/FE — il CRUD, adesso che il DB non deve più niente

> **Destinatario:** backend + frontend (`dev/backend-tid`). Aperto il 2026-09-01,
> dopo il push del team DB (merge `#1461`, commit `b6b6b83d`).
> ⭐ È l'esecuzione dei **sei passi del §5**. Non li rinumera: li raggruppa in
> fasi che si possono chiudere una per volta, ognuna con la sua prova.

### 10.1 ✅ Verifica del push — sette fatti, letti dove stanno

> Controllati il 2026-09-01 sulla **doc auto-generata** e sui guardrail, non sui
> changeSet. Sono **fatti datati**: dicono che i prerequisiti ci sono, non come
> va disegnato il CRUD.

| # | Cosa | Dove l'ho letto | Esito |
| --- | --- | --- | --- |
| 1 | Le tre colonne di forma sulla tabella | auto-gen `registri_fatturazione` | ✅ `prefisso`, `suffisso` nullable, `lunghezza_numero` NOT NULL default 7 |
| 2 | I **due** UNIQUE parziali, nessuno dei due su `attivo` | stesso auto-gen, sezione indici | ✅ `…_famiglia_emittente_utility` e `…_prefisso_suffisso`, entrambi `NULLS NOT DISTINCT` |
| 3 | Il guard sulla forma è **montato** | stesso auto-gen, sezione trigger | ✅ `trg_registri_fatturazione_a10_guard_forma_numero_upd`, `BEFORE UPDATE` |
| 4 | I **sei** guard di disattivazione | stesso auto-gen | ✅ `ddt`, `fatture`, `ordini`, `registri_fatturazione_progressivi`, `resi`, `tipi_doc_fiscale_registri` |
| 5 | Le due `fn_check_*` e le loro `reason_key` | auto-gen `script/funzioni/` | ✅ sei `reason` sulla disattivabile, **una** (`HA_NUMERATO`) sulla forma |
| 6 | Il codice errore e il suo messaggio | `codici_errore.csv` r. 833, `messaggi_errore.csv` r. 828 | ✅ `E_REGISTRO_FORMA_NUMERO_IMMUTABILE`, `CONFLITTO_STATO`, messaggio `it` id 1039 |
| 7 | Il guardrail i18n | `python3 scripts/check_i18n_keys.py` | 🔴 **rosso**, con **una** sola chiave: `…forma_blocco.ha_numerato` |

⭐ **Il punto 7 è la prima riga di codice da scrivere, non una noia di fine
lavoro.** Le **sei** chiavi della disattivazione sono già nei due `locales`
(verificate una per una, `it` **e** `en`); manca solo la settima, quella nata
col guard di ieri. ⛔ Finché non c'è, **qualunque** PR di questo cantiere nasce
rossa — e non per colpa di chi la apre.

### 10.2 ⚠️ Due cose che il push ha cambiato, e il brief sopra non le dice ancora

#### A · La whitelist di `update_registro` **si apre** — il ripiego è scaduto

Il §BE-1 tiene `prefisso`, `suffisso` e `lunghezza_numero` **fuori** dalla
whitelist di `update`, e lo dichiara *«ripiego prudente in attesa che il criterio
nasca dove sta il rifiuto»*. Il §7 lo diceva con la data di scadenza dentro:
*«il giorno che il guard esiste si aprono»*.

⇒ **Il guard esiste da ieri.** I tre campi **entrano** nella whitelist di
`update`, e a rifiutare è il database sul registro che ha già consegnato un
numero. ⛔ Tenerli fuori adesso sarebbe l'errore opposto a quello che il ripiego
evitava: un divieto **applicativo** accanto a un divieto **di database**, cioè il
secondo elenco parallelo che tutto questo brief passa il tempo a rifiutare.

⚠️ `serie_default` **resta fuori** dalla whitelist e fuori dalla maschera: non è
coperta dal guard (§8.1 Q1), il suo residuo è dichiarato e aperto, e un campo
editabile senza presidio è peggio di un campo assente.

#### B · La sola-lettura di FE-5 diventa **per riga**, non categorica

Il §FE-5 dice *«in modifica restano in sola lettura finché la §7 non è chiusa»*.
Chiusa la §7, la regola giusta non è «sempre grigi» né «sempre editabili»: è
**quello che risponde la check**, riga per riga.

* `forma_blocco_reason` **vuoto** → i tre campi si modificano;
* `forma_blocco_reason` **valorizzato** → sola lettura **col motivo**, dalla
  `reason_key`, mai grigi e muti.

⭐ È lo stesso schema del cestino di FE-2, su un secondo verbo — ed è la ragione
per cui il §9.2 insiste su **due colonne, due nomi**: `rimozione_blocco_*` e
`forma_blocco_*` rispondono a domande diverse e su un registro che ha numerato
sono spente **per motivi diversi**.

### 10.3 Le fasi

#### F0 · La chiave i18n *(minuti, e sblocca il repository)*

| Cosa | Dove |
| --- | --- |
| `amministrazione.registri_fatturazione.forma_blocco.ha_numerato` | `frontend/src/locales/it.json` **e** `en.json`, accanto alle sei `disattiva_blocco.*` già presenti |

Prova: `python3 scripts/check_i18n_keys.py` torna verde.
⛔ Non si aspetta il resto del lavoro FE: è il guardrail di tutti.

#### F1 · BE — repository, service, rotte *(passi 1 e 2 del §5)*

| File | Contenuto |
| --- | --- |
| `apps/vendite/db/registri_repository.py` | `list_registri`, `get_registro`, `create_registro`, `update_registro`, `set_attivo` |
| `apps/vendite/services/registri_service.py` | validazione payload, le due specie, traduzione vincoli |
| `apps/vendite/api/views_registri.py` | le viste, `area_funzionale = "vendite"`, `lista_codice = "vendite.registri_numerazione"` |
| `apps/vendite/api/urls_registri.py` | montato in `urls_v1.py` come `path("registri/", include(...))`, accanto ai sette fratelli |

⛔ **Sede: sottodominio suo, non `vendite_repository.py`** — che è già il generico
dello schema. È la stessa scelta di `resi_repository.py` e `ddt_repository.py`.

⭐ **La query della lista è quella del §9.2, e non si inventa**: una `SELECT` con
**due `CROSS JOIN LATERAL`** sulle due check, che porta in riga sia
`rimozione_blocco_*` sia `forma_blocco_*`. ⛔ Niente vista nuova, niente chiamata
riga per riga dal service.

**I quattro punti dove si sbaglia**, tutti già scritti sopra e qui solo raccolti:

1. ⛔ **Lo scope emittente è a carico del BE**: `registri_fatturazione` **non ha
   la RLS**. Si filtra con `PermissionResolver.get_emittenti_sr_ids` su
   `emittente_soggetto_ruolo_id` — la colonna SR, **non** la PK
   (`feedback_emittente_pk_vs_soggetto_ruolo`);
2. ⛔ **`reset_policy` e `uid` fuori dalla whitelist** in creazione e in modifica;
   `serie_default` fuori (§10.2 A); i tre campi di forma **dentro**;
3. **`map_integrity_error`** (`apps/core/services/payload_helpers.py`) con le
   **cinque** voci del §BE-2 — e le due frasi parlanti scritte per intero: quella
   della terna dice *«possibilmente disattivato»*, quella della coppia
   prefisso/suffisso pure. ⚠️ Tupla **a due** sulla terna (nessun campo è più
   sbagliato degli altri), **a tre** sulla coppia (si dichiara `prefisso`);
4. ⚠️ **Il permesso è di area `vendite`, la maschera vive in `amministrazione`**:
   da verificare in F1 che l'operatore che apre il drawer dell'emittente arrivi
   davvero alla rotta. Se non ci arriva è una domanda di permessi, **non** un
   motivo per spostare il dominio dei dati.

#### F2 · BE — i progressivi in lettura *(passo 2 del §5)*

`get_registro` porta le righe di `registri_fatturazione_progressivi`
(`anno`, `mese`, `serie`, `last_numero`, `ultima_data`) in **sola lettura**.
⛔ Nessuna rotta di scrittura, nessuna eccezione per l'amministratore (§BE-4).

#### F3 · La configurazione della lista *(passo 3 del §5)*

`ui.lista_definizione` codice **`vendite.registri_numerazione`**, creata in-app o
con `scripts/gen_seed_lista.py`. ⚠️ `vista_sql` è **nullable** e molte liste vive
non ce l'hanno: non serve una vista (§9.2).

Colonne minime: codice, descrizione, famiglia (display dal catalogo), utility,
prefisso, suffisso, `lunghezza_numero`, `attivo`.
⛔ **Filtro `attivo` con default «tutti»**, mai «solo attivi» fisso: una lista che
nasconde gli spenti nasconde le righe che spiegano il rifiuto (§FE-3, §2-bis).

#### F4 · FE — il tab, il drawer, la forma del numero *(passo 4 del §5)*

| File | Note |
| --- | --- |
| `amministrazione/components/EmittenteFiscaleRegistriTab.vue` | terzo tab del drawer emittente |
| `amministrazione/components/RegistroNumerazioneDrawer.vue` | drawer autonomo |
| `amministrazione/api/registriNumerazione.js` + `stores/registriNumerazione.js` | store `userScoped: true` |

⭐ **Il modello da copiare è `EmittenteFiscaleBillingAccountTab`**, non
`…UtilitiesTab`: il primo usa `useListaConfigurabilePage` +
`<ListaConfigurabile>` + `RowActionsMenu` + `can_remove`/`rimozione_blocco_*` con
`labelOrCode`; il secondo è ancora una `DataTable` grezza. ⛔ Si copia il primo.

Regole già in catalogo, qui solo richiamate: kebab `RowActionsMenu` +
`MANAGE_ICONS.KEBAB` (mai la matita) · prop `readonly` + `useInjectReadonly` ·
`contentReady` + `@after-show` · `watch(props.id, loadAll, { immediate: true })`
sul tab · `if (result !== null)` al salvataggio.

**FE-4 — i campi condizionati alla famiglia**: i tre fiscali solo su
`FATTURA`. ⚠️ **Nasconderli non basta, vanno anche non spediti**: un `defaultForm()`
li porta comunque.

**FE-5 — la forma del numero, ed è il pezzo che vale la maschera**:

* i tre campi valgono per **tutte** le famiglie;
* **anteprima composta nel FE** dai tre valori del form — *«`ORD` + 7 cifre →
  `ORD0000001`»*. Non si chiede al backend: è concatenazione di ciò che
  l'operatore ha appena scritto, non una regola;
* **sola lettura per riga** secondo `forma_blocco_reason` (§10.2 B), col motivo
  reso da `labelOrCode(t, te, riga.forma_blocco_reason_key, riga.forma_blocco_reason)`.

#### F5 · FE — il cestino col motivo e la riattivazione *(passi 5 e 6 del §5)*

* **FE-2**: cestino spento con `rimozione_blocco_reason_key`. ⚠️ I `reason` da
  saper tradurre sono **sei**; le chiavi ci sono già, **non se ne inventa una
  settima**;
* **FE-3**: quando la terna scelta ha già un registro **disattivato**, la
  maschera propone di **riattivarlo** invece di lasciar premere Salva.

⚠️ **Ordine dentro la fase, e non è indifferente** (§5, «una domanda di
priorità»): con sei guard, cinque sull'*esistenza*, il cestino è spento su
qualunque registro in servizio. F5 va **ultima**, e la riuscita del cantiere non
si misura su di lei.

### 10.4 I presidi

Sono quelli del §6, con l'aggiunta che il push di ieri rende possibile:

| # | Prova | Dove |
| --- | --- | --- |
| 1 | `23505` sulla terna occupata da uno **spento** → errore parlante, non `IntegrityError` nudo | test di servizio |
| 2 | ⛔ gemello positivo: sulla terna **libera** la create passa | test di servizio |
| 3 | `23505` sulla coppia prefisso/suffisso occupata da uno spento — ⛔ **in MODIFICA**, non solo in creazione | test di servizio |
| 4 | gemello positivo della 3 | test di servizio |
| 5 | `CHECK` famiglia: i campi del limite rifiutati su `DDT`, ammessi su `FATTURA` | test di servizio |
| 6 | **Scope**: un operatore non vede i registri di un altro emittente | test di servizio — ⚠️ senza RLS è l'**unico** presidio |
| 7 | 🔴 **`update` della forma su un registro che ha numerato** → il service propaga `E_REGISTRO_FORMA_NUMERO_IMMUTABILE`, non un 500 | test di servizio |
| 8 | gemello positivo della 7: **prima** di numerare l'`update` passa | test di servizio |

⛔ **Cosa NON si riscrive**: che i sei guard di disattivazione siano montati e
che il guard sulla forma rifiuti. Sono trigger, e il pgTAP li presidia già
(`test-registro-forma-numero-immutabile-v1.sql`, 8/8). Ricontarli in un test di
servizio significa metterli in un posto dove nessuno li guarda.

### 10.5 ⛔ Cosa questo piano NON fa

* **non tocca `config.sistema_codici`** — le quattro righe traslocate ne sono
  uscite di proposito;
* **non espone `serie_default`** né in whitelist né in maschera: residuo aperto;
* **non scrive endpoint sui progressivi**;
* **non deriva `can_remove` in Python**: arriva dalle due check;
* **non apre il cantiere della check generica** per le 100 tabelle: la decisione
  è presa ed è «no» (§FE-2), e chi legge non la riproponga.

### 10.6 ✅ Le tre risposte di Tid — 2026-09-01

| # | Domanda | Risposta |
| --- | --- | --- |
| 1 | BB del tab-lista, o si aspetta il quarto? | ⭐ **Si estrae il BB adesso**, e le liste su `DataTable` grezza ci **convergono** |
| 2 | `serie_default` fuori dalla maschera? | **No: almeno visualizzabile** — in sola lettura |
| 3 | Quanto del piano | ⭐ **Tutto**, F0→F5 |

#### ⚠️ Sulla 1 — «far convergere il tutto» non è una cosa sola, e va detto prima

Ho classificato i candidati **prima** di disegnare il BB, e non sono la stessa
famiglia. ⛔ Un BB che le tenesse tutte non unificherebbe una **lettura**:
trasporterebbe forme diverse dentro un contenitore unico, che è il difetto
opposto a quello che si vuole togliere.

| Componente | Forma reale | Converge? |
| --- | --- | --- |
| `EmittenteFiscaleBillingAccountTab` | lista **paginata** + kebab + motivo di blocco dal DB | ⭐ **è l'originale** — ci converge per prima, o restano due copie |
| **`EmittenteFiscaleRegistriTab`** (nuovo) | stessa forma | ✅ nasce già sul BB |
| `EmittenteFiscaleUtilitiesTab` | **matrice slot/override** con editing inline multi-riga, non paginata | 🟡 **famiglia diversa** — vedi sotto |
| `OperatorePermessiTab` | **tre** tabelle di spunte, stato locale, non paginate | 🟡 famiglia diversa |
| `PraticaFlussiTab` | due tabelle di sola lettura, non paginate | 🟡 famiglia diversa |

⭐ **Le tre 🟡 hanno in comune il difetto** (`DataTable` grezza, colonne cablate
nel template, niente catalogo `ui.lista_colonna`) **ma non la forma**: due sono
matrici a editing inline — il pattern `slot/override`, che è un pattern suo — e
una è una coppia di tabelle di lettura.

> 🔴 **CORREZIONE — l'analisi esisteva già, e dice di più** (rilievo di Tid,
> 2026-09-01). Il censimento e la classificazione stanno nel
> [piano di migrazione PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md) §Gruppo B, e
> la regola sta in [.codex/AGENTS.md](../../../../.codex/AGENTS.md) e in
> [frontend-standards §Regola zero della lista](../frontend/frontend-standards.md).
> Tutte e tre le 🟡 sono **già censite** lì (Gruppo B), quindi la tabella qui
> sopra non scopre niente: lo conferma.
>
> ⭐ **E il piano prescriveva esattamente questo lavoro.** Il testo del Gruppo B
> diceva due cose che qui si avverano insieme: che il gruppo mette insieme *«la
> tabella di righe di un documento»* e *«la lista su tab di un'entità che ha
> vita propria»* — e che la seconda **è una lista** — e che il suo equivalente
> è *«un wrapper sottile da estrarre alla seconda occorrenza»*. ⇒ La seconda
> occorrenza è `EmittenteFiscaleRegistriTab`, e il wrapper è il BB di F-BB.
>
> ⛔ **Ne discende un obbligo, non una scelta**: la nota del piano dice che se
> emerge un secondo caso si **riscrive il criterio del gruppo**, non si sposta
> una riga a mano. Fatto il 2026-09-01 — criterio in **tre domande** nel piano,
> regola estesa in AGENTS.md e in frontend-standards.
>
> 🔴 **E la riclassificazione fa vedere un buco che era coperto**: la **matrice
> slot/override** non rientra in nessuna delle due eccezioni ammesse dalla
> regola zero (righe di documento, anteprima in dialog). `…UtilitiesTab` e
> `OperatorePermessiTab` sono `DataTable` grezza **senza una motivazione
> ammessa**. Le due strade — estendere `<ListaConfigurabile>` con l'editing
> inline, o riconoscere la matrice come terza eccezione — sono una **decisione
> di Tid**, scritta nel piano. ⚠️ Non si chiude inventando un'eccezione.

⇒ **Come procedo**, e la differenza è dichiarata:

1. il BB nasce ora sulla famiglia che esiste davvero — **lista paginata di
   sotto-entità dentro un drawer, con il motivo di blocco dal database** — e ha
   subito **due** consumatori (BA e registri), non uno;
2. ⛔ `EmittenteFiscaleBillingAccountTab` **ci converge nello stesso giro**. Non
   è cortesia: un BB estratto e lasciato accanto alla sua copia è due
   implementazioni della stessa regola, e la copia diverge in silenzio;
3. le tre 🟡 restano **dichiarate**, con la loro condizione: convergono quando
   `<ListaConfigurabile>` sa fare l'editing inline. ⇒ È un cantiere suo, non una
   riga di questo — e non si chiude fingendo che lo sia.

#### La forma del BB

⛔ **Non un componente che si mangia il tab.** Tre pezzi, ognuno con un mestiere:

| Pezzo | Cosa fa | Perché separato |
| --- | --- | --- |
| `core/utils/bloccoMotivo.js` | `reason` + `reason_key` (+ `storia`) → **la frase** | è **lettura pura**: nessuno stato, testabile da sola |
| `core/composables/useDrawerTabLista.js` | **factory**: watch sul `parentId`, bind allo store, reset filtri, fetch, + `useListaConfigurabilePage` | ⛔ una **factory**, non un oggetto condiviso: due tab montati insieme devono avere due stati (`feedback_estrarre_non_condividere_stato`) |
| `core/components/DrawerTabLista.vue` | toolbar + `PageActionsBar` + `<ListaConfigurabile>` con gli slot passanti | è lo scheletro che oggi si ricopia a mano |

### 10.7 Le due decisioni che ricadono sul codice

* **`serie_default` — visualizzabile, non editabile** (risposta 2). Entra nella
  proiezione di `list`/`get` e nella maschera **in sola lettura**, con la sua
  spiegazione: *«la serie del contatore; cambiarla sposta il sezionale»*.
  ⛔ **Fuori dalla whitelist di `update`**: il guard del DB non la copre
  (§8.1 Q1), e un campo editabile senza presidio è peggio di un campo assente.
  ⚠️ E la spiegazione **non è decorativa**: è l'unica cosa che dice all'operatore
  perché quel campo si vede e non si tocca.
* **F0→F5 tutte** (risposta 3), più la fase **F-BB** qui sotto, che viene
  **prima** di F4 perché F4 ne è il primo consumatore.

#### F-BB · Il building block del tab-lista *(prima di F4)*

| Passo | Cosa |
| --- | --- |
| BB-1 | `bloccoMotivo.js` — estratto da `motivoBlocco()` di `…BillingAccountTab` |
| BB-2 | `useDrawerTabLista.js` — la factory |
| BB-3 | `DrawerTabLista.vue` — lo scheletro con gli slot |
| BB-4 | ⛔ **`EmittenteFiscaleBillingAccountTab` ci converge** — la copia sparisce |
| BB-5 | Riga nel [catalogo BB FE](../frontend/catalogo-building-block-frontend.md) e in [frontend-standards](../frontend/frontend-standards.md) |

⚠️ **BB-4 è il passo che prova il BB**, non BB-3: finché il secondo consumatore
non c'è, un BB è un'ipotesi. E il secondo consumatore qui è quello **storico**,
che è il verso giusto — si estrae da ciò che esiste, non si indovina ciò che
servirà.

### 10.8 ⚠️ Uno scostamento dal §FE-1, trovato scrivendo

Il §FE-1 dice *«un terzo tab, `EmittenteFiscaleRegistriTab`»*, e descrive
`EmittenteFiscaleBillingAccountTab` e `…UtilitiesTab` come **tab dentro il
drawer dell'emittente**. ⛔ **Non lo sono.** Sono due **drawer a sé**
(`…BillingAccountDrawer`, `…UtilitiesDrawer`) aperti dal kebab della riga nella
lista emittenti; i due `…Tab.vue` sono i loro contenuti, non tab di un
`TabPanel`.

⇒ Il terzo segue **quello che c'è**, non quello che il brief ricordava:
`EmittenteFiscaleRegistriDrawer` che wrappa `EmittenteFiscaleRegistriTab`, e una
terza voce nel kebab. Una forma diversa dai due fratelli sarebbe una terza
convenzione nella stessa schermata.

⭐ **E il tab riceve il SOGGETTO-RUOLO, non la PK.** I due fratelli passano
`itemId` (la PK dell'emittente fiscale) perché le loro tabelle si agganciano
lì; `registri_fatturazione` si aggancia a `emittente_soggetto_ruolo_id`, che la
lista emittenti porta già in riga. ⛔ Passare la PK non solleverebbe niente:
filtrerebbe su numeri che non corrispondono e la lista uscirebbe **vuota** —
cioè «questo emittente non ha registri», la risposta più rassicurante e più
falsa (`feedback_emittente_pk_vs_soggetto_ruolo`).

### 10.9 Stato — **F0→F5 CHIUSE** il 2026-09-01

| Fase | Esito | Cosa è entrato |
| --- | --- | --- |
| **F0** · chiave i18n | ✅ | `…forma_blocco.ha_numerato` in `it`+`en`; `check_i18n_keys.py` da **rosso a verde** |
| **F-BB** · il BB del tab-lista | ✅ | `core/utils/bloccoMotivo.js`, `core/composables/useDrawerTabLista.js`, `core/components/DrawerTabLista.vue` — e **`EmittenteFiscaleBillingAccountTab` convertito**, la copia non resta |
| **F1** · BE repo/service/rotte | ✅ | `registri_repository.py`, `registri_service.py`, `views_registri.py`, `urls_registri.py` montate su `/api/v1/vendite/registri/` |
| **F2** · progressivi in lettura | ✅ | `list_progressivi` nel dettaglio; **nessun** metodo di scrittura, presidiato da un test sulla superficie del repository |
| **F3** · configurazione lista | ✅ | `vendite.registri_numerazione` — definizione, **10 colonne**, preset, preset-colonne nei CSV di `80_data`; lista registrata in `WHITELIST_BE` del generatore |
| **F4** · drawer + forma del numero | ✅ | `RegistroNumerazioneDrawer` con **anteprima** (`ORD` + 7 cifre → `ORD0000001`) e forma in sola lettura **col motivo** |
| **F5** · cestino col motivo + riattivazione | ✅ | kebab con `rimozione_blocco_*`; **«Riattiva»** al posto della creazione su terna occupata; filtro stato con default «tutti» |
| **F6** 🔴 | aperta | le due **matrici slot/override** — decisione del [piano PrimeVue 5 §Gruppo B](../work-in-progress/piano-migrazione-primevue-5.md) |

**Presidi**: **24 test** in `apps/vendite/tests/services/test_registri_service.py`,
suite `apps.vendite` + `apps.core` **verde (2697)**. `check_i18n_keys` verde,
ESLint pulito, `vite build` verde, header di licenza su tutti i file nuovi.
⭐ Il contatore della regola zero **non è salito** (57 prima, 57 dopo): i
contatori nel drawer sono una tabella HTML, non una `DataTable`.

#### ⭐ Cosa è stato verificato sul database vivo, e non sui mock

* la query di lista con le **due `CROSS JOIN LATERAL`** gira su `dbdev`: 14
  registri, `dettaglio` decodificato a `dict`, e i due verbi **indipendenti**
  (`COM-159` libero su entrambi; `Back-office` bloccato su entrambi — da
  `HA_FATTURE` per lo spegnimento e da `HA_NUMERATO` per la forma, che è
  esattamente il caso che il §9.2 descrive);
* ⛔ **tutti e dodici i nomi di vincolo** delle mappe esistono davvero
  (`pg_constraint` + `pg_indexes`). È la verifica che un mock non può fare:
  `vincolo_violato` cerca il nome nel **testo** dell'eccezione, quindi un nome
  sbagliato non solleva nulla — cade nel fallback generico, cioè un messaggio
  plausibile su un difetto invisibile (`feedback_rinomina_db_binding_mockato`);
* il lookup generico **legge già** `vendite.famiglie_documento`: `dbops.fn_get_lookup_codici`
  deriva il `codice` da `codice_interno`, che qui è l'unica delle due colonne a
  esistere. ⇒ **whitelist, non un endpoint dedicato**
  (`feedback_lookup_whitelist_first`).

### 10.10 🔎 Revisione critica del 2026-09-01 — sette rilievi, tutti corretti

> Passata su codice **mio**, a lavoro finito, su richiesta di Tid. ⭐ Il dato che
> conta: **due difetti su sette rompevano davvero**, e nessuno dei due era
> visibile dai test — la suite era verde con entrambi dentro.

| # | Rilievo | Perché non falliva |
| --- | --- | --- |
| 🔴 **1** | `views_registri.post` normalizzava l'id dell'emittente con `qp_int_optional`, che è l'helper della **query string** e fa `raw.strip()` | Un id che arriva come **numero** dal corpo JSON — cioè sempre, dal frontend — sollevava `AttributeError` ⇒ **500 su ogni creazione**. ⚠️ Un test scritto con la stringa `"99"` sarebbe passato: è il motivo per cui il presidio ora usa un `int` |
| 🔴 **2** | `list_progressivi` selezionava `p.mese` | La colonna **non esiste più** sul database: il team DB l'ha tolta come il §8.1 Q1 annunciava, e **l'auto-gen non è stata rigenerata** — elenca ancora `mese`, il suo `CHECK` e la sua presenza in `uq_regprog_key`. ⇒ `ProgrammingError` alla prima apertura di un dettaglio. Un mock del cursore accetta qualunque SQL: si è visto solo chiamando il database vero |
| 🟠 **3** | `DrawerTabLista` calcolava gli slot da inoltrare con una `computed` | L'oggetto degli slot **non è reattivo**: la `computed` non aveva nessuna dipendenza tracciata ⇒ si calcolava una volta e non si aggiornava mai. Uno slot condizionato (`#actions` in sola lettura) sarebbe restato **congelato** al primo render. Ora è una funzione chiamata dal template |
| 🟠 **4** | `politica_data_documento` viaggiava nel payload **senza nessun campo a video** | È il **terzo** campo condizionato del §FE-4 (il `CHECK` verificato sul vivo dice `famiglia = FATTURA OR (limiti NULL AND politica = 'OGGI')`), e partiva sempre col valore cablato in `defaultForm()`. Ora ha il suo Select su FATTURA, e fuori da FATTURA **non parte** |
| 🟠 **5** | Nessun `maxlength` sui campi di testo | `prefisso` e `suffisso` sono `varchar(4)`, `codice` 16, `descrizione` 120 — lunghezze **non visibili nell'auto-gen**, che stampa «character varying» e basta. Un carattere in più non è un 400 parlante: è un `DataError`, che **non** è un `IntegrityError` e quindi non passa da `map_integrity_error`. Trovato provando |
| 🟡 **6** | Lo store chiamava `emittenteId` un campo che contiene un **soggetto-ruolo** | Non solleva niente: filtra su numeri che non corrispondono e la lista esce vuota. È la classe di difetto che il progetto ha già una memoria per nominare |
| 🟡 **7** | Fetch delle famiglie scritta a mano con `res.data.data?.results \|\| res.data.data \|\| []`, `set_attivo` con **due** letture complete, slot `cell-data_insert` che rifaceva (peggio) il formatter del catalogo, `'FATTURA'` e `1..18` cablati | Duplicazione e fragilità: ora `useLookup`, una lettura sola, nessuno slot, e i vocabolari **chiusi** (`CHECK` del DB) in `amministrazione/constants.js` con la loro fonte scritta accanto |

**Presidi aggiunti**: 6 test (30 in totale nel file), uno per rilievo bloccante,
ognuno col suo **gemello positivo** dove serviva.

⭐ **E la catena di scrittura è stata provata sul database vero**, in transazione
annullata: create → update della forma su un registro che non ha mai numerato
(passa) → `set_attivo` → e il **23505 vero** sulla coppia prefisso/suffisso, che
torna con `E_VENDITE_DUPLICATO` e il campo `prefisso` acceso. ⛔ Quest'ultima è
la verifica che i mock non possono dare: `vincolo_violato` cerca il nome nel
**testo** dell'eccezione di psycopg, e solo una violazione reale prova che il
formato di quel testo è quello che la mappa si aspetta.

### 10.11 📌 Al team DB — una doc auto-generata da rigenerare

⚠️ `docs/it/dbzero/vendite/tabelle/registri_fatturazione_progressivi.md` è
**disallineata dal database**: elenca la colonna `mese`, il `CHECK`
`chk_regprog_mese_valid` e `uq_regprog_key` come `(registro_id, anno, mese, serie)`.
Sul vivo la colonna non c'è e la chiave è `(registro_id, anno, serie)`.

⛔ **Non è un dettaglio di documentazione**: la regola di questo progetto è che
l'introspezione si fa dalla doc auto-generata, e questa ha fatto scrivere una
query che non compila. Il costo l'ha pagato chi ha letto la doc, non chi ha
fatto la DROP. Va rigenerata per quella tabella.

### 10.12 🔴 L'ottavo rilievo, trovato dal migrate — il seed della lista non entrava

Il migrate del 2026-09-01, dopo il merge, è morto sul mirror del catalogo
colonne (`20260507-07-seed-ui-lista-colonna-clienti`):

```
ERRORE: la sintassi per l'enumerazione ui.tipo_colonna non è valida: "numero"
```

Due delle dieci righe aggiunte per la lista 54 portavano valori che **non stanno
nei tre enum del catalogo**:

| id | colonna | scritto | ammesso |
| --- | --- | --- | --- |
| 626 | `lunghezza_numero` | `tipo_colonna = 'numero'`, `tipo_dato = 'integer'` | `informazione` / `numeric` |
| 628 | `attivo` | `tipo_colonna = 'stato'` | `informazione` |

⛔ **`tipo_colonna` non descrive il dato: descrive il COMPORTAMENTO della
colonna** — `identificatore` (sempre visibile, non nascondibile), `informazione`
(personalizzabile), `azione` (pulsanti UI, non esportabile). Il tipo del dato lo
dice `tipo_dato`, e lì `integer` non esiste: la mappa PG→`ui.tipo_dato` di
`scripts/gen_seed_lista.py` porta `integer`/`bigint`/`smallint` tutti su
`numeric`. Le due righe sono state scritte a mano; il generatore, che quei valori
li sa, non le avrebbe prodotte così.

⚠️ **Perché nessun presidio l'ha visto**, ed è la parte che vale per i prossimi:

* l'enum vive nel **database**, il seed è un **CSV**: fra i due non c'è nessun
  controllo che giri prima del migrate — il vincolo lo applica PostgreSQL al
  momento dell'`INSERT`, cioè in fondo;
* i test Django della fase mockano il cursore: nessuno di loro carica il CSV;
* e il difetto **non era isolabile a questo cantiere** — il mirror è
  `runOnChange` e rilegge **tutto** il file (§11.2 delle linee guida SQL), quindi
  due righe nuove hanno fermato il migrate di chiunque.

**Corretto il 2026-09-01** editando il CSV (`db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`, 2 righe, nessun `UPDATE` SQL: la sede del dato è il
CSV). L'export non cambia comportamento — `format_for_export`
(`apps/core/services/locale_formatters.py`) dispatcha su `tipo_dato`, e con `numeric` + `formato` vuoto
`lunghezza_numero` esce «3»; a video le due celle hanno comunque uno slot
proprio (`AttivoTag` e l'icona della forma bloccata), quindi il `formato` resta
vuoto come nelle altre `attivo` del catalogo.

🟠 **Resta aperto, e non è di questo cantiere**: un cancello statico che confronti
i CSV di `80_data` con i valori degli enum che le loro tabelle dichiarano. Oggi
`scripts/` ha quattro guardrail (migrate, `runOnChange`, preambolo pgTAP,
letterali SQL) e nessuno guarda dentro i CSV. Sarebbe l'unico modo di prendere
questa classe **prima** del migrate, invece che sulla macchina di chi migra.

#### 🔭 Cosa resta, e non è di questo cantiere

* il **residuo su `serie_default`** (§8.1 Q1): mostrata in sola lettura col suo
  perché, fuori dalla whitelist di `update`. Resta una decisione aperta;
* **F6**, le due matrici slot/override;
* ⚠️ **il collaudo in-app**: niente di questa fase è stato guardato a video.

---

## 11. ✅ Piano di sviluppo DB — il CRUD delle famiglie di documento

> ✅ **DB CHIUSO — applicato il 2026-09-01, pgTAP 21/21 come applicazione.**
> Dieci changeSet (`20260901-13` → `-22`), due codici errore, il catalogo della
> lista con la `vista_sql` dichiarata. Lo stato per esteso è al **§11.14**; ciò
> che resta è **tutto di BE e FE** ed è elencato al **§11.10**.
>
> Scritto il 2026-09-01, su richiesta di Tid, **dal lato DB**. Tutto ciò che
> segue è letto dagli oggetti vivi (`pg_constraint`, `pg_proc`, `pg_trigger`),
> non dagli YAML: le due tabelle sono state ristrutturate fra il 30-08 e oggi e
> più di un file di migrazione è già stantìo.
>
> ⛔ **Perimetro**: questo piano descrive **solo** il database. Ciò che ricade
> sul backend e sul frontend sta al §11.10, come richiesta scritta — non si
> tocca `backend/` da qui.

### 11.0 ⭐ Il modello, prima dei passi

Le due tabelle si sono divise il lavoro, e la divisione è già scritta nel
codice del provisioning:

| | `vendite.famiglie_documento` | `vendite.registri_fatturazione` |
| --- | --- | --- |
| che cos'è | il catalogo del **tipo di documento** | il **sezionale**, cioè la chiave del contatore |
| dove vive il documento | `schema_tabella`, `nome_tabella`, `colonna_numero`, `colonna_billing_account` | — |
| forma del numero | `prefisso_default`, `lunghezza_default` — **con che aspetto NASCE un registro** | `prefisso`, `suffisso`, `lunghezza_numero` — **l'effettivo**, cioè l'override |
| natura | `colonna_serie` (NULL = questa famiglia una serie non ce l'ha), `presidia_data_documento` | `serie_default`, `politica_data_documento`, i due limiti |

*«prefisso e lunghezza sono proprietà del TIPO DOCUMENTO, e `fd` È il tipo
documento. Il registro tiene l'EFFETTIVO»* — sta nel corpo di
`vendite.fn_provision_registri_emittente`, ed è la frase su cui poggia tutto
questo piano.

### 11.1 ⛔ Le quattro cose che oggi reggono perché NESSUNO può scrivere lì

Non sono difetti di oggi: sono le conseguenze di aprire una tabella che finora
solo un seed poteva toccare. Vanno chiuse **prima** che il CRUD esista, non
dopo.

| # | Cosa succede il giorno del CRUD | Dove sta oggi |
| --- | --- | --- |
| 1 | ⚠️ **Il migrate successivo riscrive quello che l'operatore ha appena salvato** sulle CINQUE righe di seed, senza dire niente: i due mirror sono `runOnChange` e rileggono il CSV intero. ⇒ D1: si accetta e si governa (§11.2), **non** si congela | `20260830-14` (possiede `descrizione`, `schema_tabella`, `nome_tabella`, `colonna_numero`, `colonna_billing_account`, `attivo`, `presidia_data_documento`, `meta`, audit) e `20260901-12` (possiede `colonna_serie`) |
| 2 | ⛔ **Spegnere una famiglia SPEGNE UN PRESIDIO**: `anagrafiche.fn_get_storia_emittente_ba` e la sua gemella `fn_ba_ha_storia_emittente` ciclano `WHERE fd.attivo`. Una famiglia spenta esce dal controllo sul cambio emittente del billing account — e quel controllo è la ragione per cui questa tabella esiste | `attivo` non ha nessun guard |
| 3 | ⛔ **La struttura di una famiglia in uso si può cambiare sotto i suoi registri.** Il caso peggiore è `colonna_serie` portata da `serie` a NULL: `script.fn_check_registro_serie_ammessa` cambia risposta, e i registri che una serie ce l'hanno restano con un secchio del contatore che il documento non sa più distinguere | nessun guard sulle sei colonne strutturali |
| 4 | ⚠️ **`codice_interno` si può rinominare.** ⭐ E il fatto verificato è che `vendite.famiglie_documento` è **l'unica** tabella del database con una colonna `codice_interno` e **senza** il trigger `script.trgfn_lock_columns` — tutte le altre ce l'hanno. Non è una scelta: è un provisioning che non è passato | `pg_trigger`: sulla tabella ci sono tre trigger (guard riferimenti, audit, tx_id), nessun lock |

⚠️ Sul punto 4 la FK `fk_registri_fatturazione_famiglia` (che punta a
`codice_interno`, **senza** `ON UPDATE CASCADE`) rifiuta la rinomina quando i
registri esistono — ma con un `23503` crudo, e **non protegge** una famiglia che
i registri non li ha ancora: lì la rinomina passa e rompe i seed e i chiamanti
che passano il letterale.

### 11.2 DB-0 · ❌ La sede del dato — NON si congela niente, ed è una decisione di classe

Oggi la sede è il CSV, e il mirror la difende rileggendola a ogni migrate
(§11.2 delle linee guida SQL). Un CRUD in-app crea la **seconda sorgente di
verità** che quella regola esiste per impedire.

La proposta era: mirror a `runOnChange: false`, il CSV declassato a seme
iniziale, la sede alla tabella.

> ❌ **RESPINTA da Tid il 2026-09-01 (D1), e la ragione è più grande di questa
> tabella**: *«abbiamo tantissime tabelle in questo stato, che dovranno essere
> spente nel momento in cui esisterà una produzione. Per ora lascia così: in
> futuro serviranno delle CI apposite per la produzione, dove le tabelle di
> `80_data` non girano più.»*

⭐ **Ed è la risposta giusta, non un rinvio**: congelare questo mirror sarebbe
stato risolvere **un caso** di una classe. La sede della soluzione non è il
singolo changeSet — è il **contesto** con cui si invoca Liquibase: una passata di
produzione che `80_data` non lo esegue affatto. Spegnere venti mirror a mano, uno
per volta, per poi introdurre comunque quel contesto, significa fare due volte un
lavoro che la seconda volta cancella la prima.

⚠️ E fino ad allora **non siamo in produzione**: una modifica che torna indietro
al prossimo migrate, su un database di sviluppo, costa un fastidio — non un dato
perso a un cliente.

#### ⇒ Cosa vuol dire, in concreto, per questo CRUD

⭐ **Il CRUD resta pienamente operativo in CREAZIONE.** I due loader sono
`loadUpdateData` con chiave `id` (il primo) e `codice_interno` (il secondo):
toccano **solo le righe che il CSV nomina**. Una famiglia nuova, creata
dall'applicazione, non è nominata da nessuno dei due — e nessun migrate la
sfiora. È il caso d'uso principale del CRUD, e funziona.

⚠️ **Sono volatili in sviluppo le modifiche alle CINQUE righe di seed**
(FATTURA, DDT, ORDINE, COMMESSA, RESO): descrizione, `attivo`,
`presidia_data_documento`, le quattro colonne strutturali e `colonna_serie`
tornano al valore del CSV al primo migrate. Se una di quelle modifiche deve
restare, si riporta nel CSV — che è la regola normale del progetto, non
un'eccezione.

#### ⛔ E la conseguenza che RICADE SUI PASSI 3 E 4 — questa non è opzionale

I mirror riscrivono quelle colonne **a ogni migrate**, con gli stessi identici
valori. E `UPDATE OF` scatta quando lo statement **nomina** la colonna, anche a
valore invariato.

⇒ **Ogni guard nuovo di DB-2 (§11.4) e DB-3 (§11.5) deve uscire subito sul
no-op**, confrontando `NEW` e `OLD` con `IS NOT DISTINCT FROM` prima di
qualunque verifica. Senza, il migrate fallisce **a ogni giro**, su un dato che
nessuno ha cambiato.

⭐ Il precedente è già in casa e dice esattamente questo, con le stesse parole:
`vendite.trgfn_registri_fatturazione_guard_serie_ammessa` — *«in UPDATE il no-op
passa: `UPDATE OF` scatta quando lo statement NOMINA la colonna, anche a valore
invariato — e il mirror CSV dei registri riscrive `serie_default` a OGNI migrate.
Senza questo confronto, ogni migrate fallirebbe.»*

⇒ **La decisione D1 non toglie un passo al piano: aggiunge un requisito a due.**

⭐ `prefisso_default` e `lunghezza_default` restano comunque **fuori da ogni
CSV** — li valorizza l'`UPDATE` di `20260831-51`, in `00_schema`. Su quelle due
colonne, cioè proprio sulla forma con cui nasce un registro, il CRUD scrive e
nessun mirror riscrive: sono durevoli anche sulle cinque famiglie di seed.

#### 🔭 Il debito, dichiarato come debito di classe

Le CI di produzione che non fanno girare `80_data` sono il cantiere che chiuderà
questo punto — per **tutte** le tabelle di configurazione con un mirror, non solo
per le famiglie. Fino ad allora la regola resta quella scritta: **la sede del
dato di configurazione è il CSV**, e ciò che il CRUD scrive sulle righe seminate
è una modifica di sviluppo.

### 11.3 DB-1 · Il guard dei riferimenti deve validare anche `colonna_serie`

`vendite.trgfn_famiglie_documento_guard_riferimenti` verifica che esistano la
tabella, la colonna del numero e quella del billing account. **Non guarda
`colonna_serie`**, che è arrivata dopo.

⚠️ E la doc manuale della tabella **afferma già** che il controllo c'è: *«col
nome, il controllo automatico verifica che la colonna esista davvero e che stia
nel vincolo di unicità del numero»*. Nel database quel controllo non esiste — il
solo presidio è un pgTAP (`db/pgtap/vendite/test-chiave-contatore-assi-dichiarati-v1.sql`),
che gira quando qualcuno lo lancia, non quando qualcuno salva una riga.

**Passo**: estendere il guard. Se `colonna_serie` è valorizzata su una famiglia
**attiva**:

1. la colonna esiste su `schema_tabella.nome_tabella`;
2. compare in un vincolo `UNIQUE` che contiene **anche** `colonna_numero` — cioè
   la regola generale *«tutto ciò che discrimina il contatore deve poter
   discriminare anche il documento»*.

Codice errore nuovo: `E_FAMIGLIA_DOCUMENTO_SERIE_NON_DISCRIMINA`, classe
`DATO_ERRATO` (lo compila una persona in un form), con `campo = 'colonna_serie'`.

⚠️ Il guard è già `BEFORE INSERT OR UPDATE`: non oscura nessun `CHECK`, perché
su queste colonne non ce n'è.

### 11.4 DB-2 · ✅ Non si spegne una famiglia che è ancora la regola di qualcuno

> ✅ **DECISO da Tid il 2026-09-01 (D2): no.** Si blocca, col motivo.

**Passo**, nella forma del §12.5 delle linee guida (la stessa dei registri, così
il rifiuto e il tooltip non possono divergere):

* `script.fn_check_famiglia_documento_disattivabile(p_id)` — pura, `STABLE`,
  ritorna `[]` oppure l'array ordinato di `{codice, reason, reason_key,
  dettaglio, valori}`. Motivi previsti, in quest'ordine:
  `HA_REGISTRI_ATTIVI`, poi `HA_DOCUMENTI_NUMERATI` (contati in SQL dinamico
  dalle **sue stesse** colonne: nessun elenco di tabelle scritto a mano);
* guard `trg_famiglie_documento_a10_guard_disattivazione_upd`,
  `BEFORE UPDATE OF attivo`, che la chiama e solleva il **primo** motivo.

⭐ La check serve due volte: al rifiuto e al cestino spento col motivo nella
maschera. È l'unica ragione per cui è una funzione e non un `IF` dentro il
trigger.

Codice errore nuovo: `E_FAMIGLIA_DOCUMENTO_IN_USO`.

### 11.5 DB-3 · La struttura di una famiglia in uso non si cambia

Le cinque colonne: `schema_tabella`, `nome_tabella`, `colonna_numero`,
`colonna_billing_account`, `colonna_serie`. (`codice_interno` **no**: lo presidia
il lock, vedi in fondo alla sezione.)

**Passo**: `script.fn_check_famiglia_documento_struttura_modificabile(p_id)` +
guard `_a10_` su `BEFORE UPDATE OF` quelle cinque colonne, stessa forma del §11.4.
Il predicato è *«esiste almeno un registro»* — non *«esiste un documento
numerato»*: un registro già nato porta i default di questa famiglia dentro di
sé, e cambiarli sotto è già una divergenza anche prima del primo numero.

Codice errore nuovo: `E_FAMIGLIA_DOCUMENTO_STRUTTURA_IMMUTABILE`.

✅ **DECISO da Tid il 2026-09-01 (D3): il LOCK automatico.** Si ripassa il
provisioning di `script.trgfn_lock_columns` su questa tabella, che la allinea
alle altre diciotto e la toglie dall'eccezione in cui si trova oggi da sola.

⛔ **Conseguenza operativa, e va rispettata**: `codice_interno` è fuori
dall'elenco del guard di struttura. Due presidi sulla stessa colonna con
due messaggi diversi sono esattamente ciò che non si fa — il lock parla per
`codice_interno`, il guard per le altre cinque.

### 11.6 DB-4 · Una famiglia nuova senza registri non produce nessun documento

`vendite.fn_provision_registri_emittente(bigint)` dà a **un emittente** i
registri di tutte le famiglie non fiscali che gli mancano, e lo fa da un trigger
su `anagrafiche.emittenti_fiscali`. La simmetrica — dare a **una famiglia** il
registro su tutti gli emittenti esistenti — **non esiste**. Senza, una famiglia
creata dal CRUD nasce senza registri e i suoi documenti non si numerano: lo dice
già la doc manuale (*«chi aggiunge una famiglia deve anche darle un registro per
emittente»*), e oggi quella frase non ha nessuno che la esegua.

**Passo**:

1. estrarre la **primitiva unica** con dentro la regola del codice
   (`left(codice_interno,3) || '-' || soggetto_ruolo_id`), la descrizione, e i
   default presi dalla famiglia;
2. due involucri sottili sopra: `fn_provision_registri_emittente(bigint)`
   — **firma invariata**, la chiama un trigger — e
   `vendite.fn_provision_registri_famiglia(varchar)` nuova.

⛔ Non una copia della `SELECT`: due porte che generano codici diversi per lo
stesso registro sono il difetto che si vede sei mesi dopo, su un solo emittente.

⚠️ Entrambe restano **idempotenti sulla coppia (emittente, famiglia)**: è già
così, e va conservato — un registro creato a mano con un altro codice vale lo
stesso e non ne fa nascere un secondo.

### 11.7 DB-5 · La madre della creazione — due scritture, una transazione

Creare la famiglia e provvisionarne i registri sono **due** scritture: §5b delle
linee guida vuole una funzione madre, non due chiamate in sequenza.

`vendite.fn_crea_famiglia_documento(...)` → `SECURITY INVOKER`, ritorna
`(id, n_registri_creati)`. Fa l'`INSERT` (lasciando ai trigger audit, `tx_id` e
i due guard il loro lavoro) e chiama il provisioning del §11.6.

⛔ **`update` e `set_attivo` NON hanno una madre**: sono scritture singole, e il
backend le fa come già fa sui registri — `UPDATE` diretto e traduzione dei
vincoli. Una madre dove non c'è niente da tenere insieme è solo un livello in
più.

### 11.8 DB-6 · La superficie di lettura che oggi non esiste

`dbops.fn_get_lookup_codici` ritorna `id, codice, codice_interno, descrizione,
attivo` e nient'altro: **non può** portare `prefisso_default`,
`lunghezza_default`, `colonna_serie`, `presidia_data_documento`. Non è un
difetto del lookup — è generico, e va lasciato generico.

**Passo**: `vendite.vw_famiglie_documento_lista`, con

* tutte le colonne di catalogo, **compresi i default della forma e le due
  colonne di natura**;
* `n_registri` e `n_registri_attivi`;
* i due blocchi capability (`reason`, `reason_key`, `dettaglio`) dalle check del
  §11.4 e del §11.5, nella stessa forma in cui il backend già legge quelle dei
  registri.

⭐ **Una vista sola serve TRE consumatori**: la lista del CRUD delle famiglie
(dove è anche la `vista_sql` dichiarata a catalogo, §11.9), il suo **export
CSV/XLSX** — che legge le stesse righe per le stesse chiavi — e il drawer dei
registri, che da lì prende i default con cui compilare il form di creazione e la
natura con cui decidere quali campi mostrare. È il pezzo che
toglie i letterali `'FATTURA'` da backend e frontend: `presidia_data_documento`
è la colonna che risponde a quella domanda.

### 11.9 DB-7 · La lista del CRUD è una lista STANDARD — e quasi tutto lo standard è catalogo

> ⭐ **Richiesta di Tid, 2026-09-01**: *«le liste del CRUD devono rispettare il
> formato liste che ci siamo dati — colonne parametrizzabili, estraibili
> CSV/XLS: lo standard delle liste»*.

La regola zero del frontend dice che una lista si monta con
`<ListaConfigurabile codice="...">`, e che **colonne, ordine, larghezze,
visibilità, personalizzazione, ritiro dinamico ed export «arrivano gratis»**.
⭐ «Gratis» vuol dire **una cosa sola**: che arrivano dal **catalogo**. Se il
catalogo è incompleto o sbagliato, non arriva niente — e non fallisce niente:
la lista si vede lo stesso, con le colonne storte e l'export che stampa `True`
al posto di `Sì`.

⇒ **La parte di questa richiesta che è lavoro DB è il seed del catalogo, ed è
quasi tutta la richiesta.** Il backend deve solo esporre l'endpoint di lista e
quello di export; il frontend consuma i building block che già esistono.

#### Cosa si semina (`80_data/sql/ui`)

| Tabella | Cosa |
| --- | --- |
| `ui.lista_definizione` | una riga: `codice = 'vendite.famiglie_documento'`, `schema_dati = 'vendite'`, `multi_emittente = f` (⛔ una famiglia non è di un emittente), **`vista_sql` VALORIZZATO** — vedi sotto |
| `ui.lista_colonna` | una riga per colonna, coi campi che governano **davvero** il comportamento (elenco sotto) |
| `ui.lista_preset` | il preset `sistema` «Vista standard famiglie di documento», `pagina_dimensione = 25` (il default dello standard), `ordinamento_default` su `codice_interno` |
| `ui.lista_preset_colonna` | una riga per colonna: ordine, `visibile`, `fissata` |

#### ⭐ `vista_sql` valorizzato — la differenza che vale il passo

Le ultime sei liste hanno `vista_sql` **NULL**, e su una lista senza vista il
trigger `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` **si ferma
subito**: nessuno verifica che i `campo_sorgente` del catalogo esistano davvero.
Il refuso non si vede finché una colonna non esce vuota a video.

Qui la vista c'è già — è `vendite.vw_famiglie_documento_lista` del §11.8 — quindi
la si dichiara, e da quel momento **ogni `campo_sorgente` è validato dal database
contro le colonne vere della proiezione**. È il presidio che rende la
parametrizzazione una promessa mantenuta invece di un elenco parallelo.

⚠️ **Il nome delle colonne della vista è il contratto**, e lo è per due
consumatori: `<ListaConfigurabile>` legge `data[campo_sorgente]`, e il renderer
di export fa lo stesso (`apps/ui/services/lista_export_service.py`: *«le chiavi
devono coincidere con `colonne[i].campo_sorgente`»*). Un rename di colonna nella
vista non è un dettaglio interno: rompe le celle e l'export insieme.

⚠️ **Ordine di esecuzione**: il seed di `80_data` gira **dopo** `20_code`, ma la
dipendenza va dichiarata lo stesso — `preConditions` con `viewExists` sulla vista.
Senza, su un database ricostruito da zero il guard rifiuterebbe le colonne una
per una e il messaggio parlerebbe di un `campo_sorgente` inesistente invece che
della vista mancante.

#### ⛔ I campi di `ui.lista_colonna` che NON sono decorazione

| Campo | Cosa governa davvero | Errore che non fallisce |
| --- | --- | --- |
| `tipo_dato` | ⭐ **l'export**: `format_for_export` dispatcha su questo, non sul tipo Python | `boolean` mancante ⇒ nel CSV esce `True`, non `Sì` |
| `formato` | il formatter di cella **e** dell'export (`date_short`, `datetime_short`, `yesno`, `number`…) | vuoto su una data ⇒ esce l'ISO grezzo |
| `esportabile` | il renderer **esclude** le colonne a `false` e tutte le `tipo_colonna='azione'` | una colonna che l'admin non voleva nel file ci finisce |
| `priorita` | ⭐ il **ritiro dinamico** delle colonne (`useResponsiveColumns`): su schermo stretto sparisce la priorità più bassa | tutte uguali ⇒ sparisce una colonna a caso |
| `gruppo` / `gruppo_ordine` | i gruppi della modale «Personalizza colonne» | tutto in un blocco solo, senza titoli |
| `ricercabile_full` | quali colonne entra nella ricerca libera | ⚠️ deve **coincidere** con la whitelist di ricerca del repository BE: sono due elenchi, e il catalogo è quello che l'operatore vede |
| `ordinabile` | l'intestazione cliccabile | ⚠️ idem: deve coincidere con la whitelist `ORDER BY` del BE, o si clicca e non succede niente |
| `sensibile` | ⛔ **è un cancello**: `true` ⇒ modello allowlist, e **senza grant la colonna è invisibile** | messo per prudenza ⇒ colonna che non si vede e nessun errore |
| `larghezza_default`, `allineamento` | layout | — |
| `etichetta_i18n_key` | l'etichetta tradotta; `etichetta` è il ripiego | chiave assente ⇒ si vede il ripiego italiano, non un errore |

⛔ E i valori degli enum si prendono **dal catalogo**: `tipo_colonna` è
`identificatore | informazione | azione` e descrive il **comportamento** (non il
tipo del dato!), `tipo_dato` è `string | numeric | date | datetime | boolean |
enum`. Due righe scritte a mano con `numero` e `integer` hanno appena fermato il
migrate di tutti — §10.12.

#### Le colonne previste

`codice_interno` (identificatore), `descrizione` (identificatore),
`schema_tabella`, `nome_tabella`, `colonna_numero`, `colonna_serie`,
`colonna_billing_account`, `presidia_data_documento` (boolean, `yesno`),
`prefisso_default`, `lunghezza_default` (**`numeric`**, allineata a destra),
`n_registri` e `n_registri_attivi` (numeric, dalla vista), `attivo` (boolean),
`data_insert` (datetime + `datetime_short`), più la colonna `azioni`
(`tipo_colonna='azione'`, `esportabile = f` — lo impone il `CHECK`
`chk_ui_lista_colonna_azione_non_esportabile`).

⭐ **Gruppi**: *Identificazione* (codice, descrizione), *Dove vive il documento*
(le quattro colonne strutturali), *Forma di nascita* (prefisso e lunghezza di
default), *Uso* (i due conteggi), *Stato*, *Audit*. Sono i gruppi della modale di
personalizzazione, e raccontano la tabella meglio di qualunque commento: sono le
tre nature del §11.0 messe in fila.

#### ⛔ Cosa NON entra nel catalogo, pur essendo nella vista

Le sei colonne di capability (`*_reason`, `*_reason_key`, `*_dettaglio` dei due
blocchi) **non sono dati della lista**: servono al tooltip del pulsante spento e
al motivo del campo bloccato. Restano nella vista e **fuori** da
`ui.lista_colonna` — altrimenti finiscono nella modale «Personalizza colonne» e,
peggio, nel file esportato.

### 11.10 📌 Cosa ricade su BE e FE (richiesta, non implementazione)

| # | Chi | Cosa |
| --- | --- | --- |
| BE-F1 | backend | leggere `vendite.vw_famiglie_documento_lista` al posto del lookup generico, sia per il CRUD famiglie sia per il drawer dei registri |
| BE-F2 | backend | ⛔ cancellare `_FAMIGLIA_FISCALE = "FATTURA"` da `registri_service.py` e derivare i tre campi condizionati da `presidia_data_documento` |
| BE-F3 | backend | mappare i tre codici errore nuovi (§11.3, §11.4, §11.5) — arrivano come `P0001`, non come violazione di vincolo: **non passano da `map_integrity_error`** |
| BE-F4 | backend | endpoint CRUD famiglie: la creazione chiama la **madre** `fn_crea_famiglia_documento`, non un `INSERT` diretto |
| BE-F5 | backend | ⭐ **il CRUD è per il solo amministratore** (D6, Tid 2026-09-01): il cancello sta sull'endpoint, non nel database. ⛔ Nessun oggetto DB per questo — `vendite.famiglie_documento` non ha RLS e non gliene si aggiunge una per un caso che un permesso risolve |
| BE-F8 | backend | tradurre il `23505` di `uq_famiglie_documento_tabella_attiva` (§11.15): il messaggio deve dire che **quella tabella ha già la sua famiglia**, e nominarla — un duplicato nudo manderebbe a cercare una riga che nella lista delle attive c'è eccome |
| BE-F6 | backend | l'endpoint di lista espone **ricerca, ordinamento e paginazione** con le solite whitelist — ⚠️ e le due whitelist (`ORDER BY`, ricerca) devono **coincidere** con `ordinabile` / `ricercabile_full` del catalogo: sono due elenchi paralleli e quello che l'operatore vede è il catalogo |
| BE-F7 | backend | export `?formato=csv\|xlsx` col renderer generico già in casa (`apps/ui/services/lista_export_service.py` + `apps/ui/api/export_helpers.py`): **non si scrive un export nuovo**, si passano righe + colonne del catalogo |
| FE-F1 | frontend | il drawer del registro, alla scelta della famiglia in **creazione**, precompila `prefisso` e `lunghezza_numero` dai default della famiglia — oggi nasce con `''` e `7` cablati, e una COMMESSA creata a mano nasce a 7 cifre mentre quella creata dal provisioning ne ha 9 |
| FE-F2 | frontend | ⛔ togliere `REGISTRO_FAMIGLIA_FISCALE` da `constants.js` (stessa ragione di BE-F2) e disabilitare la serie, col motivo, sulle famiglie che `colonna_serie` non ce l'hanno |
| FE-F3 | frontend | nel Select della famiglia in creazione, gli slot già occupati per quell'emittente non si offrono: `uq_registri_fatturazione_famiglia_emittente_utility` ne ammette **uno solo** e non filtra su `attivo` (§FE-3, «Nuovo deve inciampare prima») |
| FE-F4 | frontend | chiavi i18n `vendite.famiglie_documento.col_*` per la lista del §11.9 |
| FE-F5 | frontend | i tre campi fiscali **non si mostrano** su una famiglia che non li ammette — compresa ogni famiglia creata dal CRUD (§11.11) |
| FE-F6 | frontend | la lista si monta con `<ListaConfigurabile codice="vendite.famiglie_documento">` via `useListaConfigurabilePage` (che porta con sé «Personalizza colonne» e «Esporta» da `useListaAzioni` + `ExportDialog`). ⛔ Nessuna `DataTable` grezza: è la regola zero |

### 11.11 ⛔ Il debito che questo piano NON salda, ed è dichiarato

Il `CHECK chk_registri_fatturazione_famiglia_regole_fattura` cabla `'FATTURA'`, e
**un `CHECK` non può leggere un'altra tabella**: quella è una costrizione, non
una svista. Accanto, `vendite.fn_get_pavimento_data_documento` **deriva** il
pavimento di sequenza da `presidia_data_documento` ma cabla `'FATTURA'` per il
limite di emissione, e `vendite.fn_get_registro_documento` rifiuta `'FATTURA'`
perché quella famiglia si risolve per (tipo documento, natura).

⇒ **Una famiglia creata dal CRUD nasce necessariamente «non fiscale»**: politica
data `OGGI`, nessun limite di emissione, registro sullo slot (famiglia,
emittente, utility). È un limite del **modello**, non della maschera, e va detto
nel form — non scoperto da un `23514` su un campo che l'operatore ha compilato.

✅ **DECISO da Tid il 2026-09-01 (D5): no, e resta così.** Il `CHECK` non si
tocca e la famiglia nuova nasce non fiscale.

⛔ **La via d'uscita è quindi CHIUSA, non rimandata** — e va scritto perché, o
qualcuno la riaprirà pensando che nessuno ci avesse pensato: sostituire il
`CHECK` con un guard che legge `presidia_data_documento` costa più di quello che
rende. Un guard `BEFORE ROW` montato anche in `INSERT` **oscura** il `CHECK` e
porta lo SQLSTATE da `23514` a `P0001`: cambia il canale su cui il backend
riconosce quel vincolo **per nome**, e il messaggio parlante che il §BE-2 ha
costruito smetterebbe di uscire — in silenzio, su un form che continua a
funzionare.

⇒ **Ricade sul frontend**, e sta nel §11.10 come FE-F5: i tre campi fiscali si
mostrano solo sulla famiglia che li ammette, e su una famiglia nuova non si
mostrano affatto. Non è una limitazione da spiegare in un tooltip: è un campo
che non c'è.

### 11.12 I passi, in ordine

| # | Passo | Cartella | Dipende da |
| --- | --- | --- | --- |
| ~~0~~ | ~~Congelamento dei due mirror~~ — ❌ **non si fa** (D1): è un debito di **classe**, lo chiuderà la CI di produzione che non esegue `80_data` | — | ❌ D1 |
| 1 | Lock su `codice_interno` (provisioning `trgfn_lock_columns`) | `20_code` / registry | ✅ D3 |
| 2 | Guard riferimenti esteso a `colonna_serie` | `20_code/vendite` | — |
| 3 | `fn_check_famiglia_documento_disattivabile` + guard **con uscita sul no-op** (§11.2) | `20_code/script` + `20_code/vendite` | ✅ D2 |
| 4 | `fn_check_famiglia_documento_struttura_modificabile` + guard (**cinque** colonne, non `codice_interno`) **con uscita sul no-op** (§11.2) | idem | 1 |
| 5 | Primitiva unica di provisioning + `fn_provision_registri_famiglia` | `20_code/vendite` | — |
| 6 | Madre `fn_crea_famiglia_documento` | `20_code/vendite` | 5 |
| 7 | Vista `vw_famiglie_documento_lista` | `20_code/vendite` | 3, 4 |
| 8 | Tre codici errore nuovi — **append ai CSV**, mai un loader nuovo | `80_data/sql/config` | 2, 3, 4 |
| 9 | Seed del catalogo lista — definizione (**con `vista_sql`**), colonne, preset, preset_colonna | `80_data/sql/ui` | 7 |
| 10 | pgTAP: un file per guard, col gemello positivo | `db/pgtap/vendite` | 2→7 |
| 11 | Doc manuale delle due tabelle + questo brief | `docs/it/dbzero/vendite/manual` | tutti |

⚠️ `%TYPE` **ovunque** — firma, `DECLARE`, `RETURNS TABLE`, `COMMENT` — come già
fanno le due check dei registri. E un parametro in più su una funzione esistente
è un **overload**, non una modifica: il passo 5 tiene la firma di
`fn_provision_registri_emittente(bigint)` invariata proprio per questo.

### 11.13 ✅ Le sei decisioni di Tid — 2026-09-01

> Le domande restano scritte: una decisione senza la domanda che l'ha originata
> è un'affermazione che il prossimo lettore non sa valutare.

| # | Domanda | Risposta | Dove ricade |
| --- | --- | --- | --- |
| **D1** | La sede del dato diventa la tabella (mirror CSV congelati), o il CRUD resta ai soli campi che il CSV non possiede? | ❌ **Non si congela niente.** Il CSV è fedele (verificato: le cinque righe coincidono col database), ma **tantissime tabelle sono in questo stato**: la sede della soluzione non è il singolo mirror, è una **CI di produzione che non esegue `80_data`**, il giorno che una produzione esisterà | §11.2 — e ⛔ i guard dei passi 3 e 4 devono uscire sul **no-op** |
| **D2** | Si può spegnere una famiglia che ha ancora documenti numerati? | **No.** Si blocca, col motivo | §11.4, passo 3 |
| **D3** | `codice_interno`: lock automatico o guard dedicato? | **Lock automatico** — come le altre diciotto tabelle | §11.5, passo 1 |
| **D4** | Il CRUD ha il `DELETE` o solo `attivo = false`? | **Solo spegnimento** | §11.7 |
| **D5** | Una famiglia nuova può presidiare la data documento come la fattura? | **No** — il `CHECK` non si tocca, e il limite si dichiara nella maschera | §11.11, FE-F5 |
| **D6** | Il CRUD sta sotto un permesso suo? | **Solo amministratore** | BE-F5, nessun oggetto DB |

⭐ **Cosa cade fuori dal piano grazie a D4**: nessun verbo di cancellazione
significa **nessuna primitiva di pulizia e nessuna figlia da scoprire da
`pg_constraint`**. Una famiglia non si cancella perché la sua riga è la traccia
di documenti che esistono ancora — ed è la stessa ragione per cui D2 dice no.
Le due risposte sono la stessa risposta, data due volte.

### 11.14 ✅ Stato — **APPLICATO** il 2026-09-01, suite verde

> ✅ **APPLICATO da Tid il 2026-09-01**, e la suite gira ora **come
> applicazione**: `test-famiglie-documento-crud-v1` **21/21**, e i sei pgTAP
> vicini (chiave contatore, guard riferimenti, storia emittente BA, identità
> documenti, motore trasloco, prefisso registro, scope ricerca) tutti PASS.
>
> Prima del migrate i changeSet erano stati provati eseguendo l'**SQL estratto
> dagli YAML** dentro transazioni che si annullano — non una riscrittura a mano,
> che salterebbe proprio i `COMMENT` e i `GRANT`.
>
> ⇒ **Lato DB questo cantiere è chiuso.** Quello che resta è al §11.10, ed è
> tutto di BE e FE.

#### La verifica post-apply, letta dagli oggetti vivi

`databasechangelog`: i **dieci** changeSet `EXECUTED` (`20260901-13` → `-22`).
⭐ Il `-22` è passato **prima** del `-21` ed è giusto così: `00_schema` viene
prima di `90_end` nel master, e la numerazione dice *quando è stato scritto*, non
in che ordine si applica. I due mirror del catalogo liste risultano `RERAN`,
come devono.

| Cosa | Come si presenta ora |
| --- | --- |
| trigger su `famiglie_documento` | sei: `a10_guard_chiave_struttura_upd`, `a10_guard_disattivazione_upd`, `a10_guard_riferimenti_ins_upd`, **`a10_lock_columns_upd`** (quello che mancava), audit, tx_id |
| funzioni nuove | `fn_check_famiglia_documento_disattivabile`, `fn_check_famiglia_documento_struttura_modificabile`, `fn_provision_registri`, `fn_provision_registri_famiglia`, `fn_crea_famiglia_documento` |
| vista | `vw_famiglie_documento_lista` con `security_invoker=on` — ⚠️ l'opzione **c'è**, e va riverificata a ogni `CREATE OR REPLACE` futuro |
| vincolo | `uq_famiglie_documento_tabella_attiva` |
| codici errore | i due nuovi a catalogo (1041, 1042) |
| catalogo lista | **lista 55, 15 colonne, `vista_sql = vw_famiglie_documento_lista`** — cioè ogni `campo_sorgente` ora è validato dal database |

⛔ **`vendite.famiglie_documento` non è più l'unica tabella con `codice_interno`
senza lock**: era il rilievo del §11.1/4, ed è chiuso.

| # | Passo | File | Stato |
| --- | --- | --- | --- |
| ~~0~~ | Congelamento mirror | — | ❌ non si fa (D1) |
| 1 | Lock su `codice_interno` | `90_end/20260901-21-provision-lock-famiglie-documento` | ✅ |
| 2 | Guard riferimenti + `colonna_serie` | `20_code/vendite/20260901-13-update-trgfn-famiglie-guard-riferimenti-serie` | ✅ |
| 3 | Check + guard disattivazione | `20_code/script/20260901-14`, `20_code/vendite/20260901-15` | ✅ |
| 4 | Check + guard struttura | `20_code/script/20260901-16`, `20_code/vendite/20260901-17` | ✅ |
| 5 | Primitiva + provisioning per famiglia | `20_code/vendite/20260901-18-refactor-provision-registri-primitiva` | ✅ |
| 6 | Madre `fn_crea_famiglia_documento` | `20_code/vendite/20260901-19` | ✅ |
| 7 | Vista `vw_famiglie_documento_lista` | `20_code/vendite/20260901-20` | ✅ |
| 8 | Due codici errore | append a `codici_errore.csv` + `messaggi_errore.csv` (id 1041-1042) | ✅ |
| 9 | Catalogo lista (definizione **con `vista_sql`**, 15 colonne, preset) | append ai quattro CSV di `80_data/sql/ui` | ✅ |
| 10 | pgTAP | `db/pgtap/vendite/test-famiglie-documento-crud-v1.sql` — **21/21** | ✅ |
| 11 | Doc manuale della tabella + questo brief | `dbzero/vendite/manual/famiglie_documento.md` | ✅ |
| 12 | **Una tabella, una famiglia** — UNIQUE parziale (deciso dopo il piano) | `00_schema/vendite/20260901-22-unique-famiglie-documento-tabella` | ✅ |

⭐ **Come sono stati provati** — e conta, perché una prova sbagliata è peggio di
nessuna prova:

* l'SQL è stato **estratto dai `changes[].sql.sql`** e eseguito intero, con
  `ON_ERROR_STOP=1`, dentro `BEGIN … ROLLBACK`;
* ogni guard ha il suo **gemello positivo**: senza, un guard che rifiuta sempre
  passa i test negativi esattamente come quello giusto;
* il **no-op dei due mirror** è provato per primo su ogni guard nuovo — è la
  condizione posta dalla decisione D1;
* il seed del catalogo lista è stato caricato **attraverso i suoi guard veri**
  (B1 sulla vista, B2 su ogni `campo_sorgente`): 15 colonne accettate;
* ⚠️ il primo giro di pgTAP era stato eseguito **prima del migrate**, da owner e
  con gli oggetti anteposti al file: una verifica delle asserzioni, non della
  corsa reale. ⭐ **E la corsa reale ha trovato un difetto che quella non
  poteva trovare** — vedi il quinto rilievo qui sotto.

#### 🔴 Quattro difetti trovati PROVANDO, che leggendo non si vedevano

| # | Cosa | Perché non si vedeva |
| --- | --- | --- |
| 1 | `trg_famiglie_documento_a10_guard_riferimenti_ins_upd` **non nominava `colonna_serie`** nella lista `UPDATE OF` | Aggiornare la sola funzione avrebbe prodotto un guard che valida una colonna su cui non viene **mai** chiamato: verde in ogni prova che passi dalle altre colonne, muto proprio sul caso per cui è stato scritto. ⚠️ E il mirror `20260901-12` scrive **esattamente e solo** quella colonna |
| 2 | L'**ordine alfabetico** dei BEFORE ROW: `guard_riferimenti` parlava prima di `guard_struttura` | Cambiando `nome_tabella` su una famiglia con registri usciva *«vendite.resi non ha la colonna serie»* — vero, e non il punto: quella colonna non si cambia affatto. L'operatore avrebbe corretto il riferimento per sbattere un attimo dopo contro il muro vero. ⇒ il trigger si chiama `..._a10_guard_**chiave**_struttura_upd`: `c` < `r`. **Prima l'immutabilità, poi la validità del valore nuovo** |
| 3 | Il predicato «la serie sta nel vincolo di unicità» scritto **per attnum** avrebbe **rifiutato la FATTURA** | `uq_fatture_numero` porta la serie come `COALESCE(serie, '')`, cioè un'**espressione**, che in `pg_index.indkey` ha attnum 0. La versione «precisa» sembra migliore ed è sbagliata: il primo migrate sarebbe fallito sul mirror delle famiglie. ⇒ predicato **testuale**, lo stesso del test 5 del pgTAP già in casa |
| 4 | `script.fn_log_and_raise_error` chiamata con **cinque** argomenti non risolve la firma variadica | Rispondeva *«la funzione non esiste»* — un errore TECNICO al posto di quello di dominio, cioè il guard che si autoannulla. Serve `VARIADIC ARRAY[]::text[]` anche quando il messaggio non ha segnaposti |

⭐ I primi due appartengono alla stessa specie: **un presidio che c'è e non viene
chiamato**, oppure che viene chiamato dopo un altro che dice una cosa diversa. È
la classe di difetto che nessun test scritto sulla funzione trova, perché la
funzione è giusta — è il *montaggio* a essere sbagliato.

#### 🔴 E un quinto, trovato dal migrate vero — nel TEST, non nel codice

Lanciato come applicazione dopo l'apply, il **test 19 è fallito**: `have 1, want
0`. Il colpevole era la colonna `azioni`.

⚠️ **Il commento della DDL di `ui.lista_colonna` promette una cosa che il loader
non produce**: dice *«`campo_sorgente` NULL per `tipo_colonna = azione`»*, ma il
`loadUpdateData` scrive la **stringa vuota**. Verificato sul vivo: le colonne con
`campo_sorgente IS NULL` in tutto il database sono **zero**, e tutte e 31 le
colonne `azione` hanno `''`.

⇒ Il test, scritto sulla promessa (`campo_sorgente IS NOT NULL`), andava a
cercare una colonna chiamata `azioni` dentro la vista. **Il seed era giusto: era
il test a chiedere la cosa sbagliata.**

⭐ Corretto scrivendo il predicato **come lo scrive il guard** —
`ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` esclude le colonne
`azione` e quelle senza sorgente — invece che come lo racconta la
documentazione. È la stessa lezione del rilievo 3, dall'altro lato: *due
predicati sulla stessa invariante, prima o poi, dissentono*.

⚠️ E la lezione sul metodo: il giro pre-apply, da owner e con gli oggetti
anteposti, **non poteva** trovarlo — lì le righe del catalogo le avevo inserite
io con `NULL`, perché stavo riproducendo il `nullValue` del loader invece di
lasciarlo scrivere davvero. Una fixture che *simula* il caricamento prova la
simulazione.

#### ✅ La domanda emersa scrivendo — DECISA il 2026-09-01

⚠️ **Niente vieta due famiglie sulla stessa tabella.** Oggi non capita (le
cinque sono una per tabella), ma il CRUD è la prima cosa che lo rende possibile,
e il modello lo ammette: non c'è nessun `UNIQUE (schema_tabella, nome_tabella)`.

Cosa succederebbe: il presidio sul cambio emittente del BA conta **per tabella**
e itera **per famiglia**, quindi gli stessi documenti verrebbero contati due
volte e il messaggio all'operatore li elencherebbe sotto due nomi diversi. Non
rompe il presidio — la domanda è «ce n'è almeno uno?» — ma racconta una cosa
falsa a chi legge.

⇒ La domanda era di modello: **una famiglia è il tipo di documento**, o può
esistere più di un modo di chiamare lo stesso documento?

> ✅ **Risposta di Tid**: *«una tabella una famiglia, altrimenti si creerebbe un
> bel casino: un `ddt_reso` fa parte dello stesso insieme `ddt`.»*

⇒ Il vincolo è scritto, ed è il §11.15.

### 11.15 ✅ Una tabella, una famiglia — il vincolo che chiude la domanda

> ✅ **Deciso da Tid il 2026-09-01**: *«una tabella una famiglia, altrimenti si
> creerebbe un bel casino: un `ddt_reso` fa parte dello stesso insieme `ddt`.»*

⭐ **La famiglia non è un modo di chiamare i documenti: È il tipo di documento**,
e il tipo di documento è la tabella in cui vive. Due righe che nominano la stessa
tabella sono due nomi per la stessa cosa.

`00_schema/vendite/20260901-22-unique-famiglie-documento-tabella`:

```sql
CREATE UNIQUE INDEX uq_famiglie_documento_tabella_attiva
    ON vendite.famiglie_documento (schema_tabella, nome_tabella)
 WHERE attivo;
```

#### ⭐ Perché è PARZIALE, e perché è l'opposto dei registri

Un `UNIQUE` pieno sarebbe stato un **cancello su uno stato persistente**: una
famiglia ritirata resta scritta per sempre (D4: si spegne, non si cancella),
quindi terrebbe la sua tabella occupata **per sempre**, e l'unica via d'uscita —
il `DELETE` — è proprio quella che abbiamo deciso di non offrire.

E il perimetro *attivo* non è una concessione: è **esattamente quello che i
presidi leggono**. `anagrafiche.fn_ba_ha_storia_emittente` e la sua gemella
iterano `WHERE fd.attivo`, quindi una famiglia spenta non è nel conteggio e non
è nel problema che il vincolo esiste per impedire.

⚠️ **È il contrario di ciò che vale sui registri**, dove `attivo = false` **non**
libera lo slot. Non è un'incoerenza, sono due cose diverse:

| | lo slot è… | una riga spenta… |
| --- | --- | --- |
| `registri_fatturazione` | la **chiave del contatore** | possiede ancora i numeri che ha consegnato ⇒ **tiene** lo slot |
| `famiglie_documento` | un'**identità di catalogo** che solo le righe accese fanno valere | non è letta da nessun presidio ⇒ **libera** lo slot |

⛔ Chi legge non deve dedurre l'una dall'altra: è scritto nel `COMMENT`
dell'indice, dove lo trova chi guarda l'oggetto e non il brief.

#### Cosa cambia per chi sbaglia

Violarlo produce un `23505` col nome dell'indice — nessun codice nuovo a
catalogo, ma una riga nella mappa dei vincoli del backend (**BE-F8**). ⚠️ E il
messaggio deve **nominare la famiglia che c'è già**: un «duplicato» nudo
manderebbe a cercare una riga che nella lista delle attive si vede eccome.

⭐ Due pgTAP in più (20 e 21), e il secondo è quello che spiega il predicato: la
gemella **ritirata** sulla stessa tabella passa. Senza, un domani qualcuno
«semplificherebbe» il vincolo in uno pieno senza accorgersi di aver chiuso la
porta a chiave.

---

## 12. 🔴 La revisione BE/FE del 2026-09-02 — tre rilievi, tre decisioni

> Tre righe arrivate da `dev/backend-tid` a lavoro applicato. Le decisioni sono
> di Tid, stessa giornata.

### 12.1 ⭐ La lista famiglie sbarrava la strada al super admin — e la strada breve era una bugia

**Il rilievo:** la lista `vendite.famiglie_documento` è inutilizzabile. Una
famiglia è globale, non appartiene a nessun emittente, e il pannello chiede
comunque di sceglierne uno prima di entrare — proprio al super admin, che per la
decisione D6 è l'unico che può aprirla.

**La correzione proposta:** `multi_emittente` da `f` a `t` sulla riga 55. Un
carattere.

> ⛔ **E qui la richiesta si ferma, perché quel flag non significa «la lista è
> usabile».** Significa *«so dire da quale emittente arriva ogni riga»*, e su un
> catalogo globale è **falso**: non c'è nessun emittente da dire.
>
> Metterlo a `t` avrebbe fatto comparire una riga in
> `dbops.vw_liste_multi_emittente_non_certificate` — la vista che pretende che
> chi dichiara `true` **esponga l'emittente nella riga** — e **due pgTAP** la
> vogliono a zero righe (`test-lista-definizione-multi-emittente-v1` §6,
> `test-viste-dash-emittente-v1` §11). La suite sarebbe diventata rossa, e la
> reazione ovvia sarebbe stata allargare i due presidi con un'eccezione per la
> lista 55: cioè spegnerli un pezzo alla volta.

✅ **Deciso da Tid (2026-09-02): il terzo stato.**

`ui.lista_definizione.perimetro_emittente BOOLEAN NOT NULL DEFAULT TRUE`
(`20260902-01`), dichiarata `false` per la sola lista famiglie (`20260902-02`) ed
esposta dal risolutore (`20260902-03`).

⭐ **Due domande indipendenti, due colonne:**

| Colonna | Domanda | Natura |
| --- | --- | --- |
| `perimetro_emittente` | le righe di questa lista appartengono a un emittente? | **natura del dato** |
| `multi_emittente` | se ci appartengono, la lista sa dire a quale? | **capacità conquistata**, e certificata |

⇒ La regola per chi legge: **si entra senza scegliere un emittente quando la
lista SA DIRLO, oppure quando non c'è niente da dire.** Due ragioni diverse per
lo stesso gesto, e vanno tenute distinte.

⛔ Un enum a tre valori le avrebbe legate: è il flag che risponde a due domande
in AND, e che poi non si riesce più a invertire.

⭐ **Default `true`**, cioè il verso prudente: il comportamento delle altre 58
liste non cambia di una virgola, e la globalità si **dichiara** invece di
ereditarla. Un `CHECK` rende impossibile la combinazione incoerente — «non ho
emittenti, e so dirti quale sono».

⚠️ **Una riga sola nel seed, ed è una scelta.** Nella stessa condizione ci sono
anche `ui.lista_definizione`, `ui.lista_colonna` e `ui.lista_colonna_permesso`
(56, 57, 59): cataloghi tecnici, nessuna riga che appartenga a un emittente.
Non sono state dichiarate perché nessuno ha ancora detto di sbatterci contro, e
una riga di seed che nessuno ha chiesto è una decisione presa di nascosto —
basterà una riga per ognuna.
⛔ `ui.lista_preset` (58) **non** è fra queste, ed è il caso interessante: un
preset **può** appartenere a un emittente (`ambito = emittente_fiscale`), quindi
quella lista un perimetro ce l'ha. Per lei la strada è l'altra — esporre
l'emittente nella riga e certificarsi `multi_emittente`.

### 12.2 ✅ La famiglia dice se ammette le regole fiscali (scelta B)

✅ **Deciso da Tid: opzione B — colonna, seed, pgTAP, e il BE/FE cambiano la
derivazione.**

`vendite.famiglie_documento.ammette_regole_fiscali BOOLEAN NOT NULL DEFAULT
FALSE` (`20260902-04`), `true` sulla sola FATTURA (`20260902-05`), esposta dalla
vista di lettura (`20260902-06`).

⇒ Spariscono i **due letterali** `'FATTURA'` scritti a mano fuori dal database:
`_FAMIGLIA_FISCALE` in `registri_service.py` e `REGISTRO_FAMIGLIA_FISCALE` in
`constants.js`.

⛔ **Il `CHECK` che accompagna la colonna non è un dettaglio: è ciò che la rende
vera.** `chk_registri_fatturazione_famiglia_regole_fattura` continua a nominare
`'FATTURA'` e non si tocca (decisione D5). Una colonna **libera** accanto a quel
`CHECK` sarebbe la dichiarazione parallela classica: qualcuno la mette a `true`
su una famiglia nuova, la maschera offre i tre campi, e il database li rifiuta al
salvataggio — una promessa rotta a valle, addosso a chi compila.
⇒ Il `CHECK` la lega allo stesso letterale: **il posto in cui si decide cosa è
fiscale resta uno**, e la colonna lo *dichiara* invece di duplicarlo. Il giorno
in cui la fattura smetterà di essere l'unica, i due `CHECK` si cambiano insieme —
e il **test 23** del pgTAP verifica che concordino.

⛔ **Perché non si riusa `presidia_data_documento`**, che oggi ha lo stesso
valore su tutte e cinque: risponde a un'**altra** domanda — «questa famiglia ha
un pavimento sulla data del documento?» — usata da
`fn_get_pavimento_data_documento` per il pavimento di **sequenza**, mentre il
limite di emissione, nella stessa funzione, è gated dal letterale. ⚠️ Due domande
diverse con la stessa risposta di oggi restano due domande: unirle è il flag
composto che poi non si riesce più a invertire.

### 12.3 ✅ `serie_default` resta in sola lettura

✅ **Deciso da Tid: nessun cambiamento.** Il campo si vede e non si tocca, ed è
coerente con quello che il database presidia: il guard sulla forma del numero non
lo copre, e il mirror CSV lo riscrive a ogni migrate.
⇒ Nessun lavoro DB, e nessun debito nuovo: la situazione di oggi era già quella
voluta.

### 12.4 📌 Cosa ricade su BE e FE

| # | Chi | Cosa |
| --- | --- | --- |
| BE-F9 | backend | la configurazione risolta porta **`perimetro_emittente`**: si entra senza scegliere l'emittente quando `multi_emittente` **oppure** `NOT perimetro_emittente` |
| FE-F7 | frontend | stessa regola sul lato che disegna la schermata — ⚠️ **due ragioni diverse per lo stesso gesto**, e il codice deve mostrarlo (non una sola condizione che le confonde) |
| BE-F2 · FE-F2 | entrambi | ⭐ ora si possono chiudere: `ammette_regole_fiscali` arriva dalla vista, e i due letterali `'FATTURA'` si cancellano |

### 12.5 ✅ Stato

| Passo | File | Stato |
| --- | --- | --- |
| Colonna `perimetro_emittente` + `CHECK` | `00_schema/ui/20260902-01` | ✅ scritto |
| Seed (lista famiglie) | `80_data/.../20260902-02` + CSV dedicato | ✅ scritto |
| Risolutore | `20_code/ui/20260902-03` | ✅ scritto |
| Colonna `ammette_regole_fiscali` + `CHECK` | `00_schema/vendite/20260902-04` | ✅ scritto |
| Seed (FATTURA) | `80_data/.../20260902-05` + CSV dedicato | ✅ scritto |
| Vista di lettura | `20_code/vendite/20260902-06` | ✅ scritto |
| pgTAP | `ui/test-lista-definizione-perimetro-emittente-v1` **6/6** · `vendite/test-famiglie-documento-crud-v1` **24/24** | ✅ verde |

✅ **APPLICATO da Tid il 2026-09-02**, e i due pgTAP girano **come
applicazione**: **7/7** e **24/24**.

#### 🔴 E il migrate vero ha trovato un difetto nel test, di nuovo

Il test sulla combinazione incoerente chiedeva un `23514` — il `CHECK` — e come
applicazione è arrivato un **`P0001`**: davanti a `multi_emittente` ci sono
**due muri**, e l'applicazione incontra il primo.

| Muro | Chi è | Chi lo incontra |
| --- | --- | --- |
| 1° | il guard `trg_ui_lista_definizione_a10_guard_multi_emittente_ins_upd` — *«quel flag non si scrive dall'applicazione, si dichiara nel seed»* | l'applicazione, **sempre** |
| 2° | il `CHECK` di coerenza | chi il guard lo attraversa: l'owner, cioè il migrate |

⚠️ **Girando da owner il primo muro non c'è** (`pg_has_role` fa uscire subito il
guard), quindi il giro pre-apply vedeva parlare il `CHECK` e il test chiedeva il
suo codice. In esercizio quel test sarebbe stato **rosso su un database sano**.

⇒ Il test è stato **separato in due**: il 4 prova che dall'applicazione quel
flag non si scrive affatto, il 5 prova che il `CHECK` esiste — sulla
**struttura**, perché per vederlo agire servirebbe una veste che quel file non
deve avere.

⭐ È il gemello esatto del rilievo di ieri sul `campo_sorgente`: **un presidio
che passa solo nella veste sbagliata non presidia**. Ieri la fixture simulava il
loader, oggi il test girava da owner — due modi di provare qualcosa che in
esercizio non succede.

⚠️ **Un dettaglio trovato provando**: la vista non si aggiorna con un
`CREATE OR REPLACE`. La colonna nuova entra **in mezzo**, accanto alle altre due
che dicono la natura della famiglia, e `CREATE OR REPLACE VIEW` sa solo
**appendere in coda**: rinominare o spostare una colonna lo fa fallire («non è
possibile cambiare nome della colonna di vista `prefisso_default` in
`ammette_regole_fiscali`»). Il changeSet fa `DROP` e ricrea — **senza `CASCADE`**,
di proposito: se un domani qualcosa dipendesse da quella vista, il `DROP` deve
fallire invece di portarselo via. Verificato: nessun dipendente.

### 12.6 ✅ La commessa porta gli assi del contatore nelle sue colonne

**Il rilievo:** `vendite.commesse` è l'unica delle cinque famiglie la cui
identità è una **stringa nuda** — `UNIQUE (codice)` e basta, mentre le altre
quattro hanno `registro_id` e `anno` come colonne.

⭐ **Non è che il codice sia sbagliato.** Dal 2026-08-31 è
`CMM-<sigla>-<anno>-<9 cifre>` e gli assi li porta **dentro**, come la funzione
dichiara: *«ogni dimensione del contatore dev'essere nella stringa, o al primo
cambio di periodo la UNIQUE salta»*. Prima era `CMM-<timestamp>-<md5 random>` —
un'unicità **probabilistica** sotto un vincolo deterministico — e quel pezzo era
già stato sistemato.

⛔ **Il debito è che l'invariante regge per CONVENZIONE di chi compone la
stringa**, e nessun vincolo la impone. Il giorno che al contatore si aggiungesse
un asse senza toccare la composizione, la `UNIQUE` salterebbe al primo cambio di
periodo — come `23505` nudo in mezzo a un fan-out. E gli assi non erano
interrogabili: «le commesse del registro X nel 2026» richiedeva di **parsare**
una stringa.

#### ⭐ Servivano DUE colonne, non tre — e nessun numero da inventare

Sulle quattro sorelle `numero` è la **stringa composta** (`DDT0023454`), non il
progressivo nudo: verificato sui dati, non dedotto. Sulla commessa quella
stringa è `codice`, che già c'è.

⇒ Mancavano solo `registro_id` e `anno`. **La domanda «che numero diamo alle
righe vecchie?» non si pone**: non c'è nessun numero da assegnare, e quindi
nessun valore alto da inventare per tenerle fuori dai piedi.

#### ⭐ Il backfill non ricostruisce niente a mano — e per poco non sbagliava

`registro_id` si **chiede** a `vendite.fn_lookup_registro_documento`, la sede
unica della regola «quale registro per questo documento»: la mia utility,
altrimenti quello valido per tutte.

⚠️ **Riscrivere quel predicato a mano avrebbe risolto ZERO righe su 62**: le
commesse hanno un'utility valorizzata mentre i loro registri valgono «per
tutte», e un join ingenuo su `utility_id` non trova niente. Provato prima di
scrivere il changeSet — ed è la ragione per cui il backfill chiama la funzione
invece di copiarne la logica.

`anno` viene da `data_insert`, perché la commessa non ha una data documento: la
sua data è quella di creazione, e lo dichiara già la madre.
⇒ **62 righe su 62 risolte**, tutte 2026.

#### ⛔ Colonne NULLABLE, e non è una resa

Le sorelle le hanno nullable perché un documento può esistere prima di essere
numerato. La commessa nasce numerata, quindi il `NOT NULL` sarebbe tentante —
⚠️ ma **una decina di file pgTAP inserisce in `vendite.commesse` direttamente**,
senza passare dalla madre: li farebbe rossi tutti insieme, e in cambio non
aggiungerebbe una garanzia che il modello non abbia già (`codice` è `NOT NULL` e
`UNIQUE`, ed è l'identità).

⇒ A presidiare l'invariante è un pgTAP che **ora si può scrivere**, proprio
perché gli assi sono diventati colonne: `test-commessa-chiave-numerazione-v1`,
**6/6**, e il test che conta è il 3 — *il codice porta la sigla e l'anno che le
colonne dichiarano*.

#### Stato

| Passo | File | Stato |
| --- | --- | --- |
| Colonne + FK + indice + backfill | `00_schema/vendite/20260902-07` | ✅ scritto |
| La madre le scrive | `20_code/vendite/20260902-08` | ✅ scritto |
| pgTAP | `vendite/test-commessa-chiave-numerazione-v1` — **6/6** | ✅ verde |

⛔ Non applicato. ⚠️ E l'indice **non è unico** di proposito: l'unicità ce l'ha
già il codice, e in forma più stretta delle sorelle — porta la sigla
dell'emittente, quindi non collide fra registri diversi.


---

## 13. ✅ Sviluppo BE/FE — **fatto** il 2026-09-01 · 02

> ✅ **Backend e frontend chiusi** per tutto ciò che il §11.10 e il §12.4
> elencavano, **suite verde**.
>
> ⚠️ **Il collaudo in-app è arrivato dopo**, ed è al §13.7: cinque rilievi, tutti
> difetti che nessuna delle prove scritte aveva preso. È l'unica cosa che quelle
> prove non sostituiscono.

### 13.1 ⭐ Il cancello di perimetro e l'emittente esplicito

Non era nel piano: è nato dal presidio. Registrando la lista dei registri in
`_LISTE` è andato rosso `test_ogni_lista_configurabile_ha_il_suo_cancello`, e
guardando perché si è scoperto che **il cancello era acceso davvero**: la lista
54 ha `multi_emittente = f`, quindi un operatore con più emittenti nello scope
prendeva **422 aprendo il tab Registri dell'emittente che aveva già davanti**.

✅ **Deciso da Tid (2026-09-01): estendere il cancello**, non esentare la lista.

| Pezzo | Dove |
| --- | --- |
| `PARAM_EMITTENTE_ESPLICITO` + `emittente_esplicito_da_query()` — un valore solo, numerico | `core/services/perimetro_emittente.py` |
| `richiede_scelta_emittente()` — **la conclusione, in una sede sola** | idem |
| `lista_emittente_param`, attributo dichiarativo (solo query string) | `core/api/base_views.py` |
| Il parametro sull'endpoint di config, con nome **neutro** | `ui/api/views.py` · `ui/services/ui_service.py` |
| Il valore che viaggia dal tab fino alla richiesta di config | `ui-api.js` → `useListaConfig` → `ListaConfigurabile` → `DrawerTabLista` |

⭐ **La formula era scritta due volte** — nel cancello dell'endpoint e
nell'envelope della config — e stava per crescere di un termine su un lato solo:
è stata estratta in `richiede_scelta_emittente()`, con una cache condivisa
perché lo scope resti **una query sola**. Un test verifica che le due chiamate
ricevano lo **stesso** dizionario di cache: senza, la de-duplicazione si sarebbe
pagata al doppio del prezzo.

⛔ **Perché la query string e non il payload**: sulle scritture l'emittente è già
verificato dalla view che lo riceve, e leggere il corpo dentro `initial()`
significherebbe consumarlo prima del `post`.
⛔ **Perché un valore solo**: `?e=1&e=2` è *esattamente* l'ambiguità che il
cancello rifiuta, e leggerne uno — come farebbe un `.get()` distratto — la
trasformerebbe in un lasciapassare.

### 13.2 Il CRUD delle famiglie — le otto voci BE

| # | Fatto |
| --- | --- |
| BE-F1 | `famiglie_repository.py` legge `vw_famiglie_documento_lista` con **`SELECT v.*`**: la lista dichiara `vista_sql`, quindi il trigger DB valida il catalogo contro la vista — elencare le colonne anche qui sarebbe stata una **terza copia** che nessun presidio guarda. Più `GET /vendite/famiglie/lookup/` per il drawer dei registri |
| BE-F2 | derivazione da `ammette_regole_fiscali` (§12.2), i due letterali `'FATTURA'` cancellati |
| BE-F3 | i tre codici dei guard **non** passano da `map_integrity_error` — arrivano come `P0001` e risalgono al middleware. Un test lo inchioda |
| BE-F4 | la creazione chiama la madre `fn_crea_famiglia_documento` e riporta `registri_creati` |
| BE-F5 | CRUD su `AdminAPIView`, **lookup no** — provato in entrambi i versi |
| BE-F6 | le due whitelist coincidono col catalogo, e a tenerle allineate è `test_liste_configurabili_seed`: la lista 55 è entrata in `_LISTE`, quindi lo verifica il presidio |
| BE-F7 | export col renderer generico, zero righe di render nuove |
| BE-F8 | il `23505` di `uq_famiglie_documento_tabella_attiva` **nomina l'occupante**: *«La tabella vendite.fatture ha già la sua famiglia: "Fatture" (FATTURA)»* |
| BE-F9 | `fetch_flag_perimetro` legge le **due** colonne insieme e le restituisce nominate; la conclusione ha **tre rami separati** (§12.1) |

⛔ **Gli argomenti della madre viaggiano per NOME** (`p_colonna_serie => %s`), non
per posizione: con undici `%s` la corrispondenza sarebbe vissuta in una tupla
Python, e il giorno che la firma cambia ordine `colonna_serie` avrebbe ricevuto
il valore di `colonna_billing_account` — sono tutti `text`, quindi la famiglia
sarebbe nata **sbagliata senza che niente fallisse**.

⛔ **`presidia_data_documento` fuori dall'update, e `codice_interno` pure**: la
prima perché una famiglia creata dal CRUD nasce non fiscale (D5), il secondo
perché lo presidia il lock automatico (D3). Le **quattro colonne strutturali**
invece ci sono, ed è la stessa logica dei tre campi di forma dei registri:
esiste il guard che le rifiuta, quindi tenerle fuori sarebbe un divieto
applicativo accanto a uno di database.

### 13.3 La schermata, e le quattro voci FE sul drawer dei registri

✅ **Dove vive: Amministrazione**, voce di menu accanto a Emittenti Fiscali
(decisione di Tid, 2026-09-02). ⛔ **Non** come tab dentro i registri: quelli
stanno nel drawer di UN emittente, e una famiglia è globale — la stessa riga
sarebbe comparsa modificabile aprendo un emittente qualunque, e sarebbe sembrata
sua.

| # | Fatto |
| --- | --- |
| FE-F1 | alla scelta della famiglia in creazione, `prefisso` e `lunghezza_numero` si precompilano dai suoi default — il difetto per cui una COMMESSA creata a mano usciva a **7 cifre** e quella del provisioning a **9** |
| FE-F2 | `REGISTRO_FAMIGLIA_FISCALE` cancellato da `constants.js`; la serie dice **il perché** sulle famiglie che non la registrano, con la stessa frase che manda il database |
| FE-F3 | le famiglie con lo **slot già preso** non si offrono. ⚠️ Il controllo legge i registri dell'emittente con `limit: 500`, **non la pagina della lista**: a 25 righe per pagina uno slot occupato in seconda pagina sarebbe risultato libero |
| FE-F5 | i tre campi fiscali seguono `ammette_regole_fiscali` |
| FE-F4 · F6 | 17 chiavi i18n (14 intestazioni + 3 `reason_key`) e la lista con `<ListaConfigurabile>` via `useListaConfigurabilePage` |
| FE-F7 | il frontend legge **la conclusione sola**: ricalcolarla sarebbe la seconda sede della stessa verità. Le tre ragioni si vedono dove la decisione si prende |

⭐ **La regola del precompilamento è una sola per i due campi**: si aggiorna ciò
che porta ancora il default della famiglia *precedente*, mai ciò che ha scritto
l'operatore. La prima stesura ne aveva due — il prefisso rispettato, le cifre
sovrascritte sempre — e due regole diverse sullo stesso gesto sono un difetto
quale che sia quella giusta.

### 13.4 I quattro codici errore che il backend non sapeva tradurre

`error_policies_generated.py` rigenerato (**831 → 835**, il diff è esattamente i
quattro codici nuovi) più i quattro **ripieghi senza segnaposto**. Due erano di
questo cantiere (`E_FAMIGLIA_DOCUMENTO_*`), due venivano dal precedente
(`E_REGISTRO_FORMA_NUMERO_IMMUTABILE`, `E_REGISTRO_SERIE_NON_AMMESSA`) e
rendevano rossa la suite da giorni.

⚠️ Prima di rigenerare: catalogo vivo e CSV in git confrontati — **835 = 835,
zero divergenze**. Non eravamo nel caso «database avanti rispetto al repo», in
cui rigenerare è vietato.

### 13.5 🔴 Cinque difetti trovati costruendo, che leggendo non si vedevano

| | Cosa | Come si vedeva |
| --- | --- | --- |
| 1 | `<DrawerTabLista>` era **invisibile** al censimento del frontend, che cercava solo `<ListaConfigurabile`: la lista dei registri era fuori da `_LISTE`, cioè da **tutti** i presidi di quel modulo | niente. Il test era verde |
| 2 | `test_perimetro_emittente_copertura` scartava i `lista_codice` non letterali: diceva «registri non ha nessun cancello» mentre il cancello c'era, dichiarato via costante | un rosso su una cosa giusta — il modo più rapido di far spegnere un test |
| 3 | 🔴 **La riattivazione era spenta su entrambe le liste**: `RowActionsMenu` disabilita da sé le azioni sulle righe inattive, e senza `allowWhenInactive` l'azione «Riattiva» era disabilitata **proprio sulle righe spente**. Era così anche nel codice dei registri già rilasciato — e riattivare è la strada che il §0 impone quando la terna è occupata | un pulsante grigio con un tooltip plausibile e falso |
| 4 | `ApiAuditLog` (`core/api/views_tracciamento.py`) dichiara `lista_codice = "storico.audit_log"` ma serve `dbops.audit_log`, le **esecuzioni di funzione**: zero colonne in comune col catalogo di quella lista. La lista che il frontend monta chiama `/amm-software/audit-log/` | ✅ **corretto il 2026-09-02** (ok di Tid): il `lista_codice` è stato tolto da lì — quell'endpoint non alimenta nessuna lista — e l'esenzione scritta dove è vera, sulla schermata `AdminAPIView` che la monta davvero. ⚠️ E non era solo un'etichetta: `lista_codice` accende il **cancello**, che leggeva i flag di perimetro di una lista non sua e avrebbe risposto **422** su un endpoint dove l'emittente non c'entra. Dormiente solo perché nessuna schermata lo chiama |
| 5 | La lista 55 sbarrava la strada al super admin, e la correzione ovvia era una bugia | → §12.1, ed è diventato il terzo stato |

### 13.6 Stato, e cosa resta

| Cosa | Stato |
| --- | --- |
| Suite backend | **4371 test**, 2 rossi non di questo cantiere (sotto) |
| Guard i18n · liste · licenza | ✅ puliti |
| Frontend | `npm run build` ✅, lint invariato (3 errori preesistenti, file non toccati) |
| Prova sul database vero | lista, lookup, dettaglio, **28 ordinamenti**, creazione dalla madre (2 registri provveduti), update, spegnimento, e i tre rifiuti col messaggio giusto |
| Prova del cancello | famiglie **si apre** · registri **resta chiusa** · registri + emittente esplicito **si apre** |

✅ **E il presidio sui `campo_sorgente` copre ora 43 liste**: alle 39 senza vista
si sono aggiunte le quattro `ui.*` seminate il 2026-09-02, registrate il giorno
stesso. ⭐ Non ordinano lato backend (`:paginata="false"`), e il test degli
ordinamenti le tiene in un ramo suo — «non ha whitelist» e «non ordina lato
backend» sono due cose diverse, e confonderle farebbe sembrare debito una scelta.

🔭 **Resta il solo collaudo in-app** (§13.7, in corso).
✅ `commesse` non è più scoperta: il team DB le ha dato il suo `registro_id`,
nella stessa forma delle altre quattro famiglie (2026-09-02).

### 13.7 🔴 Il collaudo in-app — primi rilievi di Tid, 2026-09-02

| | Rilievo | Cosa era |
| --- | --- | --- |
| 1 | 🔴 La colonna **Attivo** diceva «non attivo» su ogni riga | Il prop di `AttivoTag` si chiama **`active`**, non `attivo`: col nome sbagliato Vue non solleva niente, il prop resta al suo default `false` e la colonna mente su **tutte** le righe. ⚠️ Lo stesso identico difetto era sulla lista dei **registri**, rilasciata il 2026-09-01 — le uniche due occorrenze in tutto il frontend, le altre diciotto passano `:active` |
| 2 | «Registri 2 (2 attivi)» sembra riferito a un emittente | È su **tutti**: la schermata è globale, ma chi ci arriva dal mondo dei registri — che vivono nel drawer di UN emittente — legge il numero con quella lente. Ora l'etichetta lo dice (*«Registri, su tutti gli emittenti»*), e l'aiuto sotto spiega che è anche il predicato che rende immutabili le colonne di struttura. Le due intestazioni di colonna diventano «Registri a sistema» / «Attivi a sistema» |
| 3 | La frase sulla forma nominava il «provisioning» | Riscritta senza il termine tecnico: *«quello che crei a mano e quello che il sistema crea da sé devono avere la stessa forma del numero»* |
| 4 | Sui registri il filtro stato **partiva vuoto** pur valendo «tutti» | Il valore di partenza è `null`, e per PrimeVue `null` è «niente selezionato»: la combo esce vuota su un filtro che è attivo e vale *tutti*. Il `placeholder` porta ora l'etichetta del default, così lo stato di partenza e quello scelto a mano si leggono uguali — che è la verità: sono lo stesso stato. Corretto sui registri e sulle due combo delle famiglie |

✅ **E il 4 è stato chiuso come FORMA, non come caso** (ok di Tid, 2026-09-02).
La stessa sagoma — un `<Select>` con un'opzione `value: null` («tutti») e nessun
placeholder — viveva in altri **cinque** punti: `FondiFatturaDaDecidereTab`,
`CommessaGestioneDrawer` (due), `SituazioneApertaView`, `DashboardBacklogView`.
Corretti tutti; una ri-scansione del frontend dice **zero residui**.

⭐ **E la regola non è stata inventata: era già nei file stessi.** In
`SituazioneApertaView` il filtro *fase* il placeholder ce l'ha e quello *ritardo*
no; in `DashboardBacklogView` idem con *area* e *ritardo*. Stesso file, stessa
mano, stesso schema — uno dimenticato. La correzione rende ogni file coerente
con sé stesso, e per questo non porta commenti nuovi in casa d'altri.

⛔ **E anche la lista EMITTENTI FISCALI era sbagliata, in un modo più
insidioso**: il placeholder c'era, ma portava l'etichetta del CAMPO («Stato»)
invece di quella del DEFAULT («Tutti»). Non sembrava un difetto — sembrava una
scelta — e diceva all'operatore il nome del filtro proprio nel punto in cui
doveva dirgli il suo valore.

| 5 | L'azione «Registri di numerazione» sul kebab dell'emittente portava la **matita** | La matita dice «modifica questa riga», e quell'azione apre invece i *sezionali* di quell'emittente — un elenco, non un form (`feedback_row_actions_menu`). Ora è **`pi-hashtag`**, il segno del numero, in `MANAGE_ICONS` — nel blocco delle icone di **dominio**, non fra le trasversali: nomina un'entità, non un'azione — e dichiarata nel catalogo BB. La portano anche i due drawer che si aprono: chi ha cliccato deve ritrovare il segno su cui ha cliccato, come fa già il mapping BA con la sua carta di credito. ⭐ Il drawer della famiglia prende invece il `pi-file` della sua voce di menu, per la stessa ragione |

⭐ **Il rilievo 1 è la terza volta in due giorni** che un nome sbagliato passa in
silenzio nel frontend: prima lo slot `#actions`, poi `allowWhenInactive`
mancante, ora un prop. ⛔ Nessuno dei tre dà un errore, tutti e tre producono
una schermata **plausibile e falsa** — ed è la ragione per cui il collaudo in-app
non è sostituibile da nessuna delle prove scritte.
