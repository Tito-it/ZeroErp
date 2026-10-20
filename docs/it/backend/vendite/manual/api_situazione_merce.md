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
[brief-design-partita-merce-generalizzata](../../../dev/work-done/brief-design-partita-merce-generalizzata.md)
§19.1, consumata dal pannello di
[brief-design-situazione-merce-ordine](../../../dev/work-done/brief-design-situazione-merce-ordine.md).

⭐ **Il fatto che ha generato il cantiere**: il conto della merce esisteva a DB
(allora `vw_contatore_merce`, ritirata il 22-09-2026: oggi la partita,
`vw_partite_merce`) ma *«non è mai stato mostrato a una persona»* — serviva
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

Envelope standard `success_response`, `data` con **quattro sezioni** più il
contesto:

| Campo | Grana | Fonte |
| --- | --- | --- |
| `contesto` | `"ORDINE_VENDITA"` \| `"DDT_VENDITA"` (i codici di `config.sorgenti`; fino al 2026-10-19 `"ORDINE"` \| `"DDT"`) — **quale lista è il saldo del documento** | il filtro della chiamata |
| `righe_ordine` | riga d'ordine (su entrambi i lati) | `vw_situazione_merce_ordine` |
| `partite` | riga di DDT | `vw_partite_merce` |
| `accrediti` | riga di reso | `vw_resi_da_accreditare` |
| `riconsegne` | riga di reso | `vw_resi_da_riconsegnare` |

⭐ **`contesto` non è ridondante** (rev 2026-08-19). Fino a questa revisione
`righe_ordine` era vuota sul DDT, e il client capiva «quale lista contare»
guardando quale delle due fosse popolata. Adesso sono popolate entrambe, e
quell'euristica conterebbe sul DDT il saldo dell'**intera riga d'ordine** —
tutte le sue spedizioni — al posto di questa: un numero plausibile e sbagliato.
Chi consuma legge `contesto`, non indovina.

⭐ **Dal 2026-09-14 `righe_ordine` porta anche le date di consegna e il
ritardo** (`brief-db-modifiche-certe-ciclo-vendita-e-articolo`, P-6 e §5.5
voce 6): `data_consegna_richiesta_cliente` (quando il cliente la vuole),
`data_consegna_confermata` (la nostra promessa) e `giorni_ritardo`. Il ritardo
sta **nella vista** e non altrove perché non è «oggi > data richiesta»: è
«oggi > data di riferimento **e** resta merce da spedire», e il residuo con la
soglia dell'impegno vive già lì. La data di riferimento è la **promessa** se
c'è, altrimenti la richiesta del cliente (deciso da Tid il 2026-09-14). ⛔ Tre
valori, e non si appiattiscono: `null` = il conto non si applica (`da_spedire`
NULL o zero, o nessuna data dichiarata), `0` = c'è da spedire e non è tardi,
`N > 0` = giorni di ritardo. Un `COALESCE(..., 0)` direbbe «in tempo» su una
riga che non ha niente da spedire. Il repository proietta le colonne **per
nome** (25 dal 14-09): una colonna nuova della vista non esce finché nessuno la
nomina.

Esempio reale (l'ordine del §3 del brief pannello, la riga da 21 pezzi):

```text
contesto      ORDINE_VENDITA   (dal DDT sarebbe DDT_VENDITA, e il saldo sarebbe quello delle partite)
righe_ordine  riga 1 · ordinato 21 · tenuti 13 · fatturato 21
                     · differenza −8 · da_spedire 3 · DA_ACCREDITARE
partite       DDT0010839 · origine ORDINE_VENDITA · consegnato 21 · −8 · DA_ACCREDITARE
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
* ⭐ **Sul DDT `righe_ordine` c'è, ma è filtrata sulla SPEDIZIONE** (rev
  2026-08-19, rilievo in-app): sono le righe d'ordine che *quel DDT ha toccato*,
  non quelle dell'ordine intero. Servono a leggere i due livelli insieme — «la
  riga d'ordine nel complesso sta così, questa spedizione così» — che prima
  costringeva a cambiare schermata. **Il saldo del documento resta quello delle
  `partite`**: è precisamente ciò che `contesto` dichiara.
  ⚠️ Il legame DDT→riga d'ordine si legge da `vendite.ordini_righe_fulfillment`,
  la **stessa** fonte da cui `vw_partite_merce` deriva la propria `origine`. Non
  si passa dalla partita: sarebbe la vista più costosa del sistema ri-valutata
  per rispondere a un filtro. Verificato su **tutti** i DDT del database: le
  righe d'ordine restituite coincidono con i `DISTINCT ordine_riga_id` delle
  partite, zero divergenze.
  ⚠️ Una riga di DDT **senza origine ordine** non ha riga d'ordine: la sezione
  resta più corta delle `partite`, ed è corretto.
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
