# Brief DB — la distinta cerca le RATE: lookup fattura ricco, lista rate paginata, una rata per la nota di credito

> **Cos'è.** Il seguito del **secondo giro in-app** sulla distinta contabile
> (Tid, 2026-09-15). Rilievo in una frase: *chi digita un incasso non riconosce
> il documento da un numero nudo, e la domanda vera non è «quale fattura?» ma
> «quale rata?»*. Da lì quattro pezzi, decisi in chat e riportati nel brief
> madre come **D19** ([§2-bis](brief-incassi-riconciliazione-rate-promemoria.md)):
>
> - **A** · il lookup fattura mostra il **documento** (numero parlante,
>   registro, data, totale, natura), non il contatore;
> - **B** · la riga caricata **fa vedere** la sua destinazione (fattura, rata,
>   scadenza, residuo) prima che si confermi un importo;
> - **C** · una **ricerca delle rate** azionabile da pulsante — cliente, numero
>   fattura → elenco rate col saldo — che riporta la scelta nel form;
> - **D** · la stessa ricerca lasciata aperta accumula N rate in un'**area
>   temporanea** e al Salva genera N righe (è **D1** reso a video: *«un incasso
>   che copre tre rate resta tre righe, cambia solo quando si scrivono»*).
>
> ⭐ **C è il primo consumatore dello scadenzario.** Il brief madre §3.4 lo dà
> dal 24/08 «possibile e non fatto, cantiere suo», con due cose vere da fare —
> la **rotta rate paginata** e i **seed**. Il picker le costruisce; lo
> scadenzario le riusa. Le due avvertenze scritte lì valgono qui identiche:
> i numeri dalla **base unica dei saldi**, e si guarda il **residuo**.
>
> **Sede.** Piano DB qui (§4). Per BE e FE **solo l'elenco** (§5, §6): il piano
> è in [piano-be-fe-distinta-ricerca-rate.md](piano-be-fe-distinta-ricerca-rate.md).
>
> **Stato:** 📝 **brief scritto il 2026-09-15** (lato BE/FE, su «procedi» di
> Tid). Nessun changeSet scritto, nessuna migrazione. Il pezzo **B** non ha
> prerequisiti DB e parte subito; **A** aspetta P-1; **C** e **D** aspettano
> P-2 e P-4; **P-5** è una decisione che il DB verifica sui due contro-pezzi.

---

## 0. In una pagina

| | Cosa chiede al DB | Serve a | Dove |
| --- | --- | --- | --- |
| **P-1** | rev di `vendite.vw_fatture_lista`: **`numero_documento`** (la sede unica `fn_numero_documento_fattura`) e **`registro_codice` / `registro_descrizione`** | A — il lookup, e i suoi **tre** consumatori (form riga, abbinamento, sistemazione eccedenza) | §4.1 |
| **P-2** | la **sorgente della lista rate**: una vista `security_invoker` con l'identità della rata e del suo documento — **senza** i saldi | C, D — e lo scadenzario dopo | §4.2 |
| **P-3** | 🔴 **domanda**: il saldo di N rate in **una** valutazione. Oggi `fn_get_saldo_rata` è plpgsql a tre letture, per rata; su un perimetro filtrato regge, sullo scadenzario intero no. E il filtro «solo aperte» **è** sul residuo | C (il filtro), lo scadenzario | §4.3 |
| **P-4** | seed `ui.lista_definizione` **`pagamenti.rate`** + colonne | C, D | §4.4 |
| **P-5** | ⭐ **decisione di Tid da verificare**: la **nota di credito ha UNA rata**. Oggi non ne ha nessuna (`fn_genera_scadenze_fattura`, base < 0 → zero rate) e `fatture_scadenze` porta il CHECK `chk_fatture_scadenze_importo_pos` | C — nel picker la nota di credito va **segnalata, non nascosta**: capita che il cliente la paghi | §4.5 |

---

## 1. Cosa dice il modello, verificato

Letto sulla doc auto-gen e sul codice il 2026-09-15 (struttura, non
popolazione: `pagamenti` ha ancora zero righe di esercizio, e non conterebbero).

