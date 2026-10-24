# API Registri di numerazione — la superficie di SCRITTURA

## Scopo

I registri (`vendite.registri_fatturazione`) sono i sezionali che assegnano il
numero ai documenti. Questa pagina documenta **quali campi si possono scrivere,
con quale verbo e perché** — non l'intero CRUD, che sta in
[brief-be-fe-crud-registri-di-numerazione](/dev/work-done/brief-be-fe-crud-registri-di-numerazione).

> ⭐ **Perché proprio questa tabella, e perché una pagina sua.** L'elenco dei
> campi scrivibili è l'unica cosa che separa un registro da un contatore rotto:
> ogni campo che entra nella **chiave del contatore** — la serie, la politica di
> reset — se cambiato dopo il primo numero fa ripartire il progressivo da 1 su
> una chiave nuova, contro numeri che esistono già.
> ⛔ E l'esclusione di un campo **va motivata dove si legge**: fino al
> 2026-09-08 `reset_policy` era esclusa da entrambi i verbi con la motivazione
> «è inchiodata dal CHECK», scaduta il giorno stesso in cui fu scritta. La
> conseguenza non è stata un errore, ma una politica **accesa nel database e
> irraggiungibile dall'applicazione**, per una settimana e senza che niente
> diventasse rosso.

## Endpoint

| Metodo | Path | Cosa fa |
| --- | --- | --- |
| `GET` | `/api/v1/vendite/registri/` | Lista (ricerca, ordinamento, paginazione) |
| `GET` | `/api/v1/vendite/registri/<id>/` | Dettaglio + contatori + motivi di blocco |
| `POST` | `/api/v1/vendite/registri/` | Creazione (emittente nel payload, **verificato** contro lo scope) |
| `PATCH` | `/api/v1/vendite/registri/<id>/` | Modifica delle sole colonne ammesse |
| `POST` | `/api/v1/vendite/registri/<id>/attivo/` | Accende / spegne — verbo suo, è la **riattivazione** |

Sede della verità: `_CAMPI_CREATE` / `_CAMPI_UPDATE` in
`apps/vendite/db/registri_repository.py`. ⛔ Le due tuple **sono** il presidio:
per i campi qui sotto marcati «nessun guard» non c'è nessun trigger che
rifiuti, quindi allargarle non produce un errore — produce un contatore rotto.

## I campi, per verbo

| Campo | CREATE | UPDATE | Perché |
| --- | :---: | :---: | --- |
| `codice`, `descrizione` | ✅ | ✅ | Etichette, non entrano in nessuna chiave |
| `famiglia_documento`, `utility_id` | ✅ | ⛔ | Cambiarle sposta il registro di **slot** (`uq_..._famiglia_emittente_utility`): è una creazione, non una modifica |
| `serie_default` | ✅ | ⛔ | Entra nella **chiave del contatore**, e il mirror CSV la riscrive a ogni migrate. ⚠️ Si **legge** in maschera (spiega da dove viene la serie dei numeri) ma non si scrive |
| `reset_policy` | ✅ | ⛔ | ⭐ Dal 2026-09-08. Idem: è l'asse `anno` della chiave del contatore — vedi sotto |
| `prefisso`, `suffisso`, `lunghezza_numero` | ✅ | ✅ | ⭐ In update **dal 2026-09-01**: a rifiutare è il trigger `trg_registri_fatturazione_a10_guard_forma_numero_upd` sul registro che ha già consegnato un numero, e il client sa in anticipo quali righe sono bloccate da `forma_blocco_reason` |
| `politica_data_documento`, `limite_emissione_*` | ✅ | ✅ | Solo su famiglie che **ammettono le regole fiscali**: fuori di lì il backend li riporta al neutro prima dell'INSERT, perché il `CHECK` li rifiuterebbe con un messaggio che parla di un campo mai mostrato |
| `emittente_soggetto_ruolo_id` | (nel payload) | ⛔ | Lo dà il contesto. In creazione arriva nel corpo ma **non è creduto sulla parola**: deve stare nello scope dell'operatore, o la creazione è un modo di scrivere fuori perimetro su una tabella senza RLS |
| `id`, `uid` | ⛔ | ⛔ | Identità |

## ⭐ `reset_policy` — la politica del contatore

```text
ANNUALE   il progressivo riparte da 1 a ogni anno         (default della colonna)
NESSUNA   un secchio solo: la numerazione non riparte mai
```

