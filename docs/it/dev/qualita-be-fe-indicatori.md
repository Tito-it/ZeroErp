# Qualità di backend e frontend — indicatori e lezioni

> **Ultima rilettura**: 15 novembre 2026 (la precedente: 23 ottobre 2026)
>
> **Destinatari**: chi sviluppa su backend o frontend, e chi ogni tanto si chiede *«stiamo
> lavorando bene?»* e vuole una risposta che non sia un'impressione.
>
> **Vedi anche**:
>
> * [Sicurezza e qualità statica](sicurezza-e-qualita-statica.md) — gli **strumenti**: cosa
>   gira, dove, come si usa. Qui si legge ciò che quegli strumenti lasciano nei registri.
> * [Presidi e registri del debito](../guide/presidi-e-registri-del-debito.md) — la forma
>   comune: la misura, il registro, il verso.
> * La **lettura zero**: [migliorie generali BE/FE](work-done/2026/migliorie-generali-BE-FE-da-test-valutazione.md)
>   (09-09 → 23-10-2026), con i difetti trovati e come si sono chiusi.

---

## Come si legge

Questo documento non serve a dare un voto al progetto: serve a **non dimenticare le lezioni**
e a tenere d'occhio, nel tempo, i parametri che dicono se il lavoro sta peggiorando in silenzio.

Ha tre parti:

1. **le lezioni** (§1), che non scadono;
2. **gli indicatori** (§2): che cosa si legge, in che verso deve andare, chi lo presidia. I
   valori li stampa `scripts/indicatori-qualita-be-fe.sh`, e il comando **è** la definizione
   dell'indicatore;
3. **la scorecard pesata** (§3), riscritta a ogni rilettura.

⛔ **Regola zero** ([AGENTS.md](../../../.codex/AGENTS.md)): questi numeri **trovano gli errori,
non disegnano il progetto**. Un indicatore che peggiora è una domanda («perché?»), mai il motivo
di una scelta di modello. Sono letture di struttura del repo, e portano la loro data.

---

## 1. Le lezioni

Vengono dalla valutazione del 2026-09/10: ognuna ha un caso vero dietro, nella lettura zero.

* **Si pesa, non si fa la media.** Una media su dodici aree mette sullo stesso piano «i nomi dei
  file» e «che cosa impedisce a una regressione di entrare». Il peso di un'area è la
  **conseguenza** di un difetto lì, non la sua estensione.
* **Leggere il codice dice cosa manca; solo eseguirlo dice cosa è rotto.** Il job notturno rotto
  da quattro notti (D13), il `count` che era un'eco (D6), la mail «inviata» mai partita (D14):
  li ha trovati l'uso, non la lettura.
* **Un contratto si segue fino all'ultimo anello.** Un campo che nessuno legge non ha
  comportamenti sbagliati: ne ha di invisibili (`hint` mai reso a video, D4).
* **Un registro di debito non si conta: si legge.** Il difetto di D15 è rimasto per tre giorni
  dentro la riga degli `skip_area_check`, dietro un numero.
* **Un presidio che cerca una stringa nel sorgente si accende sulla spiegazione del difetto**
  che deve trovare: si legge il sorgente **senza commenti**.
* **Un test mockato verde non prova la forma vera.** Un mock sbaglia quando la forma che finge
  non è quella che arriva (D13); `mypy` ha trovato un 500 vero dietro un test verde (D2-b).
  `autospec` (dal 2026-11-08, sui repository) prova la **firma** — nome del metodo e parametri —
  non i dati restituiti. Il giro che l'ha messo ha trovato test che verificavano a vuoto (il
  conto è nell'intestazione del presidio).
* **Un numero scritto in due posti ne ha sempre uno vecchio**, e quello senza presidio è il
  documento. Per questo qui i valori li stampa lo script.
* **Un documento che dice il vero su un difetto non si corregge: si rende falso chiudendo il
  difetto.**
* **Un lavoro fermo su una decisione costa zero e resta fermo lo stesso**, finché nessuno fa la
  domanda. Un registro che non si muove da settimane va riletto per questo.
* **Una misura che non si è potuta prendere si scrive.** Taciuta, diventa una misura implicita.

