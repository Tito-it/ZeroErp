# API Situazione merce — ordine e DDT (Django)

## Scopo

Espone in **un round-trip** la situazione della merce di un documento — quanto è
uscito, quanto è tornato, quanto è fatturato, cosa resta aperto — per il pannello
del cantiere 2. Sola lettura, nessun verbo.

```text
GET /api/v1/vendite/ordini/<ordine_id>/situazione-merce/
GET /api/v1/vendite/ddt/<ddt_id>/situazione-merce/
```

## Contesto

Richiesta **BE-1** del brief
[brief-design-partita-merce-generalizzata](../../../dev/work-in-progress/brief-design-partita-merce-generalizzata.md)
§19.1, consumata dal pannello di
[brief-design-situazione-merce-ordine](../../../dev/work-in-progress/brief-design-situazione-merce-ordine.md).

⭐ **Il fatto che ha generato il cantiere**: il conto della merce esisteva a DB
(`vw_contatore_merce`) ma *«non è mai stato mostrato a una persona»* — serviva
solo alle macchine. Ricostruire la storia di una riga d'ordine richiedeva
**cinque schermate**. Questo endpoint la restituisce in una chiamata.

Le due view nascono dal factory `build_situazione_merce_view`
(`apps/vendite/api/situazione_merce_views.py`), estrazione regola-del-2
autorizzata il 2026-08-17: i domini sono **due dal primo giorno** perché il §5.1
del brief pannello decide «sull'ordine E sul DDT». Stessa forma di
`build_riepilogo_iva_view` e `build_passaggi_view`.

**Nessuna logica di dominio in Python**: i quattro elenchi vengono da quattro
viste DB della partita generalizzata. Il backend filtra, decora con i campi di
display (codice articolo, UoM, numero documento) e presidia il perimetro.

## Input

| Parametro | Dove | Note |
| --- | --- | --- |
| `ordine_id` / `ddt_id` | path | esattamente uno dei due, secondo la rotta |

Nessun query param: le partite di un documento sono decine, quindi **nessuna
paginazione** (come `GET /<id>/righe/`).

## Output

Envelope standard `success_response`, `data` con **quattro sezioni**:

| Sezione | Grana | Fonte |
| --- | --- | --- |
| `righe_ordine` | riga d'ordine — **solo sul lato ordine**, lista vuota sul DDT | `vw_situazione_merce_ordine` |
| `partite` | riga di DDT | `vw_partite_merce` |
| `accrediti` | riga di reso | `vw_resi_da_accreditare` |
| `riconsegne` | riga di reso | `vw_resi_da_riconsegnare` |

