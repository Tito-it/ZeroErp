# Brief DB — il registro e la data che il documento prenderà, in lista

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono** i prerequisiti
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** Tid, 2026-08-26, dopo un caso reale: *«sulle liste competenza
> fattura non si può aggiungere se front/back, in pratica il tipo di registro?»*
> La domanda nasce da mezz'ora persa a capire perché un documento appena
> generato portasse la data del 31 luglio.
>
> **Correlati:** [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md)
> (il cantiere che ha reso la data una decisione del registro) ·
> [analisi-numerazione-fattura-data-e-sequenza.md](analisi-numerazione-fattura-data-e-sequenza.md)
>
> ✅ **Decisioni prese** (Tid, 2026-08-26): D-2 «più registri» con data vuota,
> D-3 nessuna colonna sulla lista per commessa. D-1 verificata sul codice.
>
> ⛔ **Stato: pronto per il team DB. Nessun file scritto.**

---

## 1. Il caso che lo motiva

Il 2026-08-25 Tid fattura un gruppo dalla Dashboard Competenza di **luglio**.
Nasce il lotto `LTF-0007307` con dentro un documento datato **31/07/2026**, e
lui se lo aspettava datato agosto — il giorno in cui stava lavorando.

Non è un difetto: il gruppo finiva sul registro **Back-office**, politica
`FINE_MESE_COMPETENZA`, quindi una competenza luglio produce un documento
datato l'ultimo giorno di luglio. È il comportamento voluto dal cantiere della
numerazione. **Ma non era scritto da nessuna parte prima di premere.**

⭐ La schermata da cui si decide di fatturare non dice né su quale **sezionale**
finirà il documento, né **che data** porterà. Sono le due informazioni che
governano tutto ciò che viene dopo — la sequenza dei numeri, la scheda
«recuperi del mese», il termine di trasmissione — e si scoprono a cose fatte.

---

## 2. Cosa si aggiunge: due colonne, e perché due

| colonna | cosa dice | perché |
| --- | --- | --- |
| `registro_codice` | `Front-office` / `Back-office` / … | è il **perché**: la politica della data vive sul registro |
| `data_documento_prevista` | `2026-07-31` | è il **cosa**: la data che il documento prenderà |

⭐ **Da sola la prima non basta**, ed è il motivo per cui sono due: «Back-office»
obbliga chi legge a tradurre registro → politica → data. La seconda risponde
alla domanda vera. La prima resta perché quando la data sorprende, il registro
è la spiegazione.

⚠️ **`data_documento_prevista` è una PREVISIONE, e il nome deve dirlo.** La
calcola `vendite.fn_calcola_data_documento(registro, competenza, NULL)`: è la
data che nascerà **se nessuno ne dichiara un'altra**. Un lotto creato con una
data dichiarata la scavalca — e va bene così, purché la colonna non prometta
una certezza.

**Su quale lista: la 42**, `vendite.dash_competenza_gruppi` — la lista da cui si
fattura. È lì che la domanda si pone, ed è lì che la risposta serve.

⚠️ **Non sulla 43** (`dash_competenza_commesse`), e non è una dimenticanza:
quella lista è aggregata **per commessa** (`n_attivita`, `valore_tot`,
`valore_fatturato_tot`), e una commessa attraversa per definizione più gruppi —
quindi potenzialmente più registri e più date. Metterci una colonna «registro»
vorrebbe dire mostrare «più registri» quasi sempre, cioè una colonna che non
informa. ✅ **D-3 DECISA** (Tid, 2026-08-26): **no**, la colonna non va sulla
lista per commessa. La lista errori (41) non c'entra.

---

## 3. ⛔ IL PUNTO DEL CANTIERE: la regola va LETTA, non riscritta

Il registro lo decide oggi `vendite.fn_build_fattura_key`, con questa catena:

```sql
-- da vendite.attivita_fatturabili a  JOIN anagrafiche.billing_account ba
v_ba_id         := a.billing_account_id
v_ba_fattura_id := COALESCE(ba.parent_account_id, a.billing_account_id)
v_utility_id    := ba.utility_id                      -- ⚠️ dalla BA DELLA RIGA
v_emittente_id  := anagrafiche.fn_get_emittente_fiscale_id(v_ba_fattura_id)
                                                      -- ⚠️ dalla BA DI FATTURAZIONE
(registro, serie) := vendite.fn_get_registro_id(tipo_doc, natura, utility, emittente)
```

⚠️ **Due ancoraggi diversi nella stessa chiave**: l'utility viene dalla BA della
riga, l'emittente dalla BA **di fatturazione** (il parent, quando c'è). Chi
ricopia la catena a occhio li scambia, e il difetto è silenzioso: la lista
mostrerebbe un registro e la fattura ne prenderebbe un altro.

⛔ **Ricopiare quella catena dentro le viste sarebbe una SECONDA implementazione
della stessa regola.** Non è un'ipotesi: è la classe di difetto che questo mese
ha già prodotto due incidenti — il messaggio del dialog che annunciava il
pavimento di un altro sezionale, e la colonna `riaperto` che leggeva l'indice
sbagliato. Una previsione che mente è peggio di una previsione assente.