---

## 2. Gli indicatori

Si stampano con:

```bash
scripts/indicatori-qualita-be-fe.sh          # tabella leggibile
scripts/indicatori-qualita-be-fe.sh --tsv    # per confrontare due letture con diff
```

Lo script legge **solo** il repo (niente DB, niente rete, un paio di secondi). `ruff`, `mypy`, i
guard e la suite hanno già un cancello in CI: qui si legge ciò che quei cancelli lasciano nei
registri, non si rilanciano.

La colonna «15-11» è la lettura di quel giorno. Si **sovrascrive** a ogni rilettura: la storia
sta in git.

### Frontend

| Indicatore | Verso | Chi lo presidia | 15-11 |
| --- | --- | --- | --- |
| file `.spec.js` / col DOM | ↑ | `vitest` in `ci-frontend` | 184 / 75 |
| guard in CI (`guard:*`) | ↑ quando nasce una regola | `npm run guards` | 15 |
| `DataTable` grezze / senza motivazione | ↓ | `check-datatable-baseline.mjs`, a cricchetto | 17 / 0 |
| agganci al DOM di PrimeVue (`.p-*`, `data-pc-*`) fuori dalle sedi / file | ↓ | `check-classi-interne-baseline.mjs`, a cricchetto (dal 2026-11-14) | 13 / 9 |
| filtri di lista scritti a mano | = 0 | `check-filtri-lista.mjs` | 0 |
| file con `<ListaConfigurabile>` / `<DrawerTabLista>` | colore: dice quanto è usato il BB | — | 77 / 27 |
| `axios` fuori da `core/api.js` · `v-html` · `console.log` | = 0 | `check-api-componenti.mjs`, lint | 0 · 0 · 0 |
| chiavi i18n / in una sola lingua | = 0 la seconda | `check_i18n_keys.py`, pre-commit e CI | 5.971 / 0 |
| `.vue` / con `useI18n` | colore | — | 465 / 382 |

### Backend

| Indicatore | Verso | Chi lo presidia | 15-11 |
| --- | --- | --- | --- |
| rilievi `mypy` nel registro | = 0 | `check_mypy_baseline.py` in `ci-validate` | 0 |
| codici errore a catalogo / ritirati / vivi | colore; lo zero che conta è quello del test | `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | 1.236 / 131 / 1.105 |
| messaggi d'errore `it` / `en` | ↑ la seconda | — (il catalogo a monte è monolingue) | 1.230 / 4 |
| view su `DomainAPIView` / `AdminAPIView` / `APIView` nudo | `APIView` nudo = solo pre-autenticazione | revisione | 508 / 90 / 8 |
| sottoclassi di `PortaleAPIView` / `ShopAPIView` | cresce col cantiere portali | — | 1 / 0 |
| righe `skip_area_check = True` | si **legge**, non si conta | `test_skip_area_check_registro.py` | 75 |
| `def` con `# Scopo:` sopra / `def` | ↑ fino all'uguale | — ⚠️ nessun presidio | 4.051 / 4.675 |
| file di test / con mock / sul DB vero | ↑ il terzo | `ZEROERP_TEST_DB_E2E=1` in CI | 731 / 413 / 195 |
| smoke non-verdi noti / smoke | ↓ il primo | `smoke-baseline.sh`, ogni notte (`smoke_notturno`) | 0 / 52 |

⚠️ **`# Scopo:`, il 2026-10-23.** La lettura zero scriveva «99%» (3.809 su 3.815, il 09-09):
contava i commenti nel file, compresi quelli sulle classi. Contando per `def`, come chiede
[api.md](api.md) («prima di ogni `def`»), sono **3.978 su 4.593**. Non è un peggioramento: è
la prima misura giusta. È anche l'unico indicatore della tabella senza presidio. Il
2026-11-15 sono **4.051 su 4.675** (86,7%, fermo): degli 82 `def` nuovi, 9 sono nati senza.

⚠️ **`skip_area_check`, il 2026-11-15.** Il solo nato dal 23-10 è `LookupAzioniRigaView`
([views_lookup.py](../../../backend/apps/core/api/views_lookup.py), 2026-10-27): serve il
registro `config.azioni_riga` alle liste di ogni documento. È configurazione, non dato di
business, e il motivo è scritto nella docstring.

