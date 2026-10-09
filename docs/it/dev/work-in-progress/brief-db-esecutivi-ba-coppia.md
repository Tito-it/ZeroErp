# Brief DB — Ordine, DDT e reso: il cliente come su preventivo, offerta e contratto

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09; **rivisto dal team DB** lo stesso giorno
> (§2, §3, §4 e §5 riscritti sul contratto letto dalla doc auto-generata). **A chi:** team DB; poi
> BE/FE (§7).
> **Origine:** §7.5 di [brief-db-istanza-nasce-col-ba.md](brief-db-istanza-nasce-col-ba.md). Il suo R-2
> ha reso `billing_account_id` NOT NULL e legato alla coppia (istanza, utility) su preventivo,
> offerta e contratto. Chiudendo il lato BE/FE e' emerso che i documenti **esecutivi** di vendita
> (ordine, DDT, reso) sono rimasti fuori: e' la stessa asimmetria, un livello piu' in basso.
> **Stato:** 📝 **decisioni chiuse** — tutte e otto decise da Tid il 2026-10-09 (§4; D-7 con
> l'istruttoria del §4.1). Tocca al team DB: forma (§5) e righe fuori regola (§6).
> **Nel registro dei difetti DB:** voce **D21** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La regola

Un documento di vendita parla di **un cliente a grana fine**, cioe' di un billing account: la
fornitura (istanza, utility) di un ruolo CLIENTE. Su preventivo, offerta e contratto e' un vincolo
dal 2026-10-08; sulla fattura `billing_account_id` e' NOT NULL da prima. Ordine, DDT e reso stanno
in mezzo alla stessa catena — il preventivo diventa ordine, l'ordine diventa DDT, il DDT diventa
fattura o reso — e oggi sono gli unici anelli in cui il cliente puo' mancare, non coincidere con le
altre colonne della testata, o **non coincidere con quello dell'anello precedente**.

⭐ Il principio e' quello gia' scritto: *vendite = acquisti, e le asimmetrie si chiudono subito*.
Qui l'asimmetria e' **dentro** vendite, fra famiglie di documento e lungo la catena.

## 2. Che cosa dice oggi il DB (contratto, letto dalla doc auto-generata)

| | `billing_account_id` | `utility_id` | ruolo di testata | lock del BA | guard emittente ↔ BA |
| --- | --- | --- | --- | --- | --- |
| `preventivi`, `offerte_commerciali`, `contratti` | **NOT NULL** + FK composta verso la coppia | NOT NULL, nella FK composta | — (dal BA) | — | si' |
| `fatture` | **NOT NULL** | nullable | — | — | — |
| `ordini` | **nullable**, FK semplice | nullable, FK semplice | `soggetto_ruolo_id` NOT NULL | si' (`trgfn_lock_columns`, `E_ORD_CLIENTE_IMMUTABILE`) | si', **salta se il BA e' NULL** |
| `ddt` | **nullable**, FK semplice | nullable, FK semplice | `destinatario_soggetto_ruolo_id` NOT NULL | **no** | si', salta se il BA e' NULL |
| `resi` | **nullable**, FK semplice | nullable, FK semplice | `destinatario_soggetto_ruolo_id` NOT NULL | **no** | si', salta se il BA e' NULL |

Ordine, DDT e reso **non hanno** la colonna `istanza_utility_id`: la coppia si legge dal BA
(`ba.istanza_utility_id`, `ba.utility_id`), ed e' giusto cosi'. Il punto e' che sulla testata
restano **due copie** di cio' che il BA gia' dice, e nessun vincolo le lega a lui:

* `utility_id` della testata contro `ba.utility_id`;
* il ruolo di testata (`soggetto_ruolo_id` dell'ordine, `destinatario_soggetto_ruolo_id` di DDT e
  reso) contro `ba.soggetto_ruolo_id`. Chi crea l'ordine dal preventivo
  (`vendite.fn_push_preventivo_a_ordine`) lo prende **dal BA**: la regola c'e', ma la scrive il
  verbo, non la tabella. Una scrittura diretta non la vede.

### 2.1 Come si ereditano, anello per anello

* **Ordine → DDT.** `vendite.fn_genera_ddt_da_ordine` scrive `destinatario_soggetto_ruolo_id` =
  `ordini.soggetto_ruolo_id`; `vendite.trgfn_ddt_normalize` (solo su INSERT, con `COALESCE`) mette
  il BA **dell'ordine** e la utility **del BA** (`ba.utility_id`, non la copia dell'ordine). Sul
  percorso del verbo le copie nascono coerenti; ma un valore esplicito diverso passa, perche' il
  `COALESCE` tiene quello del chiamante. Un DDT **standalone** non eredita niente.
