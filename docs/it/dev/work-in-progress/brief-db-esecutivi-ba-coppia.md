# Brief DB — Ordine, DDT e reso: il cliente come su preventivo, offerta e contratto

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB; poi BE/FE (§7).
> **Origine:** §7.5 di [brief-db-istanza-nasce-col-ba.md](brief-db-istanza-nasce-col-ba.md). Il suo R-2
> ha reso `billing_account_id` NOT NULL e legato alla coppia (istanza, utility) su preventivo,
> offerta e contratto. Chiudendo il lato BE/FE e' emerso che i documenti **esecutivi** di vendita
> (ordine, DDT, reso) sono rimasti fuori: e' la stessa asimmetria, un livello piu' in basso.
> **Stato:** 📝 **bozza** — cinque decisioni di Tid (§4) prima della forma.
> **Nel registro dei difetti DB:** voce **D21** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La regola

Un documento di vendita parla di **un cliente a grana fine**, cioe' di un billing account: la
fornitura (istanza, utility) di un ruolo CLIENTE. Su preventivo, offerta e contratto e' un vincolo
dal 2026-10-08; sulla fattura `billing_account_id` e' NOT NULL da prima. Ordine, DDT e reso stanno
in mezzo alla stessa catena — il preventivo diventa ordine, l'ordine diventa DDT, il DDT diventa
fattura o reso — e oggi sono gli unici anelli in cui il cliente puo' mancare o non coincidere con le
altre colonne della testata.

⭐ Il principio e' quello gia' scritto: *vendite = acquisti, e le asimmetrie si chiudono subito*.
Qui l'asimmetria e' **dentro** vendite, fra famiglie di documento.

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

`vendite.trgfn_ddt_normalize` eredita BA e utility dall'ordine sorgente (`COALESCE`, solo su
INSERT): il DDT nato da un ordine con BA lo prende. Un DDT **standalone** non eredita niente.

## 3. Perche' e' un difetto, sul modello

* **Un esecutivo fatturabile senza BA esce dalla fatturazione in silenzio.**
  `vendite.fn_list_ordini_da_pushare` e `vendite.fn_list_ddt_da_pushare` fanno una `JOIN`
  **interna** su `anagrafiche.billing_account`, e `vendite.fn_get_or_create_commessa` rifiuta un BA
  NULL. Un ordine o un DDT che si fattura e non ha BA non compare nella lista di push: nessun
  errore, una riga che manca. E' il difetto che non da' errore.
* **Le copie possono dissentire.** Un ordine col BA del cliente A e il `soggetto_ruolo_id` del
  cliente B, o col BA del GAS e `utility_id` dell'energia elettrica, oggi si scrive. Da li' in poi
  ogni lettore che sceglie una delle due colonne risponde in un modo, e quello che sceglie l'altra
  nell'altro: indirizzi del documento (il BE ancora l'ancora sul ruolo nativo, `_indirizzi_repo_mixin`),
  liste, stampe, fattura.
* **Il backend da' gia' per scontato il contrario.** Il docstring del BB
  `_indirizzi_repo_mixin` dice che gli esecutivi «hanno sempre un BA e l'istanza e' univoca da
  li'», e due righe sotto lo stesso file gestisce «l'ordine prospect con billing_account NULL».
  Le due frasi non possono essere vere insieme: la regola va scritta nel DB, e il BE la segue.
* **Il DDT e il reso cambiano cliente, l'ordine no.** L'ordine blocca BA e ruolo; DDT e reso no.
  Un DDT gia' emesso puo' cambiare cliente con un `UPDATE`.

⚠️ Nessuna di queste ragioni dipende da quante righe ci siano oggi in quello stato: valgono anche se
non ce n'e' nessuna (AGENTS.md, regola zero).

## 4. Decisioni per Tid