### Fuori dallo script: la copertura della doc API

Lo script legge solo file; questa misura chiede l'URLconf, quindi Django avviato (non il DB):

```bash
cd backend && ./manage-env.sh copertura_doc_api              # per area
cd backend && ./manage-env.sh copertura_doc_api --dettaglio  # le rotte scoperte, una per una
```

| Indicatore | Verso | Chi lo presidia | 15-11 |
| --- | --- | --- | --- |
| rotte documentate / rotte · scoperte · fantasmi | = 0 le ultime due | cancello a zero dal 2026-11-15: `test_copertura_doc_api_cancello.py` nella suite Django (la misura la prova `test_copertura_doc_api.py`) | 731 / 731 · 0 · 0 |

⚠️ **Il 2026-11-15.** La prima lettura del giorno dava **727 su 731**: quattro rotte di
`anagrafiche` nate coi due giri BE/FE dello stesso giorno (copia indirizzo sul soggetto e sul
ruolo, motivi del cambio di natura, eliminazione dei dati societari). Documentate lo stesso giorno
([api_soggetti.md](../backend/anagrafiche/manual/api_soggetti.md) §8.3, §13, §14;
[api_indirizzi_ruolo.md](../backend/anagrafiche/manual/api_indirizzi_ruolo.md) §5). La scorecard
del 23-10 scriveva «presidiata (722/722)»: il presidio c'è, ma sulla correttezza del conto. Che il
conto restasse a zero non lo impediva niente, ed è per questo che quelle quattro rotte sono nate
senza pagina. Dallo stesso giorno lo impedisce il cancello, che gira in `ci-validate` anche quando
cambia solo `docs/it/backend/**`. Provandolo nel verso rosso è emersa la **trappola 10** del
comando: la rotta del ruolo senza pagina risultava coperta dal pezzo di un esempio `curl` del
soggetto, spezzato ai puntini. Il verso permissivo, corretto nella misura e presidiato da un caso
costruito.

### Che cosa non si misura, e perché

| Cosa | Perché no |
| --- | --- |
| Copertura vera della suite | Nel progetto non c'è `coverage`: il numero di test è un limite superiore, non una misura |
| Header di licenza mancanti | L'hook guarda solo i file **aggiunti**, per scelta; un conteggio sull'intero repo non ha ancora un comando |
| Endpoint senza consumatore | Le famiglie cross-dominio sono chiamate col dominio come parametro: uno strumento testuale non le vede ([piano](work-done/2026/piano-be-fe-endpoint-senza-porta.md)) |
| Rilievi `ruff`, `oxlint` | Sono già un cancello a zero: se sono rossi, la CI è rossa |
| Patch di repository senza `autospec` | Cancello a zero dal 2026-11-08: `test_presidio_autospec_repository` gira nella suite Django, quindi in CI |

---

## 3. La scorecard pesata — rilettura del 2026-11-15

Il **peso** è la conseguenza di un difetto nell'area. Un voto che si muove dice il suo perché;
uno fermo dice che cosa lo tiene fermo. «Era» è il voto della rilettura precedente (2026-10-23).

