# Collaudo in-app · l'esito parziale del pull da commessa

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md)
> §13.1 (voce **V1**); qui c'è solo **cosa fare, cosa deve succedere, e cosa
> fare se non succede**.
>
> **Stato**: ✅ **CHIUSO il 2026-09-12** — prova 5 **verde** dopo D1 e la
> correzione della catena al rilancio (brief
> [brief-db-rilancio-step-non-rivede-le-proprie-commesse](../work-in-progress/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md),
> §10): rilancio → `totale 2 · ok 2` e due fatture in «Documenti»; annullo e
> rigenerazione dopo correzione verificati in-app da Tid. La V1 del brief
> fan-out si chiude con questo verbale; la V2 era chiusa dal 2026-09-01, quindi
> la linea del fan-out chiude per intero. Storia sotto, com'era.
>
> **Stato precedente**: 🔴 **SOSPESO sulla prova 5 — il rilancio non rivede le proprie
> commesse** (2026-09-12). · **Ambiente**: sviluppo (`dbdev`). · **Pagine**:
> `Vendite → Fatturazione` (cockpit) e `vendite/lotti`.
>
> 🔴 **Esecuzione del 2026-09-12 — prova 5 spuntata fino al lotto in ERRORE,
> ROSSA al rilancio.** Ripristinate le ROOT, «Riprova step» ha chiuso il pull
> `COMPLETATO` con **`totale 0`**, ritirato le proprie critiche e portato il
> lotto a `COMPLETATO` **senza emettere niente** (LTF-0010972, poi annullato;
> LTF-0010973 ricostruito e lasciato fermo per la diagnosi). Non è il dato:
> la discovery `fn_list_commesse_emittibili` (changeSet `20260909-61`) scarta le
> commesse `TRATTENUTA` **anche quando a trattenerle è il lotto stesso** —
> l'auto-esclusione del §5.4 del brief del trattenuto è stata scritta solo
> nell'emit (`-62`), un cancello che non viene mai raggiunto. Brief al team DB:
> [brief-db-rilancio-step-non-rivede-le-proprie-commesse.md](../work-in-progress/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md).
> ⛔ **Le prove 3 e 4 vanno RIFATTE dopo D1**: la 3 era passata il 09-09 alle
> 01:44 (LTF-0010330, il rilancio ritentò 34137); L3 è stato applicato alle
> 17:12 dello stesso giorno, e da allora nessun rilancio ha più rivisto una
> commessa fallita.
>
> 🔴 **Esecuzione del 2026-09-04 — prova 1 VERDE, prova 2 ROSSA, collaudo
> SOSPESO.** Il pull ha rifiutato la commessa guastata e lo ha scritto per
> esteso (`E_PULL_COMMESSA`, `commesse_fallite: [34137]`, segnalazione critica
> sul log di lotto): **prova 1 spuntata**. Ma il lavoro della commessa respinta
> è finito in fattura lo stesso, e la prova 2 non ha misurato il savepoint —
> ha misurato un **residuo** di `attivita_fatturabili` sopravvissuto alla
> riapertura del giro precedente. Cinque difetti, due di modello, in
> [brief-residuo-fatturabili-e-bandiere-esito-parziale.md](brief-residuo-fatturabili-e-bandiere-esito-parziale.md).
> ⛔ **La prova 2 va rifatta dopo D1 e D2**: finché il perimetro di un giro è
> «tutto ciò che è libero in competenza» e non «ciò che il pull consegna», la
> prova misura il residuo e non il savepoint.
>
> ✅ **Revisione del 2026-09-05 — il blocco è caduto, la materia no.**
> **D1 e D2 sono chiusi** su entrambi i lati (DB e BE): il pull firma il
> perimetro, la select filtra, e il backend consegna `context.lock_batch_id`.
> ⇒ La prova 2 misurerebbe finalmente il **savepoint** e non il residuo.
>
> ✅ **E la materia è INTEGRA**, verificato dopo il ripristino del 2026-09-05:
> tutte e tre le commesse sono di nuovo fatturabili, con gli stessi numeri della
> fotografia del 04 (34136 · 3 attività · 53,00 — 34137 · 1 · 15,00 — 34138 ·
> 1 · 10,00), e ciascuna ha la sua riga `ROOT`.
>
> ⚠️ **Come ci si è arrivati, perché la prossima volta è più corto.** Annullare
> i lotti restituisce le attività ma **non disfa il guasto**: la `ROOT` tolta a
> 34137 (riga `17005`, degradata a `COLLEGATO`) era rimasta lì, e finché
> c'era, ogni pull respingeva quella commessa e riaccendeva il badge. ⇒ Il
> ripristino del guasto è un passo **separato** dall'annullo del lotto, e va
> fatto per **id**.
>
> ⭐ **E la materia non era consumata**, come sembrava contando le commesse
> emittibili a guasto ancora in piedi: 34137 non compariva perché era
> **respinta**, non perché fosse stata fatturata. Contare ciò che è
> «emittibile» mentre un guasto è attivo misura il guasto, non la materia.
>
> **Revisione del 2026-09-04 — materia rifatta su `2026-09`, e un `SET` che
> mancava.** Tre cose:
>
> - 🔴 **corretto il contesto operatore delle query**: i `SET` sono **due**, non
>   uno. Senza `app.ruolo_applicativo = 'OPERATORE'` la RLS di `vendite.commesse`
>   svuota `vw_dash_competenza_gruppi` (che è `security_invoker=on`) e il copione
>   fa concludere «nessuna materia» su un mese che ce l'ha — successo davvero, il
>   2026-09-04. Vale anche per il **controllo finale** della prova 5, dove il
>   fail-closed è peggio: un «tutto a posto» su una commessa lasciata senza ROOT;
> - ✅ **materia nuova su `2026-09`**, costruita da push su tre clienti diversi
>   (34136 · 34137 · 34138). Quella di agosto è **scaduta in quattro giorni**:
>   `3939` era già emessa e `3941` irreperibile. La vecchia tabella resta in
>   fondo alla sezione, richiusa, come fatto datato;
> - ✅ **prerequisito `RESUME_TASK` ri-verificato** (pipeline 1 e 8).
>
> **Revisione del 2026-08-31 — il copione è pronto per essere eseguito.** Tre
> cose sono cambiate, e la prima è un difetto che sarebbe emerso solo a metà
> collaudo:
>
> - 🔴 **corretto l'`UPDATE` di ripristino**, che era lo speculare del guasto
>   *per ruolo* e su una commessa multi-sorgente non ripristina niente: viene
>   respinto da `uq_commesse_sorgenti_commessa_root` e lascia la commessa
>   **senza ROOT**. Ora si scrive sull'`id` della riga (§La materia);
> - ✅ **misurata la materia**, che la sezione dichiarava assente: mese
>   consigliato `2026-08`, 7 commesse emittibili, con l'`id` della riga ROOT di
>   ciascuna e il motivo per cui tre è meglio non guastarle;
> - ✅ **verificato il prerequisito** `RESUME_TASK` (pipeline 1 e 8).
>
> **Perché esiste.** È l'ultima voce di **V1**, e l'unica cosa che tiene aperto
> il cantiere del fan-out insieme alle due di V2. Il codice è scritto dal
> 2026-08-09, i test sono verdi, e il **telaio** del BB `run_fan_out` è stato
> esercitato in applicazione il 2026-08-26 — ma su un **altro** consumatore
> (l'accredito massivo, prova 5 di
> [collaudo-in-app-nota-credito-resi.md](collaudo-in-app-nota-credito-resi.md)).
> Sul **pull da commessa** il ramo parziale non è **mai** stato percorso.
>
> ⚠️ **La misura del 2026-08-16 che lo diceva è ormai scaduta, e la sostanza
> non cambia — anzi, ora la prova è più netta.** Quella diceva «zero run dal
> 2026-03» e oggi sarebbe falsa: la pipeline **è** stata lanciata (415 task_run
> in tutto, l'ultimo il 2026-08-28). La misura del **2026-08-31** guarda la cosa
> giusta, cioè lo **stato** delle corse:
>
> | | |
> | --- | --- |
> | `pull_attivita_da_commessa` | 24 `COMPLETATO` + 21 `ANNULLATO` — **zero `ERRORE`** |
> | task_run in `ERRORE`, tutta la tabella | **19**, e sono tutti di `numera_fatture` (13) e `genera_scadenze_lotto` (6) |
>
> ⭐ Cioè: quello step **non ha mai chiuso in ERRORE in vita sua**, e il
> resolver non ha mai avuto occasione di rispondere `RESUME` su di lui. Contare
> i run era la domanda sbagliata — un lotto che gira e riesce non percorre il
> ramo di cui qui si parla.
>
> ⭐ **E la ragione vera per cui questo documento esiste è una sola riga dei
> test.** I tre test che coprono il caso portano
> `@patch("apps.core.services.fan_out.transaction")`: **il savepoint è mockato
> via**. Quindi la proprietà su cui poggia tutto il cantiere — *«una commessa
> rifiutata non si porta via il lavoro di quelle passate prima»* — è oggi
> **asserita e mai eseguita** su questo percorso. Se si rompesse, si romperebbe
> in silenzio: attività perse, nessun errore, un lotto che sembra a posto.

---

## ⛔ Cinque cose da sapere prima di cominciare

**1 · ⚠️ Il guasto lo inietti tu, nei dati, e va DISFATTO.** Non esiste un modo
di far fallire una commessa «per caso»: si crea la condizione di errore a mano
(§La materia), si esegue il giro, e **si ripristina**. Se ti fermi a metà, resta
una commessa che non emette più — e nessuno saprà perché.

**2 · ⚠️ `kill -HUP` sul master gunicorn PRIMA di cominciare.** Il backend di
sviluppo non ha autoreload: senza il segnale gira ancora il codice vecchio e la
prova direbbe il falso. È lo stesso prerequisito del §13.1 del brief, ed è la
ragione per cui la misura del 2026-08-16 fu inconcludente.

**3 · ⛔ Le azioni sul database non le fa l'agent.** Le tre `UPDATE` di questo
documento (guasto + ripristino) le esegui tu o le giri al team DB. Sono di sola
manutenzione del dato, reversibili, e scritte per esteso.

**4 · Nessun documento fiscale viene bruciato.** Il giro si ferma **prima** della
numerazione: si lavora su un lotto in `DRAFT`, si guardano i `task_run` e le
attività. ⛔ **Non premere «Rendi definitive»** in nessuna delle prove.

**5 · L'ordine conta.** Le prove **1 → 2** preparano e osservano; la **3** è il
cuore (il rilancio che ritenta); la **4** ripristina e chiude il giro; la **5**
è il caso tutto-rosso e va per ultima, perché lascia lo step fermo.

---

## La materia

> ~~⚠️ **I soggetti NON sono stati misurati, ed è dichiarato.**~~ ✅ **Rimisurati
> il 2026-09-04** su materia costruita apposta, e la tabella è qui sotto. Resta
> valida la ragione per cui l'avvertenza c'era: *un id inventato in un copione è
> peggio di un id assente, perché sembra verificato*. Per questo la sezione dice
> ancora **quali proprietà** deve avere la materia — gli id sono un aiuto, non il
> contratto.
>
> ⚠️ **E i numeri qui sotto sono una fotografia**: se al momento della prova il
> mese non mostra più quelle commesse, si ricontrolla con la query, non si
> insegue l'id. ⭐ **La fotografia del 2026-08-31 è scaduta in quattro giorni**:
> `3939`, la candidata di allora, il 2026-09-04 risultava **già emessa** — e
> `3941`, il ripiego, nemmeno più reperibile a video. È il motivo per cui la
> materia di settembre è stata **costruita**, non cercata.

### Cosa serve

Un **mese di competenza** il cui perimetro contenga **almeno due commesse
emittibili** — meglio tre. Una farà da guasto, le altre da controprova.

Lo trovi da `Vendite → Fatturazione`: scegli l'anno e scorri i mesi finché la
card **«Da emettere»** ne mostra almeno due. In alternativa, la lista
**gruppi fatturabili** dello stesso cruscotto elenca le unità dell'emissione e
dice a quale commessa appartengono.

#### Se la materia non c'è: si COSTRUISCE, e da documento

⛔ **Le commesse devono nascere dal push di un documento, non essere create a
mano.** La riga `ROOT` in `commesse_sorgenti` la scrive
`vendite.fn_link_commessa_sorgente`: la **prima** sorgente di una commessa prende
`ROOT`, le successive `COLLEGATO`. Una commessa creata a mano non ha **nessuna**
riga sorgente — e allora non è solo che il guasto non ha niente da guastare:
**anche le commesse sane fallirebbero** con lo stesso `E_VALORE_MANCANTE`, e la
prova 1 degraderebbe nella prova 5 (il caso tutto-rosso) senza che tu abbia
toccato niente.

⚠️ **E non bastano tre documenti: servono tre CLIENTI diversi.**
`vendite.fn_get_or_create_commessa` **riusa** la commessa esistente quando
coincidono le dimensioni della chiave — billing account, utility, tipo, policy,
competenza e condizioni di pagamento. Tre ordini sullo stesso cliente con le
stesse condizioni danno **una** commessa sola, cioè un perimetro su cui il
collaudo non è eseguibile.

Le attività devono arrivare in stadio **`DA_EMETTERE`**: `stato_approvazione =
APPROVATA`, `stato_emissione = NON_EMESSA`, `tipo_doc_fiscale_id` valorizzato. Se
il push le lascia `DA_APPROVARE` vanno **approvate**, o il mese resta vuoto.

#### I soggetti, misurati il 2026-09-04

⛔ **Prima della query, il contesto operatore — o leggi uno zero che non è un
dato. E i `SET` sono DUE.** Il primo è quello che il copione dichiarava fin
dall'inizio: `vw_dash_competenza_gruppi` filtra su
`script.fn_get_emittenti_scope_sr_ids(current_setting('app.current_user_id'))`,
che **senza contesto ritorna `{}`** (array vuoto, non NULL): il predicato
`= ANY('{}')` è falso per ogni riga e la vista risponde **zero righe a chiunque**.

🔴 **Il secondo mancava, e da solo bastava a far dire «nessuna materia» su un mese
che ce l'ha** — è successo il 2026-09-04, sulle tre commesse appena caricate.
`vendite.commesse` porta la policy RLS `rls_commesse_ef_whitelist`, che pretende
**anche** `app.ruolo_applicativo = 'OPERATORE'`; la vista è `security_invoker=on`,
quindi la RLS della **tabella base** svuota il risultato prima ancora che il
filtro sullo scope emittente entri in gioco. Un `psql` aperto e via dà «nessuna
materia» su un database che ne ha in abbondanza — è **fail-closed**, non una
misura.

```sql
SET app.ruolo_applicativo = 'OPERATORE';   -- ⛔ RLS di vendite.commesse
SET app.current_user_id   = '1';           -- ⛔ scope emittente della vista

-- ⭐ Il filtro sullo STADIO non è un dettaglio: senza, commessa_emittibile
--    conta anche le commesse il cui lavoro è già FATTURATO — è lo stato della
--    commessa, non la presenza di lavoro da emettere. È l'inganno su cui è
--    caduta 3939.
SELECT competenza_mese, commessa_id, commessa_codice, cliente_display,
       count(*) AS gruppi, sum(n_attivita) AS attivita, sum(valore) AS valore
  FROM vendite.vw_dash_competenza_gruppi
 WHERE commessa_emittibile
   AND stadio = 'DA_EMETTERE'
 GROUP BY 1, 2, 3, 4
 ORDER BY 1 DESC, 2;
```

Le tre commesse di `2026-09`, costruite il 2026-09-04 da tre clienti diversi,
tutte nate da push, con la riga di `commesse_sorgenti` da guastare.
✅ **Rimisurate il 2026-09-05 dopo il ripristino: integre, stessi numeri.**

| Commessa    | Codice                          | Cliente (BA)                 | Attività `DA_EMETTERE` | Valore | ROOT (`id` riga) | COLLEGATO     |
| ----------- | ------------------------------- | ---------------------------- | ---------------------- | ------ | ---------------- | ------------- |
| 34136       | `CMM-PGTAPEF202-2026-000000003` | Azienda PG Test Natura (169) | 3                      | 53,00  | 17003            | **1** (17004) |
| ⭐ **34137** | `CMM-PGTAPEF202-2026-000000004` | Azienda ConTutto (173)       | 1                      | 15,00  | **17005**        | 0             |
| 34138       | `CMM-PGTAPEF202-2026-000000005` | Titini Michele Carlo (155)   | 1                      | 10,00  | 17006            | 0             |

ℹ️ Nel perimetro di `2026-09` compare anche **33285**, ma è in stadio
`FATTURATA`: non partecipa al pull e non va contata fra le sane.

#### ⛔ Rimettere in ordine dopo una prova: sono TRE cose, non una

Imparato il 2026-09-05, ripulendo settembre. Annullare il lotto **non basta**, e
ognuno dei tre passi ha un padrone diverso:

| #   | Che cosa resta su                                                     | Come si abbassa                                                                                                                                                                                        |
| --- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | il **guasto** (`ROOT` tolta a 34137)                                  | si rimette `ruolo_link='ROOT'` sulla riga **per id** — l'annullo non lo tocca                                                                                                                          |
| 2   | i **task run** in `ERRORE`                                            | ✅ l'annullo li porta ad `ANNULLATO` da sé (**D4**). ⚠️ I lotti annullati *prima* del 2026-09-04 sono rimasti indietro e vanno allineati a mano                                                          |
| 3   | le **segnalazioni di lotto** (`fatturazione_lotti_log`, `status='C'`) | ⛔ **nessuno le abbassa**: restano accese anche a lotto `ANNULLATA`, e sono la sorgente della lista «commesse respinte». Oggi si spengono a mano (`disabilitato=true`) — è un tampone, la cura è del DB |

⭐ Il criterio per sapere se si è puliti davvero: `vw_dash_competenza_errori` e
`vw_dash_commesse_respinte` **entrambe a zero** sul mese, e le tre commesse di
nuovo in `vw_dash_competenza_gruppi` con `commessa_emittibile`.

**Quale guastare, e perché non le altre:**

- ⭐ **34137** è la candidata: una sola attività, valore positivo, sorgente unica
  — «è entrata / non è entrata» si legge senza contare;
- **34138** è il ripiego con le stesse proprietà, se 34137 nel frattempo è stata
  consumata;
- ⭐ **34136 va lasciata SANA di proposito**, ed è il guadagno di questa materia
  rispetto a quella di agosto: è **multi-sorgente** (1 ROOT + 1 COLLEGATO), quindi
  la controprova della prova 2 esercita quel caso sul lato che deve **passare**.
  Guastala solo se vuoi provare anche il ripristino per `id`, che su di lei è
  **obbligatorio**.

<details>
<summary>La materia di <code>2026-08</code>, misurata il 2026-08-31 — ⛔ scaduta, non usarla</summary>

Tenuta come fatto datato: dice quanto in fretta una fotografia di materia
smette di valere. `3939` era la candidata; il 2026-09-04 risultava già emessa.

| Commessa | Codice                          | Cliente                | Attività | Valore     | ROOT (`id` riga) | COLLEGATO |
| -------- | ------------------------------- | ---------------------- | -------- | ---------- | ---------------- | --------- |
| 322      | `CMM-20260719090755356-a2b9f9`  | Azienda PG Test Natura | 3        | **−17,00** | 248              | 0         |
| ⛔ 3939   | `CMM-20260802230720152-e574f8`  | Azienda ConTutto       | 1        | 700,00     | 2039             | 0         |
| ⛔ 3941   | `CMM-20260802231427331-a33197`  | Titini Michele Carlo   | 1        | 264,00     | 2040             | 0         |
| 4277     | `CMM-20260803100729415-ee7090`  | Azienda PG Test Natura | 4        | 1.820,00   | 2211             | **1**     |
| 15370    | `CMM-20260816224228686-b9946f`  | Azienda ConTutto       | 3        | 32,50      | 7789             | 0         |
| 25092    | `CMM-20260823232717992-e46ded`  | Titini Michele Carlo   | 1        | 408,00     | 12795            | 0         |
| 32899    | `CMM-PGTAPEF202-2026-000000001` | Titini Michele Carlo   | 4        | 74,00      | 16433            | 0         |

⚠️ Quel conteggio («7 commesse emittibili» su `2026-08`) era fatto **senza** il
filtro sullo stadio: comprendeva commesse il cui lavoro era già fatturato.

</details>

### Il guasto: togliere la ROOT source a **una** commessa

`vendite.fn_emit_attivita_fatturabili_da_commessa` può sollevare in tre punti.
Ne serve **uno solo**, e la scelta è motivata:

| Strada                                           | Perché sì / no                                                                                                                        |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| ⭐ **ROOT source mancante** → `E_VALORE_MANCANTE` | **questa.** Condizione **di dato**, mirata su **una** commessa, e **reversibile** con un `UPDATE` che rimette tutto com'era           |
| `E_RIGA_GIA_FATTURATA`                           | serve una riga già fatturata: si costruisce solo passando da un giro precedente, ed è più intricata da disfare                        |
| `E_CODICE` su `config.sorgenti` COMMESSA         | ⛔ **no**: è configurazione **globale**, farebbe fallire *tutte* le commesse e romperebbe il sistema per chiunque altro stia lavorando |

**Perché funziona** — righe 73-85 della funzione: la ROOT è obbligatoria, e se
manca solleva `E_VALORE_MANCANTE` con dettaglio *«ROOT source mancante per
commessa N»*.

⭐ **E non si CANCELLA la riga: le si cambia il ruolo.** La commessa è
multi-sorgente (1 ROOT + N COLLEGATO) e l'unicità è **parziale, solo sulla
ROOT** (`uq_commesse_sorgenti_commessa_root`) — quindi portarla a `COLLEGATO`
è ammesso, non perde niente, e si torna indietro con l'`UPDATE` speculare.
Una `DELETE` distruggerebbe il legame documento→commessa.

⛔ **Il guasto e il ripristino si scrivono sull'`id` DELLA RIGA, non sul ruolo.**
La `commesse_sorgenti` ammette **1 ROOT + N COLLEGATO** per commessa: l'unicità
è parziale, solo sulla ROOT. Quindi il guasto (`WHERE ruolo_link = 'ROOT'`) è
mirato e colpisce una riga sola — ma il suo speculare
(`WHERE ruolo_link = 'COLLEGATO'`) su una commessa multi-sorgente colpisce
**tutte** le N+1 righe e prova a promuoverle tutte a ROOT: l'indice parziale
`uq_commesse_sorgenti_commessa_root` respinge con `23505`, l'`UPDATE` non passa,
e la commessa **resta senza ROOT**. Cioè: il ripristino fallisce esattamente
sulle commesse per cui il guasto era più interessante.

> ⚠️ Non è un'ipotesi di scuola, ed è comunque il **modello** a decidere:
> il ripristino per ruolo è sbagliato anche su una commessa a sorgente unica,
> dove per caso funziona. *(Fatto datato, 2026-08-31: delle 31 commesse con
> sorgenti, **5** hanno più di un COLLEGATO — una ne ha 31.)*

ℹ️ **Qui il contesto operatore non serve, e la differenza conta.**
`vendite.commesse_sorgenti` **non ha RLS** — quindi il `RETURNING` è affidabile
alla lettera: zero righe significa davvero *«questa commessa non ha ROOT»*, non
*«non stai vedendo niente»*. È l'opposto delle query sulla vista e del controllo
finale della prova 5, che leggono `vendite.commesse` e vanno fatte con i `SET`.

```sql
-- GUASTO — sostituisci <commessa_id>. ⭐ ANNOTA l'id che RETURNING ti stampa:
--          è l'unica cosa che serve al ripristino.
UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'COLLEGATO'
 WHERE commessa_id = 34137
   AND ruolo_link = 'ROOT'
RETURNING id, commessa_id, sorgente_tipo_id, sorgente_uid;

UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'COLLEGATO'
 WHERE commessa_id = 36984
   AND ruolo_link = 'ROOT'
RETURNING id, commessa_id, sorgente_tipo_id, sorgente_uid;
```

```sql
-- RIPRISTINO — la stessa RIGA, per id. Da eseguire nella prova 4.
-- <riga_id> è l'id stampato dal RETURNING del guasto.
UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'ROOT'
 WHERE id = 17005
RETURNING id, commessa_id, ruolo_link;

UPDATE vendite.commesse_sorgenti
   SET ruolo_link = 'ROOT'
 WHERE id = 18375
RETURNING id, commessa_id, ruolo_link;
```

> 🩺 **Se l'id l'hai perso** — la riga si ritrova senza indovinare: è l'unica
> sorgente `COLLEGATO` di una commessa che **non ha ROOT**.
>
> ```sql
> SELECT cs.id, cs.commessa_id, cs.sorgente_tipo_id, cs.sorgente_uid
>   FROM vendite.commesse_sorgenti cs
>  WHERE cs.commessa_id = <commessa_id>
>    AND cs.ruolo_link = 'COLLEGATO'
>    AND NOT EXISTS (SELECT 1 FROM vendite.commesse_sorgenti r
>                     WHERE r.commessa_id = cs.commessa_id AND r.ruolo_link = 'ROOT');
> ```
>
> ⚠️ Se restituisce **più di una riga**, la commessa aveva già dei COLLEGATO
> suoi: non tirare a indovinare, la ROOT si riconosce dal `sorgente_uid` del
> documento che ha generato la commessa.

⚠️ **Prima di guastare, annota quali commesse sono nel perimetro e quali no.**
Serve alla prova 2: senza l'elenco di partenza, «le altre sono passate» non è
verificabile.

### Il prerequisito che decide il senso della prova 3

Il rilancio ritenta **solo se** la policy del task lo ammette:
`vendite.fn_resolve_lotto_task_execution_mode` dà `RESUME` su ultimo run in
`ERRORE` **quando** `resume_mode` è `RESUME_TASK` o `RESUME_STEP`; altrimenti dà
`RESET_REQUIRED`.

```sql
-- Deve rispondere RESUME_TASK. Se risponde altro, la prova 3 va riletta.
SELECT pipeline_id, task_code, resume_mode, annullabile
  FROM vendite.fatturazione_pipeline_task_policy
 WHERE task_code = 'pull_attivita_da_commessa';
```

- [x] `resume_mode` = **`RESUME_TASK`** su tutte le righe — ✅ **verificato il
      2026-08-31 e ri-verificato il 2026-09-04**: due righe, pipeline **1** e
      **8**, entrambe `RESUME_TASK` (`annullabile = false` su entrambe).
      ℹ️ `fatturazione_pipeline_task_policy` non ha RLS: qui il contesto
      operatore non serve.

> 📌 Al seed è `RESUME_TASK` per la pipeline **1** (MASSIVO) e la **8**
> (GIORNALIERO). Il controllo serve a escludere che sia stato cambiato dopo, e
> va **rifatto** se fra questa verifica e la prova è passato un migrate.

---

## Prove

### 1 · Il giro **non si ferma**, e il task_run va in **ERRORE**

**Dove**: `Vendite → Fatturazione`, mese scelto. Applica il **guasto** a una sola
commessa, poi lancia **«Fattura adesso»** (o l'emissione mirata sui gruppi, se
preferisci restringere il perimetro).

- [X] il giro **arriva in fondo**: non compare un errore rosso che ferma tutto;
- [X] viene creato un **lotto**, e lo trovi in `vendite/lotti`.

Apri il lotto, scheda **Task** (i `task_run`):

- [X] la riga di **`pull_attivita_da_commessa`** ha stato **`ERRORE`**, non
      `COMPLETATO`;
- [X] il suo `meta` porta i quattro numeri: `totale`, `ok`, `falliti`, e
      **`commesse_fallite`** con dentro **l'id della commessa che hai guastato**.

⚠️ **Se il task_run è `COMPLETATO`**: è il difetto originale del cantiere,
tornato. Un parziale chiuso in COMPLETATO significa che al rilancio il resolver
dirà `SKIP` e la commessa rimasta indietro **non verrà mai più ritentata**.
Fermati e segnala — è la cosa che questo cantiere esisteva per correggere.

⚠️ **Se il giro si è fermato senza nessuna commessa passata**: il perimetro
conteneva **una sola** commessa e hai fatto la prova 5 per sbaglio — rimetti la
ROOT, allarga il perimetro, ricomincia. ⛔ Dal 2026-09-07 non lo riconosci più
da un codice d'errore dedicato: il ramo tutto-rosso non solleva, e il segnale è
che gli `ok` siano **zero su N**.

### 2 · ⭐ Le commesse **sane** sono passate — e sono RIMASTE

> È la prova che conta più di tutte. Il savepoint per commessa è la proprietà
> che i test **non eseguono** (transazione mockata): se è rotto, il rollback
> della commessa rifiutata si porta via anche il lavoro di quelle passate prima,
> **senza nessun errore**.

Sul lotto, scheda **Documenti**:

- [X] ci sono documenti, e **non sono zero**;
- [X] le attività delle commesse **non guastate** sono dentro — confronta con
      l'elenco che ti eri annotato.

Poi, sul cruscotto (`Vendite → Fatturazione`, stesso mese):

- [X] le commesse sane **non compaiono più** fra quelle da emettere;
- [X] la commessa guastata **c'è ancora**: il suo lavoro non è stato consumato.

⚠️ **Se il lotto è vuoto, o mancano attività di commesse che non hai toccato**:
🔴 **fermati e segnala.** È l'isolamento per item che non regge, ed è il difetto
peggiore possibile su questo percorso — silenzioso, e con perdita di lavoro.

### 3 · 🔴 IL CUORE — il rilancio **RITENTA**, non salta

> Questa prova chiude l'unica voce che nessun altro percorso ha mai esercitato.
> Fino al 2026-08-09 qui il rilancio faceva **SKIP** e la commessa rimasta
> indietro spariva in silenzio, per sempre.

**Prima**, verifica cosa dice il resolver — sostituisci `<lotto_id>` e
`<pipeline_id>` (li leggi sul lotto):

```sql
SELECT execution_mode, last_task_stato, last_tentativo
  FROM vendite.fn_resolve_lotto_task_execution_mode(
         <lotto_id>, <pipeline_id>, 'pull_attivita_da_commessa');
```

- [X] `last_task_stato` = **`ERRORE`**;
- [X] `execution_mode` = **`RESUME`** — ⛔ **non `SKIP`**.

⚠️ **Se dice `SKIP`**: il difetto è tornato, e la prova 1 aveva già dato il
segnale (task_run COMPLETATO). ⚠️ **Se dice `RESET_REQUIRED`**: la policy non è
più `RESUME_TASK` — vedi il prerequisito nella Materia.

**Poi** rilancia lo step **lasciando il guasto in piedi**, dal drawer del lotto.

- [X] il pulsante c'è e si può premere: **«Riprova step»** se il lotto è in
      `ERRORE`, **«Rigenera la bozza»** se è stato riportato in lavorazione,
      **«Avanza step»** altrimenti;
- [X] il tentativo **riparte** e la commessa guastata viene **ritentata** — nella
      scheda **Task** compare un run **nuovo** (`last_tentativo` incrementato),
      non un salto;
- [X] fallisce **di nuovo**, con lo stesso motivo: il guasto è ancora lì, ed è
      giusto così.

⚠️ **Se «Avanza step» è DISABILITATO** con il tooltip sulle segnalazioni: è
atteso e non è un difetto — il pull scrive una segnalazione **critica** per ogni
commessa fallita (`E_PULL_COMMESSA`, severity `C`), e le criticità bloccano
l'**avanzamento**. Il rilancio dello **stesso** step invece è ammesso di
proposito (`is_rilancio_stesso_step` nel runner): è la via d'uscita.
🔴 **Ma se NESSUNO dei tre pulsanti è premibile**, l'operatore è in un vicolo
cieco — il lavoro non è recuperabile da video. **Fermati e segnala**: sarebbe un
difetto di percorso, non di calcolo, e nessun test poteva vederlo.

### 4 · Rimosso il guasto, il lavoro **torna a casa**

Esegui il **RIPRISTINO** (la `UPDATE` speculare della Materia), poi rilancia lo
step ancora una volta.

- [X] il task_run **nuovo** chiude in **`COMPLETATO`**;
- [X] le attività della commessa prima guastata sono **entrate** nel lotto;
- [X] sul cruscotto quella commessa **non risulta più** da emettere;
- [X] ⭐ e non ci sono **doppioni**: le attività delle commesse sane non sono
      state emesse due volte.

⚠️ **Se compaiono doppioni**: l'idempotenza dell'emit non regge al ri-tentativo.
La funzione mappa `segment_key` in UUID deterministico proprio per evitarlo —
segnala con l'id della commessa.

### 5 · Il caso **tutto-rosso** — la catena si ferma, ma i segni restano

> ⚠️ **QUESTA PROVA È CAMBIATA IL 2026-09-07 (P-5).** Prima lo step *sollevava*
> `E_PULL_COMMESSA_ALL_FAILED`, e quel `raise` faceva rollback: si portava via
> anche le marcature dei documenti caduti, appena scritte. Il caso peggiore era
> l'unico che non lasciava traccia.
> ⇒ Adesso il ramo «tutte fallite» **si comporta come il parziale**: nessuna
> eccezione, l'esito si scrive, e a fermare la catena ci pensa il blocco per
> segnalazioni critiche. *Fermarsi* e *strappare gli appunti* erano due cose che
> faceva lo stesso gesto.
> ⛔ Il codice è **ritirato** (`obsoleto_dal = 2026-09-07`): se lo vedi, qualcosa
> è tornato indietro.

> Ultima, perché lascia lo step fermo e va poi ripulita.

Applica il guasto a **tutte** le commesse del perimetro (se sono poche; se sono
molte, restringi il perimetro con l'emissione mirata a un gruppo solo, poi
guasta quella commessa). Lancia il giro.

- [X] lo step **non solleva**: il giro finisce, e finisce male;
- [X] il `task_run` si chiude in **ERRORE** con **`E_PULL_COMMESSA`** — lo stesso
      codice del parziale, perché i due rami adesso sono lo stesso codice;
- [X] ⭐ nella scheda **«Presi in carico»** del lotto ci sono **tutti** i
      documenti, ognuno in `ERRORE` col suo motivo. È la prova che i segni sono
      sopravvissuti: prima di oggi qui non c'era niente;
- [X] il lotto va in **ERRORE** e la catena **non avanza**: il giro si ferma con
      `BLOCCATO_CRITICITA` / `E_PIPELINE_LOTTO_CRITICAL`;
- [X] 🔴 il rilancio dello **stesso** step resta ammesso — è la via d'uscita:
      correggi la commessa, rilancia, il task ritira le sue segnalazioni.
      **ROSSO il 2026-09-12**: il pulsante c'è e si preme, ma il pull
      **non rivede le commesse** (`totale 0 · ok 0`), ritira le segnalazioni
      lo stesso e il lotto esce `COMPLETATO` a vuoto. Le righe risultano
      `TRATTENUTA` **dal lotto stesso** e la discovery le scarta prima che
      l'emit — che l'eccezione ce l'ha — venga chiamato. Da rifare dopo D1
      del brief.

⛔ **Il segnale d'allarme si è spostato, e va letto al contrario di prima.** Non
è più «lo step prosegue»: adesso il giro finisce senza eccezione *per progetto*.
Il difetto sarebbe che il lotto **AVANZI allo step successivo** e nasca un
documento vuoto. Se succede, il blocco per segnalazioni critiche non ha
funzionato — segnala.
⚠️ E se la scheda «Presi in carico» fosse **vuota**, il difetto è l'altro: la
marcatura non è arrivata a nessun documento. Nei log cerca
`pull_commesse.esito_non_appeso`.

**Poi ripristina tutto** e verifica di essere tornato al punto di partenza:

- [X] tutte le commesse toccate hanno di nuovo `ruolo_link = 'ROOT'`;
- [X] il mese di competenza torna a mostrare le commesse da emettere.

⛔ **Il controllo finale è quello che il fail-closed tradisce peggio**: legge
`vendite.commesse`, che ha la RLS, e **senza i due `SET` torna zero righe** —
cioè esattamente l'esito che stai sperando di vedere. Un «tutto a posto» che è
solo assenza di contesto, su una commessa lasciata senza ROOT.

```sql
SET app.ruolo_applicativo = 'OPERATORE';   -- ⛔ o lo zero non è un dato
SET app.current_user_id   = '1';

-- Controllo finale: nessuna commessa deve essere rimasta senza ROOT.
SELECT c.id
  FROM vendite.commesse c
  LEFT JOIN vendite.commesse_sorgenti cs
    ON cs.commessa_id = c.id AND cs.ruolo_link = 'ROOT'
 WHERE cs.id IS NULL;
```

- [X] la query non restituisce **nessuna** delle commesse che hai toccato.

---

## Verbale

**Chiuso il**: — · **Da**: — · **Ambiente**: sviluppo (`dbdev`)

| #   | Prova                                                        | Scrive | Esito | Note                                   |
| --- | ------------------------------------------------------------ | ------ | ----- | -------------------------------------- |
| 0   | La policy del task è `RESUME_TASK`                           | no     |       |                                        |
| 1   | Il giro non si ferma, il task_run va in **ERRORE**           | **sì** |       |                                        |
| 2   | ⭐ Le commesse sane sono passate **e rimaste** (savepoint)    | no     |       |                                        |
| 3   | 🔴 Il rilancio **RITENTA**, non salta                         | **sì** |       | da rifare dopo D1 (passata pre-L3)     |
| 4   | Rimosso il guasto, il lavoro torna a casa senza doppioni     | **sì** |       | da rifare dopo D1, insieme alla 3      |
| 5   | Tutto-rosso → nessuna eccezione, segni scritti, catena ferma | **sì** | 🟡/🔴   | 2026-09-12 · il rilancio non ritenta 🔴 |

### Che cosa ha trovato il collaudo

**2026-09-12 (prova 5, Tid).** Il caso tutto-rosso si comporta come promesso
fino al lotto in `ERRORE`. Al **rilancio**, dopo il ripristino delle ROOT, il
pull chiude `COMPLETATO` con `totale 0`: non ha visitato nessuna commessa. La
causa è di **modello** e sta nella discovery (`fn_list_commesse_emittibili`,
`20260909-61`): esclude le commesse `TRATTENUTA` senza ricevere l'identità del
giro, quindi al rerun scarta le **proprie** — e ogni commessa fallita è
trattenuta dal proprio lotto per costruzione (esiti `ERRORE` scritti fuori dal
savepoint). L'auto-esclusione decisa nel §5.4 del brief del trattenuto esiste
solo nell'emit (`-62`), che non viene raggiunto; P-5 (test 3) prova l'emit da
solo e non poteva vederlo. Secondo effetto: ritirate le bandiere all'avvio e
non rialzate da un giro vuoto, il lotto esce pulito con due esiti `ERRORE` che
il verdetto non conta. Dettaglio, prova a cerchio e richieste in
[brief-db-rilancio-step-non-rivede-le-proprie-commesse.md](../work-in-progress/brief-db-rilancio-step-non-rivede-le-proprie-commesse.md).
⚠️ La prova 3 era passata il 09-09 alle 01:44 (LTF-0010330), **prima** che L3
venisse applicato alle 17:12: le prove 3 e 4 vanno rifatte.
✅ **12-09 pomeriggio: DB (`20260912-12…16`), BE e FE consegnati** — brief §8
e §9.6. Sul 13338 la discovery chiamata dal repository con l'identità del lotto
restituisce le due commesse. Da rifare qui: «Riprova step» su 13338 (atteso
`totale 2 · ok 2`), poi le prove 3, 4 e 5.

---

## Quando questo verbale è chiuso

La voce **V1** del §13.1 di
[brief-be-fan-out-isolato-e-esito-parziale.md](brief-be-fan-out-isolato-e-esito-parziale.md)
si chiude, e con lei la metà **pipeline** dell'esito parziale — l'altra metà, il
**telaio** del BB, è già validata dal collaudo nota di credito del 2026-08-26.

Restano allora le due voci di **V2**: il ramo `CONFERMATO` di **DL-23** (nessun
soggetto, va costruito) e la verifica dell'**area RESI** delle card, che dal
2026-08-26 non è più bloccata. Chiuse quelle, il brief va in `work-done` e la
linea del fan-out chiude per intero.

⚠️ **Se una prova fallisce, non aggiustare il dato**: annota cosa hai visto e
passa alla successiva — tranne la 2, dove un difetto significa perdita di lavoro
e conviene fermarsi. E **ripristina sempre le ROOT** prima di chiudere la
sessione, comunque sia andata.

---

## Prove aggiuntive · l'USCITA DAL GIRO — il secondo consumatore del fan-out

> **Perché stanno qui e non in un file loro.** È lo **stesso** telaio: il verbo
> «togli dal giro» di massa gira su `run_fan_out`, con savepoint per elemento e
> lo stesso esito a tre stati delle prove 1-5. Cambia il dominio, non il
> meccanismo — e un collaudo per consumatore renderebbe tre copie della stessa
> trafila.
> Il *perché* di ogni scelta sta in
> [brief-db-uscita-documento-dal-giro.md](brief-db-uscita-documento-dal-giro.md).
>
> **Stato**: 🔵 **da eseguire**. Aggiunte il 2026-09-08, quando la parte con il
> dato già pronto è stata spuntata a video (colonna «Documento» leggibile,
> ordinamento con le critiche del giro in testa, kebab senza id con le icone
> giuste, banner che conta documenti, azione spenta col motivo su un documento
> già uscito).
>
> 🔴 **E queste tre NON si possono provare su ciò che c'è.** Misurato il
> 2026-09-08: **nessun lotto ha più di UN documento in `ERRORE`**, quindi il
> gesto di massa non ha su cosa esercitarsi. La materia va costruita, come per
> la prova 3.

### Cosa serve costruire

Un lotto **pre-fiscale** (`DRAFT`) con **due** documenti in `ERRORE`, e — per la
prova 7 — i due devono **condividere la stessa bozza**.

⚠️ Le bozze condivise esistono già (una copre 10 documenti), ma su lotti vecchi
che sono **oltre il pre-fiscale**: lì l'azione è spenta col motivo
`lotto_non_pre_fiscale`, che è corretto e non serve alla prova.

⛔ Non si costruisce con un `UPDATE` diretto su `fatturazione_lotti_esiti`: il
trigger dell'uscita governa quella colonna, e uno stato messo a mano
salterebbe proprio la strada che si sta collaudando. Si guasta a monte — come la
`ROOT` tolta alla commessa della prova 3 — e si lascia fallire il giro.

### 6 · Il gesto di MASSA

1. Scheda **«Presi in carico»**, spuntare i **due** documenti in errore.
2. Il pulsante deve comparire **solo ora** e portare il conteggio: «Togli dal
   giro **(2)**».
3. Premere: si apre la **stessa** conferma della riga singola, con il motivo
   obbligatorio.

**Deve succedere:** il pulsante è spento finché il motivo è vuoto; alla conferma
l'esito dice quante bozze sono state cancellate e quanti documenti sono tornati
«da emettere».

**Se non succede:** un pulsante che compare a selezione vuota, o una conferma
diversa da quella di riga, significa che il verbo ha due superfici — ed è
esattamente ciò che l'endpoint unico esiste per impedire.

### 7 · ⭐ IL CUORE — l'esito **PARZIALE**, e si costruisce da sé

Due documenti che **condividono la bozza**, entrambi in errore, **tolti
insieme**.

⭐ Non serve inventare un guasto: togliendo il primo, il secondo viene
**trascinato** e torna a `PENDING` (D-2b). A quel punto non è più «in errore», e
il suo rifiuto arriva da solo.

**Deve succedere:**

|              |                                                                                  |
| ------------ | -------------------------------------------------------------------------------- |
| esito        | `PARZIALE` — e la risposta è **200**, non un errore                              |
| messaggio    | «Tolti dal giro 1 documenti su 2. I restanti non sono passati: …»                |
| il motivo    | quello **vero** della riga — `E_LOTTO_DOC_NON_IN_ERRORE`, non un codice generico |
| la selezione | resta spuntata **solo la riga fallita**                                          |

⛔ **E il numero dei «tornati da emettere» deve dire `0`, non `2`.** I due sono
usciti entrambi: nessuno torna in coda. Si contano per **insieme** e non
sommando le righe, proprio perché due documenti che condividono una bozza si
nominano a vicenda come trascinati.

**Se non succede:** un `E_PIPELINE_VALIDATION` al posto del codice vero
significa che la traduzione dell'errore è tornata al confine dell'API invece che
nel service — dentro il fan-out l'eccezione è ancora quella grezza di psycopg, e
i due rifiuti diventano indistinguibili.

### 8 · L'avviso «trascina», PRIMA di premere

Su un documento che condivide la bozza, aprire la conferma **senza** confermare.

**Deve succedere:** compare l'avviso arancio col numero degli altri documenti
che vengono via insieme, e dice che **tornano «da emettere»** — non che si
perdono.

**Se non succede:** l'avviso assente su una riga con `n_trascinati > 0` è la
conseguenza nascosta che la D-2b esiste per dichiarare — l'operatore la
scoprirebbe dopo, sul lotto successivo.

### Verbale delle prove aggiuntive

| N°  | Cosa dimostra                                                               | Atteso | Esito | Note |
| --- | --------------------------------------------------------------------------- | ------ | ----- | ---- |
| 6   | Il gesto di massa è lo stesso verbo della riga                              | **sì** |       |      |
| 7   | Esito PARZIALE: codice per riga, spunta sulle fallite, riaperti per insieme | **sì** |       |      |
| 8   | La conseguenza si dichiara prima                                            | **sì** |       |      |