* **DDT → reso.** Il reso **non e' mai standalone**: `resi.sorgente_tipo_id` e' NOT NULL, e
  `vendite.trgfn_resi_normalize` eredita dal DDT BA, utility **e destinatario** (stesso `COALESCE`).
  `vendite.trgfn_resi_guard_ddt_consegnato` vieta il reso da un DDT di trasferimento (`TRASF_OUT`);
  non lo vieta da un conto visione, una riparazione o un conto lavoro.
* **Riga d'ordine → riga di DDT.** `vendite.trgfn_ordini_ful_guard_consistenza` su
  `ordini_righe_fulfillment` controlla articolo, UoM e quantita': **non il cliente**.

### 2.2 La causale del DDT ha una sua fase

`ddt.causale_trasporto_id` e' NULL ammesso in bozza, obbligatoria all'emissione
(`script.fn_check_ddt_emittibile`, motivo `E_DDT_CAUSALE_OBBLIGATORIA`, sede unica di guard e
capability) e immutabile fuori bozza (`vendite.trgfn_ddt_guard_causale_immutabile`). Il seed
`config.causali_trasporto` (contratto, `80_data`) ha **una sola** causale `fatturabile`, `VENDITA`;
`OMAGGIO` e `CAMPIONATURA` non si fatturano ma scaricano merce con `SCARICO_VEN`; `TRASFERIMENTO`
muove con `TRASF_OUT`; `CONTO_VISIONE`, `RESO`, `RIPARAZIONE`, `CONTO_LAVORO` non hanno causale di
magazzino.

## 3. Perche' e' un difetto, sul modello

