# Qualità di backend e frontend — indicatori e lezioni

> **Ultima rilettura**: 23 ottobre 2026
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
> * La **lettura zero**: [migliorie generali BE/FE](work-done/migliorie-generali-BE-FE-da-test-valutazione.md)
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

La colonna «23-10» è la lettura di quel giorno. Si **sovrascrive** a ogni rilettura: la storia
sta in git.

### Frontend

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| file `.spec.js` / col DOM | ↑ | `vitest` in `ci-frontend` | 140 / 53 |
| guard in CI (`guard:*`) | ↑ quando nasce una regola | `npm run guards` | 13 |
| `DataTable` grezze / senza motivazione | ↓ | `check-datatable-baseline.mjs`, a cricchetto | 28 / 9 |
| filtri di lista scritti a mano | = 0 | `check-filtri-lista.mjs` | 0 |
| file con `<ListaConfigurabile>` / `<DrawerTabLista>` | colore: dice quanto è usato il BB | — | 75 / 24 |
| `axios` fuori da `core/api.js` · `v-html` · `console.log` | = 0 | `check-api-componenti.mjs`, lint | 0 · 0 · 0 |
| chiavi i18n / in una sola lingua | = 0 la seconda | `check_i18n_keys.py`, pre-commit e CI | 5.819 / 0 |
| `.vue` / con `useI18n` | colore | — | 458 / 375 |

### Backend

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| rilievi `mypy` nel registro | = 0 | `check_mypy_baseline.py` in `ci-validate` | 0 |
| codici errore a catalogo / ritirati / vivi | colore; lo zero che conta è quello del test | `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | 1.126 / 120 / 1.006 |
| messaggi d'errore `it` / `en` | ↑ la seconda | — (il catalogo a monte è monolingue) | 1.120 / 2 |
| view su `DomainAPIView` / `AdminAPIView` / `APIView` nudo | `APIView` nudo = solo pre-autenticazione | revisione | 505 / 89 / 8 |
| sottoclassi di `PortaleAPIView` / `ShopAPIView` | cresce col cantiere portali | — | 1 / 0 |
| righe `skip_area_check = True` | si **legge**, non si conta | `test_skip_area_check_registro.py` | 74 |
| `def` con `# Scopo:` sopra / `def` | ↑ fino all'uguale | — ⚠️ nessun presidio | 3.978 / 4.593 |
| file di test / con mock / sul DB vero | ↑ il terzo | `ZEROERP_TEST_DB_E2E=1` in CI | 662 / 393 / 145 |
| smoke non-verdi noti / smoke | ↓ il primo | `smoke-baseline.sh`, ogni notte (`smoke_notturno`) | 2 / 51 |

⚠️ **`# Scopo:`, il 2026-10-23.** La lettura zero scriveva «99%» (3.809 su 3.815, il 09-09):
contava i commenti nel file, compresi quelli sulle classi. Contando per `def`, come chiede
[api.md](api.md) («prima di ogni `def`»), sono **3.978 su 4.593**. Non è un peggioramento: è
la prima misura giusta. È anche l'unico indicatore della tabella senza presidio.

### Che cosa non si misura, e perché

| Cosa | Perché no |
| --- | --- |
| Copertura vera della suite | Nel progetto non c'è `coverage`: il numero di test è un limite superiore, non una misura |
| Header di licenza mancanti | L'hook guarda solo i file **aggiunti**, per scelta; un conteggio sull'intero repo non ha ancora un comando |
| Endpoint senza consumatore | Le famiglie cross-dominio sono chiamate col dominio come parametro: uno strumento testuale non le vede ([piano](work-in-progress/piano-be-fe-endpoint-senza-porta.md)) |
| Rilievi `ruff`, `oxlint` | Sono già un cancello a zero: se sono rossi, la CI è rossa |

---

## 3. La scorecard pesata — rilettura del 2026-10-23

Il **peso** è la conseguenza di un difetto nell'area. Un voto che si muove dice il suo perché;
uno fermo dice che cosa lo tiene fermo. «Era» è il voto della rilettura precedente.

| Area | Peso | Voto | Era | Che cosa lo tiene dov'è |
| --- | --- | --- | --- | --- |
| Catena di verifica — frontend | 🔴 alto | **7,5** | 7 | Cancello in CI, test di componente diventati la norma, `npm audit`. Manca la prova del percorso a video (end-to-end) e una misura di copertura |
| Analisi statica — backend | 🔴 alto | **8,5** | 6,5 | `ruff` e `mypy` a registro zero con cancello. `E`/`B` di `ruff` spenti per scelta scritta, `mypy` non `strict` |
| Catena di verifica — backend | 🔴 alto | **8,5** | 8 | Cancello duro, `check --deploy` completo, smoke ogni notte, test sul DB vero in crescita. Suite in maggioranza mockata; gli smoke non sono un cancello prima del merge |
| Contratto API pubblicato | 🟠 medio | **9,5** | 9 | Schema OpenAPI a zero rilievi con cricchetto; copertura della doc API presidiata (722/722). Aperti al team DB i tre difetti dell'idempotenza forte ([brief](work-done/brief-be-verifica-documentazione-api.md) §D5-D7) |
| Contratto d'errore — lato backend | 🟠 medio | **9** | 9 | Zero codici vivi senza ripiego. Un codice con la classe sbagliata e la `soluzione` che non arriva per gli errori sollevati in Python (stesso brief, §D1 e §D4) |
| Contratto d'errore — arrivo a video | 🟠 medio | **8** | 8 | `fields`, `targets`, `hint` a video. `notify.error` a mano resta fuori |
| Perimetro e permessi (applicativo) | 🟠 medio | **8** | 7,5 | Catena unica, fail-closed; letture con lo skip lette una per una. Il controllo nel corpo è invisibile al presidio; la chiave d'idempotenza non è legata a utente ed endpoint |
| Correttezza dei contratti di lista | 🟠 medio | **8** | 8 | `troncato` presidiato sul DB vero. Nessun cancello sui `count: len()` senza `LIMIT` |
| Simmetria del dominio | 🟠 medio | **non votata** | — | BE/FE di `acquisti`/`magazzino` indietro sul DB è l'ordine di costruzione scelto, non un difetto. Si presidia la regola: *ogni decisione su `vendite` vale per `acquisti`* |
| Building block — frontend | 🟡 basso | **9** | 9 | Un solo punto HTTP, 13 guard. Le `DataTable` senza motivazione aspettano decisioni nel [piano PrimeVue 5](work-in-progress/piano-migrazione-primevue-5.md) |
| Multilingua | 🟡 basso | **9** | 9 | Parità delle chiavi presidiata. Il catalogo dei messaggi a monte è monolingue |
| Gestione del debito | 🟡 basso | **8,5** | 8 | Ogni registro ha un verso; quello degli smoke è sceso davvero. Le `DataTable` ferme dal 06-10; `# Scopo:` senza presidio |
| Documentazione di contesto | 🟡 basso | **9** | 9 | Copertura della doc API presidiata. Un numero di questo stesso documento era sbagliato per metodo (`# Scopo:`, §2) |

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