`chk_registri_fatturazione_reset` ammette **questi due e solo questi**
(changeSet `20260901-06`), e `vendite.fn_get_next_progressivo` ramifica davvero:
sotto `NESSUNA` la chiave del contatore porta `anno = 0`, cioè un secchio unico.

⛔ **`MENSILE` non esiste e non torna**: nessun documento porta il mese in
chiave, quindi un contatore che discriminasse per mese consegnerebbe numeri che
il documento non è in grado di ospitare — è l'asimmetria del
[brief chiave del contatore §1](/dev/work-done/brief-db-registri-numerazione-chiave-del-contatore).

**Nel corpo della POST è opzionale.** Ometterlo, o mandarlo vuoto, significa
*«non l'ho scelto»* e decide il **default della colonna**: il backend toglie la
chiave invece di mandare un `NULL`, che il `NOT NULL` respingerebbe parlando di
un campo obbligatorio invece che di una scelta che il modello non chiede.

⚠️ **In PATCH è rifiutato** — `400 E_VENDITE_VALIDATION` «Campi non ammessi in
modifica del registro.» (`validate_allowed_keys` su `_CAMPI_UPDATE`, come ogni
chiave fuori elenco) — e questa è la parte che conta: cambiare la politica
su un registro che ha già consegnato numeri **sposta il secchio sotto il
contatore**. Il progressivo riparte da 1 su una chiave nuova e sbatte contro i
numeri già scritti, con un errore che parla del numero e non nomina la causa.
⛔ **Nessun trigger lo rifiuta**: `_CAMPI_UPDATE` è l'unico presidio, ed è la
ragione per cui `test_reset_policy_si_crea_ma_non_si_modifica` esiste.

## Errori tradotti

I vincoli DB non arrivano al client come violazioni nude: `registri_service.py`
li traduce, perché un `23505` senza frase manda a cercare una riga che nella
lista delle attive c'è eccome.

| Vincolo | Cosa dice il messaggio |
| --- | --- |
| `uq_..._famiglia_emittente_utility` | Lo slot è occupato — **anche da un registro spento**: si riattiva quello che c'è, non se ne crea un altro |
| `uq_..._prefisso_suffisso` | Due sezionali dello stesso emittente non possono produrre numeri della stessa forma (accende il campo `prefisso`) |
| `chk_..._reset` | I due valori ammessi, `ANNUALE` e `NESSUNA` — ⚠️ **non** un divieto applicativo: questo è il messaggio di un vincolo del *database*, e nominare la whitelist del backend manderebbe a cercare un permesso invece del valore ammesso |
| `chk_..._famiglia_regole_fattura` | I campi fiscali sono ammessi solo sulla famiglia FATTURA |

## Test

| File | Cosa presidia |
| --- | --- |
| `apps/vendite/tests/services/test_registri_service.py` | Le due tuple per verbo, la normalizzazione del payload, i neutri fiscali, `reset_policy` (crea/non modifica, vuoto → default) |

⚠️ **BUCO DICHIARATO (verificato il 2026-09-08): non esiste un
`test_registri_api.py`.** Le rotte dei registri non hanno copertura a livello
API — né sulle rotte, né sul cancello di perimetro, né sulla forma
dell'envelope. Tutto il presidio sta al livello di **service**, cioè sotto il
punto in cui vivono l'autenticazione, il permesso e la serializzazione.
⛔ Non è una svista da riempire con un file di smoke: è la stessa classe di
buco che il 2026-09-08 ha lasciato passare l'envelope sbagliato del lookup
famiglie — dove il test c'era, ma guardava lo **status** e non la **forma**.
Il gemello `apps/vendite/tests/api/test_famiglie_api.py` è il modello da
seguire quando si colmerà.

## Riferimenti

- Repository: `apps/vendite/db/registri_repository.py` — `_CAMPI_CREATE` / `_CAMPI_UPDATE`
- Service: `apps/vendite/services/registri_service.py` — normalizzazione + traduzione vincoli
- View: `apps/vendite/api/views_registri.py`
- Frontend: `frontend/src/amministrazione/components/RegistroNumerazioneDrawer.vue`
- Modello e decisioni: [brief chiave del contatore](/dev/work-done/brief-db-registri-numerazione-chiave-del-contatore) · [brief CRUD registri](/dev/work-done/brief-be-fe-crud-registri-di-numerazione)
