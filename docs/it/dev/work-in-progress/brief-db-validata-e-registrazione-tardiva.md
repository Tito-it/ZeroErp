# Brief DB — che cosa vuol dire VALIDATA, e il futuro delle righe che restano indietro

> **Cos'è.** Il seguito del **terzo collaudo in-app** del giro incassi (Tid,
> 2026-09-18, sulla distinta `DIS-PGTAPEF202-2026-0000001`). Quattro rilievi,
> e stavolta **uno è un buco del modello**, non solo di resa:
>
> - **§1 · «Registra» è acceso anche in BOZZA** — e il database lo rifiuta
>   (`E_CONTABILE_NON_REGISTRABILE`): un pulsante che finisce in errore;
> - **§2 · che cosa deve essere vero per VALIDARE** — oggi solo la quadratura
>   col dichiarato (quando c'è). Si valida con righe `DA_ABBINARE`;
> - **§3 · 🔴 le righe che restano indietro non hanno un futuro**: registrata la
>   distinta (`CHIUSA`), una `SOSPESA` o una `SCARTATA` sotto di lei **non entra
>   più in nessun conto** e non può più diventarlo — D3-a diceva «lascia lì il
>   resto», e il resto oggi non ha strada;
> - **§4 · i «Porta a» da ABBINATA** (`DA_ABBINARE`, `SOSPESA`) sono attivi su
>   una riga già abbinata — vengono dalla matrice (D14-a), e Tid li vuole fuori.
>
> **Sede.** Le **decisioni di dominio** (D20-a…e) stanno qui e sono riportate in
> sintesi nel brief madre
> ([brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis), che resta la sede unica. Il **piano DB** è qui (§4). Per BE e FE qui
> c'è **solo l'elenco di cosa fare** (§5, §6): il piano lo scrivono loro in
> [brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md).
>
> ⛔ **Niente misure come motivo.** Al 2026-09-18 su dev non c'è nessuna riga
> viva sotto una `CHIUSA` in uno stato diverso da `POSTATA`/`SCARTATA` (zero
> righe): non vuol dire che il caso non esista — il modello lo ammette, e basta
> una sospesa alla prima registrazione vera. Si progetta sul modello.
>
> **Stato:** 🔵 **scritto il 2026-09-18, in attesa del team DB.** BE e FE
> **aspettano** l'apply (`feedback_be_fe_attende_prerequisiti_db`). ⏳ Una
> decisione è **da confermare** da Tid prima di P-6: **D20-e** (§2.5).

---

## 0. In una pagina

| | Cosa | Dove |
| --- | --- | --- |
| **D20-a** | **VALIDATA = «ogni riga è stata guardata»**: entrando in `VALIDATA` nessuna riga attiva può essere in uno stato **non lavorato** (`DA_ABBINARE`, `IMPORTATA`). `ABBINATA`, `SOSPESA` e `SCARTATA` sono ammesse. La quadratura col dichiarato resta com'è (facoltativo sulla `MANUALE`, D12 — **confermato da Tid il 18/09**) | §2.1 · §4 P-1, P-3, P-4 |
| **D20-b** | **Il resto ha un futuro: la registrazione TARDIVA per riga.** Una `SOSPESA` sotto una distinta **registrata** si abbina **e si registra nello stesso gesto**: una madre sua, riga → `POSTATA` col suo movimento, distinta che resta `CHIUSA`, quadratura intatta (la riga era già contata). La 4ª mossa del guard di riga resta vera — sotto una chiusa nessuna riga «pronta e mai registrata» — perché non esiste più il momento in cui sta pronta ad aspettare | §2.2 · §4 P-5 |
| **D20-c** | **`SCARTATA` tiene un significato solo: «non è nostra».** Resta nella distinta (è lei la traccia, e conta nella quadratura: «quel denaro è arrivato») ma **esce dal lavoro**: nascosta di default nel drawer, mai in nessuna coda. Reversibile (`→ SOSPESA`) anche a distinta chiusa; se poi risulta nostra, si registra tardiva. ⛔ **Non si toglie dalla distinta** (§2.3: romperebbe la quadratura, e una `CHIUSA` è immutabile) | §2.3 · §6 |
| **D20-d** | **«Registrabile» sta nel catalogo**, non nel letterale `'VALIDATA'` della madre: bandiera `is_registrabile` su `vendite_contabili_stati`, letta dalla madre e portata nel dettaglio — così «Registra» si spegne **col motivo** invece di finire in 409 | §2.4 · §4 P-2 |
| **D20-e** ⏳ | *(da confermare da Tid)* Dalla matrice di riga escono `ABBINATA → DA_ABBINARE` e `ABBINATA → SOSPESA`: su una riga abbinata si **ri-abbina** (il dialogo si apre già sulla destinazione, FE del 18/09), non si «sgancia». ⚠️ Conseguenza: una abbinata non si parcheggia — in `BOZZA` si elimina, sotto `VALIDATA` si torna in bozza | §2.5 · §4 P-6 |
| **BE** | `stato_is_registrabile` + `can_validare`/`validazione_blocco_*` nel dettaglio; `righe_per_stato`; `POST /righe/{id}/registra/` (la tardiva, col doppio tempo); le code con le azioni di riga; scartate fuori di default + `scartate_count` | §5 |
| **FE** | «Porta a VALIDATA» con i numeri (dialog, non confirm generico) e spento col motivo; «Registra» spento col motivo; `Mostra scartate (N)`; «di cui non nostre» in quadratura; le code con Abbina / **Abbina e registra** / Sospendi / Scarta / Riprendi | §6 |

---

## 1. Cosa dice il modello, verificato

| Domanda | Risposta del modello | Dove è scritto |
| --- | --- | --- |
| Da dove si registra? | **Solo da `VALIDATA`** — guard 3 della madre: «da BOZZA la distinta potrebbe cambiare mentre la si registra». Il nome dello stato è un **letterale** nella funzione | [fn_posta_contabile](/dbzero/pagamenti/manual/fn_posta_contabile) §3 |
| Che cosa si controlla entrando in `VALIDATA`? | **Solo** la quadratura: Σ righe attive (`SCARTATA` compresa) = `importo_dichiarato`, **se** il dichiarato c'è. Sugli stati delle righe **niente** | [guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) |
| Il dichiarato quando c'è? | obbligatorio sull'`AUTOMATICA` (`chk_vendite_contabili_automatica_dichiara`), vietato sulla `GENERATA`, **facoltativo sulla `MANUALE`** | D12, CHECK sulla testata |
| Che cosa succede a «il resto» alla registrazione? | La madre posta le `is_postabile` (`ABBINATA`), **conta** le altre (`righe_saltate`) e porta la distinta a `CHIUSA` — la chiusura è una conseguenza (22/08) | fn_posta_contabile §5-§11 |
| E dopo, sotto la `CHIUSA`? | La **4ª mossa** rifiuta a qualunque riga di entrare in uno stato `is_postabile`; la correzione **salta** le non postate; **nessun verbo** sposta una riga in un'altra distinta (`_CAMPI_RIGA_PATCH` non porta `contabile_id`). ⇒ una `SOSPESA` o una `SCARTATA` lì sotto può solo restare, o oscillare fra i due stati | [guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale), [fn_crea_distinta_correzione](/dbzero/pagamenti/manual/fn_crea_distinta_correzione), `pagamenti_service.py` |
| Che cos'è `SCARTATA`? | *«non è nostra»*: denaro **arrivato** che non ci appartiene. Conta nella quadratura. **Non finale** dal 21/08 (S1-21): `SCARTATA → SOSPESA` per riprenderla in mano | D14-a, D12-e, [matrice](/dbzero/pagamenti/tabelle/transizioni_stati_contabile_riga) |
| `DA_ABBINARE` vs `SOSPESA`? | *«la differenza è **chi ha guardato** — lavoro non ancora fatto contro lavoro fatto che ha trovato un ostacolo: due code per due persone diverse»* | brief madre §2-bis D14 (f) |
| La capienza della rata quando si verifica? | **Solo** se la riga occupa spazio davvero: attiva e in uno stato `is_postabile`. *«Il posting non lo incontra: quando la riga passa a POSTATA il suo movimento è già scritto»* | [guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) |
| Un guard può distinguere «lo chiede una persona» da «lo fa una madre»? | Sì, per **GUC transazionale** (`set_config(…, true)`): il precedente è `app.cessazione_automatica`, letto da `trgfn_contratti_guard_transizione_stato` | [fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) |

⭐ **Il buco è la somma di tre decisioni giuste prese in momenti diversi**: D3-a
(9/08, «registra il pronto, lascia lì il resto»), la chiusura come conseguenza
del posting (22/08) e la 4ª mossa (22/08, lotto 4). Ognuna regge da sola;
insieme lasciano il resto senza uscita. ⚠️ La 4ª mossa lo sapeva —
*«sotto possono restare righe DA_ABBINARE … dire che cosa ne è stato di quel
denaro deve restare l'ultima cosa che si può fare»* — e ha scelto di far
restare **solo** «sospendere o scartare». Per il denaro **nostro** non basta.

---

## 2. Le decisioni

### 2.1 ✅ D20-a — VALIDATA = «ogni riga è stata guardata»

**Cosa si fa.** Entrando in `VALIDATA` una distinta non può avere righe attive in
uno stato **non lavorato**. Quali stati siano «non lavorati» lo dice il
**catalogo** (bandiera `lavorata`, P-1), non un elenco nel guard: `IMPORTATA` e
`DA_ABBINARE` sono `false`; `ABBINATA`, `SOSPESA`, `SCARTATA`, `POSTATA` sono
`true`. La regola vive in una `script.fn_check_contabile_validabile` (P-3), che
il guard chiama e che il dettaglio espone.

**Perché.** `VALIDATA` è *«ho finito di inserire»* (D14-a-bis); una riga che
nessuno ha guardato è lavoro **non finito**. E dopo la registrazione quella riga
non avrebbe più nessuno che la guardi (§1). La sospesa invece **è** stata
guardata: ha un motivo, sta nella coda «Sospese», e con D20-b ha un futuro.

**Cosa NON cambia.** Il dichiarato resta **facoltativo sulla MANUALE** (D12,
confermato da Tid il 18/09): sulla manuale senza dichiarato la quadratura *non
si applica* — e il drawer lo dice già («Nessun importo dichiarato»). La
quadratura, quando si applica, **entra nella stessa check** come secondo
motivo: una sede sola, e il guard smette di calcolarla in proprio.

⚠️ **Effetto sulle prove esistenti**: ogni pgTAP che oggi porta a `VALIDATA` una
distinta con righe `DA_ABBINARE` (la fixture di «niente da postare», le
`righe_saltate`) va adeguato: `SOSPESA` al posto di `DA_ABBINARE`. Non è una
regressione, è la regola che entra.

### 2.2 ✅ D20-b — La registrazione tardiva per riga

**Cosa si fa.** Una madre, `pagamenti.fn_posta_riga_tardiva` (P-5): prende una
riga **`SOSPESA`** sotto una distinta **registrata** (`CHIUSA` con
`data_conferma`), la abbina (fattura, cliente, rata facoltativa, forzatura a due
tempi) e la registra — movimento scritto, riga a `POSTATA`, distinta **che
resta `CHIUSA`** e non tocca `data_conferma`/`user_conferma` (la conferma è
l'atto della prima registrazione; chi ha registrato tardi sta sull'audit del
movimento).

**Perché così e non altrimenti.**

| Alternativa | Perché no |
| --- | --- |
| **Ricreare la riga in una distinta di recupero** (proposta di Tid, 18/09) | raddoppia l'euro — una scartata nel giorno 1, una nuova nel giorno 30 — e vuole un legame più uno stato sulla vecchia per non contarla due volte. È la forma della **correzione**, giusta là perché esiste un *movimento* da rovesciare; qui un movimento non c'è ancora: la riga stessa si può postare |
| **Allentare la 4ª mossa** (ABBINATA ammessa sotto CHIUSA, poi «Registra riga») | riapre esattamente il caso che la mossa chiude — una riga «in lavorazione» nei saldi che aspetta qualcuno. Due gesti dove ne basta uno |
| **`SOSPESA → POSTATA` diretta nella matrice** | salta il guard della **capienza**, che gira solo entrando in uno stato `is_postabile` (§1): il doppio tempo non scatterebbe mai sulla tardiva, e la regola di capienza avrebbe una seconda copia dentro la madre |

⭐ **Quindi la madre passa da `ABBINATA`** — così girano *tutti* i guard che
girano sull'abbinamento normale (transizione, dati, rata col doppio tempo,
scope) — e alla 4ª mossa **si presenta**: GUC transazionale
`app.registrazione_tardiva_riga_id = <id>`, che il guard legge e lascia passare
**solo quella riga, solo in quella transazione**. Precedente:
`app.cessazione_automatica`. Poi il movimento, poi `POSTATA`: gli stessi due
statement separati della madre del posting (RLS: padre e figlio nella stessa
snapshot non si vedono), un `UPDATE … WHERE id = <id>` e non un predicato.

**Chi la chiama**: solo il verbo BE `POST /righe/{id}/registra/` (§5), dalla
coda «Sospese» e dal drawer di una distinta chiusa. ⛔ Non un job: la tardiva
è una **decisione** di chi ha identificato il denaro.

### 2.3 ✅ D20-c — SCARTATA: un significato, fuori dal lavoro, dentro la quadratura

**Cosa si fa.** Niente a DB oltre la bandiera di P-1. `SCARTATA` resta *«non è
nostra»* e resta **nella distinta**. Cambia la **resa** (§6): nel drawer le
scartate sono nascoste di default con `Mostra scartate (N)` (il BB
`ToggleNascoste`, come le archiviate delle code) e il pannello di quadratura
dice *dichiarato · righe · di cui non nostre*; nelle code non compaiono mai.

**Perché non «togliere la riga dalla distinta»** (l'idea di Tid del 18/09,
scartata insieme):

- la quadratura **conta le scartate apposta** — *«quel denaro è arrivato»*
  (D12-e). Tolta la riga, la distinta di quel giorno non quadra più con la
  banca;
- una `CHIUSA` è **immutabile**: dopo la registrazione non si toglie niente,
  quindi non si potrebbe più scartare una sospesa — è il «va pensato bene» che
  Tid ha visto da sé.

⭐ **Dopo la chiusura `SOSPESA ↔ SCARTATA` restano possibili** già oggi:
nessuna delle due entra in uno stato `is_postabile`, e la 4ª mossa blocca solo
quello. Non serve toccare niente.

### 2.4 ✅ D20-d — «Registrabile» sta nel catalogo

**Cosa si fa.** `vendite_contabili_stati.is_registrabile` (P-2): `true` sulla
sola `VALIDATA`. La madre del posting legge la bandiera al posto del letterale;
il dettaglio la porta (`stato_is_registrabile`); «Registra» si spegne col
motivo. ⚠️ È la stessa scelta di `is_postabile` sulle righe e di `is_final`
sulle testate: *«la domanda si fa al catalogo, non a un elenco scritto nel
guard»* (commento della 4ª mossa).

**Perché una bandiera e non una `fn_check`.** Il motivo per cui non si registra
è **uno** e statico — lo stato — e sotto `VALIDATA` il lavoro non finito non
esiste più (D20-a). Una check con un motivo solo sarebbe una macchina per una
riga.

### 2.5 ⏳ D20-e — I «Porta a» da ABBINATA (da confermare)

**Richiesta di Tid (18/09)**: su una riga abbinata, «Porta a Da abbinare» e
«Porta a Sospesa» devono essere attivi *«solo se la riga non è abbinata»*. Le
due voci vengono dalla **matrice** (D14-a: `ABBINATA → DA_ABBINARE` è il
«ri-abbinamento» del collaudo §3.1), quindi la sede del cambiamento è la
matrice (P-6), non un `if` nel drawer.

**Che cosa cambia se entra.** Il ri-abbinamento diventa «Abbina» sulla riga già
abbinata — il dialogo dal 18/09 si apre già sulla destinazione e resta spento
finché non si cambia documento o rata. Una abbinata **non si parcheggia** più:
in `BOZZA` si elimina; sotto `VALIDATA` (contenuto fermo) si torna in bozza e
si elimina. Con D20-a, `ABBINATA → SOSPESA` non serve nemmeno per «tenere fuori
una riga dalla registrazione»: si ri-abbina o si torna in bozza.

⏳ **Tid conferma** (a) entrambe fuori — la richiesta com'è; oppure (b) fuori
solo `ABBINATA → DA_ABBINARE`, tenendo la sospensione di una abbinata. P-6 si
scrive dopo la risposta; il resto del brief non dipende da lei.

---

## 3. Cosa NON cambia, e va tenuto fermo

| | Resta | Perché |
| --- | --- | --- |
| **La madre del posting** | posta le `is_postabile`, conta le saltate, chiude | D20-a cambia *che cosa* può restare indietro (solo sospese e scartate), non il posting |
| **`STATI_*_RICHIEDIBILI`** nel BE | invariati; `POSTATA` non si chiede | la tardiva è un **verbo**, non una transizione richiesta |
| **`contenuto_modificabile`** | copia dichiarata com'è (residuo 5 del brief D16-D18) | non è questo giro |
| **`meta.manuale` sulle matrici** | `{"manuale": false}` ovunque | residuo 4 del brief D16-D18, decisione a parte |
| **La correzione** | salta le non postate e le conta | con D20-a e D20-b le non postate sotto una `CHIUSA` sono solo sospese e scartate, e la tardiva è la loro strada — non la correzione |
| **Il dichiarato** | facoltativo sulla `MANUALE` | Tid, 18/09: «lasciamo com'è ora» |

---

## 4. Il piano DB

> ⚠️ Prove in `BEGIN … ROLLBACK` come per i lotti precedenti; **l'apply è di
> Tid**. Un changeSet per file, `00_schema`/`20_code` senza `runOnChange`,
> `80_data` dai CSV. I codici nuovi nascono **a catalogo con la classe**, e il
> BE rigenera le policy + scrive i ripieghi (§5).

| Passo | Cosa | Note |
| --- | --- | --- |
| **P-0** | Cercare i pgTAP che portano a `VALIDATA` con righe `DA_ABBINARE` e i pgTAP della 4ª mossa | sono le fixture che P-3 e P-5 cambiano; si adeguano nello stesso lotto (`SOSPESA` al posto di `DA_ABBINARE`) |
| **P-1** | `vendite_contabili_righe_stati.lavorata boolean NOT NULL DEFAULT false` + colonna nel CSV: `false` su `IMPORTATA`, `DA_ABBINARE`; `true` sugli altri (`STORNATA` compresa, è ritirata) | ⚠️ I mirror del CSV sono `runOnChange` + `ANY`: la colonna nuova va aggiunta **prima** nella `00_schema`, poi al CSV. Scheda manuale del catalogo: che cosa vuol dire «lavorata» |
| **P-2** | `vendite_contabili_stati.is_registrabile boolean NOT NULL DEFAULT false` + CSV: `true` solo su `VALIDATA` | **e** `fn_posta_contabile` guard 3 legge `s.is_registrabile` al posto di `'VALIDATA'` (stesso codice, stessa frase) |
| **P-3** | `script.fn_check_contabile_validabile(p_contabile_id bigint) RETURNS jsonb`, STABLE, forma di `fn_check_riga_contabile_eliminabile`: `[]` se si può validare, altrimenti motivi **ordinati** | **motivo 1** `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` (`CONFLITTO_STATO`, nuovo): righe attive con `lavorata = false`; `dettaglio = {quante, contabile_righe_ids}`, `valori = [codice distinta, quante]`. **motivo 2** `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` (riuso, **stessi valori** di oggi): solo se `importo_dichiarato IS NOT NULL` e ≠ Σ righe attive. Guard di parametro e «non trovata» come nella gemella (`E_PAGAMENTI_CHIAMATA_NON_VALIDA` / `E_CONTABILE_NON_TROVATA`) |
| **P-4** | `trgfn_vendite_contabili_guard_validazione`: entrando in `VALIDATA` chiama la check e solleva con `script.fn_raise_primo_motivo_se_presente`; il blocco (1) della quadratura **esce** dal guard (è nella check). Il blocco (2), la riapertura solo `MANUALE`, resta com'è | ⛔ Il codice letto dall'array → `fn_raise_primo_motivo_se_presente`, non la coda a mano (AGENTS.md §«due funzioni per sollevare») |
| **P-5** | `pagamenti.fn_posta_riga_tardiva(p_riga_id, p_fattura_id, p_billing_account_id, p_scadenza_id DEFAULT NULL, p_forzata DEFAULT false, p_motivo_forzatura DEFAULT NULL) RETURNS TABLE(movimento_id, riga_id, importo, esito)` | vedi §4.1 |
| **P-6** ⏳ | Matrice di riga (`20260821-31` è `runOnChange` con `ON CONFLICT … SET attivo`): le due coppie `ABBINATA → DA_ABBINARE` e `ABBINATA → SOSPESA` a `attivo = false` — **dopo la conferma di D20-e** | ⚠️ Togliere la coppia dal `VALUES` **non** la spegne (l'upsert non cancella): serve la riga esplicita a `false`, o un `DELETE`. La matrice della distinta non cambia |
| **P-7** | Codici a catalogo (`codici_errore.csv`, con la classe): `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE`, `E_RIGA_CONTABILE_TARDIVA_STATO` (la riga non è `SOSPESA`), `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` (la distinta non è registrata: annullata, o ancora aperta — «usa il giro normale»); messaggi in `messaggi_errore` con `soluzione` | tutti `CONFLITTO_STATO`. ⚠️ Nel `VARIADIC` valori, mai nomi di parametro |
| **P-8** | pgTAP: `test-contabile-validabile-v1.sql` (check + guard: rifiuta con una `DA_ABBINARE`, passa con `SOSPESA`/`SCARTATA`, quadratura ancora lì, messaggio con `throws_like`) e `test-posta-riga-tardiva-v1.sql` (§4.2); i pgTAP di P-0 adeguati; `test-rls-pagamenti-perimetro` se la madre tocca le policy | ⛔ Casi **costruiti**, non letti dai dati |
| **P-9** | Doc auto-gen + schede manuali (`script/manual/fn_check_contabile_validabile`, `pagamenti/manual/fn_posta_riga_tardiva`, i due cataloghi); riquadro D20 nel brief madre §2-bis (già scritto insieme a questo brief) | |

### 4.1 La madre della tardiva, passo per passo

1. **guard di parametro** (`E_PAGAMENTI_CHIAMATA_NON_VALIDA`, TECNICO): id nullo o ≤ 0; `p_fattura_id` obbligatorio; forzatura senza motivo ammessa (Q-8);
2. **lock** della riga (`FOR UPDATE OF r`) e lettura della testata con lo stato;
3. **guard di stato della riga**: attiva e in `SOSPESA` — `E_RIGA_CONTABILE_TARDIVA_STATO`. Da `SCARTATA` si passa prima da «Riprendi» (`→ SOSPESA`, matrice); da `DA_ABBINARE` non si arriva qui (D20-a);
4. **guard di stato della testata**: `is_final` **e** `data_conferma IS NOT NULL` — `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA`. Sotto `ANNULLATA` niente si registra («non è mai successa»); sotto `BOZZA`/`VALIDATA` c'è il giro normale, e il messaggio lo dice;
5. `PERFORM set_config('app.registrazione_tardiva_riga_id', p_riga_id::text, true)` — transazionale;
6. **`UPDATE` riga → `ABBINATA`** con `fattura_id`, `billing_account_id`, `scadenza_id`, `forzata`, `motivo_forzatura`. Girano i guard dell'abbinamento normale: transizione (`SOSPESA → ABBINATA`), dati, **rata** (coerenza rifiutata, capienza col doppio tempo: primo tentativo senza `forzata` → `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`, `confirm_and_retry`), scope. La **4ª mossa** legge la GUC e lascia passare **solo** `NEW.id = <id>`; per ogni altra riga resta com'è;
7. **`INSERT` movimento**, come il passo 8 del posting: `data_effettiva = COALESCE(data_pagamento, data_contabile)`, `data_contabile` della testata, `data_registrazione` e `data_contabilizzazione = current_date` (è registrata **oggi**: la testata porta la data della *prima* registrazione, il movimento la sua), `centro_riscossione_id` della testata, `meta = {origine: 'POSTING_TARDIVO', contabile_codice}`. Il mirror deriva fattura e cliente **dalla riga**, che a quel punto li ha;
8. **`UPDATE` riga → `POSTATA`** (`WHERE id = <id>`): scatta `marca_fondo_eseguito` se è una riga di fondo — come nel posting;
9. ritorno: `movimento_id, riga_id, importo, 'POSTATA'`. ⛔ Nessun `NULLA_DA_POSTARE`: una tardiva su una riga che non si può registrare è un **rifiuto**, non un esito.

⚠️ **La 4ª mossa cambia di una riga, nel solo ramo del cambio di stato** (non
sulle altre tre mosse — nascere, riattivare, spostare — che la madre non fa):
quando `v_diventa_pronta` è vero e
`current_setting('app.registrazione_tardiva_riga_id', true) = NEW.id::text`, il
guard lascia passare. Il pgTAP prova **anche** che la GUC settata su un altro
id **non** apre la porta, e che fuori dalla transazione è vuota.

### 4.2 Che cosa deve provare `test-posta-riga-tardiva-v1.sql`

| # | Caso | Atteso |
| --- | --- | --- |
| 1 | `SOSPESA` sotto una `CHIUSA` registrata, fattura + rata con spazio | movimento nato, riga `POSTATA`, testata ancora `CHIUSA`, `data_conferma` **invariata**, Σ righe della distinta invariata |
| 2 | stessa riga, rata **senza** spazio, `p_forzata = false` | `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` — niente scritto |
| 3 | idem con `p_forzata = true` + motivo | registrata, `forzata` e `motivo_forzatura` scritti sulla riga |
| 4 | riga `SCARTATA` | `E_RIGA_CONTABILE_TARDIVA_STATO` |
| 5 | riga `SOSPESA` sotto `ANNULLATA` | `E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA` |
| 6 | riga `SOSPESA` sotto `VALIDATA` | idem, frase «usa il giro normale» |
| 7 | rata di **un'altra** fattura | `E_RIGA_CONTABILE_RATA_INCOERENTE` (il guard della coerenza gira) |
| 8 | fuori dalla madre: `UPDATE` a mano di una `SOSPESA` → `ABBINATA` sotto una `CHIUSA` | ancora `E_RIGA_CONTABILE_DISTINTA_FINALE` (la 4ª mossa regge) |
| 9 | GUC settata su **un altro** id, poi l'`UPDATE` del caso 8 | rifiutato lo stesso |
| 10 | saldo rata dopo il caso 1 | `incassato` cresciuto dell'importo, `in_lavorazione` a zero per quella riga |

---

## 5. Cosa fa il BE (elenco — dopo l'apply)

| | Cosa | Note |
| --- | --- | --- |
| **BE-1** | `get_distinta`: `stato_is_registrabile` dalla proiezione; `can_validare` + `validazione_blocco_reason` / `_reason_key` / `_dettaglio` dalla check (la terna di §12.5, prefisso `validazione_blocco`); `righe_per_stato: [{stato_codice, stato_descrizione, righe, importo}]` sulle righe attive | la terna viaggia **solo** se lo stato corrente ammette `VALIDATA` fra le uscite; altrimenti `null` |
| **BE-2** | `list_righe_distinta`: `scartate` (`qp_bool_optional`, default `false` ⇒ le `SCARTATA` **fuori**) + `scartate_count` con `conta_con_perimetro` — la forma di `archiviate_count` | lo stato si nomina per `codice_interno` come `STATO_RIGA_ABBINATA`; l'export segue la lista a video |
| **BE-3** | `POST /pagamenti/righe/{id}/registra/` → `fn_posta_riga_tardiva`, payload = quello di `abbina` (`_CAMPI_DESTINAZIONE`), `Idempotency-Key`, `post_permission = registra_distinta` (lo stesso cancello della registrazione: rovescia denaro), cliente derivato dalla fattura se assente | il doppio tempo passa **intatto**: `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` con `confirm_and_retry` |
| **BE-4** | Code (`list_righe_coda`): `contabile_stato_codice`, `contabile_registrata` (= `data_conferma IS NOT NULL`, fatto della testata) | il FE sceglie il verbo da un **fatto**, non ricalcola una regola |
| **BE-5** | `genera_error_policies` per i tre codici + ripieghi in `error_messages_fallback.py` | `feedback_ripiego_ogni_codice_vivo` |
| **BE-6** | `api_pagamenti.md`; test service (mock) + `tests/db/` sul DB provvisto per la madre e per la check (EXPLAIN della proiezione, come per `_RIGA_INSERT`) | |

## 6. Cosa fa il FE (elenco — dopo BE)

| | Cosa | Note |
| --- | --- | --- |
| **FE-1** | `DistintaDrawer`: «Porta a VALIDATA» apre un **dialog di validazione** (`AppDialog`): dichiarato · totale righe · scarto (i tre esiti) · righe per stato; spento col motivo quando `can_validare = false` (`bloccoMotivo`, prefisso `validazione_blocco`) | non più il confirm generico; «Registra» tiene la sua anteprima |
| **FE-2** | «Registra» spento col motivo quando `!stato_is_registrabile` (chiave `pagamenti.registra.blocco.stato`) | oggi finisce in 409 |
| **FE-3** | `Mostra scartate (N)` (`ToggleNascoste`) sopra la lista delle righe; in quadratura la riga «di cui non nostre» da `righe_per_stato` | D20-c |
| **FE-4** | `CodaRigheSearchTable`: azioni di riga — **Da abbinare**: Abbina · Sospendi · Scarta; **Sospese**: Abbina (distinta aperta) / **Abbina e registra** (distinta registrata, `contabile_registrata`) · Scarta · Riporta da abbinare (dalla matrice, come oggi nel drawer); da una **scartata** (solo nel drawer, con `Mostra scartate`): Riprendi | `AbbinaRigaDialog` riusato con un modo `registra`: titolo e verbo diversi, avviso «non si torna indietro», stesso doppio tempo |
| **FE-5** | Kebab del drawer su una riga `ABBINATA`: segue la matrice (P-6) — niente da scrivere | |
| **FE-6** | i18n it/en; `check_i18n_keys` sulle `reason_key` nuove (`pagamenti.distinte.validazione_reason.*`) | |

## 7. Il copione di collaudo — righe da riscrivere

In [collaudo-in-app-incassi-distinte-e-sistemazioni.md](collaudo-in-app-incassi-distinte-e-sistemazioni.md):
**§3.1** (il ri-abbinamento passa da «Abbina» sulla riga abbinata, non da «Porta
a DA_ABBINARE» — se D20-e entra); **§2.9** («abbina e sospendi restano» sotto
`VALIDATA`: sospendere una **abbinata** no); **§4.0** (la validazione ora si
ferma **anche** su una riga da abbinare, con la frase che le conta);
**nuove §3.8–3.10**: una sospesa sotto una distinta registrata → coda «Sospese»
→ «Abbina e registra» → il movimento c'è, la distinta è ancora chiusa, la
quadratura del giorno non è cambiata; una scartata → «Mostra scartate» →
Riprendi → idem.

## 8. Registro

| Quando | Cosa |
| --- | --- |
| 2026-09-18 | Stesura, dal terzo collaudo in-app. Ordine dei rilievi di Tid: «Registra» in bozza → le regole di VALIDATA → *«un sospeso che non riesco ad abbinare, se lo scarto resta traccia e lo riprendo?»* → *«e se la scartata uscisse dalla contabile?»*. La risposta è cambiata due volte nella giornata: dalla B (sospese bloccano la validazione) alla tardiva per riga, e dal «togliere» al «nascondere». Dichiarato: **com'è** (Tid). D20-e in attesa di conferma |