Esempio reale (l'ordine del §3 del brief pannello, la riga da 21 pezzi):

```text
righe_ordine  riga 1 · ordinato 21 · tenuti 13 · fatturato 21
                     · differenza −8 · da_spedire 3 · DA_ACCREDITARE
partite       DDT0010839 · origine ORDINE · consegnato 21 · −8 · DA_ACCREDITARE
accrediti     RESO0005122 · 5 · DOVUTA      RESO0005123 · 3 · FACOLTATIVA
riconsegne    RESO0005123 · residua 3 · DA_RICONSEGNARE
```

## Regole

* ⛔ **`null` non è zero — e vale per DUE colonne.** `differenza` è `null`
  quando il conto non si applica (ordine non ancora impegnato, riga mai spedita,
  causale di trasporto non fatturabile, conto non calcolabile); `da_spedire` è
  `null` quando l'ordine è **sotto la soglia** (`20260818-06`, vedi sotto). Un
  `COALESCE(..., 0)` nel repository o nel client rimette dentro i falsi allarmi
  che il cantiere della partita ha tolto — *«da fatturare»* su un conto visione,
  *«da accreditare»* su merce che deve solo partire, *«N da spedire»* su una
  bozza.
* ⛔ **Il verso del saldo non si ri-traduce.** `stato` arriva già tradotto dalle
  viste e ha **sette** valori: `NON_IMPEGNATA` · `NON_SPEDITA` · `PAREGGIATA` ·
  `DA_FATTURARE` · `DA_ACCREDITARE` · `NON_FATTURABILE` · `NON_MISURABILE` sul
  livello ordine; sulla partita al posto dei primi due c'è `RICONSEGNA`. Due
  traduzioni diventano due frasi diverse per lo stesso numero.
* ⭐ **La soglia di impegno dell'ordine** (`20260818-06`): una riga di ordine
  **sotto CONFERMATO** o su ordine abortito esce `NON_IMPEGNATA` con
  `da_spedire` **NULL** — non è un arretrato, è merce che nessuno si è ancora
  impegnato a spedire. È la gemella della decisione D1 sul DDT (la partita nasce
  da EMESSO in poi). ⚠️ **La riga resta**, con la sua quantità ordinata: la
  cardinalità è invariata (una per riga d'ordine attiva), perché il pannello si
  legge **per un ordine** e togliere le righe renderebbe vuoto il pannello di
  ogni bozza — «non c'è nulla» che in realtà è «non sto vedendo niente».
  ⚠️ E la precedenza nel `CASE` protegge il caso limite: una riga **con
  partite** su un ordine abortito mostra il suo saldo, non `NON_IMPEGNATA` —
  se la merce è uscita davvero, il conto è reale.
* ⚠️ **`fatturato_anticipato` non è un accredito**: è merce fatturata e non
  ancora uscita (corsia ORD, `fatturazione_trigger = CONFERMATO` su 93 ordini su
  95). Sommarlo alla differenza riapre il falso allarme.
* ⚠️ **`da_spedire` non è `ordinato − consegnato`**: il `consegnato` di una
  partita include le ri-consegne. Viene dalla formula di
  `fn_ordine_ha_residuo_evasione`, l'unica del sistema.
* **Sul DDT `righe_ordine` è vuota di proposito**: la domanda è *«cosa è successo
  a QUESTA spedizione»*, non *«come stanno le partite che il DDT tocca»* — sono
  due risposte diverse e la prima è quella che serve a chi apre un DDT.
* **Le due code sono le stesse della coda di lavoro**, con la stessa etichetta
  `DOVUTA` / `FACOLTATIVA`: il pannello non può contraddirle perché legge le
  stesse viste.

## Dipendenze DB

| Oggetto | Ruolo |
| --- | --- |
| `vendite.vw_situazione_merce_ordine` | livello 1 (`20260817-15`) |
| `vendite.vw_partite_merce` | livello 2 (`20260817-07`/`-11`/`-14`) |
| `vendite.vw_resi_da_accreditare` | coda accrediti (`20260817-09`) |
| `vendite.vw_resi_da_riconsegnare` | coda ri-consegne |
| `vendite.ordini` / `vendite.ddt` | **il cancello di scope** (RLS) |

Tutte `security_invoker=on`: la RLS del chiamante si applica da sé, e il
repository **non passa `auth_user_id`** né aggiunge filtri applicativi.

🔴 **L'ordine di lettura è vincolante.** Il perimetro si verifica sulla
**testata** *prima* di qualunque lettura di dettaglio: `vendite.ordini` e
`vendite.ddt` hanno la RLS, le loro righe **no**. Un documento fuori scope
risponde **404** (`E_VENDITE_NOT_FOUND`), indistinguibile da uno inesistente —
senza questo passo tornerebbe un pannello **vuoto**, cioè *«non ho il permesso di
saperlo»* presentato come *«non c'è nulla da fare»*. È lo stesso difetto che il
team DB ha corretto dentro `vw_situazione_merce_ordine` aggiungendo il `JOIN
vendite.ordini`, e la stessa regola del dettaglio fattura.

⭐ **L'aggancio delle due code è `ddt_riga_id`, mai `ordine_riga_id`**:
quest'ultimo è nullable, e sulla merce senza origine ordine è vuoto. Usarlo come
chiave farebbe uscire quelle righe dal conto **senza dare errore** — è il difetto
§8.5 che la partita generalizzata ha chiuso, e riproporlo qui lo riaprirebbe nel
solo posto in cui una persona lo guarda.

## Note di migrazione

`vw_situazione_merce_ordine` (`20260817-15`) è in repository dal 2026-08-18
(PR #1282), insieme al backend che la consuma (PR #1283). Il backend era stato
scritto introspezionando la vista **viva** prima del push: il corpo pubblicato
coincide con quello su cui è costruito.

**Frontend**: il pannello non esiste ancora. Le tre richieste FE del §19.2 del
brief partita — `NON_MISURABILE` visibilmente diverso da `PAREGGIATA`,
`sospetto_duplicato_ordine` mostrato, `fatturato_anticipato` mai sommato al saldo
— sono la definizione di fatto di quel cantiere, non di questo endpoint.
