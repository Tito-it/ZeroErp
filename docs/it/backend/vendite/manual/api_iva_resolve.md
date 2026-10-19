# API iva_resolve (Django)

## Scopo

Esporre via HTTP l'**anteprima del trattamento IVA** di una riga di documento,
così che i tre `*RigaForm.vue` (preventivi, ordini, DDT) possano **sostituire**
l'auto-fill `form.iva_id = articolo.iva_id` con una risposta che viene dalla
sede unica.

## Contesto

Endpoint di sola lettura, calco di `POST /vendite/pricing/resolve/`: stesso
mestiere — esporre un resolver DB a un form — stessa area, stessa forma.

Espone `IvaResolverService.risolvi_anteprima`, cioè il risolutore
[fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga).
⭐ **Nessun side-effect**: la funzione DB è `STABLE` e **non consuma** il
plafond dei titoli — la risposta è una **proiezione**, non un impegno.

⛔ **Perché esiste, e non è una comodità del form.** L'auto-fill dall'articolo
rispondeva alla stessa domanda del risolutore ma guardando una fonte sola:
ignorava l'uso della fornitura (`TIPO_UTENZA`) e i **titoli documentati del
cliente** — su un esportatore abituale proponeva l'aliquota piena. Due risposte
alla stessa domanda sono due risposte che prima o poi divergono; qui ne resta
una.

## ⛔ Il contratto NON accetta un imponibile

Il risolutore, quando riceve l'importo, può rispondere con **due parti** — la
quota coperta da un titolo e il resto ad aliquota ordinaria.