| # | Domanda | Proposta del BE |
| --- | --- | --- |
| **D-1** | L'**ordine** ha sempre il BA? | **Si'.** L'ordine e' gia' legato a un ruolo (`soggetto_ruolo_id` NOT NULL) e ne blocca il BA; nasce dal preventivo, che il BA lo ha sempre, o standalone su un cliente. Un ordine senza fornitura non si sa a chi si fattura |
| **D-2** | Il **DDT** ha sempre il BA, o ci sono DDT senza cliente per natura? | Da decidere sul dominio: la tabella ha `magazzino_arrivo_id` (il trasferimento fra magazzini) e `config.causali_trasporto.fatturabile`. Se un DDT di trasferimento o di conto lavorazione e' un DDT di vendita senza cliente, la regola e' «BA obbligatorio quando la causale e' fatturabile» (un CHECK non lo sa dire, serve un guard); altrimenti BA sempre, come l'ordine |
| **D-3** | Il **reso** ha sempre il BA? | **Si'**, se un reso e' sempre di un cliente (ritorna merce venduta, e genera la nota di credito). Se esistono resi senza cliente, stessa domanda di D-2 |
| **D-4** | Il **destinatario** di DDT e reso e' sempre il ruolo del BA, o puo' essere un altro soggetto (consegna a terzi)? | Se puo' essere un altro, il legame ruolo ↔ BA vale solo per l'ordine, e su DDT e reso il destinatario resta libero. Se no, la stessa FK dell'ordine |
| **D-5** | Le due copie (`utility_id`, ruolo di testata) si **legano** al BA o si **ritirano**? | Legarle, come R-2 sul preventivo: ritirarle costerebbe tutti i lettori (liste, filtri, indici `ix_ddt_vendita_dest_stato_data`, push), e la FK composta rende la copia innocua |

## 5. Forma proposta (la sceglie il team DB)

Lo stampo e' R-2 di `brief-db-istanza-nasce-col-ba` (§6.3):

* `billing_account_id` NOT NULL su `ordini` (D-1) e, secondo D-2 e D-3, su `ddt` e `resi`
  (oppure un guard legato alla causale);
* FK composta `(billing_account_id, utility_id)` → `billing_account (id, utility_id)`: serve un
  indice unico nuovo `(id, utility_id)` sul BA (quelli che ci sono contengono anche l'istanza, che
  questi documenti non hanno). Con `utility_id` NULL la FK non scatta (`MATCH SIMPLE`): se la
  utility deve esserci sempre, NOT NULL anche lei;
* FK composta `(billing_account_id, soggetto_ruolo_id)` → `billing_account (id, soggetto_ruolo_id)`
  sull'ordine, e su DDT e reso secondo D-4: altro indice unico `(id, soggetto_ruolo_id)`;
* il lock del BA su `ddt` e `resi` come sull'ordine (riga in `dbops.automation_lock_columns`), con
  il codice che il team DB ritiene giusto (`E_ORD_CLIENTE_IMMUTABILE` parla dell'ordine);
* i guard emittente ↔ BA (`trgfn_ordini_guard_emittente_ba`, `trgfn_ddt_guard_emittente_ba`,
  `trgfn_resi_guard_emittente_ba`) tengono l'uscita anticipata su NULL per la stessa ragione del
  preventivo (§6.3 del brief d'origine: il NOT NULL si controlla dopo i trigger BEFORE).

Da censire nel giro (non qui): i verbi che creano ordini, DDT e resi (`fn_push_preventivo_a_ordine`,
l'evasione ordine → DDT, la creazione del reso dal DDT) e i pgTAP che costruiscono questi documenti
senza BA — il brief d'origine ne ha trovati due giri dopo il primo censimento (§6.12.2, §6.13).

## 6. Prima dei vincoli

Come in R-5 del brief d'origine: NOT NULL e FK composte verificano anche le righe esistenti, quindi
le righe fuori regola si correggono **prima**, e ogni changeSet porta la `preCondition` sulle righe
che non passerebbero. Il modo (a mano o changeSet) si decide con Tid. Le righe da guardare:
esecutivi senza BA; `utility_id` diversa da quella del BA; ruolo di testata diverso dal ruolo del BA
(secondo D-4). ⛔ Il loro numero entra solo come fatto datato, mai come motivo.

## 7. Ricaduta BE/FE (dopo la consegna DB)

* Commenti e rami sul «prospect» / «BA NULL» da riscrivere o ritirare: `ordini_repository`
  (`_indirizzi_doc_sr_column`), `_indirizzi_repo_mixin` (docstring e `LEFT JOIN` sul BA),
  `ddt_repository`, `ordine_document_context_builder`.
* Form di ordine, DDT e reso: il BA diventa obbligatorio (o obbligatorio per causale, D-2).
* Nomi delle FK nuove nelle mappe dei vincoli dei service (`ordini_service`, `ddt_service`,
  `resi_service`), sul campo `billing_account_id`; codici nuovi con policy e frase di ripiego.

## 8. Fuori da questo brief

* **Il BA di un documento chiuso si riscrive** (§6.9 del brief d'origine): la domanda generale «quali
  colonne di testata si riscrivono in fase chiusa» e' sua, e resta da aprire. Qui si chiede solo il
  lock del BA che l'ordine ha gia'.
* **Acquisti**: ordini e DDT di acquisto parlano di un fornitore, non di un BA. Se il fornitore ha un
  analogo a grana fine (un ruolo con piu' rapporti), la stessa domanda andra' posta li'; oggi no.