| Fatto | Dove | Conseguenza |
| --- | --- | --- |
| `vw_fatture_lista` porta `numero` (bigint, il **contatore**), `serie`, `anno`, `data`, `totale_doc`, `totale_a_pagare`, `stato_descrizione`, `natura_doc_descrizione`, `ragione_sociale_completa`, `ba_codice`, `id_fiscale_univoco_cf_piva` — e `registro_id` **senza** il registro | [vw_fatture_lista](../../dbzero/vendite/views/vw_fatture_lista.md) | il lookup ha già data, totale, natura e non li rende (FE); **non ha** numero parlante né registro (DB) |
| Il numero parlante ha **una sede**: `vendite.fn_numero_documento_fattura(numero, serie)` — «numero - serie», senza anno, `NULL` sulla non numerata. IMMUTABLE, `LANGUAGE sql`: si inlinea nella select list di una vista | [fn_numero_documento_fattura](../../dbzero/vendite/funzioni/fn_numero_documento_fattura.md) | il FE **non compone** (`FatturaDrawer` lo legge dal dettaglio); la lista deve portarlo |
| Il registro: `vendite.registri_fatturazione` (`codice`, `descrizione`, `prefisso`, `serie_default`), FK da `fatture.registro_id` | [registri_fatturazione](../../dbzero/vendite/tabelle/registri_fatturazione.md) | un LEFT JOIN in più nella vista |
| `vendite.fatture_scadenze`: `fattura_id`, `numero_rata`, `data_scadenza`, `importo`; CHECK `chk_fatture_scadenze_importo_pos`; indice su `data_scadenza`; UNIQUE `(fattura_id, numero_rata)`; **RLS** dal `20260909-27 ÷ 20260910-33` (perimetro via testata) | [fatture_scadenze](../../dbzero/vendite/tabelle/fatture_scadenze.md), api.md §Enforcement RLS | la lista rate è già fail-closed a DB; lo scope BE si somma |
| Il saldo di una rata: `pagamenti.fn_get_saldo_rata(p_scadenza_id, p_escludi_contabile_riga_id)` → `saldo · in_lavorazione · incassato · has_movimenti`. **plpgsql**, tre letture (importo, registrato, in lavorazione), guard e `E_RATA_NON_TROVATA` | [fn_get_saldo_rata](../../dbzero/pagamenti/funzioni/fn_get_saldo_rata.md) | il BE la chiama **solo** da `saldi_service` (§2.7); per una fattura è una `CROSS JOIN LATERAL` (`list_rate_con_saldo`) |
| `fn_genera_scadenze_fattura`: legge `totale_a_pagare`; **NULL** → `E_SCADENZE_BASE_NON_PRONTA`; **0** → zero rate; **< 0** → «saldo a favore del cliente», **zero rate**, log non critico `W_SCADENZE_TOTALE_NEGATIVO` | [fn_genera_scadenze_fattura](../../dbzero/vendite/funzioni/fn_genera_scadenze_fattura.md) | una **nota di credito** (segno nel numero, D-NC-2) oggi **non ha rate** e non comparirà mai in un elenco di rate |
| La capienza è **una regola sola** per fatture e note di credito (D14-c): «un movimento normale riduce il residuo e non lo supera; il resto si segnala». Su una NC a −20 un pagamento +15 è «verso sbagliato» → **segnala**, e l'operatore può forzare | brief madre §2-bis D14-c | «il cliente paga la nota di credito» è già un caso **ammesso col secondo tempo**: oggi passa dal lookup fattura (riga su documento, senza rata) |
| La riga contabile porta `fattura_numero/anno/serie`, `scadenza_numero_rata`, `scadenza_data`, il BA — non data, totale, registro del documento né importo della rata | `pagamenti_repository._RIGA_COLONNE` | pezzo **B**: i JOIN su `fatture` e `fatture_scadenze` ci sono già, manca il registro — **solo BE** |
| Il perimetro dell'operatore sulle rate: la RLS di `fatture_scadenze` passa dalla testata (`fn_scope_ef_whitelist_via_fattura`) | api.md §Enforcement RLS | la vista di P-2 **non filtra**: denormalizza (come le sette sorelle) |

---

## 2. Le decisioni (D19, in sintesi — per esteso nel piano BE/FE)