* **Un ordine fatturabile senza BA esce dalla fatturazione in silenzio.**
  `vendite.fn_list_ordini_da_pushare` filtra `o.billing_account_id IS NOT NULL` (residuo
  dell'ordine «prospect») e fa una `JOIN` interna sul BA; `vendite.fn_get_or_create_commessa`
  rifiuta un BA NULL. Nessun errore, una riga che manca.
  ⚠️ **Il DDT no**: `vendite.fn_ddt_push_diagnosi` ha il motivo `SENZA_BA` (rank 3, dopo
  `SOLO_TRASPORTO` al rank 2) e `script.fn_available_actions_ddt` lo espone. Sul DDT il difetto non
  e' il silenzio: e' che il BA si cerca in **due fonti** (sotto).
* **Le copie in testata possono dissentire.** Un ordine col BA del cliente A e il
  `soggetto_ruolo_id` del cliente B, o col BA del GAS e `utility_id` dell'energia elettrica, oggi si
  scrive. Da li' in poi ogni lettore che sceglie una delle due colonne risponde in un modo, e quello
  che sceglie l'altra nell'altro: indirizzi del documento (il BE ancora l'ancora sul ruolo nativo,
  `_indirizzi_repo_mixin`), liste, stampe, fattura.
* **Gli anelli della catena possono dissentire fra loro** — ed e' la forma piu' grave, perche'
  arriva in fattura:
  * una riga di DDT del cliente A puo' evadere una riga d'ordine del cliente B (il fulfillment non
    guarda il cliente);
  * la diagnosi del push risolve il BA **per riga**: `COALESCE(BA del DDT, BA dell'ordine
    sorgente)`. Un DDT senza BA in testata, con righe che evadono ordini di BA diversi, spinge le
    righe su BA diversi; un DDT con un BA diverso da quello dell'ordine spinge col BA del DDT;
  * un reso puo' nascere con un BA esplicito diverso da quello del suo DDT.
* **Il backend da' gia' per scontato il contrario.** Il docstring del BB
  `_indirizzi_repo_mixin` dice che gli esecutivi «hanno sempre un BA e l'istanza e' univoca da
  li'», e due righe sotto lo stesso file gestisce «l'ordine prospect con billing_account NULL».
  Le due frasi non possono essere vere insieme: la regola va scritta nel DB, e il BE la segue.
* **Il DDT e il reso cambiano cliente, l'ordine no.** L'ordine blocca BA e ruolo; DDT e reso no.
  Un DDT gia' emesso puo' cambiare cliente con un `UPDATE`.

⚠️ Nessuna di queste ragioni dipende da quante righe ci siano oggi in quello stato: valgono anche se
non ce n'e' nessuna (AGENTS.md, regola zero).

## 4. Decisioni per Tid

| # | Domanda | Proposta | Decisione di Tid |
| --- | --- | --- | --- |
| **D-1** | L'**ordine** ha sempre il BA? | **Si'.** L'ordine e' gia' legato a un ruolo (`soggetto_ruolo_id` NOT NULL) e ne blocca il BA; nasce dal preventivo o dall'offerta, che il BA lo hanno sempre, o standalone su un cliente. Un ordine senza fornitura non si sa a chi si fattura. ⚠️ **Conseguenza da accettare:** dopo [brief-db-istanza-nasce-col-ba](brief-db-istanza-nasce-col-ba.md) l'istanza nasce col BA, quindi un ruolo CLIENTE **senza fornitura non riceve ordini**. L'ordine «prospect» sparisce: e' voluto? | ✅ **Si'** (2026-10-09), conseguenza sul prospect compresa |
| **D-2** | Su quali **DDT** il BA e' obbligatorio? | Il modello ha gia' il discriminante, la causale (§2.2), e la diagnosi gia' mette `SOLO_TRASPORTO` prima di `SENZA_BA`. Resta da scegliere il perimetro: **(a)** solo causale `fatturabile` (`VENDITA`); **(b)** ogni causale che manda merce **al cliente** (`SCARICO_VEN`: anche `OMAGGIO` e `CAMPIONATURA`, che non si fatturano ma escono verso un cliente). Proposta del team DB: **(b)** — omaggio e campionatura sono consegne a un cliente, e il cliente a grana fine e' il BA; il «fatturabile» decide il push, non chi e' la controparte. ⚠️ Il criterio va scritto in una colonna del vocabolario delle causali (non per codice), e la diagnosi resta com'e' | ✅ **(b)** (2026-10-09): il BA serve su ogni DDT che manda merce a un cliente. Quali causali: D-2-bis |
| **D-2-bis** | Con (b), **quali causali** vogliono il cliente? | Non si deriva da `causale_magazzino = 'SCARICO_VEN'`: il conto visione manda merce a un cliente e non ha causale di magazzino, quindi resterebbe fuori. Serve una colonna nuova in `config.causali_trasporto` (nome di lavoro `richiede_cliente boolean NOT NULL`), valorizzata nel CSV. Proposta per il seed: **si'** `VENDITA`, `OMAGGIO`, `CAMPIONATURA`, `CONTO_VISIONE`; **no** `TRASFERIMENTO` (deposito nostro), `CONTO_LAVORO` e `RIPARAZIONE` (terzista); **da dire** `RESO` (un DDT con causale reso porta merce a chi? se e' il rientro verso un fornitore, no) | ✅ **Come proposto** (2026-10-09): si' `VENDITA`, `OMAGGIO`, `CAMPIONATURA`, `CONTO_VISIONE`; no `TRASFERIMENTO`, `CONTO_LAVORO`, `RIPARAZIONE`, `RESO`. ⚠️ La causale di trasporto `RESO` e' la bolla **nostra verso un fornitore** (commento di `20260928-60`, Lotto 4); il reso **del cliente** e' un'altra cosa, il documento `vendite.resi`, e segue D-3 (BA del suo DDT). La riconsegna al cliente dopo un reso eredita la causale del DDT d'origine (`fn_genera_ddt_riconsegna`) |
| **D-3** | Il **reso** ha il BA? | **Il BA del suo DDT, sempre.** Il reso non e' mai standalone (§2.1): la regola non e' «obbligatorio» ma «uguale a quello del DDT sorgente», NULL compreso — un reso da un conto visione senza BA resta senza BA. Non e' una decisione autonoma: segue D-2 | ✅ **Si'** (2026-10-09) |
| **D-4** | Il **destinatario** di DDT e reso e' sempre il ruolo del BA, o puo' essere un altro soggetto? | Se il BA c'e', proposta: **si'**, la stessa FK dell'ordine. La consegna a terzi si scrive negli indirizzi (`ddt_indirizzi`), non cambiando la controparte del documento. Dove il BA manca per D-2 (trasferimento, conto lavoro, riparazione) il destinatario resta libero: e' il terzista o il deposito, non un cliente | ✅ **Come proposto** (2026-10-09): con il BA, il destinatario e' il ruolo del BA; senza BA resta libero; la consegna a terzi passa dagli indirizzi |
| **D-5** | Le due copie (`utility_id`, ruolo di testata) si **legano** al BA o si **ritirano**? | Legarle, come R-2 sul preventivo: ritirarle costerebbe tutti i lettori (liste, filtri, indici `ix_ddt_vendita_dest_stato_data`, push), e la FK composta rende la copia innocua | ✅ **Legarle** (2026-10-09) |
| **D-6** | Gli anelli della catena hanno **lo stesso BA**? (§3, terzo punto) | **Si'.** Regola: *un esecutivo derivato ha il BA della sua sorgente.* Riga di DDT che evade una riga d'ordine → stesso BA della testata d'ordine; reso → stesso BA del DDT. Quando il BA del DDT e' obbligatorio (D-2), la seconda fonte nella diagnosi (`COALESCE` col BA dell'ordine) diventa superflua e si ritira | ✅ **Si'** (2026-10-09) |
| **D-7** | `billing_account.soggetto_ruolo_id` fa parte dell'**identita'** del BA? | **Si'**, come istanza e utility (R-1 del brief d'origine). Oggi non e' bloccato (il lock copre `codice`, `istanza_utility_id`, `utility_id`). Una FK composta `(billing_account_id, soggetto_ruolo_id)` lo bloccherebbe comunque, ma **di nascosto**: con `NO ACTION` il cambio di ruolo di un BA gia' usato fallisce con un 23503 grezzo, senza codice registrato; con `CASCADE` riscrive l'ordine e sbatte su `E_ORD_CLIENTE_IMMUTABILE`. Va bloccato in modo dichiarato, riga in `dbops.automation_lock_columns` col suo codice | ✅ **Si'** (2026-10-09), nella forma del §4.1: istanza, BA e cliente non cambiano intestatario; la fornitura sul soggetto sbagliato si annulla e si ricrea |