Sui documenti quella spezzatura **non si fa** (decisione di Tid: il titolo si
applica a tutta la riga finché c'è capienza, e il documento porterà
un'annotazione che avvisa che il conteggio effettivo si stabilisce
all'emissione della fattura).

⭐ **Il modo solido di tenere quella regola non è ricordarsela: è non dare al
client il parametro con cui romperla.** La ripartizione vera la calcola la
fattura, dove serve e dove il plafond si **consuma**.

## ⛔ Il contratto NON accetta `data_riferimento` né il billing account

Si mandano le **coordinate del documento** (`documento_tipo` + `documento_id`) e
l'articolo. Emittente, billing account, utility e data li deriva il backend
dalla **testata** — la stessa che leggerà al salvataggio.

⚠️ Accettarli dal client avrebbe ammesso che l'anteprima rispondesse per un
contesto diverso da quello su cui il salvataggio calcola: cioè avrebbe
**costruito** il disaccordo che questo endpoint esiste per togliere. Un campo
dichiarato e ignorato sarebbe la stessa promessa falsa.

📌 Un `billing_account_id` o una `data_riferimento` mandati dal client vengono
**ignorati**: c'è un test che lo presidia.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/iva/resolve/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body (JSON):
  - `articolo_id` (uuid) — obbligatorio, `catalogo.articoli.id`
  - `documento_tipo` (string) — obbligatorio, whitelist: `PREVENTIVO` | `ORDINE_VENDITA` | `DDT_VENDITA`
    (i codici di `config.sorgenti`; dal 2026-10-19 `ORDINE` e `DDT` sono un 400,
    brief-db-grammatica-unica-documenti lotto 2a)
  - `documento_id` (int) — obbligatorio, id del documento su cui si scrive la riga

⚠️ `documento_tipo` è una **whitelist**, non un suggerimento: un tipo fuori
elenco non arriva mai a comporre un nome di tabella.

## Output

- `200`:
```json
{
  "data": {
    "iva_id": 16,
    "aliquota": "22.00",
    "natura_codice": null,
    "is_reverse_charge": false,
    "esigibilita": "I",
    "split_payment": false,
    "riferimento_normativo": "Aliquota I.V.A. al 22%",
    "origine": "ARTICOLO",
    "titolo_iva_id": null
  },
  "meta": { "request_id": "..." }
}
```
- `400`: payload non valido, documento non trovato, tipo fuori whitelist,
  documento senza data, emittente non risolvibile (`E_VENDITE_VALIDATION`)
- `401`: JWT mancante o non valido

⚠️ **`quota` non esce dal payload**: in anteprima vale sempre `NULL` — la
spezzatura non è calcolabile senza importo — e un campo sempre nullo è una
promessa che qualcuno prima o poi prova a leggere.

## Le due caselle che il frontend deve tenere

| Campo | A cosa serve |
| --- | --- |
| `iva_id` | il valore che va nel campo del form |
| `origine` | ⭐ **il perché**, e non è un lusso: dal 2026-08-31 (`I6`) la casella IVA è **chiusa**, e un numero che non si può cambiare **e** che non viene spiegato sarebbe la forma peggiore. A video diventa l'hint sotto il campo |
| `titolo_iva_id` | quale titolo del cliente ha deciso, quando `origine = 'TITOLO'` |

⚠️ **`origine` ha un vocabolario del DB ed è APERTO** (`ARTICOLO`,
`TIPO_UTENZA`, `TITOLO`, `ASSENTE`, e domani altro). Si rende con `labelOrCode`:
un valore nuovo compare come **codice grezzo**, non come path di chiave i18n.
Le etichette vivono in `vendite.iva_origine.*`.

📌 Il resto del composito (`aliquota`, `natura_codice`, `riferimento_normativo`)
è **derivato** da `iva_id` e serve solo a mostrare: non va copiato su nessuna
riga. `riferimento_normativo` è `config.iva.descrizione`, l'unica colonna che il
lock lascia modificabile apposta — copiarla su un documento vivo produrrebbe una
frase che invecchia.

## Regole

- Area `vendite`, livello **LETTURA**; endpoint v1, richiede JWT.
- Nessun `Idempotency-Key`: non scrive.
- L'emittente si risolve in **due passi** — quello della testata, poi quello
  dell'operatore (`ParameterService.get_emittente_fiscale_id_for_user`).
  ⛔ Se non si risolve, **errore**: mai una risposta che ripiega sull'aliquota
  ordinaria. La funzione DB è `SECURITY INVOKER` e legge una tabella con RLS —
  senza contesto emittente leggerebbe **zero titoli** e risponderebbe con
  l'ordinaria *senza sollevare*. Non è una lista più corta: è un'imposta
  applicata dove non andava.
- ⛔ `emittente_fiscale_id` è la **PK** di `anagrafiche.emittenti_fiscali`, non
  il `soggetto_ruolo_id` che il pricing usa: i due numeri si somigliano
  abbastanza da passare inosservati, e con quello sbagliato il risolutore non
  trova l'emittente, quindi non trova i suoi titoli.
- Il documento fuori dal perimetro RLS diventa un **«non trovato»**, che è la
  stessa risposta che darà il salvataggio.
- ⚠️ Lato FE la chiamata è **best-effort di proposito**: se non risponde, il
  campo resta com'è e si salva lo stesso. L'autorità è il backend **al
  salvataggio** — questa chiamata serve a far *vedere*, non a decidere.

## Dipendenze DB

- `vendite.fn_resolve_iva_riga` (guscio: smista per paese, solleva
  `E_IVA_PAESE_NON_IMPLEMENTATO` fuori dall'Italia)
- `vendite.fn_resolve_iva_riga_it` (stadio A: articolo → uso fornitura →
  default; stadio B: titoli documentati del soggetto)
- `anagrafiche.soggetti_titoli_iva` (RLS), `config.iva`, `config.iva_natura`
- le testate `vendite.preventivi` / `ordini` / `ddt` (lettura del contesto)

## Note di migrazione

- Introdotto il 2026-08-31 (`F2-b`, poi allargato a `F2-d` con le coordinate del
  documento). Piano:
  [brief-be-fe-iva-fase-3-consumatori-risolutore.md](../../../dev/work-done/brief-be-fe-iva-fase-3-consumatori-risolutore.md).
- Lato FE il consumatore è il building block `useIvaRisolta`
  (`frontend/src/vendite/_shared/righe/useIvaRisolta.js`), estratto alla 3ª
  occorrenza: la chiamata, l'anti-race e la label dell'origine stanno lì, non
  nei tre form.
- ⚠️ Finché il seed di `F0` non è applicato, un `E_IVA_*` sollevato dal DB
  risolve sulla scorciatoia dei codici `E_` non registrati (**400** «errore di
  validazione») invece che sulla sua classe. Si sana col seed.
