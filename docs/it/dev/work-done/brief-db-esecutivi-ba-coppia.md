# Brief DB — Ordine, DDT e reso: il cliente come su preventivo, offerta e contratto

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09; **rivisto dal team DB** lo stesso giorno
> (§2, §3, §4 e §5 riscritti sul contratto letto dalla doc auto-generata). **A chi:** team DB; poi
> BE/FE (§7).
> **Origine:** §7.5 di [brief-db-istanza-nasce-col-ba.md](brief-db-istanza-nasce-col-ba.md). Il suo R-2
> ha reso `billing_account_id` NOT NULL e legato alla coppia (istanza, utility) su preventivo,
> offerta e contratto. Chiudendo il lato BE/FE e' emerso che i documenti **esecutivi** di vendita
> (ordine, DDT, reso) sono rimasti fuori: e' la stessa asimmetria, un livello piu' in basso.
> **Stato al 2026-10-10:** ✅ **chiuso e archiviato.** Lato DB applicato su dbdev e verde, giro 1 e
> giro 2 (§9, §11); lato BE/FE fatto (§12, commit `062b06368`). Il debito fuori perimetro e' in tre
> brief: [brief-db-guard-emittente-ba-unico](brief-db-guard-emittente-ba-unico.md) (D22, chiuso),
> [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md) (D26) e
> [brief-db-indirizzi-documento-seguono-il-cliente](brief-db-indirizzi-documento-seguono-il-cliente.md)
> (D27, dal §12.3). Il collaudo a video dei form di DDT e ordine resta di Tid (§12.2).
> **Dettaglio:** 31 changeSet
> `20261009-62…-92`, tutti `EXECUTED` nel `databasechangelog` di dbdev (`-62…-82` alle 19:19, `-83…-85`
> alle 19:30, `-86…-92` alle 23:46 del 2026-10-09). Il giro e' cresciuto due volte oltre il §5: il lock
> dell'emittente fuori bozza su sei documenti (§9.8, §9.9). **Da leggere per primo: §10** (verifica
> incrociata del 2026-10-10, le cinque domande chiuse da Tid lo stesso giorno, e il §10.4: che cosa
> resta da fare); poi §9 (cosa e' stato fatto). Decisioni sul modello chiuse il 2026-10-09 (§4), sulla
> forma il 2026-10-10 (§10.2), messe nel codice dal giro DB 2 (§11: 6 changeSet `20261010-02…-07`,
> 2 codici a catalogo, pgTAP a 39 test, 4 pagine `manual/`), applicato e verde il 2026-10-10.
> **Da leggere per primo, ora: §11** (e il §11.5 per il backend).
> **Giro BE/FE fatto il 2026-10-10: §12** (i due punti del §12.3 chiusi o passati a un brief nuovo).
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

* [db-brief-ordini-lock-cliente](db-brief-ordini-lock-cliente.md) §1: «la relazione
  BA → SR e' **1:1 deterministica**», ed e' la premessa del lock del cliente sull'ordine;
* [brief-db-billing-account-cambio-emittente](brief-db-billing-account-cambio-emittente.md)
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
  ⚠️ **Superato in parte (2026-10-09):** per l'**emittente** la risposta e' stata data qui, su sei
  documenti (§9.8, §9.9), con il BB fuori bozza del §9.3 punto 1. Resta aperta la domanda generale
  per le **altre** colonne di testata.
* **Acquisti**: ordini e DDT di acquisto parlano di un fornitore, non di un BA. Se il fornitore ha un
  analogo a grana fine (un ruolo con piu' rapporti), la stessa domanda andra' posta li'; oggi no.

## 9. Giro DB 1 — consegna (team DB, 2026-10-09)

> ✅ **Applicato su dbdev il 2026-10-09** (vedi intestazione). L'avviso qui sotto e' quello scritto
> prima dell'apply, lasciato come storia della prova.
>
> ⚠️ **Scritto e provato, NON applicato.** Prova: SQL estratto dagli YAML (preCondition comprese)
> in una transazione annullata su `zeroerp_ci`, piu' l'upsert di **tutte** le righe dei quattro CSV
> toccati e la convergenza dei lock (`fn_run_automations_lock_columns`), come fa il `90_end`.
> `zeroerp_ci` non ha anagrafiche: le preCondition li' passano per costruzione, sui dati veri
> vale il fatto datato del §6. Apply e corsa pgTAP restano di Tid.

### 9.1 ⛔ Prima dell'apply, su dbdev

* i tre DDT del §6 (61 `DDT0000034`, 82 `DDT0000041`, 91 `DDT0000043`): utility dal BA, a mano.
  Senza, la preCondition di `20261009-65` ferma il migrate (CHECK «tutti e due o nessuno»).
  ✅ **Fatto** (la preCondition di `-65` e' passata: `EXECUTED` alle 19:19 del 2026-10-09).

### 9.2 I changeSet

I 24 del giro 1 (`-62…-85`). I sette successivi (`-86…-92`, l'emittente) stanno nelle tabelle del §9.8
e del §9.9.

| # | Cosa | Decisione |
| --- | --- | --- |
| `-62` | `config.causali_trasporto.richiede_cliente` (+ CSV e mirror `20260709-11`): si' VENDITA, OMAGGIO, CAMPIONATURA, CONTO_VISIONE | D-2-bis |
| `-63` | `UNIQUE (id, soggetto_ruolo_id, utility_id)` su `billing_account`: destinazione unica delle quattro FK | §5.1 |
| `-64` | ordini: BA e utility NOT NULL + `fk_ordini_ba_cliente` | D-1, D-5 |
| `-65`, `-66` | ddt, resi: `chk_*_ba_utility_insieme` + `fk_*_ba_cliente` `MATCH SIMPLE` | D-4, D-5 |
| `-67` | clienti: utility NOT NULL + `fk_clienti_ba_cliente` | D-7 p.4 |
| `-68`, `-69` | guard del ruolo del BA: + tipo CLIENTE dal BB `script.fn_guard_soggetto_ruolo`; trigger in fascia `_a20_` | D-7 p.1, p.5 |
| `-70` | **BB nuovo** `vendite.trgfn_doc_testata_lock_fuori_bozza` (stato VECCHIO, coppie colonna/codice) | §5.2 lock |
| `-71`…`-75` | montato su DDT (causale, BA, utility, destinatario, magazzino) e reso (magazzino); ritirate le tre copie | regola del 2 |
| `-76`, `-77` | motivo `E_DDT_CLIENTE_OBBLIGATORIO` in `fn_check_ddt_emittibile` e suo ramo nel gate d'emissione | D-2 |
| `-78`…`-82` | D-6 sulle tre porte: testata del DDT (ordine o reso sorgente), fulfillment, reso — un codice, `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE` | D-3, D-6 |
| `-83` | `fn_ddt_push_diagnosi`: un BA solo, quello della testata | D-6 |
| `-84`, `-85` | normalize di ordine e DDT: utility (e destinatario sul DDT) dal BA quando il chiamante non li dice | D-4, D-5 |
| `80_data` | 4 codici nuovi, 3 frasi riscritte (`E_DDT_CAUSALE_IMMUTABILE`, `E_DDT_CLIENTE_IMMUTABILE`, `E_BA_ISTANZA_IMMUTABILE`); 6 righe di lock (BA ruolo, istanza soggetto, 4 colonne del cliente) e la nota di `ordini.soggetto_ruolo_id` riscritta | D-7 |

### 9.3 Dove la forma si scosta dal §5 — ✅ confermato da Tid il 2026-10-10 (§10.2, domande 1, 2 e 4)

1. **Un BB invece di un gemello.** Il §5.2 chiedeva il lock del BA «gemello di
   `trgfn_ddt_guard_causale_immutabile`». Sul catalogo la regola «colonna di testata immutabile fuori
   bozza» era gia' scritta a mano tre volte (causale DDT, magazzino DDT, magazzino reso): la quarta
   ha fatto estrarre il BB e ritirare le tre copie nello stesso giro. Frasi del magazzino invariate;
   quella della causale cambia forma («La bolla e' in stato %s: la causale … si sceglie solo in
   bozza»), come il magazzino.
2. **Fuori bozza si blocca anche il destinatario senza BA** (deposito, terzista): BA, utility e
   destinatario sono la controparte stampata, e col BA la FK li lega comunque — bloccarne uno solo
   lascerebbe agli altri un 23503 grezzo. ✅ Confermato da Tid il 2026-10-10 (§10.2, domanda 1).
   ⚠️ Decisione di forma presa dal team DB: se il
   destinatario di un trasferimento deve restare correggibile dopo l'emissione, basta togliere la
   colonna dal montaggio di `-71`.
3. **Il reso non ha un lock del BA fuori bozza** (§5.3, terzo punto): il guard «BA uguale a quello
   del DDT» gira in ogni stato, e il BA del DDT (consegnato) e' bloccato. Un lock in piu' direbbe la
   stessa regola due volte.
4. **Il cliente e' bloccato su quattro colonne**, non sul solo `billing_account_id` (§4.1): le altre
   tre le fermerebbe la FK composta, ma con un 23503 grezzo — lo stesso argomento di D-7.
5. **Il guard del BA cambia fascia** (`_a10_` → `_a20_`): veniva prima del lock di colonna (g < l), e
   il lock nuovo su `soggetto_ruolo_id` non avrebbe mai parlato.
6. **Utility e destinatario si derivano dal BA** (`-84`, `-85`), non solo si verificano: col NOT NULL
   e le FK nuove ogni chiamante avrebbe dovuto ripetere cio' che il BA gia' dice. Stessa forma di
   `anagrafiche.clienti` (la copia se manca, il rifiuto se dissente). Il controesempio che l'ha fatta
   vedere: una cinquantina di fixture pgTAP e le tre righe di dbdev — DDT standalone col BA e senza
   utility, che il normalize non riempiva.
7. **Non toccati**, e perche': `trgfn_ordini_normalize` resta con `billing_account_id IS NOT NULL`
   (in un BEFORE ROW il BA puo' ancora essere NULL: il NOT NULL si controlla dopo, la condizione non e'
   «sempre vera»); il filtro `o.billing_account_id IS NOT NULL` di `fn_list_ordini_da_pushare` resta,
   ridondante e innocuo; nessuna riga di `fk_index_policy` per le quattro FK (le registra
   `fn_populate_fk_index_policy` a `false`, come le FK coppia di R-2).

### 9.4 Prove

* **24 changeSet** in transazione annullata su `zeroerp_ci`: tutti verdi, preCondition comprese; i
  quattro CSV si ricaricano interi dopo (FK `messaggi → codici` rispettata dall'ordine dei loader).
* **pgTAP nuovo** `db/pgtap/vendite/test-esecutivi-ba-coppia-v1.sql`, 27 test, fixture fabbricati
  (gira anche da zero): **27/27 dopo**, rosso dal test 1 prima.
* **153 pgTAP di `dbops/` e `script/`** prima/dopo: 146 identici. Dei 7 diversi, uno e' un artefatto
  della prova (`test-user-update-not-null-v1` vedeva le tabelle temporanee dell'upsert dei CSV), sei
  sono fixture del §9.5.
* Nella prova il log remoto via `dblink` e' spento (`myapp.log_with_dblink = off`): la sessione del
  log scrive `error_log` con FK verso le righe di `messaggi_errore` che la transazione di prova ha
  appena inserito, e aspetta la sua fine — mentre la prova aspetta lei. Dopo l'apply il caso non
  esiste.

### 9.5 Fixture pgTAP — sistemati e da sistemare

Censimento statico del 2026-10-09 sui `db/pgtap/**`: le forme che le regole nuove rifiutano.

* ✅ **Sistemati** (in questo giro):
  * 6 file con DDT che passava la utility senza BA (`rls/test-rls-ddt-satelliti`,
    `-note-padre`, `-resi-ef-whitelist-write`, `-resi-satelliti`,
    `script/test-fn-check-prezzi-autorizzati-v1`, `vendite/test-righe-e-componenti-le-altre-famiglie-v1`):
    ora col BA del cliente; nei 5 RLS il BA e' legato all'emittente del mondo (terzo argomento di
    `fn_pgtap_crea_cliente_ba`), perche' col BA il guard emittente <-> BA ora guarda;
  * 2 file con ordini senza BA (`rls/test-rls-ordini-satelliti`,
    `vendite/test-riepilogo-iva-equivalenza-cross-doc`, che usava come cliente il ruolo dell'emittente);
  * 29 file che sceglievano come cliente «il primo ruolo del database» accanto a un BA scelto a parte:
    il ruolo e' ora quello del BA;
  * `vendite/test-fn-list-ddt-da-pushare-v1` caso 9: costruiva una bolla VENDITA spedita senza BA, che
    il modello non ammette piu' — ora misura che non si emette;
  * `anagrafiche/test-trgfn-billing-account-guard-soggetto-coerenza-istanza-v1` (nome del trigger
    `_a20_`) e un commento di `test-istanza-nasce-col-ba-v1`.
* ⏳ **Da sistemare** — ordini creati **di proposito** col BA NULL «per saltare il guard emittente <->
  BA», forma che D-1 vieta: `script/test-fn-available-actions-ordine-v1`, `-v2`,
  `script/test-guard-emittente-senza-utente`, `script/test-seed-stati-doc-ordini-evaso-v1`,
  `vendite/test-fn-list-ordini-da-pushare-v3`, `vendite/test-ordini-guard-transizione-v1`; piu'
  `script/test-fn-available-actions-ddt-reason-catch-all-v1` (emette una VENDITA senza BA) e
  `script/test-fn-check-ddt-emittibile-v1` (destinatario scollegato dal BA). Vanno ripensati uno per
  uno: il caso che misuravano esiste ancora, ma va costruito con un cliente fabbricato.
  ⚠️ **Aggiornato il 2026-10-10** (lettura statica dei file): `vendite/test-ordini-guard-transizione-v1`
  e `vendite/test-fn-list-ordini-da-pushare-v3` sistemati nella terza corsa (sotto),
  `script/test-fn-check-ddt-emittibile-v1` sistemato (il ruolo e' quello del BA). Restavano ⏳ cinque — 🔧 **tutti
  corretti nell'albero nella notte fra il 9 e il 10** (cliente fabbricato, BA legato all'emittente
  dell'operatore dal trigger z90); ⏳ **da confermare con la corsa** (§10.5):
  * `script/test-fn-available-actions-ordine-v1` — ordine con `NULL::bigint` come BA (riga 100);
  * `script/test-fn-available-actions-ordine-v2` — **sfuggito al censimento dei «29 file»**: BA preso
    dai dati (`push_ba_id`) e ruolo = «il primo `soggetti_ruoli` del database» (riga 69). La FK
    composta lo rifiuta, salvo che i due coincidano per caso; su un database senza BA pushabile non
    inserisce niente (`WHERE r.push_ba_id IS NOT NULL`): verde per sottrazione;
  * `script/test-guard-emittente-senza-utente` — tre INSERT con BA `NULL` dentro `throws_ok`: ora
    escono col 23502 del NOT NULL, non col codice che il test aspetta;
  * `script/test-seed-stati-doc-ordini-evaso-v1` — ordine con BA `NULL` (riga 140);
  * `script/test-fn-available-actions-ddt-reason-catch-all-v1` — DDT VENDITA con BA `NULL` (riga 413):
    `E_DDT_CLIENTE_OBBLIGATORIO` all'emissione.
* ⚠️ Il censimento e' statico: la conferma e' la corsa di Tid su dbdev dopo l'apply.

**Dopo l'apply (2026-10-09 sera).** Il primo migrate si e' fermato su `-83` (il `COMMENT` nello stesso
`- sql:` del `BEGIN ATOMIC`: pgjdbc lo manda come istruzione unica — corretto separando i due change,
come `20260922-14`). Con `-84`/`-85` assenti la corsa pgTAP dava ~60 rossi «utility_id nullo»; dopo il
secondo migrate ne restavano quattro, sistemati cosi':

* `vendite/offerte_commerciali/test_fn_push_offerta_a_contratto`: l'ordine nato dall'offerta ha ora il BA
  dell'offerta e il suo ruolo (D-6), non BA NULL e il primo ruolo del database;
* `vendite/test-ordini-riepilogo-iva-totali` e `vendite/test-riepilogo-iva-equivalenza-cross-doc`: il
  cliente dell'ordine si fabbrica (`fn_pgtap_crea_cliente_ba` sotto l'operatore), invece di pescare un BA
  dai dati — su un database senza BA l'ordine non nasceva;
* `vendite/test-esecutivi-ba-coppia-v1` (il mio): gira come app, e il BA passato col terzo argomento
  dell'helper non era visibile sotto la RLS. Ora agisce come l'operatore dell'emittente fabbricato e il BA
  lo lega il trigger z90. ⚠️ L'avevo provato solo da owner, dove la RLS non c'e'.

⚠️ **Trovato strada facendo, da decidere (Tid).** Il test 15 di `test-ordini-riepilogo-iva-totali`
collaudava `trg_ordini_z90_ricalcola_totali_upd` (`AFTER UPDATE OF emittente_fiscale_id`) spostando
l'ordine su un altro emittente. Con il BA obbligatorio (D-1) e un emittente per BA, quel cambio lo
rifiuta sempre il guard emittente <-> BA: il ramo «l'ordine cambia emittente» non ha piu' un caso
legittimo. Il test ora riscrive l'emittente con lo stesso valore (`UPDATE OF` scatta lo stesso); il
trigger resta. Se l'emittente dell'ordine e' di fatto immutabile, va dichiarato (lock) e il trigger
ripensato. ⚠️ Superato dal §9.8 (decisione di Tid dello stesso giorno): il test 15 ora verifica il lock.

### 9.6 Ricaduta BE/FE, in piu' del §7

* **FE**: `reason_key` nuova `vendite.ddt.azione_reason.cliente_mancante` nei locales
  (`scripts/check_i18n_keys.py`, controllo 4, va in rosso finche' manca).
* **BE**: codici nuovi `E_DDT_CLIENTE_OBBLIGATORIO` (CONFLITTO_STATO),
  `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE` (DATO_ERRATO, campo `billing_account_id`),
  `E_ISTANZA_SOGGETTO_IMMUTABILE`, `E_CLIENTE_FORNITURA_IMMUTABILE` (CONFLITTO_STATO); FK nuove
  `fk_ordini_ba_cliente`, `fk_ddt_ba_cliente`, `fk_resi_ba_cliente`, `fk_clienti_ba_cliente`, CHECK
  `chk_ddt_ba_utility_insieme`, `chk_resi_ba_utility_insieme`.
* **BE, regola duplicata**: `ddt_service.aggiorna_ddt` rifiuta il cambio di BA **anche in bozza**
  (`E_DDT_CLIENTE_IMMUTABILE`, «cambiare cliente = nuovo DDT»). Il DB dal 2026-10-09 lo blocca solo
  **fuori bozza**, e D-2 vuole che il BA si possa scegliere in bozza prima di emettere: col guard BE
  una bolla nata senza BA non lo riceve mai. Il guard BE va tolto (decide il DB, con lo stesso
  codice) — e con lui la frase di ripiego «dopo la creazione».
* ⚠️ **Allargato il 2026-10-10** (analisi critica; nessun commit BE ha toccato `ddt_service` dopo il
  giro DB). Togliere il guard non basta, perche' lo stesso service contraddice D-2 e D-4 in altri tre
  punti:
  * **la creazione pretende il BA su ogni DDT** — `ddt_service.crea_ddt` (`E_DDT_VALIDAZIONE`,
    «Cliente obbligatorio»): dall'API non nasce un trasferimento, un conto lavoro o una riparazione
    senza BA, cioe' proprio i casi che D-2 lascia senza cliente. Col modello di oggi l'obbligo e' un
    motivo d'emissione che decide la causale, e lo dice il DB;
  * **il destinatario si deriva dal BA in Python** (`repo.get_soggetto_ruolo_id_by_ba`): dal `-85` lo
    fa `trgfn_ddt_normalize` (punto 2-bis). E' la stessa regola su due livelli: quella in Python va
    ritirata;
  * **la whitelist `UPDATE_KEYS_DDT` e' rovesciata**: non contiene `billing_account_id` (quindi la
    scelta del BA in bozza non arriva mai al DB, anche senza il guard) e contiene `utility_id`, che ora
    e' una copia del BA (in bozza: 23514 dal CHECK senza BA, 23503 dalla FK con un BA diverso). Va
    dentro il BA, fuori la utility; il destinatario resta fuori (col BA lo scrive il normalize, senza
    BA e' da decidere — §10.2, domanda 1).

### 9.7 Resta nel giro (DB)

* ✅ i fixture ⏳ del §9.5: verdi su dbdev nella corsa del 2026-10-10 (§10.5);
* ✅ doc `manual/`: tolta la frase sulla «continuita'» dal §7.3 di `istanze_utilities` (D-7, punto 3),
  insieme alla riga «1:1 tra istanza e cliente» superata da R-8; cancellata
  `vendite/manual/trgfn_ddt_guard_causale_immutabile.md` (funzione ritirata). ⏳ Pagine per il BB nuovo
  e i due guard D-6.

**Terza corsa (2026-10-09 notte), sei rossi:**

* `test-esecutivi-ba-coppia-v1` test 1: confrontava i nomi con `regclass::text`, che dipende dal
  `search_path` (come app esce `clienti`, non `anagrafiche.clienti`): ora schema e nome dal catalogo.
* `test-ddt-causale-immutabile-v1`, `test-ddt-componenti-senza-prezzo-v1`: cliente = «il primo
  `soggetti_ruoli`» (forma `SELECT … INTO v_sr`, sfuggita al censimento) accanto a un BA preso a parte;
  l'eccezione del fixture la inghiottiva e il test 1 diceva «fixture non costruita». Ora il cliente si
  fabbrica.
* `test-fn-list-ordini-da-pushare-v3`: ruolo legato a `push_ba_id` nei cinque ordini.
* `test-ordini-guard-transizione-v1`: ordini col BA NULL «per saltare il guard»; ora cliente fabbricato.
  Lo slot F copiava la commessa dalla prima del database (altro cliente, altro emittente): ora la
  commessa e' quella del cliente dell'ordine.
* Provati sullo scratch **come app**: 5/5, 30/30, 8/8, 18/18; il test dei kit sullo scratch non ha un
  composito (0 contro 16 su dbdev), la `v3` non ha un BA pushabile (uguale prima e dopo).
* ⏳ `test-ordini-riepilogo-iva-totali`: verde sullo scratch come app (18/18), rosso su dbdev — serve la
  riga `not ok` della corsa. ⏳ Ancora da vedere (§10.5).

**Baseline CI su `zeroerp_ci` (2026-10-10), cinque rossi** — riprodotti come app sullo scratch:

* `script/test-fn-available-actions-ordine-v1`, `-offerta-v1`: ordini col BA NULL; ora col BA del cliente
  fabbricato (l'offerta ce l'aveva gia', `tmp_aa_cli`); il ruolo dell'ordine pushabile e' quello del suo BA.
  10/10 e 19/19.
* `script/test-guard-emittente-senza-utente`: gli ordini erano senza BA «per lasciare in prova solo il
  guard di scope». Ora cliente fabbricato col BA dell'emittente dell'operatore: il guard emittente <-> BA
  e' soddisfatto e resta in prova lo scope (test 3-5, 9-10). ⚠️ Il test 6 (emittente ALTRUI) passa su un
  **DDT senza BA**: su un ordine, che il BA ce l'ha sempre, parlerebbe prima il guard emittente <-> BA
  (`b` < `s`) e il test sarebbe verde per la ragione sbagliata. 10/10 (il 6 salta sullo scratch: come app
  non vede un secondo emittente).
* `script/test-fn-available-actions-ddt-reason-catch-all-v1` test 17: costruiva `DDT_SENZA_BA` con una
  VENDITA **emessa** senza BA, che D-2 vieta. Il ramo resta raggiungibile **in bozza** (rank 2 non
  scatta, la 3 precede la 5): la bolla ora resta in bozza. 17/17.
* `dbops/test-fn-non-editable-fields-conditional`: non riprodotto — 4/4 come app e da owner. Verifica i
  flag di distinta degli articoli, nulla di questo giro: da ricontrollare alla prossima corsa.
  ✅ **Spiegato il 2026-10-10**: e' rosso solo col runner a fuso ostile del T-5, nella finestra in cui
  il giorno della sessione non e' quello aziendale. Le regole di `dbops.lock_columns_conditional` sugli
  articoli chiedevano `CURRENT_DATE`; corrette da `80_data/changelog/20261010-01` del cantiere del fuso
  aziendale (brief-be-db-fe-un-solo-fuso-aziendale §8.2), applicato col migrate del §10.5.

**Ultimi due (2026-10-10).** `script/test-fn-available-actions-ordine-v2` (forma di `v3`, sfuggita: ruolo
scelto a parte da `push_ba_id` in tre ordini, un quarto col BA NULL) e
`script/test-seed-stati-doc-ordini-evaso-v1` (ordine col BA NULL): corretti come gli altri. Un censimento
su tutto `db/pgtap` non trova piu' ordini col BA NULL ne' la forma `r.soggetto_ruolo_id, r.push_ba_id`.
⚠️ Restano rossi per ragioni gia' in baseline, non di questo giro: `ordine-v2` test 1 sullo scratch (nessun
BA da push nei dati); `ordini-evaso` test 4 (matrice delle transizioni) e 6, che si aspetta il motivo
`ORDINE_GIA_EVASO` che la capability non produce piu' dal fix dell'orfano (e col BA vero quell'ordine e'
proprio un orfano pushabile). Entrambi i file sono gia' in `baseline-rossi*.tsv`.
✅ Verdi (o rossi solo per le ragioni gia' in baseline) nella corsa del 2026-10-10 (§10.5).

### 9.8 L'emittente dei documenti si sceglie solo in bozza (Tid, 2026-10-09)

**La domanda di Tid:** «perche' sulla tabella ordini si puo' cambiare l'emittente? da quando?». Risposta:
da sempre — nessuno l'aveva mai bloccato. Nel registro dei lock `emittente_fiscale_id` c'era solo sul
**preventivo** (dal 2026-05-01); il 2026-06-05 (`20260605-05`) era nato anzi un trigger che ricalcolava i
totali dell'ordine **dopo** un cambio di emittente: gestiva l'effetto invece di vietare la causa. In
pratica il cambio era gia' chiuso per conseguenza (backend che non lo espone, guard di perimetro,
guard emittente <-> BA), tranne che sull'ordine senza BA — che D-1 ha tolto — e sui DDT senza BA, dove
fuori bozza si cambiava davvero.

**Decisione (punti 1, 2, 3):** bloccato in modo dichiarato su ordine, DDT, reso, offerta e contratto.

| # | Cosa |
| --- | --- |
| `-86` | ordini: `trg_ordini_a05_lock_fuori_bozza_upd` (emittente) |
| `-87`, `-88` | ddt, resi: trigger del BB **rimontati** con l'emittente in piu' |
| `-89` | ritirati `trg_ordini_z90_ricalcola_totali_upd` e `vendite.trgfn_ordini_ricalcola_totali` |
| `-90`, `-91` | offerte (stato bozza `BOZZA`), contratti: montaggio nuovo |
| `80_data` | codice `E_DOC_EMITTENTE_FUORI_BOZZA` (CONFLITTO_STATO, id 1236), uno per tutti |

* **Fuori bozza, non assoluto**: sull'offerta in bozza il backend cambia cliente ed emittente insieme
  (`offerte_service.UPDATE_KEYS_OFFERTA`), ed e' legittimo; in bozza, col BA, l'emittente lo lega il
  guard emittente <-> BA. Stesso BB del §9.3 punto 1, stesso stato VECCHIO.
* **Codice nuovo**, non `E_EMITTENTE_NON_MODIFICABILE`: quello e' il codice dell'associazione
  operatore <-> emittente, e la sua frase dice «L'emittente fiscale di un operatore e' immutabile…».
  ⚠️ **Difetto trovato, non corretto qui:** il lock del **preventivo** usa proprio quel codice, quindi
  chi prova a cambiare l'emittente di un preventivo legge una frase che parla di operatori. ✅ Chiuso
  dal §9.9 (Tid: il preventivo passa sul BB fuori bozza, col codice nuovo).
* pgTAP: `test-esecutivi-ba-coppia-v1` + test 28 e 29 (29/29 su `zeroerp_ci`); in
  `test-ordini-riepilogo-iva-totali` il test 5 verifica che il trigger ritirato non ci sia e il 15 il
  montaggio del lock (18/18). Nessun pgTAP cambia l'emittente di un documento (censimento statico).
* doc: cancellata `vendite/manual/trgfn_ordini_ricalcola_totali.md`, aggiornata
  `fn_ricalcola_totali_ordine.md`.
* BE: codice nuovo con policy e frase di ripiego; l'emittente dell'offerta resta modificabile solo in bozza.

### 9.9 Anche il preventivo: emittente fuori bozza (Tid, 2026-10-09)

* `-92`: `trg_preventivi_a05_lock_fuori_bozza_upd` sul BB, codice `E_DOC_EMITTENTE_FUORI_BOZZA`.
* `automation_lock_columns`: la riga `vendite.preventivi.emittente_fiscale_id` si **spegne** (`enabled = f`,
  nota datata col testo di prima, come `ddt.numero`). La convergenza del `90_end` rigenera
  `trg_preventivi_a10_lock_columns_upd` col solo `numero` — provato: dopo la convergenza l'emittente non
  e' piu' fra i suoi argomenti.
* ⚠️ **Il preventivo si allenta in bozza**: prima l'emittente era bloccato dalla nascita, ora in bozza si
  cambia, legato al BA dal guard emittente <-> BA (il BA del preventivo e' NOT NULL). E' la stessa regola
  degli altri sei documenti.
* Prove su `zeroerp_ci` (da owner, sopra `-62…-85` gia' applicati): `test-esecutivi-ba-coppia-v1` 30/30
  (test 30 nuovo; prima 27/30), `test-ordini-riepilogo-iva-totali` 18/18,
  `test-user-emittenti-fiscali-immutable` 3/3 (il codice dell'operatore resta suo),
  `test-lock-columns-convergenza` 22/22 prima e dopo.

## 10. Verifica incrociata e domande aperte (2026-10-10)

### 10.1 Altri cantieri: nessuno ha riscritto cio' che questo brief tocca

Controllato il 2026-10-10, prima di aggiornare lo stato:

* **Corpi riscritti, contro la versione precedente piu' recente** (fra tutti i changeSet): ogni
  funzione di questo giro parte dall'ultima versione e **aggiunge** soltanto, tranne le righe ritirate
  di proposito (il punto «immutabile fuori bozza» dei due guard del magazzino, la seconda fonte del BA
  in `fn_ddt_push_diagnosi`). ⚠️ Lo stesso giorno il cantiere del fuso aziendale (`20261009-50`) aveva
  riscritto `trgfn_ordini_normalize` e `trgfn_ddt_normalize`: `-84` e `-85` partono dalla sua versione
  (`script.fn_data_operativa()`, non `CURRENT_DATE`), quindi nessuna regressione.
* **Branch:** i commit di `Tito-dev` non ancora in `dev/db-tid` sono del fuso aziendale lato BE
  (`fn_data_operativa` nei test Django): nessuno tocca i service di ordine, DDT o reso.
* **Helper pgTAP:** `dbops.fn_pgtap_crea_ordine` prende BA e ruolo dalla stessa riga del mondo,
  `dbops.fn_pgtap_crea_ddt` ricava la utility dal BA: coerenti con le FK nuove.
* **Brief aperti:** i lotti 3 e 3-bis del magazzino nominano `trgfn_ddt_guard_causale_immutabile` e i
  codici `E_*_MAGAZZINO_IMMUTABILE`, ma come storia (lato DB chiuso): da qui in poi la regola sta nel BB
  del §9.3 punto 1, con gli stessi codici.
* **dbdev:** 31 changeSet `EXECUTED` (intestazione); `richiede_cliente` 4 si' e 4 no; le sei righe di
  lock nuove attive, e quella dell'emittente del preventivo spenta (§9.9).

### 10.2 Domande aperte per Tid

Ciascuna con la proposta del team DB. Le si chiude una alla volta.

1. **Il destinatario di una bolla senza cliente si blocca dopo l'emissione?** (§9.3 punto 2) Oggi si':
   fuori bozza il destinatario e' bloccato anche su trasferimento, conto lavoro e riparazione.
   Proposta: lasciarlo bloccato. ✅ **Tid, 2026-10-10: bloccato.** La bolla emessa e' un foglio gia'
   consegnato: se il destinatario e' sbagliato si annulla e se ne fa una nuova. Il montaggio di `-71`
   (rimontato da `-87`) resta com'e'.
2. **La regola «la utility (e il destinatario) si copia dal BA se manca» e' scritta in tre posti**
   (`trgfn_clienti_sync_utility_from_ba`, `trgfn_ordini_normalize` punto 3, `trgfn_ddt_normalize`
   punto 2-bis; la quarta copia in Python, §9.6, va ritirata). Regola del 2: estrarre un BB o lasciare
   le tre copie? Proposta: un BB che legge dal BA ruolo e utility, adottato dai tre trigger.
   ✅ **Tid, 2026-10-10: building block, in questo giro.** Le tre copie gia' divergono: sul cliente un
   valore diverso dal BA esce con un codice parlante (`E_CLIENTE_UTILITY_MISMATCH_BA`), su ordine e DDT
   col 23503 della FK. Il BB dice una sola cosa — le copie del documento sono quelle del suo BA: le
   scrive se mancano, rifiuta con un codice se dissentono — e i tre trigger lo chiamano; le copie si
   ritirano nello stesso giro. Forma (funzione chiamata dai normalize o trigger parametrico come il
   lock fuori bozza) da scegliere scrivendolo.
3. **I guard D-6 non vedono la sorgente e lasciano passare.** `trgfn_ddt_guard_cliente_sorgente` e
   `trgfn_resi_guard_cliente_ddt` leggono ordine, reso e DDT come INVOKER: se la RLS nasconde la
   sorgente, non confrontano ed escono senza errore. ~~Proposta: il guard emittente <-> BA copre gia'
   il caso (sorgente invisibile = altro emittente); scriverlo nei COMMENT e in un pgTAP che lo prova,
   invece di passare a SECURITY DEFINER.~~
   ⛔ **Ipotesi smentita il 2026-10-10** (trigger di `vendite.ddt` e `vendite.resi` letti su dbdev): il
   guard emittente <-> BA confronta l'emittente del DDT con quello del **suo** BA, non con quello della
   sorgente; e nessun guard controlla che la sorgente dichiarata (`sorgente_tipo_id`, `sorgente_uid`)
   sia dello stesso emittente. Un DDT di E1 col BA di E1 e come sorgente l'ordine di E2 (invisibile
   sotto RLS) passa tutti e tre i guard. La strada e' solo la scrittura diretta: il verbo
   `fn_genera_ddt_da_ordine` l'ordine lo deve vedere.
   Proposta nuova: **fail-closed** — sorgente di tipo ORDINE_VENDITA, RESO_VENDITA o DDT_VENDITA
   dichiarata e non trovata = errore (invisibile e inesistente rispondono uguale, come per i
   magazzini); una sorgente di un altro tipo resta fuori dal confronto.
   ✅ **Tid, 2026-10-10: bloccare.** Nei due guard D-6 il ramo «non trovata» diventa un errore; serve
   un codice (da scegliere: uno esistente sulla sorgente, se c'e', o uno nuovo registrato) e un pgTAP
   che costruisce la sorgente dell'altro emittente e la prova come app.
4. **Gli altri scostamenti del §9.3** (punti 1, 3, 4, 5, 7: BB invece del gemello, reso senza lock del
   BA, cliente bloccato su quattro colonne, guard del BA in fascia `_a20_`, normalize dell'ordine e
   filtro del push non toccati): da confermare in blocco. Proposta: confermare.
   ✅ **Tid, 2026-10-10: confermati tutti e cinque.**
5. **Due nomi** (minori): il BB segnala il montaggio errato con `E_DOC_RIGHE_LOCK_MONTAGGIO`, che parla
   di righe anche quando si monta sulla testata; e il BB sta nello schema `vendite`, non in
   `script`/`dbops` (come il gemello delle righe). ~~Proposta: codice rinominato in
   `E_DOC_LOCK_MONTAGGIO` per tutti e due i BB~~ — ⚠️ rivista il 2026-10-10 dopo il censimento dei
   consumatori: il codice e' nei due CSV, nella frase di ripiego del BE (`error_messages_fallback`:
   «Il controllo sulle righe del documento…», sbagliata quando parla la testata) e nelle policy
   generate. Rinominarlo vuol dire un codice nuovo, il vecchio ritirato e i due BB riscritti, per un
   errore TECNICO che esce solo da un montaggio sbagliato. Proposta: **codice invariato**, descrizione
   e frase (CSV e ripiego BE) riscritte per righe e testata; schema lasciato com'e', con l'eccezione
   scritta nel COMMENT del BB.
   ✅ **Tid, 2026-10-10: solo le frasi.** Codice invariato; descrizione e frase riscritte (CSV e
   ripiego BE); schema `vendite` con l'eccezione nel COMMENT.

### 10.4 Che cosa resta da fare (decisioni chiuse il 2026-10-10) — ⚠️ i punti DB 1, 2, 3, 5 e i pgTAP del 4 sono nel giro 2 (§11)

Nessuna modifica al codice e' stata fatta il 2026-10-10: solo questo brief e il registro.

* **DB:**
  1. il BB «copie dal BA» e i tre trigger che lo adottano, copie ritirate (domanda 2);
  2. il ramo «sorgente non trovata = errore» nei due guard D-6, col suo codice (domanda 3);
  3. descrizione e frase di `E_DOC_RIGHE_LOCK_MONTAGGIO` per righe e testata; eccezione dello schema
     nel COMMENT del BB (domanda 5);
  4. i cinque fixture del §9.5 (corretti nell'albero, da confermare con la corsa) e i pgTAP mancanti
     del §10.3;
  5. le pagine `manual/` del BB e dei due guard D-6 (§9.7).
* **Da Tid:** la riga `not ok` di `test-ordini-riepilogo-iva-totali` su dbdev, se resta rosso; la
  corsa pgTAP completa (adesso per i fixture corretti, poi dopo i punti 1–4).
* **BE/FE** (dopo la consegna DB): §7 e §9.6, compresi i tre punti di `ddt_service` aggiunti il
  2026-10-10, e la frase di ripiego del punto 3.

**Cosa serve da Tid, non da decidere:** la riga `not ok` di `test-ordini-riepilogo-iva-totali` su
dbdev (§9.7), e la corsa dei cinque fixture del §9.5, ora corretti nell'albero (§10.5).

### 10.3 Debito: che cosa resta qui e che cosa no

Fuori perimetro — all'archiviazione va in un **brief nuovo**, con la voce-rimando nel registro:

* le **sette copie** del guard emittente <-> BA (ordini, DDT, resi, preventivi, offerte, contratti,
  commesse), annotate nel §5.5: regola del 2, un BB parametrico. ➡️ **Brief aperto il 2026-10-10**:
  [brief-db-guard-emittente-ba-unico](brief-db-guard-emittente-ba-unico.md) (D22);
* la domanda generale del §8 sulle **altre** colonne di testata in fase chiusa. ➡️ **Brief aperto il
  2026-10-10**: [brief-db-testata-dopo-emissione](../work-done/brief-db-testata-dopo-emissione.md) (D26).

Dentro il giro:

* i buchi del pgTAP nuovo: lock dell'emittente su offerte, contratti, preventivi e resi;
  `fk_clienti_ba_cliente` su INSERT col ruolo di un altro soggetto; reso con BA NULL da un DDT senza
  BA (D-3, «NULL compreso»); BA tolto in bozza che toglie la utility; emissione di OMAGGIO e
  CAMPIONATURA senza BA. Questi si chiudono **in questo** giro, insieme ai fixture del §9.5.
  ✅ **Chiusi** dal giro 2 (§11.2, test 32-35 e 38), verdi nella corsa di Tid del 2026-10-10.

### 10.5 Stato del 2026-10-10, verificato su file e `databasechangelog`

* ✅ **Migrazione applicata, corsa pgTAP completa verde, nessuna regressione** (Tid, 2026-10-10).
  Copre i 31 changeSet `20261009-62…-92`, `20261010-01` e tutti i fixture corretti del §9.5 — compresi
  `test-ordini-riepilogo-iva-totali` e gli ultimi due (`script/test-fn-available-actions-ordine-v2`,
  `script/test-seed-stati-doc-ordini-evaso-v1`).
* Su dbdev e' entrato alle 00:20 `20261010-01` del cantiere del fuso aziendale
  (`dbops.lock_columns_conditional`, condizioni degli articoli dal giorno aziendale), con le
  convergenze `runAlways` (`RERAN`). Non tocca gli oggetti di questo brief.
* ⚠️ **Da guardare:** `script/test-fn-available-actions-ordine-v1` costruisce l'ordine «pushabile» con
  un BA **preso dai dati** (`fn_get_emittente_fiscale_pk` su un BA reale), non fabbricato: su un
  database ricostruito da zero (CI) quel caso puo' non nascere. Si guarda insieme ai pgTAP del §10.3.
* Le decisioni del 2026-10-10 (§10.2, domande 2, 3 e 5) **non sono ancora nel codice**: la corsa
  verde riguarda il giro gia' scritto. Il cantiere resta aperto sul §10.4.
  ⚠️ Superato poco dopo: le decisioni sono nel giro DB 2 (§11), scritto e provato, non applicato.

## 11. Giro DB 2 — consegna (team DB, 2026-10-10)

> ✅ **Applicato su dbdev, test verdi** (Tid, 2026-10-10: «migrazione applicata, test verdi»). Sotto,
> l'avviso scritto prima, lasciato come storia della prova.
>
> ⚠️ **Scritto e provato, NON applicato.** Prova: SQL estratto dagli YAML, preCondition comprese
> (eseguite nella stessa transazione, nell'ordine dei changeSet), righe nuove del catalogo e pgTAP in
> una transazione annullata su `zeroerp_ci`, da proprietario (`zeroerp`), con `SET CONSTRAINTS ALL
> DEFERRED` come Liquibase e `myapp.log_with_dblink = off`. Lo scratch era allo stesso punto di dbdev
> (giro 1 e `20261010-01`). Il passaggio su dbdev e la corsa pgTAP restano di Tid.
> Numerazione `-02…-07` (Tid: «in sequenza, da -02»); `-01` e' del cantiere del fuso aziendale.

### 11.1 I changeSet

| # | Cosa | Decisione |
| --- | --- | --- |
| `-02` | **BB nuovo** `script.fn_cliente_dal_billing_account(ba, ruolo, utility, documento, colonna_ruolo, tx_id)`: rende ruolo e utility del BA, scritti se mancano, `E_DOC_CLIENTE_DIVERSO_DA_BA` se dissentono; BA non trovato o invisibile `E_CODICE` | §10.2, domanda 2 |
| `-03` | `anagrafiche.trgfn_clienti_sync_utility_from_ba` adotta il BB (anche per il ruolo); esce il ramo `E_BILLING_ACCOUNT_UTILITY_NULL` (la utility del BA e' NOT NULL); resta il PDP | domanda 2 |
| `-04` | `vendite.trgfn_ordini_normalize` adotta il BB (INSERT, e UPDATE che tocca una delle tre colonne) | domanda 2 |
| `-05` | `vendite.trgfn_ddt_normalize` adotta il BB; il «quando» (INSERT, cambio in bozza, copia non toccata = NULL) resta suo | domanda 2 |
| `-06` | `vendite.trgfn_ddt_guard_cliente_sorgente`: ordine o reso sorgente non trovato = `E_DOC_SORGENTE_NON_TROVATA` | domanda 3 |
| `-07` | `vendite.trgfn_resi_guard_cliente_ddt`: DDT sorgente non trovato = `E_DOC_SORGENTE_NON_TROVATA` | domanda 3 |
| `80_data` | codici `E_DOC_CLIENTE_DIVERSO_DA_BA` (id 1237) e `E_DOC_SORGENTE_NON_TROVATA` (1238), tutti e due `DATO_ERRATO`; `E_DOC_RIGHE_LOCK_MONTAGGIO`: nota, causa e soluzione per righe **e** testata, codice invariato | domande 2, 3, 5 |

* **Forma del BB (domanda 2): funzione, non trigger.** Sul DDT le copie si risolvono dopo il
  normalize, che eredita il BA dall'ordine; fra `trg_ddt_normalize_ins_upd` e i guard `_z10_` non c'e'
  una fascia (la `_mXX_` delle linee guida girerebbe prima). Il BB dice **cosa**, il chiamante
  **quando**. Sede `script`, come chiede la regola del 2.
* **Il reso non adotta il BB**: le sue copie vengono dal DDT (`trgfn_resi_normalize`), non dal BA.
* **`E_CLIENTE_UTILITY_MISMATCH_BA` e `E_BILLING_ACCOUNT_UTILITY_NULL` restano a catalogo**: li
  solleva ancora `vendite.fn_get_or_create_commessa`, e altri.
* **Domanda 5:** l'eccezione dello schema (`vendite` e non `script`) sta nella pagina `manual/` nuova
  del BB di testata; la pagina del gemello delle righe non e' stata toccata.
* Le FK composte, e le loro mappe nel BE, restano: sono la rete sotto per chi scrivesse senza passare
  dai trigger.

### 11.2 pgTAP

`vendite/test-esecutivi-ba-coppia-v1`: da 30 a **39 test**.

* **Cambiati:** 5 e 9 non aspettano piu' il 23503 della FK, ma la frase del BB («il cliente non
  corrisponde al billing account»).
* **Nuovi:** 31 (ordine con un'altra utility), 32 (cliente col ruolo di un altro soggetto, il buco
  «INSERT» del §10.3), 33 (BA tolto in bozza: la utility se ne va, il destinatario resta), 34 (omaggio e
  campionatura senza BA), 35 (reso senza BA da un DDT di conto lavoro senza BA: D-3, «NULL compreso»),
  36 (DDT con un ordine sorgente che non esiste), 37 (reso spostato su un DDT che non esiste: su UPDATE
  parla solo questo guard), 38 (lock dell'emittente montato su offerte, contratti e resi), 39 (DDT di E1
  dall'ordine di E2, invisibile).
* ✅ **Verde come app nella corsa di Tid del 2026-10-10** (39/39), insieme ai quattro file che sullo
  scratch non giravano (§11.3).
* ⚠️ **Il 39 e' rosso da proprietario e verde come app, per costruzione**: da proprietario la RLS non
  c'e', l'ordine di E2 si vede e parla `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`. E' per ultimo perche' cambia
  contesto. **La conferma «come app» arriva solo dalla corsa di Tid.**
* Il lock dell'emittente su offerte, contratti e resi e' provato sul **montaggio** (38), non sul
  comportamento: il BB e' gia' provato sul comportamento su DDT e ordine (28, 29).

### 11.3 Prove (pre-apply, scratch `zeroerp_ci`, da proprietario)

* **preCondition:** `-02` 0 (atteso 0), `-03…-05` 1 (atteso 1), lette dentro la transazione dopo i
  changeSet precedenti.
* **`plpgsql_check`** sulle sei funzioni: nessuna segnalazione.
* **Catalogo:** id unici, ogni riga a 6 colonne; il controllo dei segnaposto segnala solo
  `E_BOM_IVA_DISCORDANTE` (`%s%%`, valido e preesistente). ⚠️ Trovato e corretto nella prova: la causa
  nuova di `E_DOC_RIGHE_LOCK_MONTAGGIO` conteneva una virgola in un campo senza virgolette, e la riga
  era passata a 7 colonne.
* **pgTAP nuovo:** **38/39 dopo** (rosso solo il 39, come dichiarato), **32/39 prima**: senza il giro 2
  sono rossi proprio 5, 9, 31, 32, 36, 37, 39. Il 33, il 34, il 35 e il 38 sono verdi anche prima:
  coprono comportamento del giro 1 che nessun test provava (i buchi del §10.3).
* **Regressione mirata**, 24 file, ognuno con e senza il giro 2 in testa nella sua transazione
  annullata: gli 11 pgTAP che inseriscono clienti, quelli di DDT da ordine, riconsegna, resi, push,
  transizioni d'ordine, satelliti RLS di DDT e resi, check d'emissione, causale immutabile, e i presidi
  `dbops/test-riferimenti-morti-v1`, `dbops/test-vw-codici-errore-motivo-nominato`,
  `script/test-catalogo-messaggi-errore-completo`. **Identici prima e dopo**, tranne il test nuovo.
* ⚠️ **Quattro di quei file sullo scratch non girano, prima come dopo**:
  `vendite/test-fn-genera-ddt-da-ordine-v1`, `vendite/test-fn-genera-ddt-riconsegna-eredita-v1`,
  `vendite/test-resi-motore-v1`, `vendite/test-fn-list-ddt-da-pushare-v1` si fermano al test 2
  («riferimenti minimi disponibili»): pescano i dati della macchina, e lo scratch non li ha. Sono i piu'
  vicini a questo giro: **la loro conferma e' la corsa di Tid su dbdev.**

### 11.4 Da Tid — ✅ fatto il 2026-10-10 (migrazione applicata, test verdi)

* il passaggio su dbdev di `-02…-07` e dei due CSV;
* la corsa pgTAP: in particolare `test-esecutivi-ba-coppia-v1` **come app** (39/39 atteso) e i quattro
  file del §11.3 che sullo scratch non girano.

### 11.5 Ricaduta BE (dopo il passaggio su dbdev)

* **Codici nuovi**, con policy e frase di ripiego: `E_DOC_CLIENTE_DIVERSO_DA_BA` (DATO_ERRATO; `campo`
  = `soggetto_ruolo_id`, `destinatario_soggetto_ruolo_id` o `utility_id`), `E_DOC_SORGENTE_NON_TROVATA`
  (DATO_ERRATO; `campo` = `sorgente_uid`).
* **Errori che cambiano strada**: ordine, DDT e cliente con ruolo o utility diversi dal BA non arrivano
  piu' col 23503 della FK (le mappe dei vincoli per nome restano, ma non sono piu' la strada normale);
  il cliente non solleva piu' `E_CLIENTE_UTILITY_MISMATCH_BA`.
* **Frase di ripiego di `E_DOC_RIGHE_LOCK_MONTAGGIO`** (`error_messages_fallback.py`): parla delle
  righe; dal giro 1 lo solleva anche il BB di testata. Va riscritta per tutti e due (domanda 5).
* Invariati i punti del §9.6 (`ddt_service`: creazione senza BA, destinatario derivato in Python,
  whitelist `UPDATE_KEYS_DDT`).

### 11.6 Agganci con altri brief

* [brief-db-codici-non-trovato-email-e-permessi](brief-db-codici-non-trovato-email-e-permessi.md): R-9
  (builder pgTAP fino al cliente) va scritto **dopo** questo giro, perche' `-03` cambia il trigger dei
  clienti; R-7 prende gli id dei messaggi da 1239. Annotato nel suo §13.2.

## 12. Giro BE/FE (sessione backend, 2026-10-10)

> ✅ **Fatto** il §7, il §9.6 e il §11.5. Decisioni di forma chieste a Tid prima di scrivere
> (2026-10-10): **campo destinatario** nel form del DDT, e **ritiro delle copie Python** sull'ordine.

### 12.1 Che cosa c'e'

| Dove | Che cosa |
| --- | --- |
| Catalogo | `error_policies_generated.py` rigenerato (dal DB allineato a `20261010-16`); ripieghi senza segnaposto per `E_DDT_CLIENTE_OBBLIGATORIO`, `E_DOC_CLIENTE_DIVERSO_DA_SORGENTE`, `E_DOC_CLIENTE_DIVERSO_DA_BA`, `E_DOC_SORGENTE_NON_TROVATA`, `E_DOC_EMITTENTE_FUORI_BOZZA`, `E_ISTANZA_SOGGETTO_IMMUTABILE`, `E_CLIENTE_FORNITURA_IMMUTABILE`; riscritte le frasi di `E_DDT_CLIENTE_IMMUTABILE`, `E_DDT_CAUSALE_IMMUTABILE`, `E_BA_ISTANZA_IMMUTABILE` e `E_DOC_RIGHE_LOCK_MONTAGGIO` (righe **e** testata, domanda 5) |
| `ddt_service` | BA facoltativo in creazione; ritirati la derivazione Python del destinatario (`get_soggetto_ruolo_id_by_ba`, tolta dai due repository) e il guard «cliente immutabile» anche in bozza. Whitelist: dentro `billing_account_id` e `destinatario_soggetto_ruolo_id` (anche in update), fuori `utility_id` (create e update). Senza BA il NOT NULL del destinatario lo dice il DB, col campo. I due id si coerciscono col BB `PayloadValidator` (400 col campo, non 500) |
| `ordini_service` | BA obbligatorio (validazione del payload, col campo); ruolo e utility fuori dalle whitelist (li scrive il BB); ritirata la copia Python del lock del BA: il BA arriva al DB, che risponde `E_ORD_CLIENTE_IMMUTABILE` (409). `crea_ordine_da_offerta` non passa piu' la utility |
| Mappe vincoli | `fk_ordini_ba_cliente`, `fk_ddt_ba_cliente`, `fk_resi_ba_cliente` → `E_DOC_CLIENTE_DIVERSO_DA_BA`; `chk_ddt_ba_utility_insieme`, `chk_resi_ba_utility_insieme` → `E_VENDITE_VALIDATION`; tutte col campo `billing_account_id` |
| Commenti «prospect / BA NULL» | riscritti in `_indirizzi_repo_mixin` (docstring e `LEFT JOIN`), `ordini_repository`, `ddt_repository`, `ordine_document_context_builder` |
| FE DDT | campo **Destinatario** (`SoggettoRuoloLookup`): senza cliente si sceglie ed e' obbligatorio, col cliente si spegne e mostra il cliente. Cliente modificabile in bozza; utility spenta col cliente (filtra solo la ricerca, non si salva); autosave della bozza da cliente **o** destinatario. Reason `vendite.ddt.azione_reason.cliente_mancante` (it/en) |
| FE ordine | utility spenta dopo la creazione e uguale a quella del BA scelto; non si manda piu' nei payload |
| `config_panel` | etichette delle colonne nuove `richiede_cliente` ed `entita_esistenza` (presidio `test_config_panel_registro_db`) |
| Doc | `api_ddt.md`, `api_ordini.md` |

### 12.2 Prove

* Suite backend 6107 test verdi senza DB; ruff pulito; mypy a cricchetto 0 rilievi nuovi.
* Sul DB vero (`ZEROERP_TEST_DB_E2E=1`): nuovo `vendite/tests/db/test_esecutivi_cliente_dal_ba_db.py`
  (3 test, dai verbi del service: DDT senza cliente → cliente in bozza → tolto; destinatario diverso
  dal BA rifiutato; ordine con ruolo e utility dal BA e BA bloccato). Riallineati
  `test_ddt_create_db` e `test_ordini_create_db`: non passano piu' le copie, e la rilettura prova che
  le scrive il DB.
* Frontend: vitest 765/765, eslint e oxlint puliti, build ok. ⚠️ **Non provato a video.**

### 12.3 Rimasto aperto

* ⚠️ **Due rossi sul DB vero che non sono di questo giro**: `test_error_policies_divergenza_db` e
  `test_ui_action_e_canale_campi` (promesse `highlight` di sei `*_EMITTENTE_BA_INCOERENTE`). Su
  dbdev e' stato applicato il 2026-10-10 alle 10:03 il giro DB di
  [brief-db-guard-emittente-ba-unico](brief-db-guard-emittente-ba-unico.md), che e' su
  `origin/dev/db-tid` ma non ancora in `dev/backend-tid`: il DB e' avanti rispetto a git, e le
  policy **non** si rigenerano finche' il commit non e' nel branch. Si chiudono col giro BE di quel
  brief.
  ✅ **Chiuso il 2026-10-10** dal giro BE di quel brief (commit `62811ab10`: `E_DOC_EMITTENTE_BA_INCOERENTE`
  al posto dei sei codici, policy rigenerata).
* ⚠️ **Da verificare (Tid)**: al cambio di cliente in bozza gli **indirizzi del documento** gia'
  assegnati (lo slot Consegna, auto-assegnato alla creazione dal ruolo del cliente) restano quelli
  del cliente di prima. Il guard di ownership del picker guarda il destinatario attuale, ma lo
  snapshot gia' scritto non si riallinea. Non l'ho toccato: se va riallineato, la sede e' il DB (o
  l'auto-assegnazione all'UPDATE del BA), e la domanda e' di modello.
  ➡️ **Deciso da Tid il 2026-10-10, passato a un brief nuovo**:
  [brief-db-indirizzi-documento-seguono-il-cliente](brief-db-indirizzi-documento-seguono-il-cliente.md)
  (D27). L'istruttoria ha trovato lo stesso buco su preventivo e offerta, e il gate d'emissione che
  non guarda l'origine dell'indirizzo. La regola va nel DB, e con lei l'auto-assegnazione dello slot
  di default.