### 4.1 D-7 — che cosa dicono guide e contratto (istruttoria del 2026-10-09)

Domanda di Tid: perche' `billing_account.soggetto_ruolo_id` non e' stato bloccato, e se ci sono
cose date per vere che non lo sono.

**Nessuna decisione scritta di non bloccarlo.** R-1 di
[brief-db-istanza-nasce-col-ba](brief-db-istanza-nasce-col-ba.md) (§6.2) blocca istanza e utility
perche' «sono l'identita' del BA»; il ruolo non e' mai nominato, ne' per tenerlo dentro ne' per
lasciarlo fuori. Lo stesso per il manuale di `billing_account`, che dichiara immutabili istanza e
utility (e `canale_origine`) e tace sul ruolo. E' una **dimenticanza**, non una scelta: lo stesso caso
del codice offerta senza lock (riga 29 del CSV di `automation_lock_columns`).

**I documenti lo danno gia' per fisso.**

* [db-brief-ordini-lock-cliente](../work-done/db-brief-ordini-lock-cliente.md) §1: «la relazione
  BA → SR e' **1:1 deterministica**», ed e' la premessa del lock del cliente sull'ordine;
* [brief-db-billing-account-cambio-emittente](../work-done/brief-db-billing-account-cambio-emittente.md)
  D-3: due BA dello stesso cliente sotto due emittenti «risalgono gia' alla stessa persona
  giuridica» tramite `soggetto_ruolo_id`. Se il ruolo si sposta, la risposta cambia senza che
  nessuno lo sappia;
* guida [gestione delle istanze utility](../../guide/gestione-delle-istanze-utility.md) e manuale
  di `istanze_utilities` §7.3: «1 istanza = 1 cliente», e **il subentro crea un'istanza nuova** (e
  quindi un BA nuovo), non cambia l'intestatario di quella esistente
  ([generazione-cliente](../../guide/generazione-cliente.md), appendice «Subentro»). Nessun flusso di
  dominio descritto nelle guide ha bisogno di cambiare il ruolo di un BA.

**Che cosa il modello ammette oggi.**

* `uq_soggetto_ruolo (soggetto_id, tipo_ruolo_id)`: un soggetto ha **un solo** ruolo CLIENTE;
* `trgfn_billing_account_guard_soggetto_coerenza_istanza`: il soggetto del ruolo del BA e' quello
  dell'istanza.

Messi insieme: l'unico `UPDATE` di `billing_account.soggetto_ruolo_id` che passa oggi e' verso un
**altro ruolo dello stesso soggetto, di un altro tipo** (FORNITORE, VETTORE…). Cioe' l'unico cambio
ammesso e' proprio quello che non dovrebbe esistere.