| | Decisione | Perché |
| --- | --- | --- |
| **D19-a** | Il lookup fattura mostra il **documento**: numero parlante, registro, data, totale, natura, cliente | un contatore nudo è ambiguo per costruzione (una fattura 1 e una nota di credito 1 nello stesso anno) |
| **D19-b** | La destinazione di una riga **si vede sempre**, anche in modifica; R-6 protegge la **scrittura** della destinazione, non la sua lettura | chi corregge un importo deve sapere su cosa lo corregge |
| **D19-c** | Nasce la **lista rate paginata** (`GET /pagamenti/rate/`) col saldo dalla base unica, e un **picker** che la monta. Nel picker un criterio (cliente o numero fattura) è **obbligatorio** | si sta registrando il pagamento di *questo* cliente, non guardando lo scadenzario; e il costo del saldo per rata è sul perimetro |
| **D19-d** | N rate scelte → **N righe** in un Salva, con esito **PARZIALE** per riga (`run_fan_out`): le riuscite entrano, le rifiutate restano nell'area temporanea col loro motivo, il secondo tempo della capienza è per riga | D1; ogni riga è un atto suo, e il foglio è in bozza |
| **D19-e** ⭐ | *(Tid, 2026-09-15, da verificare in P-5)* La **nota di credito ha una rata sola**; nel picker si **segnala** (natura), non si esclude | «ci sono anche casi in cui il cliente paga la nota di credito»; una NC senza rate è invisibile a un elenco di rate e a uno scadenzario |

---

## 3. Che cosa NON cambia

- **Il lookup resta un autocomplete** (`ILIKE` su numero, cliente, BA, id fiscale): chi ha il numero sotto gli occhi lo digita. Il picker sta **accanto**, non al posto.
- **Il form riga singola resta documento-first** (D16): lookup → rate col saldo → importo proposto. Il picker in modalità singola lo **compila**, non lo sostituisce.
- **Nessuna copia dei saldi**: la lista rate legge `fn_get_saldo_rata` (o la sua forma set-based, P-3) **solo** da `saldi_service`.
- **Nessun guard nuovo**: la riga nata da rata passa dagli stessi trigger di `INSERT` (coerenza rata/fattura, capienza, scope) di D16.

---

## 4. Piano DB

### 4.1 P-1 — `vendite.vw_fatture_lista`: numero parlante e registro

`CREATE OR REPLACE VIEW … WITH (security_invoker=on)` (⚠️ ri-specificata, o
PostgreSQL la azzera), **appendendo** in coda — la vista ammette solo l'append:

```sql
    …,
    lin.frontiera_tipo_codice_interno,
    vendite.fn_numero_documento_fattura(f.numero, f.serie) AS numero_documento,
    reg.codice        AS registro_codice,
    reg.descrizione   AS registro_descrizione
   FROM … 
     LEFT JOIN vendite.registri_fatturazione reg ON reg.id = f.registro_id
```

- `LEFT`: una fattura in bozza può non avere registro; una senza registro deve comparire senza registro, non sparire (la regola di forma della vista).
- `numero_documento` è `NULL` sulla non numerata: il consumatore ha già il suo ripiego (`fattura_lookup.senza_numero`). ⛔ Non la stringa vuota.
- ⚠️ **Simmetria (Q-1)**: le altre sei sorelle hanno `registro_id` dal `20260831` e nessuna espone il registro. Il blocco `registro_*` è lo stesso per tutte: la scelta di aggiungerlo a **tutte e sette** nello stesso giro è del DB (e il costo è un LEFT JOIN a testa). `numero_documento` invece è **solo** della fattura: sulle sorelle `numero` è già il parlante.
- pgTAP: le tre colonne esistono; `numero_documento` è `NULL` sulla non numerata e «`numero - serie`» sulla numerata (**costruite**, non lette); il presidio delle sorelle (se confronta le colonne) va allineato.
- Doc: la scheda auto-gen si rigenera; la `manual/` della vista, se c'è, una riga.

### 4.2 P-2 — La sorgente della lista rate

Una vista **di identità**, sullo stampo delle sorelle: `security_invoker=on`,
nessun filtro, nessuno scope, **nessun saldo**. Nome proposto
`vendite.vw_fatture_scadenze_lista` (la rata è di `vendite`; il saldo è di
`pagamenti` e resta fuori dalla vista — §4.3).

Colonne (una riga per rata):

