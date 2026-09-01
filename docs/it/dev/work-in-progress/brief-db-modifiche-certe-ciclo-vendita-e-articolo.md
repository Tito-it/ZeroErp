# Brief DB — le modifiche certe: le date di consegna, il modo di approvvigionamento, la commessa leggibile

> **Destinatario:** team DB (`dev/db-tid`) per l'esecuzione, **e team BE/FE come
> lettori** — ⭐ **questo documento è l'unica comunicazione che BE e FE
> riceveranno su questo lavoro.** Decisione di Tid, 2026-09-01: *«non faremo
> documentazione BE/FE, manderemo solo questo nuovo brief con tutta l'attività
> fatta»*. Quindi la §5 non è un'appendice: è la parte che va letta dall'altro
> lato, e deve bastare da sola.
>
> **Origine.** Le due analisi del 2026-09-01 su commessa e magazzino. Tid:
> *«da questi dobbiamo estrarre quali potrebbero essere le modifiche necessarie,
> quelle che sicuramente servono, tenendo fuori quelle collegate a decisioni da
> prendere»*.
>
> **Stato:** 🔵 **APERTO — piano scritto, nulla applicato.** Nessun changeSet
> ancora creato. ⛔ Niente si applica senza autorizzazione esplicita di Tid.
>
> ⚠️ **Perimetro:** solo ciò che **nessuna decisione aperta può cambiare**. Il
> criterio è dichiarato in §1 ed è l'unica ragione per cui una voce sta qui.

---

## 1. Il filtro, ed è tutto il valore di questo documento

Le due analisi contengono molto più di quanto sta qui. La domanda che ha separato
le voci è **una sola**:

> **Se le decisioni aperte venissero prese in un modo o nell'altro, questa voce
> cambierebbe?** Se sì, non è in questo brief.

Le decisioni aperte sono le **D-1 → D-8** dell'[analisi
magazzino](analisi-db-magazzino-aggancio-documento-e-produzione.md) §8 e la **§7**
dell'[analisi commessa](analisi-db-commessa-e-produzione-predisposizione.md) —
cioè: se l'ODL è una sorgente o un anello proprio, se il ledger di magazzino usa
il catalogo delle sorgenti o il riferimento testuale, e se la commessa di
produzione è `vendite.commesse` o un'entità sua.

⚠️ **Il filtro NON è «serve anche se la produzione non si farà mai».** La
produzione non è una delle decisioni aperte: Tid l'ha data per assunta — *«siamo
vicini a iniziare lo sviluppo, e anche se ora non c'è dobbiamo prevederlo»*. È
aperta la sua **forma**, non la sua esistenza.

### ⭐ Il risultato del filtro, ed è la cosa più utile che è emersa

**Tutte le voci certe stanno su `vendite` e `catalogo`. Tutte le decisioni aperte
stanno su `magazzino` e sulla forma dell'ODL.**

Le due analisi sembravano contigue e in realtà **non si bloccano a vicenda**: il
lavoro di questo brief si può fare adesso, sulle tabelle in esercizio, mentre
`magazzino` aspetta le sue decisioni. Non c'è un ordine da rispettare fra i due.

---

## 2. Blocco A — Le date di consegna

### 2.1 Che cosa manca, e perché è la prima

⛔ **Non esiste alcuna data di consegna in tutto il database.** Cercata su
`vendite`, `acquisti` e `magazzino` il 2026-09-01: l'unica data di previsione
dell'intero modello è `magazzino.reservations.data_prevista`, in uno schema che
non è in esercizio.

⚠️ **Nessuna delle date esistenti serve, e vanno nominate per non farsele
proporre di nuovo:**

| Colonna | Perché non è quella |
| --- | --- |
| `vendite.ordini.data` | è la **data documento**, e governa numerazione, anno e pavimenti |
| `commesse.competenza_dal/al` | è **competenza fiscale**: riusarla farebbe dissentire due domande sulla stessa colonna |
| `data_insert` | è quando la riga è stata scritta, non quando la merce è attesa |

⭐ **E serve anche senza produzione**: senza una data di consegna non esiste la
nozione di **ritardo**. `vw_situazione_merce_ordine` sa dire *quanto* resta da
spedire e non saprà mai dire *se è tardi*. Nessun sollecito, nessuna priorità di
evasione, nessun indicatore di puntualità.

### 2.2 Le colonne