**Le cose date per vere che non lo sono** (le «cose immaginate»):

1. ⛔ **«Il BA e' del ruolo CLIENTE».** Lo dicono le guide (generazione-cliente: «Ruolo CLIENTE →
   … → Billing Account»), ma nel contratto non c'e' un vincolo sul **tipo** del ruolo: la FK va a
   `soggetti_ruoli` qualunque, e il guard di coerenza confronta il **soggetto**, non il tipo. Un BA
   puo' nascere (non solo diventare) sul ruolo FORNITORE del soggetto giusto.
2. ⛔ **«Il soggetto dell'istanza e il soggetto del BA coincidono sempre».** Il guard di coerenza
   scatta solo su `billing_account`. `istanze_utilities.soggetto_id` non e' bloccato (il lock copre
   solo `codice`) e nessun trigger sull'istanza ricontrolla i BA: un `UPDATE` del soggetto
   dell'istanza rompe la regola **in silenzio**, dall'altra porta. La regola ha due madri e ne
   presidia una.
3. ⚠️ Il manuale di `istanze_utilities` §7.3 dice «salvo **casi di continuita' pre-definiti**»: non
   e' scritto quali siano, e nessuna funzione li implementa. Se esistono, sono l'unico argomento per
   **non** bloccare; se no, la frase si toglie. «Intestatario» qui vuol dire il **soggetto** a cui
   appartiene la fornitura: `istanze_utilities.soggetto_id`, e di riflesso il ruolo su BA e cliente.
   ✅ **Risposta di Tid (2026-10-09): i casi di continuita' non esistono.** La fornitura creata sul
   soggetto sbagliato **si annulla e si ricrea** sul soggetto giusto, sempre. La correzione sul
   posto non e' percorribile: una fornitura con documenti emessi (ordini, DDT, fatture) li
   porterebbe con se' su un altro soggetto. Strumenti straordinari per questi casi, se serviranno,
   saranno un cantiere a parte: non sono operazioni semplici, e non si progettano qui.

**Dubbio di Tid: il multi-utility spiega il lock mancante?** No. Un BA e' **una** coppia (istanza,
utility): `istanza_utility_id` e `utility_id` NOT NULL e `uq_billing_instance_utility`, che c'era gia'
prima di R-1. Un'istanza con piu' utility ha piu' BA, uno per utility, e un soggetto ha tanti BA quante
sono le sue forniture: e' il modello deciso il 2026-10-08 (D-5 e D-6 di
[brief-db-istanza-nasce-col-ba](brief-db-istanza-nasce-col-ba.md); guida istanze, «Multi-utility»).
Tutti quei BA puntano allo **stesso** `soggetto_ruolo_id`, perche' il ruolo CLIENTE e' uno per
soggetto: bloccare la colonna non costringe a creare BA in piu', vieta solo che un BA **gia' nato**
cambi intestatario. La fattura unica su piu' forniture dello stesso cliente c'e' gia', ed e' un'altra
cosa: la gerarchia `parent_account_id` (la fattura va al BA padre, `fn_build_fattura_key`).

Esempio: il soggetto SG1 ha il gas e vuole anche l'elettricita' o il servizio BASE. Il ruolo CLIENTE
resta uno; cambia il numero di forniture. Due forme, secondo dove sta la fornitura nuova:

```text
Stesso luogo (stessa istanza)            Luogo diverso (istanza nuova)
SG1 ── SR1 (CLIENTE, unico)              SG1 ── SR1 (CLIENTE, unico)
        └── IU1 ── BA1 (IU1, GAS) ── CL1         ├── IU1 ── BA1 (IU1, GAS)  ── CL1
               └── BA2 (IU1, ELE) ── CL2         └── IU2 ── BA2 (IU2, BASE) ── CL2
```

In entrambe BA1 e BA2 puntano allo **stesso** SR1. Fatto datato (dbdev, 2026-10-09): `SGT-0000121` e'
nella seconda forma — `IFO-0000027` GAS → `BAC/0000023` → cliente 20, e `IFO-0000036` BASE →
`BAC/0000042` → cliente 137, tutti sul ruolo 64 — e resta valido con i lock proposti. Per l'utente
cambia una cosa sola: un documento non sceglie «il cliente» ma **quale fornitura** del cliente.