| Gruppo | Colonne |
| --- | --- |
| rata | `scadenza_id` (= `sc.id`), `fattura_id`, `numero_rata`, `data_scadenza`, `importo` |
| documento | `numero_documento` (P-1, stessa fn), `serie`, `anno`, `data` (**emissione**), `registro_codice`, `registro_descrizione`, `natura_doc_codice_interno`, `natura_doc_descrizione`, `tipo_doc_fiscale_descrizione`, `stato_codice_interno`, `stato_descrizione`, `totale_doc`, `totale_a_pagare`, `valuta_codice` |
| cliente | `billing_account_id`, `ba_codice`, `soggetto_id`, `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva` |
| emittente | `emittente_soggetto_ruolo_id`, `emittente_fiscale_id`, `emittente_fiscale_codice`, `emittente_ragione_sociale` |

- I JOIN sono quelli di `vw_fatture_lista` (un solo INNER, `nature_doc_fiscale`; il resto LEFT, per la stessa ragione). ⭐ Se il DB preferisce **appoggiarsi** a `vw_fatture_lista` (`JOIN vendite.vw_fatture_lista v ON v.id = sc.fattura_id`) invece di ricopiare i JOIN, i nomi restano canonici da soli e la rev P-1 arriva gratis: è la strada che consiglio, salvo un costo sul piano che il DB vede e io no.
- ⛔ **Niente colonna «scaduta»/«insoluta»**: sono derivate dal residuo (§3.4 del brief madre) e il residuo non sta nella vista. Le calcola chi legge, dai numeri della base unica.
- Indici: `ix_fatture_scadenze_data` c'è; il filtro tipico del picker è per `fattura.billing_account_id` (indice FK sulla testata) o per `numero` esatto. Da guardare col piano in mano, non da aggiungere a priori.
- pgTAP: forma (colonne), `security_invoker`, una rata **costruita** su una fattura numerata e una su una bozza (numero_documento NULL), e il perimetro: come operatore fuori whitelist la rata **non si vede** (è la RLS della tabella che morde, e va provato che morda **attraverso** la vista).

### 4.3 P-3 — 🔴 Il saldo di N rate in una valutazione *(domanda)*

Il picker chiede il saldo di ogni rata della pagina — e, col filtro **«solo
aperte»** (residuo ≠ 0), di ogni rata del **perimetro**, perché il filtro sta
nel `WHERE`. Oggi la sola porta è `fn_get_saldo_rata`, **per rata**, plpgsql a
tre letture. Sul perimetro di un cliente regge; sullo scadenzario (tutte le rate
aperte, per data) è N × 3 letture prima di poter filtrare.

⭐ Questa non è una misura, è struttura: uno scadenzario **è** il perimetro
intero per costruzione.

**Chiedo al DB** una delle due forme — o una terza che vede lui:

| Forma | Cosa | Pro | Contro |
| --- | --- | --- | --- |
| (a) `pagamenti.fn_get_saldi_rate(p_scadenza_ids bigint[])` `RETURNS TABLE(scadenza_id, saldo, in_lavorazione, incassato, has_movimenti)` | la stessa formula, set-based (`GROUP BY scadenza_id`) | il chiamante passa gli id della **pagina**; `fn_get_saldo_rata` può diventarne il caso a un elemento, così la formula resta **una** | non aiuta il filtro «solo aperte» sul perimetro |
| (b) `pagamenti.vw_saldi_rate` (una riga per rata, `security_invoker`) | il residuo di **tutte** le rate in un passaggio | il BE fa `JOIN` e filtra `residuo <> 0` nel `WHERE`; è la forma dello scadenzario | è una **seconda scrittura** della formula accanto alla funzione, a meno che la funzione non legga la vista |

⛔ Qualunque forma: **una formula sola**. Due sedi del residuo divergono alla
prima regola nuova, e sono numeri su cui si sollecita un cliente (§2.7).
🔵 **Finché P-3 non c'è**, il BE legge `fn_get_saldo_rata` in `LATERAL` sulla
**pagina** (non sul perimetro) e il filtro «solo aperte» **non esiste**: il
picker elenca tutte le rate del criterio, col residuo accanto, e le esaurite
non sono selezionabili. È onesto e regge il caso d'uso; è lo scadenzario che
aspetta.

