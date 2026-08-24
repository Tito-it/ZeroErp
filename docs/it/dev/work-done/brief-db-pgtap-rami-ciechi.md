# Brief DB — i rami ciechi dei presidi pgTAP

> **Cos'è.** Tre presidi del progetto cercavano i test con un glob a **un
> livello solo** (`db/pgtap/*/*.sql`). Le sottocartelle di schema — 16 file —
> erano quindi **fuori da tutto**: fuori dalla baseline, fuori dal guardrail del
> preambolo, fuori dal censimento dei `LIMIT 1`. Dodici di quei sedici erano
> **rossi**, e nessuno lo sapeva.
>
> **Origine.** 2026-08-24, di rimbalzo. Verificando un'asserzione del cantiere
> [brief-db-bersaglio-errore.md](../work-in-progress/brief-db-bersaglio-errore.md) è emerso un test
> rosso; la baseline appena girata da Tid diceva *«nessuna regressione»*. Non
> mentiva: **quel file non l'aveva guardato**.
>
> ✅ **CHIUSO il 2026-08-24: 16 file su 16 verdi.** Presidi riparati (tre
> script), preambolo aggiunto a 15 file — **7 test recuperati subito** — e i 5
> rimasti risolti uno per uno, §3.
>
> ⭐ **La cosa che questo cantiere ha scoperto non è un bug: è che quattro
> rossi su cinque erano test rimasti indietro rispetto a decisioni di dominio
> prese e scritte.** Il codice era andato avanti, il test no, e il ramo cieco
> impediva a chiunque di accorgersene — in un caso per dodici settimane.
>
> ⛔ **Perimetro: nessuna modifica al database.** Qui si toccano solo script di
> presidio e file di test.

---

## 1. Il difetto, e perché è nominabile

> **Un presidio che guarda in un ramo solo non dice «tutto a posto»:
> dice «non ho guardato».**

Il glob `db/pgtap/*/*.sql` prende `db/pgtap/<schema>/<test>.sql` e si ferma lì.
Quando qualcuno ha creato `db/pgtap/vendite/offerte_commerciali/` — una scelta
ragionevole, quella famiglia ha 15 file — quei test sono usciti dal radar di
**tre** strumenti contemporaneamente, senza che nessuno dei tre avesse modo di
accorgersene: un file che non viene letto non produce nessuna riga di output.

| Presidio | Cosa non vedeva |
| --- | --- |
| `scripts/pgtap-baseline.sh` | i 16 file non entravano mai in una corsa di baseline |
| `scripts/guardrail_pgtap_preambolo.py` | il preambolo di quei file non è mai stato verificato |
| `scripts/censimento_limit1.py` | i `LIMIT 1` senza `ORDER BY` di quei file non sono mai stati contati |

⚠️ **E il terzo è quello che spiega gli altri due.** Il preambolo non
verificato è la ragione per cui i test erano rossi — vedi §2.

---

## 2. Perché erano rossi: una data e una regola non applicata

Il **2026-08-07** il pgTAP di questo progetto è passato da girare come *owner* a
girare come **applicazione** (`zeroerp_app`): da quel giorno **le policy RLS
vengono esercitate a ogni corsa**. Il preambolo di casa esiste per questo —

```sql
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;
```

— e senza la riga di contesto `app.ruolo_applicativo` non vale `'OPERATORE'`,
quindi **ogni `INSERT` su una tabella con RLS viene rifiutato dal `WITH CHECK`**.

⭐ **I quindici file non l'hanno mai ricevuta**, perché il guardrail che la
impone non li leggeva. Sono rimasti scritti per il mondo di prima, e sono
diventati rossi tutti insieme il giorno del cambio di runner — in silenzio.

⚠️ **La forma del fallimento non è sempre la stessa**, e questo ha reso il
difetto meno riconoscibile: dove l'`INSERT` è diretto si legge *«la nuova riga
viola la regola di sicurezza per riga»*; dove invece il fixture **legge** una
riga che la RLS nasconde, il valore arriva `NULL` più a valle e l'errore accusa
tutt'altro (*«Parametro non valido: parametri NULL non ammessi»*).

**La correzione**: `find` / `rglob` al posto del glob a un livello nei tre
script, e il preambolo di casa aggiunto ai 15 file. ⚠️ Corretto anche un
**esempio in un commento** di `testpgtap.sh`, che insegnava il glob sbagliato a
chi lo copiava.