**La tabella `anagrafiche.clienti` (verifica del 2026-10-09, su richiesta di Tid).** Il cliente e'
il terzo oggetto della fornitura, dopo istanza e BA, e porta anche lui una copia del ruolo.

| Colonna di `clienti` | Legata a che cosa | Come |
| --- | --- | --- |
| `billing_account_id` | NOT NULL, **un cliente per BA** | `uq_clienti_billing_account` (R-8) |
| `istanza_utility_id` | l'istanza del BA | FK composta `fk_clienti_billing_account (billing_account_id, istanza_utility_id)` |
| `utility_id` | la utility del BA | `trgfn_clienti_sync_utility_from_ba`: la copia se manca, `E_CLIENTE_UTILITY_MISMATCH_BA` se dissente. Nullable, ma il trigger la valorizza sempre |
| `soggetto_ruolo_id` | **solo il tipo**: e' un ruolo CL | `trgfn_clienti_guard_ruolo_cliente` → BB `script.fn_guard_soggetto_ruolo(NULL, sr, 'CL')`. ⛔ **Non** e' confrontato col ruolo del BA, ne' col soggetto dell'istanza |

Quello che ne segue:

* **Punto 4.** ⛔ **Il cliente puo' essere di un altro soggetto rispetto al suo BA.** Istanza e utility del
  cliente sono legate al BA; il ruolo no. Un cliente col BA di Rossi e il ruolo CLIENTE di Verdi
  oggi si scrive: e' la stessa copia slegata dell'ordine (§2), un piano piu' in basso.
* **Punto 5.** ⭐ **Il controllo del tipo esiste gia', ed e' un BB.** `script.fn_guard_soggetto_ruolo` lo usano
  dieci specializzazioni (clienti, fornitori, vettori, gestori, psp, resellers, emittenti
  fiscali…). Il BA e' l'unico oggetto legato a un ruolo CLIENTE che **non** lo chiama: il punto 1
  si chiude chiamando il BB, non scrivendo un guard nuovo.
* **Punto 6.** ⛔ **Niente e' bloccato sul cliente.** `automation_lock_columns` non ha righe per `clienti`:
  `billing_account_id`, `istanza_utility_id` e `soggetto_ruolo_id` si cambiano con un `UPDATE`.
  Spostare un cliente su un altro BA vuol dire cambiargli la fornitura; il subentro, l'unico flusso
  di dominio che cambia l'intestatario, crea un cliente nuovo su un'istanza nuova
  (`fn_subentro_cliente` chiude il vecchio).
* **Punto 7.** Un BA senza cliente resta ammesso (la fase precontrattuale, R-8): niente da cambiare.

**D-7 — la forma (decisione di Tid del 2026-10-09).**

* `billing_account.soggetto_ruolo_id` **bloccato** come istanza e utility: riga in
  `dbops.automation_lock_columns` con `E_BA_ISTANZA_IMMUTABILE` (il messaggio va allargato: «la
  fornitura e il cliente sono l'identita' del billing account») o con un codice suo;
* `istanze_utilities.soggetto_id` **bloccato** anch'esso: chiude la seconda porta (punto 2) — il
  subentro non ne ha bisogno, crea un'istanza nuova;
* il **tipo** del ruolo del BA presidiato (punto 1) chiamando il BB `script.fn_guard_soggetto_ruolo`
  con `'CL'`, come fanno le dieci specializzazioni (punto 5) — non un guard nuovo;
* il **cliente legato al ruolo del suo BA** (punto 4): FK composta `(billing_account_id,
  soggetto_ruolo_id, utility_id)` → `billing_account (id, soggetto_ruolo_id, utility_id)`, lo
  **stesso** indice unico dell'ordine (§5.1), con `clienti.utility_id` NOT NULL (il trigger la
  valorizza gia' sempre). Il controllo di `trgfn_clienti_sync_utility_from_ba` sulla utility diventa
  la FK; il trigger resta per la copia e per il PDP obbligatorio;
* il **cliente bloccato** su `billing_account_id` (punto 6): istanza, utility e ruolo seguono dal BA
  tramite la FK composta, e il BA e' gia' bloccato su tutti e tre;
* la frase del §7.3 del manuale di `istanze_utilities` sulla «continuita'» **si toglie** (risposta di
  Tid al punto 3), nello stesso giro dei lock;
* prima dei lock, le righe fuori regola (§6): BA su un ruolo non CLIENTE, BA il cui soggetto non e'
  quello dell'istanza.