### 4.4 P-4 — Seed `ui.lista_definizione` `pagamenti.rate`

Come le quattro del cantiere incassi (id 50-53) — una definizione, le colonne.
`schema_dati = pagamenti`, `vista_sql = NULL` (la lettura è del BE: vista +
saldi), `multi_emittente = f`.

| `codice` colonna | `campo_sorgente` | tipo | note |
| --- | --- | --- | --- |
| `scadenza_id` | `scadenza_id` | identificatore | nascosta |
| `fattura_numero_documento` | `numero_documento` | testo | ordinabile su `numero` |
| `registro` | `registro_codice` | testo | |
| `fattura_data` | `data` | date | ordinabile, **DESC** al primo click (regola di Tid) |
| `natura` | `natura_doc_descrizione` | testo | ⭐ è la colonna che **segnala** la nota di credito |
| `cliente` | `ragione_sociale_completa` | testo | ordinabile |
| `ba_codice` | `ba_codice` | testo | |
| `numero_rata` | `numero_rata` | numero | |
| `data_scadenza` | `data_scadenza` | date | ordinabile, **default della lista ASC** (vedi sotto) |
| `importo_rata` | `importo` | currency_eur | |
| `residuo` | `residuo` | currency_eur | dalla base unica |
| `in_lavorazione` | `in_lavorazione` | currency_eur | «già digitato, non registrato» |
| `incassato` | `incassato` | currency_eur | ⚠️ non è «a posto» |
| `fattura_totale` | `totale_doc` | currency_eur | |
| `stato_fattura` | `stato_descrizione` | testo | |
| `emittente` | `emittente_ragione_sociale` | testo | |

- ⚠️ **Ordine di default `data_scadenza ASC`**, non DESC come le liste di lettura: è una **coda** — la rata più vecchia è quella che un pagamento più probabilmente salda — la stessa ragione dei residui di competenza (api.md, dashboard competenza). Il primo click dell'operatore sull'intestazione resta DESC per regola generale.
- Le colonne dei saldi non sono ordinabili (non stanno nella vista): il seed le dichiara `ordinabile = false`, e la whitelist BE non le nomina — il presidio dei seed lo verifica.
- Il CSV lo genera `scripts/gen_seed_lista.py --codice pagamenti.rate --vista vendite.vw_fatture_scadenze_lista` a vista applicata; i campi curati (gruppo, larghezze, priorità) li decide chi lo scrive.

### 4.5 P-5 — ⭐ La nota di credito ha una rata *(decisione di Tid, da verificare)*

Tid, 2026-09-15: *«propendo per note credito un solo rateo; nel picker incassi
va segnalata; ci sono anche casi in cui il cliente paga la nota di credito»*.

Cosa c'è oggi, e sono **due** contro-pezzi:

1. `fn_genera_scadenze_fattura`: base **negativa** → «saldo a favore del cliente», **zero rate** (log `W_SCADENZE_TOTALE_NEGATIVO`). ⚠️ Non guarda la natura: guarda il segno.
2. `chk_fatture_scadenze_importo_pos` su `fatture_scadenze.importo`: dal nome, importo positivo — il predicato lo legge il DB.

La forma che propongo, sul modello e non sulla comodità:

- **una rata, importo col segno** (`importo = totale_a_pagare`, negativo): è la regola già scelta per i movimenti (D-NC-2, «il segno sta nel numero»), e `fn_get_saldo_rata` la regge già — la capienza D14-c non ha estremi da invertire. Il CHECK passa a `importo <> 0`.
- `data_scadenza = fattura.data` (**non** il termine di pagamento del cliente): una nota di credito non «scade» per il cliente, è un nostro debito da regolare; se il DB preferisce applicare comunque il termine (una rata, primo offset), è una scelta di forma che non cambia il resto.
- ⛔ **Non** «una rata per rata della fattura rettificata»: il legame con l'originale è lineage, non piano rate.
- Conseguenze da censire (il DB le vede meglio): `fn_genera_scadenze_lotto` (il wrapper), `vw_rate_fuori_capienza` (motivo `MOVIMENTO_CONTRARIO` su una NC con rata), `ScadenzeSintesi` nel drawer fattura (mostrerebbe una rata negativa: va detto a parole, vedi FE), i pgTAP che oggi asseriscono «zero rate su base negativa».
- ⚠️ E il **pregresso**: le NC già emesse senza rata — rigenerare il piano oltre `EMESSA` è `E_SCADENZE_FATTURA_BLOCCATA` (D-F). Backfill fail-closed o niente: decisione del DB, scritta nel brief quando risponde.