### 3.1 ⭐ La forma giusta: estrarre, e chiamare in due

Nuova funzione che incapsula la catena **per intero**, dagli ingressi grezzi:

```sql
vendite.fn_resolve_registro_documento(
    p_billing_account_id  bigint,
    p_tipo_doc_fiscale_id bigint,
    p_natura_doc_id       bigint
) RETURNS TABLE(registro_id bigint, serie varchar,
                politica_data_documento varchar)
```

e **due chiamanti**:

* `fn_build_fattura_key` — che smette di risolvere in proprio e chiama questa
  (rifattorizzazione **a comportamento invariato**);
* le due viste della dashboard.

⭐ È la disciplina di [[feedback_estrarre_non_condividere_stato]] applicata a una
regola invece che a un oggetto: **si condivide la funzione, non una copia della
sua logica**. Ed è ciò che rende la colonna una lettura e non una profezia.

⚠️ **La rifattorizzazione va provata sul risultato, non sulla lettura del
codice**: per ogni fattura esistente il registro risolto dalla funzione nuova
deve coincidere con `fatture.registro_id` già scritto. È un confronto secco su
dati veri, e senza quello la «rifattorizzazione a comportamento invariato» è
una promessa.

---

## 4. ⛔ Il ponte NON c'è dove serve: misurato

L'idea più naturale — leggere gli ingressi da `attivita_fatturabili`, come fa
`fn_build_fattura_key` — **non funziona proprio sulla popolazione che conta**.
Misurato il 2026-08-26:

| stadio | con riga in `attivita_fatturabili` | SENZA |
| --- | ---: | ---: |
| **DA_EMETTERE** | 2 | **46** |
| EMESSA_NON_FATTURATA | 5 | 0 |
| FATTURATA | 43 | 0 |

⭐ **46 su 48.** La riga in `attivita_fatturabili` nasce all'**emit**: prima di
fatturare non esiste. E «prima di fatturare» è esattamente il momento in cui la
colonna serve — è il senso della richiesta.

⚠️ Le 2 con la riga sono l'eccezione che spiega la regola: vengono da un lotto
**annullato**, e la riga è sopravvissuta al reset (è il «vaso» che il ri-emit
riempie di nuovo).

⛔ Conseguenza: la funzione di §3.1 deve accettare gli ingressi **grezzi**
(`billing_account_id`, `tipo_doc_fiscale_id`, `natura_doc_id`) e non un
`attivita_fatturabile_id`. Solo così serve entrambi i lati: chi ha già la riga
e chi non ce l'ha ancora.

### 4.1 ❓ La domanda aperta che ne discende (D-1)

`vendite.commesse_attivita` **non ha** `billing_account_id`: la BA sta sulla
**commessa** (`vw_dash_competenza_attivita.billing_account_id = co.billing_account_id`).
`attivita_fatturabili` invece ce l'ha **per riga**.

**Sono sempre la stessa?** Se l'emit copia la BA della commessa su ogni riga,
sì e la vista può usare quella della commessa. Se esiste un percorso che la
cambia per riga (destinatario diverso, split), allora **no**, e la previsione
sarebbe sbagliata proprio nei casi non banali.

⚠️ Non l'ho verificato e non lo do per buono: è la prima cosa da guardare, e la
risposta decide se la vista può fermarsi alla commessa o deve arrivare alla
riga.

---

## 5. ⚠️ Un gruppo può toccare PIÙ registri

La chiave del gruppo (`fn_build_gruppo_fatturabile_key`) è
`(sorgente_tipo, sorgente_uid, commessa)`: **non contiene tipo documento né
natura**. Un gruppo con righe di tipo diverso si separa in terne diverse e
finisce su registri diversi — è un fatto già noto e dichiarato («un gruppo con
righe di tipo doc fiscale diverso finisce in terne diverse»).

Quindi sulla lista **gruppi** le due colonne sono «uno oppure N»:

* un solo registro → il codice e la data;
* più registri → una dicitura esplicita (`più registri`), **mai il primo che
  capita**. ⛔ Un `min()` o un `LIMIT 1` qui sarebbe la stessa bugia del dialog:
  un valore plausibile che descrive solo una parte di ciò che sta per succedere.

Sulla lista **attività** (drill-down) il registro è invece sempre uno solo.

✅ **D-2 DECISA** (Tid, 2026-08-26): quando i registri sono più d'uno, il
registro mostra **«più registri»** e la data prevista resta **vuota**. Una data
sola su un gruppo che ne produrrà due è di nuovo una mezza verità.

---

## 6. Le consegne