Una volta deciso D-7, le FK composte del §5 verso `(id, soggetto_ruolo_id, …)` non bloccano piu' «di
nascosto»: il lock dichiarato scatta prima, col suo codice.

## 5. Forma proposta (la sceglie il team DB)

Lo stampo e' R-2 di `brief-db-istanza-nasce-col-ba` (§6.3), con una differenza di fase sul DDT.

### 5.1 Ordine (D-1, D-5, D-7)

* `billing_account_id` e `utility_id` NOT NULL;
* **una** FK composta a tre colonne `(billing_account_id, soggetto_ruolo_id, utility_id)` →
  `billing_account (id, soggetto_ruolo_id, utility_id)`, con **un** indice unico nuovo su quelle tre
  colonne. Due FK separate (`(id, utility_id)` e `(id, soggetto_ruolo_id)`) costerebbero due indici
  per lo stesso legame;
* i lock e il guard di D-7 (§4.1), prima della FK.

### 5.2 DDT (D-2, D-4, D-5, D-6)

* ⛔ **Non** NOT NULL e **non** un guard su INSERT: la causale, che decide se il BA serve, in bozza
  puo' non esserci ancora (§2.2). Il vincolo sta dove sta la causale:
  * la colonna nuova di D-2-bis su `config.causali_trasporto`, valorizzata dal CSV;
  * un **motivo nuovo** in `script.fn_check_ddt_emittibile` («la causale vuole un cliente e il BA
    manca», letto da quella colonna) e il suo ramo in `vendite.trgfn_ddt_guard_causale_emissione`
    — sede unica di guard e capability, come gli altri motivi d'emissione;
  * il **lock del BA fuori bozza**, gemello di `trgfn_ddt_guard_causale_immutabile` (si guarda lo
    stato VECCHIO: l'`UPDATE` che porta DRAFT → EMESSO scegliendo il BA e' legittimo). Non il lock
    assoluto dell'ordine: vieterebbe di scegliere il BA su una bozza, cioe' il caso giusto;
* utility e destinatario legati al BA (D-4, D-5) con la **stessa** FK a tre colonne dell'ordine e
  del cliente, `(billing_account_id, destinatario_soggetto_ruolo_id, utility_id)` →
  `billing_account (id, soggetto_ruolo_id, utility_id)`, in `MATCH SIMPLE`: con il BA NULL non
  scatta, ed e' il comportamento voluto — senza cliente il destinatario resta libero (terzista,
  deposito). ⚠️ `MATCH SIMPLE` salta anche quando e' NULL la sola utility: la chiude un CHECK
  `(billing_account_id IS NULL) = (utility_id IS NULL)` («tutti e due o nessuno»). Cosi' un solo
  indice unico sul BA serve ordine, cliente, DDT e reso; `MATCH FULL` non va, perche' il
  destinatario e' NOT NULL anche senza BA;