🔵 **Finché P-5 non c'è**, la NC non compare nel picker (non ha rate) e si
paga dal **lookup fattura** come riga su documento senza rata — il lookup ricco
di P-1 la **segnala** già con la natura. Il caso di Tid è coperto oggi; P-5 lo
porta nell'elenco.

---

## 5. Cosa deve fare il backend *(solo l'elenco: il piano è loro)*

- **B** (subito): cinque colonne in `_RIGA_COLONNE` (`fattura_numero_documento`, `fattura_data`, `fattura_totale_doc`, `fattura_registro_codice`, `scadenza_importo`) + `LEFT JOIN registri_fatturazione`.
- **C** (dopo P-2/P-4): `GET /pagamenti/rate/` paginata in `saldi_service`; whitelist di ordinamento chiavata sul `campo_sorgente`; saldi in `LATERAL` sulla pagina (P-3 quando c'è).
- **D** (dopo C): `POST /pagamenti/distinte/{id}/righe/da-rate/` — fan-out per riga, `falliti[]` con l'errore intero (`ErrorTranslator.to_api_error`), `forzata`/`motivo_forzatura` per riga.
- **A** (dopo P-1): niente da fare, la lista passa `v.*`.

## 6. Cosa deve fare il frontend *(solo l'elenco)*

- **A**: opzione del `FatturaLookup` a tre righe (documento · registro · data · totale · natura / cliente · id fiscale) — e la natura è un **Tag**, non testo.
- **B**: tabella righe con documento e «rata n · scadenza»; blocco «Destinazione» in sola lettura nel form (creazione e modifica) + `SaldoPanel` RATA/DOCUMENTO; `RataSelect` con l'importo della rata.
- **C**: `RatePickerDialog` (`AppDialog` xl + `<ListaConfigurabile codice="pagamenti.rate">`), pulsante accanto al lookup, criterio obbligatorio, modalità singola → compila il form.
- **D**: modalità multipla dal toolbar del drawer, area temporanea (`useSelezioneLista` + importi per riga), Salva → `da-rate/`, esito parziale → restano le fallite col motivo e il secondo tempo per riga.
- Dopo P-5: il residuo negativo si dice per **natura** («da rimborsare» su una NC, «di troppo» su una fattura).

## 7. Il copione di collaudo — righe da aggiungere

Al piano BE/FE, §6: la ricerca per numero **esatto** (101 non porta 1010), la
NC segnalata, tre rate → tre righe, una rata esaurita non selezionabile, il
rifiuto di capienza su una riga sola che non porta via le altre.

## 8. Trappole da non ripagare, viste scrivendo

- ⛔ **`numero::text ILIKE '%101%'`** nel picker: è la forma del lookup, dove serve; nel picker il numero è un confronto **esatto** — la stessa scelta di `id_fiscale` nella lista fatture, per la stessa ragione (una partita IVA è contenuta in altre).
- ⛔ Un `COUNT(*) OVER ()` con la `LATERAL` del saldo **nella stessa query** calcola il saldo per ogni riga del perimetro, non della pagina — è il costo già letto sul piano della coda righe (`_RIGA_FROM`, EXPLAIN del 14/09). Qui si fa «pagina prima, saldo dopo» dal primo giorno.
- ⛔ `residuo > 0` come predicato di «selezionabile»: su una NC con rata (P-5) il residuo è **negativo** e la rata **va** selezionata (rimborso). Il predicato è `residuo <> 0`.
- ⚠️ Il seed dichiara ordinabile solo ciò che la whitelist BE sa ordinare, e i saldi non ci sono: `test_liste_configurabili_seed` lo presidia.

## 9. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-15** | 📝 Brief scritto (BE/FE), dopo la decisione di Tid in chat: i quattro pezzi accettati; sulla nota di credito «una rata sola, segnalata nel picker». Fatti verificati sulla doc auto-gen: NC senza rate per costruzione (base < 0), CHECK sull'importo positivo. D19 riportata nel brief madre §2-bis |