**Esito**: 12 rossi → **5**. Sette test recuperati con la sola riga di contesto.

---

## 3. I cinque — ✅ **tutti risolti il 2026-08-24**

⭐ **La cosa che li tiene insieme, e che nessuno dei cinque diceva da solo:
quattro su cinque non erano difetti del codice. Erano test rimasti indietro
rispetto a decisioni di dominio prese, scritte e applicate** — in un caso da
dodici settimane. Il codice era andato avanti, il test no, e nessuno poteva
accorgersene perché nessuno lo eseguiva.

| File | Cos'era | Come si è chiuso |
| --- | --- | --- |
| `contratti/test_fn_successione_contratti` | Il fixture usava un contratto **DRAFT** come incumbent dell'overlap | ⭐ Dal changeSet **20260602-18** (*«Overlap contratti: escludere i DRAFT dal vincolo»*) la partecipazione è decisa da `partecipa_overlap_snapshot`, colonna **GENERATED** = `NOT is_abortito AND NOT is_draft`: una bozza **non blocca**, di proposito. I due incumbent nascono ora **ATTIVI** |
| `offerte_commerciali/test_fn_push_offerta_successione` | Stessa causa, ma con una **contraddizione interna**: il test 1 asserisce che il contratto A nasce in DRAFT, il test 2 pretendeva che quel DRAFT bloccasse | Il contratto A si porta ad **ATTIVO** (`DRAFT → ATTIVO` è una transizione ammessa, quindi passa dal guard invece di aggirarlo) e nasce l'asserzione **1-bis**, che verifica la partecipazione: se un domani la formula della colonna generata cambiasse, i test 2-5 tornerebbero a misurare il caso sbagliato **in silenzio** |
| `offerte_commerciali/test_fn_crea_revisione_offerta` | Errore duro: *«Quantità nulla o mancante»* — il fixture non valorizzava `qta_operativa` con `fonte = 'FISSA'` | La trappola nota di questa famiglia: la quantità "parlante" è quella **operativa**. Tre `INSERT` corretti |
| `offerte_commerciali/test_offerte_commerciali_eccezioni_struttura` | L'asserzione 10 presidiava l'**assenza** di `stato_approvazione_prezzo` e `pratica_approvazione_prezzo_id` | ⭐ **Decisione presa due volte in senso opposto, e vale la pena saperlo**: il 24/05 la tabella nasce apposta senza (*«l'approvazione prezzo è solo sui contratti»*); il **01/06** la scelta è ribaltata con la sua ragione — le *componenti* quei campi li avevano già, e senza la simmetria un OVERRIDE non composito non ha dove registrare lo stato L3. L'asserzione non è stata cancellata ma **rovesciata**: ora presidia la **simmetria** |
| `offerte_commerciali/test_offerte_eccezioni_componenti` | L'asserzione 14 attendeva `E_PARAMETRO_INVALIDO` | Quel ramo ha ricevuto un **codice proprio** (`E_OFFERTA_ECCEZIONE_NON_TROVATA`, classe `NON_TROVATO`): il test blindava il generico, cioè **protestava contro un miglioramento**. Riscritto per asserire il **codice** e non un frammento di frase — così un domani riscrivere il messaggio non fa diventare verde un ramo sbagliato |

⛔ **E il sospetto sul cantiere del bersaglio è caduto, con la prova.** Il rosso
di `test_fn_push_offerta_successione` sembrava toccare `fn_push_offerta_a_contratto`,
riscritta lo stesso giorno: il guard di overlap è invece **intatto** e non c'entra
— la causa è del 2 giugno. La verifica valeva comunque: la coincidenza di data
non è una prova d'innocenza.

⚠️ **Un fatto emerso strada facendo, che vale oltre i test**:
`fn_push_offerta_a_contratto` crea **sempre** il contratto in DRAFT, quindi il
suo guard di overlap — e con lui tutto il ramo `p_chiudi_contratto_esistente` —
può scattare **solo** contro un incumbent già promosso. È coerente col disegno
(una bozza non blocca), ma vuol dire che la successione, sul flusso di push, non
è raggiungibile finché il contratto precedente resta in bozza. ~~**Registrato
qui, non deciso qui.**~~

> ✅ **CHIUSA il 2026-08-24, e la risposta è: non è un difetto.** L'osservazione
> è stata verificata fino in fondo e portata **accanto alla decisione che la
> genera** — [refactor-overlap.md §3.4](refactor-overlap.md), dove ora c'è il
> riquadro *«Una conseguenza sul push offerta→contratto»*.
>
> ⛔ **E una deduzione che sembrava ovvia era falsa**, vale la pena saperlo: da
> qui si era concluso che il conflitto riemergesse alla promozione come
> violazione nuda dell'`EXCLUDE`. Non succede — il guard proattivo di
> `contratti_service.emetti()` rifiuta **nominando** il contratto in conflitto, e
> `ex_contratti_no_overlap` è comunque **mappato** a `E_VENDITE_CONTRATTO_OVERLAP`.
> La catena a monte si verifica in un minuto; la conseguenza a valle **si misura**,
> non si deduce.

---

## 4. Cosa NON si è fatto, e perché

| Non fatto | Perché |
| --- | --- |
| **Mettere i cinque nella baseline dei rossi** | Un rosso registrato è un rosso che smette di far rumore. Sono stati guardati, non archiviati |
| **Aggiustare i test perché tornassero verdi** | ⭐ La differenza sta nel come: in ogni caso si è prima stabilito **chi aveva ragione** — e la risposta è sempre venuta da un changeSet con la sua data e la sua motivazione, non da una preferenza. Due asserzioni ne sono uscite **più forti** di prima (la 10 rovesciata, la 14 che ora asserisce il codice), e una è **nata** (la 1-bis) |
| **Toccare il database** | Nessuno dei cinque lo chiedeva: erano tutti test che descrivevano un mondo superato, non oggetti difettosi |

---

## 5. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-24 (secondo giro) | ✅ **CHIUSO: 16 su 16 verdi.** I cinque rossi risolti uno per uno (§3), e nessuno era un difetto del codice: **quattro su cinque erano test rimasti indietro rispetto a decisioni di dominio prese e scritte** — l'esclusione dei DRAFT dall'overlap (02/06), l'aggiunta dei campi di approvazione prezzo per simmetria (01/06), lo scorporo di `E_PARAMETRO_INVALIDO` in un codice dedicato. Il quinto era la trappola nota di `qta_operativa`. ⭐ **Due asserzioni sono state RESE PIÙ FORTI invece che aggiustate**: la 10 di `eccezioni_struttura` è stata **rovesciata** (presidia la simmetria invece dell'assenza) e la 14 di `eccezioni_componenti` ora asserisce il **codice** e non un frammento di frase, che era il modo in cui blindava il generico. E in `push_offerta_successione` è nata l'asserzione **1-bis**, che verifica la partecipazione all'overlap: senza, i test 2-5 tornerebbero a misurare il caso sbagliato in silenzio se la colonna generata cambiasse formula. ⛔ **Caduto il sospetto sul cantiere del bersaglio**: il guard di overlap di `fn_push_offerta_a_contratto` è intatto, la causa era del 2 giugno |
| 2026-08-24 | 🔎 **Nascita, di rimbalzo dal cantiere del bersaglio.** Un test rosso trovato verificando un'asserzione, e una baseline che diceva «nessuna regressione» — perché quel file non lo leggeva. ⭐ **Il difetto è in tre presidi, non in uno**: `pgtap-baseline.sh`, `guardrail_pgtap_preambolo.py` e `censimento_limit1.py` cercavano tutti con `db/pgtap/*/*.sql`, un livello solo. 🔴 Misurato: **12 file rossi su 16**, invisibili da settimane. ⭐ **La causa dei rossi ha una data**: il 2026-08-07 il pgTAP è passato a girare come applicazione e la RLS ha cominciato a mordere — quei file non avevano la riga di contesto, e il guardrail che la impone non li vedeva. ✅ Corretti i tre script (`find`/`rglob`), più un esempio in un commento di `testpgtap.sh` che insegnava il glob sbagliato; aggiunto il preambolo di casa ai **15** file. Esito: **12 rossi → 5**. ⛔ I cinque restanti sono difetti distinti e non sono stati toccati: §3 |

---

*Brief DB — i rami ciechi dei presidi pgTAP (24 agosto 2026).*