* D-6: guard su `ordini_righe_fulfillment` (BA della testata d'ordine = BA della testata del DDT),
  accanto ai controlli di articolo e UoM di `trgfn_ordini_ful_guard_consistenza`; e
  `trgfn_ddt_normalize` che **rifiuta** un BA esplicito diverso da quello dell'ordine sorgente invece
  di tenerlo col `COALESCE`.

### 5.3 Reso (D-3, D-4, D-6)

* il BA **uguale** a quello del DDT sorgente, NULL compreso: guard (o `trgfn_resi_normalize` che
  rifiuta un valore esplicito diverso) — non un NOT NULL;
* utility e destinatario come sul DDT (FK a tre colonne `MATCH SIMPLE` + CHECK «tutti e due o nessuno»);
* il lock del BA fuori bozza, come sul DDT.

### 5.4 Comune

* i codici d'errore nuovi registrati, con policy e frase di ripiego (`E_ORD_CLIENTE_IMMUTABILE`
  parla dell'ordine);
* i guard emittente ↔ BA (`trgfn_ordini_guard_emittente_ba`, `trgfn_ddt_guard_emittente_ba`,
  `trgfn_resi_guard_emittente_ba`) tengono l'uscita anticipata su NULL: sull'ordine per la ragione
  del preventivo (§6.3 del brief d'origine: il NOT NULL si controlla dopo i trigger BEFORE), su DDT e
  reso perche' il NULL resta un caso del modello.

### 5.5 Da censire nel giro (non qui)

* i verbi che creano ordini, DDT e resi: `fn_push_preventivo_a_ordine`, `fn_genera_ddt_da_ordine`,
  **`fn_genera_ddt_riconsegna`**, la creazione del reso dal DDT;
* `vendite.trgfn_ordini_normalize`: col BA NOT NULL la condizione `billing_account_id IS NOT NULL`
  del ramo `fatturazione_trigger` e' sempre vera — si semplifica;
* `vendite.fn_list_ordini_da_pushare`: il filtro `o.billing_account_id IS NOT NULL` diventa ridondante;
* `vendite.fn_ddt_push_diagnosi`: la seconda fonte del BA (D-6), e il rank `SENZA_BA` che resta solo
  per le causali del perimetro di D-2;
* la nota di `dbops.automation_lock_columns` sulla riga `ordini.soggetto_ruolo_id` («copertura
  ordini con BA NULL») si riscrive;
* i pgTAP che costruiscono questi documenti senza BA, o con BA diversi lungo la catena — il brief
  d'origine ne ha trovati due giri dopo il primo censimento (§6.12.2, §6.13).

⚠️ **Fuori da qui, da annotare:** i guard emittente ↔ BA sono sette copie quasi uguali (ordini, DDT,
resi, preventivi, offerte, contratti, commesse). Questo brief non li tocca; il giro che li tocchera'
li estrae in un BB parametrico (regola del 2).

## 6. Prima dei vincoli

Come in R-5 del brief d'origine: NOT NULL e FK composte verificano anche le righe esistenti, quindi
le righe fuori regola si correggono **prima**, e ogni changeSet porta la `preCondition` sulle righe
che non passerebbero. Il modo (a mano o changeSet) si decide con Tid. Le righe da guardare:

* ordini senza BA; `utility_id` o ruolo diversi da quelli del BA;
* DDT **fuori bozza** con causale nel perimetro di D-2 e senza BA — vanno corretti **prima** del
  lock fuori bozza, altrimenti dopo non si correggono piu';
* DDT e resi con `utility_id` o destinatario diversi dal BA (secondo D-4);
* righe di DDT che evadono ordini di un altro BA; resi con un BA diverso da quello del DDT (D-6);
* BA su un ruolo non CLIENTE; BA il cui soggetto non e' quello dell'istanza (D-7);
* clienti col ruolo diverso da quello del loro BA (D-7, punto 4).

⛔ Il loro numero entra solo come fatto datato, mai come motivo.

**Fatto datato (dbdev `zeroerp`, 2026-10-09, letto da owner, RLS non forzata):** tutte le regole sopra
a zero tranne una, tre DDT col BA e senza utility (61 `DDT0000034` CONSEGNATO, 82 `DDT0000041` e 91
`DDT0000043` ANNULLATI, tutti `VENDITA`). Su dbdev la correzione e' a mano (la utility presa dal BA),
decisa da Tid: non serve su altri database, quindi nessun changeSet di bonifica. La `preCondition` dei
changeSet dei vincoli resta comunque, per i database che non sono dbdev.

## 7. Ricaduta BE/FE (dopo la consegna DB)

* Commenti e rami sul «prospect» / «BA NULL» da riscrivere o ritirare: `ordini_repository`
  (`_indirizzi_doc_sr_column`), `_indirizzi_repo_mixin` (docstring e `LEFT JOIN` sul BA),
  `ddt_repository`, `ordine_document_context_builder`. Sul DDT e sul reso il `LEFT JOIN` resta: il
  BA puo' mancare (D-2, D-3).
* Form dell'ordine: BA obbligatorio. Form del DDT: BA facoltativo in bozza, l'azione «Emetti»
  disabilitata col motivo nuovo dalla capability (nessuna regola ricopiata nel FE). Form del reso: il
  BA non si sceglie, viene dal DDT.
* Nomi delle FK nuove nelle mappe dei vincoli dei service (`ordini_service`, `ddt_service`,
  `resi_service`), sul campo `billing_account_id`; codici nuovi con policy e frase di ripiego.

## 8. Fuori da questo brief

* **Il BA di un documento chiuso si riscrive** (§6.9 del brief d'origine): la domanda generale «quali
  colonne di testata si riscrivono in fase chiusa» e' sua, e resta da aprire. Qui si chiede solo il
  lock del BA che l'ordine ha gia', e su DDT e reso quello per fase che la causale ha gia'.
* **Acquisti**: ordini e DDT di acquisto parlano di un fornitore, non di un BA. Se il fornitore ha un
  analogo a grana fine (un ruolo con piu' rapporti), la stessa domanda andra' posta li'; oggi no.