| | Cosa |
| --- | --- |
| **DB-1** | `vendite.fn_resolve_registro_documento(ba, tipo_doc, natura)` → `(registro_id, serie, politica_data_documento)`. Incapsula la catena del §3, `parent_account_id` e i **due ancoraggi** compresi |
| **DB-2** | `fn_build_fattura_key` chiama DB-1 invece di risolvere in proprio. ⚠️ Comportamento invariato, **provato sul risultato**: per ogni fattura esistente il registro risolto deve coincidere con `fatture.registro_id` |
| **DB-3** | `vw_dash_competenza_attivita`: due colonne nuove via DB-1 (+ `fn_calcola_data_documento`) |
| **DB-4** | `vw_dash_competenza_gruppi`: le stesse due, con la regola «uno oppure N» del §5 |
| **DB-5** | Seed `ui.lista_colonna` per le liste **42** e **43** (vedi §7) |
| **DB-6** | pgTAP: DB-1 risolve come la catena vecchia su casi reali; un gruppo multi-registro non mostra un registro solo; la data prevista di un registro `FINE_MESE_COMPETENZA` è l'ultimo giorno della competenza, di uno `OGGI` è la data operativa |

---

## 7. Il seed delle colonne (DB-5)

Lista **42** (`vendite.dash_competenza_gruppi`) — ordini liberi dopo `valore` (60)
e `data_attivita_max` (70), priorità libere sotto 60. Verificato sul CSV: gli
ordini 75/78 e le priorità 45/50 non collidono con le undici colonne già a
catalogo.

| campo | `registro` | `data_documento_prevista` |
| --- | --- | --- |
| `campo_sorgente` | `registro_codice` | `data_documento_prevista` |
| `tipo_dato` / `formato` | `string` / — | `date` / `date_short` |
| `ordine_default` | 75 | 78 |
| `priorita` | 45 | 50 |
| `larghezza` / `allineamento` | 140 / left | 120 / center |
| `filtrabile` / `ordinabile` | `t` / `t` | `f` / `t` |
| `etichetta_i18n_key` | `vendite.dashboard_competenza.col_registro` | `vendite.dashboard_competenza.col_data_prevista` |

⚠️ Il namespace i18n è **`vendite.dashboard_competenza`** (`dashboard_`, non
`dash_`): è quello delle undici colonne già a catalogo — `col_commessa`,
`col_cliente`, `col_valore`… Sbagliarlo non dà un errore, dà una **colonna
senza intestazione**, e il guard i18n lo vede solo perché controlla proprio
questo.

⚠️ `filtrabile = t` sul registro **sì**, ed è il caso opposto a
`lotti.data_documento`: qui la colonna è valorizzata su **tutte** le righe, e
«mostrami solo ciò che finisce sul Back-office» è una domanda che si fa.
Sulla data prevista `f`: è derivata, e un filtro su un valore calcolato promette
una precisione che non ha.

⛔ **Due prerequisiti, o il seed sanguina** — entrambi già pagati questo mese:

1. `ordinabile = t` vuole la voce nella **whitelist di ordinamento** del
   repository (`DASH_COMPETENZA_GRUPPI_SORT_COLUMNS`), o la freccia risponde
   400. Presidiato da `test_liste_configurabili_seed`;
2. `etichetta_i18n_key` vuole la chiave in `it.json` **e** `en.json`, o
   `check_i18n_keys.py` fallisce in CI.

Sono lavoro BE/FE: vanno fatti **prima** del seed, o insieme.

---

## 8. Cosa parte dopo

| | Consegna |
| --- | --- |
| BE-1 | Proiezione delle due colonne nella lista gruppi (`vendite_repository`, la `SELECT` su `vw_dash_competenza_gruppi`) |
| BE-2 | Voci in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` (nome verificato nel repository) |
| BE-3 | Chiavi `vendite.dashboard_competenza.col_registro` / `col_data_prevista` (it **e** en) |
| FE-1 | Nulla di strutturale: le liste sono `<ListaConfigurabile>` e prendono le colonne dal catalogo. Da guardare solo la resa di «più registri» |

---

## 9. Cosa NON è in questo cantiere

* **La politica della data** in sé: se un arretrato di luglio lavorato oggi
  debba portare la data di luglio o quella di oggi è una decisione **aperta** di
  Tid, e da lì dipende un'eventuale terza politica sul registro. Questo cantiere
  rende visibile ciò che succede, non cambia ciò che succede.
* **La scheda «recuperi del mese»**, che con `FINE_MESE_COMPETENZA` è vuota per
  costruzione (il suo criterio è la data del documento, che ha smesso di dire
  «quando l'ho fatto»). Cantiere suo, e la decisione è la stessa del punto
  sopra.
* Il **filtro per registro** sulla lista lotti: qui si parla delle liste di
  competenza.

---

## 10. Registro

### 2026-08-26 · Analisi e consegna

Richiesta di Tid dopo il caso `LTF-0007307`. Misurato sul DB vivo: il registro è
risolvibile dagli ingressi già disponibili, ma **il ponte `attivita_fatturabili`
non esiste su 46 righe DA_EMETTERE su 48** — quindi la funzione va scritta sugli
ingressi grezzi, e la catena va estratta invece che ricopiata. **Nessuna domanda resta aperta**: D-1 verificata sul codice che scrive la
colonna (§4.1), D-2 e D-3 decise da Tid lo stesso giorno.

⚠️ Due dettagli corretti prima di consegnare, entrambi del tipo che finisce
copiato in un seed e fallisce in CI: la lista 43 è aggregata **per commessa**
(non per attività) e il namespace i18n è `dashboard_competenza`, non
`dash_competenza`.
