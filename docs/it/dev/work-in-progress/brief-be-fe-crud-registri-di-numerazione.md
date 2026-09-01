# Brief BE/FE — il CRUD dei registri di numerazione

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