| Tabella | Colonna | Tipo | Null |
| --- | --- | --- | --- |
| `vendite.ordini_righe` | `data_consegna_richiesta` | `date` | sì |
| `vendite.ordini_righe` | `data_consegna_confermata` | `date` | sì |
| `vendite.preventivi_righe` | `data_consegna_richiesta` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_richiesta` | `date` | sì |
| `acquisti.ordini_righe` | `data_consegna_confermata` | `date` | sì |

**Le due date sono due cose diverse** e la differenza fra loro *è* la promessa:
la prima è quando il cliente la vuole, la seconda quando ci si impegna a darla.
Sull'ordine d'acquisto lo stesso, ribaltato: quando la si chiede al fornitore e
quando lui conferma — ed è l'informazione che oggi manca per sapere se la merce
arriverà in tempo per una consegna già promessa.

⛔ **Sulla RIGA, non sulla testata**, e non è un dettaglio: una riga può essere
pronta e un'altra no. È esattamente il caso «questa riga richiede produzione», ed
è anche il caso banale «il pezzo grosso arriva a marzo, il resto subito».

⛔ **Niente colonna di testata.** La data della testata è
`min(data_consegna_richiesta)` sulle righe attive: una colonna sarebbe una
**seconda sorgente di verità** che va fuori sincrono al primo cambio di riga.
Dove serve come dato — la lista ordini — si espone dalla vista (§5.2), non dalla
tabella.

⚠️ **`vendite.preventivi_righe` ha solo la richiesta**, non la confermata: su un
preventivo non c'è ancora niente da confermare.

⛔ **`vendite.offerte_commerciali` NON entra**: non ha righe articolo (ha
utilities ed eccezioni), quindi non c'è la riga a cui la data apparterrebbe.

### 2.3 ⛔ Nessun CHECK fra le due date, ed è una scelta

La tentazione è `data_consegna_confermata >= data_consegna_richiesta`. **È
falsa**: si può confermare *prima* di quanto chiesto, ed è una buona notizia, non
un errore.

E nemmeno un CHECK contro `ordini.data`: la **retrodatazione è un caso d'uso
vivo** in questo progetto — è la lezione già pagata dal cantiere numerazione, dove
un cancello sulla data era stato motivato con «la sceglie una persona» mentre è
proprio per questo che va lasciata scegliere.

⭐ La regola applicata: *un vincolo si mette dove il modello lo richiede, non
dove sembra ordinato.*

### 2.4 Il passaggio preventivo → ordine

`vendite.fn_push_preventivo_a_ordine` deve **portare avanti** la data richiesta,
altrimenti si perde nel punto in cui il documento cambia natura, ed è il punto in
cui gli utenti smetteranno di fidarsene.

⚠️ Toccando quella funzione si incontra un residuo già noto: nel corpo cita in un
commento `trgfn_ordini_gen_codice`, funzione che non esiste più. ⭐ È dichiarato
nel brief archiviato del prefisso sul registro (§6.3) come *«si fa alla prossima
occasione in cui la si tocca»*: **questa è quell'occasione**, e costa una riga.

---

## 3. Blocco B — Da dove arriva un articolo

### 3.1 Il buco, e le tre risposte sbagliate

⛔ **Oggi niente, in nessuna tabella, sa rispondere a «questa riga richiede
produzione?»** — e neppure a «questo articolo movimenta giacenza?», che serve a
`magazzino` a prescindere dall'ODL.

⚠️ **Le tre colonne che sembrano rispondere già, e non rispondono** — vanno
nominate perché sono la scorciatoia che qualcuno proporrà:

| Colonna | A che domanda risponde davvero |
| --- | --- |
| `articoli.is_composito` | *l'articolo ha componenti da esporre in fattura* (pricing v5, `esposto_in_fattura`). Un assemblato può essere comprato finito |
| `articoli.natura_vendita_id` | *dove va la riga venduta* (`destinazione_tipo`: ORDINE / COMMESSA / CONTRATTO). Dice la destinazione, non la provenienza |
| `nature_vendita.e_cessione_beni` | è **fiscale**: lo consuma `fn_resolve_iva_riga_guscio`. Riusarlo farebbe rispondere a un dato due domande in AND |

### 3.2 Il vocabolario `config.modi_approvvigionamento` (tabella nuova)

Colonne, sulla forma già usata da `config.nature_vendita`:

| Colonna | Note |
| --- | --- |
| `id` | identity |
| `codice_interno` | UNIQUE, **immutabile** (lock column) — è ciò su cui il codice confronta |
| `codice`, `descrizione` | mutabili, per l'operatore |
| `attivo`, `ordine`, `meta` | come tutti i vocabolari |

Seed: `ACQUISTO`, `PRODUZIONE`, `STOCK`, `NON_APPLICABILE`.

⭐ **Perché una tabella e non un CHECK su varchar**, ed è una scelta fatta qui
(revocabile, ma motivata): il modo di approvvigionamento è una **dimensione
dell'articolo** come la natura di vendita, e la natura di vendita è una tabella.
Il FE ha bisogno di una **select con etichetta** e la lista di un valore
**decodificabile**; un CHECK non dà né l'una né l'altro, e ogni consumatore
finirebbe per riscriversi le quattro stringhe a mano. ⚠️ E il giorno in cui la
produzione esiste, quel vocabolario avrà **attributi** (per esempio «richiede
ODL»): un CHECK non li può portare.

⚠️ **Tabella nuova = ciclo delle automazioni.** Audit, `tx_id` e storico non
esistono finché non gira `ci_apply`; il lock su `codice_interno` va seminato in
`dbops.automation_lock_columns`, che è **create-if-not-exists** — se la riga
esiste già va **DROP + rigenera**, non un UPDATE. E serve la riga in
`dbops.fk_index_policy` per la FK che nasce (⚠️ `dll_command` **sempre
valorizzato**, anche a `consentito = false`).

### 3.3 Le colonne su `catalogo.articoli`

| Colonna | Tipo | Null | Default |
| --- | --- | --- | --- |
| `modo_approvvigionamento_id` | `bigint` FK → `config.modi_approvvigionamento` | **no** | `ACQUISTO` |
| `gestito_a_magazzino` | `boolean` | **no** | `false` |
| `lead_time_giorni` | `integer` (CHECK `>= 0`) | **sì** | — |

⭐ **Perché queste nullabilità e non altre**, applicando la regola del progetto
(*un `NOT NULL` va dove il dato si può fornire*):

* **`modo_approvvigionamento_id` NOT NULL**: il valore si può sempre dare, e un
  NULL significherebbe «non lo so» — cioè esattamente lo stato che questa colonna
  esiste per abolire. Il default `ACQUISTO` è il caso comune e non inventa niente.
* **`gestito_a_magazzino` NOT NULL DEFAULT `false`**: il default è **fail-safe** —
  nessun articolo comincia a movimentare giacenza per distrazione. ⚠️ Ne discende
  che al rilascio *tutti* sono `false` e la merce va marcata: è un lavoro di dato,
  ed è il momento giusto per farlo, perché `magazzino` non è in esercizio.
* **`lead_time_giorni` NULLABLE**: per una prestazione non significa niente, e
  `0` non è «non si applica». Qui il NULL è un'informazione.

⚠️ **`gestito_a_magazzino` non si deriva da `natura_vendita = MERCE`**: una merce
può essere venduta senza passare da giacenza (consegna diretta dal fornitore).
Sono due domande, e vanno tenute separate anche quando oggi le risposte
coincidono.

---

## 4. Blocco C — La commessa leggibile

⛔ Oggi `vendite.commesse` ha `codice` e **nient'altro di parlante**: in una lista
non si capisce che cosa sia.

| Colonna | Tipo | Null | Note |
| --- | --- | --- | --- |
| `descrizione` | `varchar(255)` | sì | l'oggetto della commessa, in parole |
| `data_apertura` | `date` | **no**, default `script.fn_data_operativa()` | ⛔ **mai `now()` nudo**: è la convenzione del progetto |
| `responsabile_soggetto_ruolo_id` | `bigint` FK → `anagrafiche.soggetti_ruoli` | sì | chi la governa |

⭐ **Perché sono certe**: servono alla commessa **così com'è oggi**, cioè al
contenitore di fatturazione. Valgono identiche in tutti e due gli esiti della §7 —
se domani la commessa diventasse anche la testata di produzione, queste tre
resterebbero e se ne aggiungerebbero altre.

⚠️ **Attenzione al guard che nasce da solo.** La FK nuova genera un trigger
`BEFORE ROW` di *parent attivo*, e i trigger `BEFORE ROW` scattano in **ordine
alfabetico**: su `commesse` ce ne sono già tre scritti a mano
(`guard_emittente_ba`, `guard_transizione`, `guard_chiave_immutabile`). Va
verificato che il generato non **oscuri** uno di quelli, cambiando l'errore che
l'operatore vede.

---

## 5. ⭐ La predisposizione BE/FE — la parte che va letta dall'altro lato

> ⛔ **Non ci sarà altra documentazione.** Questa sezione è la richiesta a BE e FE,
> e dichiara **tutto ciò che il DB consegna già pronto**, così che dall'altro lato
> non serva nessun lavoro di scoperta.

### 5.1 Che cosa il DB consegna, in una riga

**Le colonne nuove escono già dalle viste canoniche e sono già configurate come
colonne di lista.** BE e FE non devono aggiungere una vista, né una riga di
configurazione: devono **consumare** e, sul FE, tradurre le chiavi i18n.

### 5.2 Le viste che cambiano

| Vista | Colonne aggiunte | A cosa serve |
| --- | --- | --- |
| `vendite.vw_ordini_lista` | `data_consegna_richiesta_min` | ⭐ è la vista **canonica lista *e* dettaglio** degli ordini: la stessa colonna serve la lista e il drawer di testata |
| `vendite.vw_situazione_merce_ordine` | `data_consegna_richiesta`, `data_consegna_confermata`, `giorni_ritardo` | è la vista **per riga** che già tiene ordinato / consegnato / `da_spedire` con la soglia dell'impegno |
| `catalogo.vw_articoli_dettaglio` | `modo_approvvigionamento_id`, `modo_approvvigionamento_codice_interno`, `modo_approvvigionamento_descrizione`, `gestito_a_magazzino`, `lead_time_giorni` | è la vista della lista **e** del drawer articolo (lista `catalogo.articoli`, id 26) |

⭐ **`giorni_ritardo` sta lì e non altrove**, ed è la scelta che evita un difetto:
il ritardo non è «oggi > data richiesta», è «oggi > data richiesta **e** resta
merce da spedire». Il residuo e la soglia dell'impegno vivono in
`vw_situazione_merce_ordine`, che li calcola già; metterlo altrove significherebbe
ricalcolarli, cioè creare una seconda verità sul residuo. ⛔ **NULL quando
`da_spedire` è NULL o zero**: «non è in ritardo» e «non c'è niente da spedire»
sono due cose diverse, e quella vista ha già la disciplina di non confonderle.

⚠️ **Due trappole tecniche su queste viste, entrambe verificate:**

1. **`CREATE OR REPLACE VIEW` può solo APPENDERE**: le colonne nuove finiscono
   **in ultima posizione**. Non è disordine da sistemare, ed è già dichiarato nel
   commento di `vw_ordini_lista`. Chi consuma per posizione si romperebbe: si
   consuma per nome.
2. **`security_invoker=on` va RI-SPECIFICATA** in ogni `CREATE OR REPLACE VIEW`,
   altrimenti PostgreSQL la azzera e la vista smette di rispettare l'RLS di chi
   la legge. È la reloption di tutte e tre.

⛔ **E un nome che il guardrail CI respinge**: `codice_interno AS *_codice` è
**vietato** (`linee-guida-sql` §6c, presidiato da
`scripts/sql/check_naming_stato_codice.sql`). Per questo la colonna decodificata
si chiama `modo_approvvigionamento_codice_interno` e **non** `..._codice`: quel
valore viene dalla colonna immutabile, e un consumatore che confronta contro un
`*_codice` si aspetta invece quella mutabile.

### 5.3 Le colonne di lista — sono **dato**, non DDL

La configurazione delle liste è una riga in `ui.lista_colonna` per colonna,
appesa al CSV `db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`.

| Lista | `lista_id` | Colonne nuove |
| --- | --- | --- |
| `vendite.ordini` | **7** | `data_consegna_richiesta_min` |
| `catalogo.articoli` | **26** | `modo_approvvigionamento`, `gestito_a_magazzino`, `lead_time_giorni` |

Per ogni riga vanno dati: `codice`, `etichetta`, `campo_sorgente` (il nome della
colonna **nella vista**), `tipo_colonna = informazione`, `tipo_dato`
(`date` / `boolean` / `numero`), `formato` (`date_short` per le date),
`larghezza_default`, `ordine_default`, `allineamento`, `gruppo`,
`filtrabile` / `ordinabile` / `esportabile`, `etichetta_i18n_key`, `priorita`.

⛔ **`sensibile` resta `f`.** Non è un'etichetta: è un **cancello** — a `t`, senza
il grant corrispondente, la colonna diventa **invisibile** e nessuno capisce
perché.

⚠️ **Il CSV si appende a mano.** `csv.writer` di Python pianta un CRLF e ri-quota
tutto il file: dopo l'append, `git diff --numstat` deve dare **`1 1`** e non un
rewrite di centinaia di righe.

⭐ **Non c'è niente da aspettare, sul FE.** Le liste si montano già con
`<ListaConfigurabile>`: una colonna nuova **compare come dato**, senza toccare un
componente. L'unica cosa che serve dall'altro lato sono le **traduzioni**.

### 5.4 Le chiavi i18n dichiarate qui

Le chiavi seguono la convenzione già in uso (`vendite.contratti.col_data`,
`vendite.ordini.col_data`). Sono queste, e il FE deve solo aggiungere il testo:

```
vendite.ordini.col_data_consegna_richiesta_min
vendite.ordini_righe.col_data_consegna_richiesta
vendite.ordini_righe.col_data_consegna_confermata
catalogo.articoli.col_modo_approvvigionamento
catalogo.articoli.col_gestito_a_magazzino
catalogo.articoli.col_lead_time_giorni
config.modi_approvvigionamento.acquisto
config.modi_approvvigionamento.produzione
config.modi_approvvigionamento.stock
config.modi_approvvigionamento.non_applicabile
```

### 5.5 Che cosa deve fare il BE

1. **Righe d'ordine — scrittura**: gli endpoint di creazione/aggiornamento riga
   (vendite e acquisti) devono accettare e persistere le due date. Sono
   nullable: ometterle resta legittimo.
2. **Drawer articolo — scrittura**: i tre campi nuovi nel payload del drawer, con
   il modo di approvvigionamento come **lookup** sul vocabolario.
3. **Lookup nuovo**: `config.modi_approvvigionamento` va esposto come le altre
   decodifiche (attivi, ordinati per `ordine`).
4. **Drawer commessa**: `descrizione` e `responsabile` in scrittura,
   `data_apertura` in sola lettura (la scrive il default).
5. **Niente da fare per la lista**: le colonne arrivano dalla configurazione.

⚠️ **Sulla commessa, un fatto che eviterà una ricerca a vuoto: non esiste una
lista configurata `vendite.commesse`.** In `ui.lista_definizione` ci sono
`vendite.commesse_attivita` (id 38, senza vista) e il drill-down di dashboard,
non la commessa. Le tre colonne del Blocco C hanno quindi come sola superficie il
**drawer/API**, finché una lista non verrà configurata — e configurarla è dato,
non un cantiere.

⛔ **Capability solo sul DETTAGLIO**: se serviranno azioni di riga governate, la
sede è il dettaglio, non la lista.

### 5.6 Che cosa NON arriva a BE/FE con questo brief

Niente che riguardi la produzione: **nessun ODL, nessuno stato di copertura,
nessun ciclo di lavorazione, nessun consuntivo**. Se compaiono in una richiesta,
non vengono da qui.

---

## 6. I passi

> ⚠️ La numerazione dei file (`YYYYMMDD-NN`) è **globale per data** e il numero
> libero **scade nel minuto**: si ricontrolla subito prima di salvare, non
> all'inizio del lavoro.

| # | Passo | Fase |
| --- | --- | --- |
| **P-1** | `config.modi_approvvigionamento`: tabella + seed + lock su `codice_interno` + `fk_index_policy` | `00_schema` + `80_data` |
| **P-2** | `catalogo.articoli`: le tre colonne (FK, boolean, integer) | `00_schema` |
| **P-3** | `vendite.ordini_righe` + `vendite.preventivi_righe` + `acquisti.ordini_righe`: le date | `00_schema` |
| **P-4** | `vendite.commesse`: `descrizione`, `data_apertura`, `responsabile_soggetto_ruolo_id` | `00_schema` |
| **P-5** | `fn_push_preventivo_a_ordine` porta avanti la data richiesta (+ toglie il nome morto nel commento) | `20_code` |
| **P-6** | `catalogo.vw_articoli_dettaglio` + `vendite.vw_ordini_lista` + `vendite.vw_situazione_merce_ordine` | `20_code` |
| **P-7** | `ui.lista_colonna`: le righe nuove, append al CSV | `80_data` |
| **P-8** | pgTAP (§7) | `db/pgtap` |

⛔ **L'ordine di fase non è negoziabile**: `00_schema` → `20_code` → `80_data`.
Una `preCondition` di `20_code` **non** deve verificare il *contenuto* di
`80_data`, che gira dopo.

⚠️ **Stato finale `runOnChange: false`** su schema e codice — è vietato e
presidiato in CI (`guardrail_run_on_change.py`); resta lecito solo sul mirror CSV
di `80_data`. E `validCheckSums` **al plurale**: il singolare è una chiave che
Liquibase ignora.

⛔ **Negli YAML si cita il NOME di questo brief**
(`brief-db-modifiche-certe-ciclo-vendita-e-articolo`), **mai il path
`work-in-progress/`**: il documento un giorno si sposterà, e il riferimento deve
sopravvivere al trasloco.

---

## 7. I presidi

| Test | Che cosa prova |
| --- | --- |
| `catalogo/test-articoli-approvvigionamento-v1` | il vocabolario ha i quattro valori; un articolo non può puntare a una riga **spenta**; il default è `ACQUISTO`; `lead_time_giorni` rifiuta il negativo |
| `vendite/test-date-consegna-ordine-v1` | le date si scrivono e si rileggono sulla riga; ⭐ **la data sopravvive al push** preventivo → ordine — provata sul **percorso reale**, chiamando `fn_push_preventivo_a_ordine`, non confrontando due colonne |
| `vendite/test-situazione-merce-ritardo-v1` | `giorni_ritardo` è **NULL** quando `da_spedire` è NULL o zero, ed è valorizzato solo sopra la soglia dell'impegno |

⚠️ **Un `has_column` sulle viste non basta**: prova che la colonna esiste, non
**da dove viene il valore**. Sulle tre viste il test deve confrontare il valore
con la sorgente, altrimenti passa anche se la colonna arriva dal posto sbagliato.

⚠️ **Preambolo obbligatorio** in ogni file (`BEGIN;`, riga di contesto,
`SET CONSTRAINTS ALL IMMEDIATE`), presidiato da
`scripts/guardrail_pgtap_preambolo.py`: senza, il file diventa verde **per
sottrazione**.

⚠️ E la suite ha **rossi preesistenti**: si confronta con
`scripts/pgtap-baseline.sh`, non si attribuisce un rosso a questo lavoro senza
averlo verificato.

---

## 8. Che cosa NON entra, e dove sta

| Voce | Dove vive | Perché non è qui |
| --- | --- | --- |
| Stato di **copertura** della riga d'ordine | analisi commessa §8.3 | se ODL e ordine d'acquisto saranno agganciati alla riga è **derivabile**: una colonna sarebbe una seconda verità. Va fatta vista, dopo la §7 |
| `uom_id` del componente e **sfrido** sulla BoM | analisi commessa §8.4 | dipendono dal fatto che la distinta di produzione sia o no `articoli_componenti`, che è **immutabile** per un altro motivo |
| **Consuntivo**, ODL, ciclo di lavorazione | analisi commessa §6 e §7 | sono **strutture**, non colonne, e stanno di là dalla decisione |
| Cliente proprio, budget, data di chiusura prevista sulla commessa | analisi commessa §8.5 ⏸️ | dipendono dalla §7 |
| `uq_mag_movimenti_docref`, `vw_giacenza`, causale di versamento, `ambito_causale_id` | analisi magazzino §5, §6, §9, D-4 e D-8 | ⚠️ **il fatto è certo, la forma è una decisione**: che vadano toccati non è in dubbio, *come* sì |
| Chi scrive un movimento di magazzino | analisi magazzino D-1 | la forma del riferimento al documento è la prima decisione aperta |

---

## 9. Riferimenti

* [analisi-db-commessa-e-produzione-predisposizione.md](analisi-db-commessa-e-produzione-predisposizione.md)
  — perché il punto di fermata non è la commessa, e la §8 da cui questo brief è estratto
* [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md)
  — le decisioni D-1 → D-8, nessuna delle quali tocca questo brief
* Convenzioni SQL (naming, §6c sul `codice_interno`): `docs/it/linee-guida-sql.md`
* Standard liste e `<ListaConfigurabile>`: `docs/it/dev/frontend/frontend-standards.md`
* Il residuo del nome morto in `fn_push_preventivo_a_ordine`:
  [brief-db-prefisso-sul-registro-e-allineamento-contatori.md](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) §6.3