| Area | Peso | Voto | Era | Che cosa lo tiene dov'è |
| --- | --- | --- | --- | --- |
| Catena di verifica — frontend | 🔴 alto | **8** | 7,5 | Cancello in CI, `npm audit`; i test di componente sono saliti a 184 (75 col DOM), i guard a 15. Manca la prova del percorso a video (end-to-end) e una misura di copertura |
| Analisi statica — backend | 🔴 alto | **8,5** | 8,5 | `ruff` e `mypy` a registro zero con cancello. `E`/`B` di `ruff` spenti per scelta scritta, `mypy` non `strict` |
| Catena di verifica — backend | 🔴 alto | **8,5** | 8,5 | Cancello duro, `check --deploy` completo, smoke ogni notte e tutti verdi, test sul DB vero da 145 a 195. Suite in maggioranza mockata; gli smoke non sono un cancello prima del merge |
| Contratto API pubblicato | 🟠 medio | **9,5** | 9,5 | Schema OpenAPI a zero rilievi con cricchetto; i difetti dell'idempotenza forte sono chiusi ([brief](work-done/2026/brief-be-verifica-documentazione-api.md) §D5-D7). Copertura della doc API a 731/731, e dal 2026-11-15 con un cancello che la tiene a zero (§2, «Fuori dallo script»): prima era solo misurata, e quattro rotte erano nate senza pagina |
| Contratto d'errore — lato backend | 🟠 medio | **9** | 9 | Zero codici vivi senza ripiego; la classe sbagliata di §D1 è chiusa. La `soluzione` del catalogo non arriva per gli errori sollevati in Python: scelta di disegno BE ancora aperta (stesso brief, §D4) |
| Contratto d'errore — arrivo a video | 🟠 medio | **8** | 8 | `fields`, `targets`, `hint` a video. `notify.error` a mano resta fuori |
| Perimetro e permessi (applicativo) | 🟠 medio | **8,5** | 8 | Catena unica, fail-closed; letture con lo skip lette una per una (l'unico nuovo, §2, è giusto). La chiave d'idempotenza è legata a utente ed endpoint (§D7). Il controllo nel corpo resta invisibile al presidio |
| Correttezza dei contratti di lista | 🟠 medio | **8** | 8 | `troncato` presidiato sul DB vero. Nessun cancello sui `count: len()` senza `LIMIT` |
| Simmetria del dominio | 🟠 medio | **non votata** | — | BE/FE di `acquisti`/`magazzino` indietro sul DB è l'ordine di costruzione scelto, non un difetto. Si presidia la regola: *ogni decisione su `vendite` vale per `acquisti`* |
| Building block — frontend | 🟡 basso | **9** | 9 | Un solo punto HTTP, 15 guard; le `DataTable` senza motivazione sono a zero. Nuovo registro a cricchetto degli agganci al DOM di PrimeVue (13 in 9 file), legato al [piano PrimeVue 5](work-in-progress/piano-migrazione-primevue-5.md) |
| Multilingua | 🟡 basso | **9** | 9 | Parità delle chiavi presidiata. Il catalogo dei messaggi a monte è monolingue (4 messaggi `en` su 1.230) |
| Gestione del debito | 🟡 basso | **9** | 8,5 | Ogni registro ha un verso, e due sono arrivati in fondo: `DataTable` senza motivazione e smoke non-verdi a zero. `# Scopo:` resta senza presidio e non sale |
| Documentazione di contesto | 🟡 basso | **9** | 9 | Doc API di nuovo completa (731/731). Questo documento diceva «copertura presidiata» per un presidio che provava il conto, non lo zero: ora c'è anche il cancello |

---

## 4. Quando e come si rilegge

* **Quando**: alla chiusura di un cantiere grosso, o quando un indicatore si muove senza che
  nessuno sappia perché. Non a calendario: una rilettura senza niente di nuovo è rumore.
* **Come**: si lancia lo script, si confronta con la colonna della rilettura precedente, e per
  ogni riga che si è mossa ci si chiede **perché**. Poi si riscrivono la colonna di §2, la data
  in testa e i voti di §3 che hanno un motivo per muoversi.
* ⛔ **Un indicatore nuovo** entra nello script **e** nella tabella di §2 nello stesso giro, col
  suo verso e il suo presidio (o col «nessun presidio» scritto). Uno solo dei due non basta.
* ⭐ Un difetto trovato rileggendo **non si scrive qui**: va nel brief del suo tema (regola «un
  tema, un brief», [AGENTS.md](../../../.codex/AGENTS.md)). Qui pesa solo sul voto.

---

## 5. Il lato database

Lo strato DB ha il suo documento gemello,
[qualita-db-indicatori.md](qualita-db-indicatori.md) (dal 2026-10-23), con lo stesso formato e
`scripts/indicatori-qualita-db.sh`; la sua lettura zero,
[migliorie-generali-da-test-valutazione.md](work-in-progress/migliorie-generali-da-test-valutazione.md),
è ancora aperta. Un indicatore di confine vive in uno solo dei due. Il punto d'incontro è la
[mappa concentrica](../mappa-concentrica.md) §4 «La qualità si misura».
