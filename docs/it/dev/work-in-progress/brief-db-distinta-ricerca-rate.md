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
> Tid). Nessun changeSet scritto, nessuna migrazione. ✅ **Il pezzo B è scritto
> e committato il 2026-09-17** (BE + FE, riletto criticamente lo stesso giorno
> — consuntivo in [piano §0-bis](piano-be-fe-distinta-ricerca-rate.md) e
> registro): la riga porta il suo documento e la sua rata, il form li mostra
> nei due modi, `RataSelect` l'importo, la base dei saldi il «prima di sé»
> sulla rata. **A** aspetta P-1; **C** e **D** aspettano P-2 e P-4; **P-5** è
> una decisione che il DB verifica sui due contro-pezzi; **P-6** (17/09) nasce
> da B: l'esclusione «prima di sé» manca sul documento.

---

## 0. In una pagina

| | Cosa chiede al DB | Serve a | Dove |
| --- | --- | --- | --- |
| **P-1** | rev di `vendite.vw_fatture_lista`: **`numero_documento`** (la sede unica `fn_numero_documento_fattura`) e **`registro_codice` / `registro_descrizione`** | A — il lookup, e i suoi **tre** consumatori (form riga, abbinamento, sistemazione eccedenza) | §4.1 |
| **P-2** | la **sorgente della lista rate**: una vista `security_invoker` con l'identità della rata e del suo documento — **senza** i saldi | C, D — e lo scadenzario dopo | §4.2 |
| **P-3** | 🔴 **domanda**: il saldo di N rate in **una** valutazione. Oggi `fn_get_saldo_rata` è plpgsql a tre letture, per rata; su un perimetro filtrato regge, sullo scadenzario intero no. E il filtro «solo aperte» **è** sul residuo | C (il filtro), lo scadenzario | §4.3 |
| **P-4** | seed `ui.lista_definizione` **`pagamenti.rate`** + colonne | C, D | §4.4 |
| **P-5** | ⭐ **decisione di Tid da verificare**: la **nota di credito ha UNA rata**. Oggi non ne ha nessuna (`fn_genera_scadenze_fattura`, base < 0 → zero rate) e `fatture_scadenze` porta il CHECK `chk_fatture_scadenze_importo_pos` | C — nel picker la nota di credito va **segnalata, non nascosta**: capita che il cliente la paghi | §4.5 |
| **P-6** *(17/09, dal pezzo B)* | «prima di sé» anche sul **documento**: `fn_get_saldo_fattura_contabili` prende il solo `p_fattura_id`, mentre `fn_get_saldo_rata` ha `p_escludi_contabile_riga_id`. Chi corregge una riga **senza rata** (fondo fattura) legge un «in lavorazione» che conta la riga stessa — il pannello lo dichiara, non lo sana | B — la modifica di una riga su documento | §4.6 |

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

### 4.6 P-6 — `fn_get_saldo_fattura_contabili` con l'esclusione di una riga *(piccolo, dal pezzo B)*

Stessa forma della sorella: `p_escludi_contabile_riga_id bigint DEFAULT NULL`,
stesso guard (`<= 0` → `E_PAGAMENTI_CHIAMATA_NON_VALIDA`), la riga esclusa dal
solo conto dell'«in lavorazione» (è l'unico numero in cui una riga non
registrata entra). ⚠️ `fn_get_saldo_fattura` la chiama con un argomento: resta
valida per l'overload con `DEFAULT`, ma vale la regola di
`feedback_overload_ambiguo_default` — **non** due funzioni, un parametro in
più sulla stessa. Il BE (`saldi_service.saldo_documento`) e il FE (`useSaldi`,
`ESCLUSIONE_SUPPORTATA[DOCUMENTO]`) sono già scritti per riceverla: si accende
un flag, niente di nuovo da disegnare.

---

## 4-bis. Risposta del DB — analisi critica e piano (2026-09-17)

> Letto il 2026-09-17 su `pg_catalog` del DB di sviluppo e sulla doc auto-gen:
> **struttura**, non popolazione (CHECK, policy, indici, corpi di funzione,
> piani di esecuzione). Dove un fatto del §1 non regge, qui è corretto; il §1
> non è riscritto, il registro sta in §9.

### 4-bis.0 Il verdetto, in una pagina

| | Verdetto | In una riga |
| --- | --- | --- |
| **P-1** | ✅ si fa — con Q-1 corretta | le «sei sorelle col registro» sono **tre** (ddt, ordini, resi): contratti, preventivi e offerte un registro **non ce l'hanno** |
| **P-2** | ✅ si fa — **senza** appoggiarsi a `vw_fatture_lista` | quella vista trascina la CTE ricorsiva del lineage in ogni lettura delle rate, anche senza leggerne una colonna: il planner rimuove un LEFT JOIN solo su una relazione con chiave unica, e una vista non ce l'ha |
| **P-3** | ✅ terza forma: **un nucleo set-based, tre porte** | `fn_get_saldi_rate(ids[], escludi)` in SQL puro, `STABLE`; `fn_get_saldo_rata` ne diventa il caso a un elemento; `vw_saldi_rate` è il nucleo senza filtro. Una formula, e «solo aperte» diventa un `WHERE` |
| **P-4** | ✅ si fa — **spento** | definizione e colonne `attivo=f` finché il BE non proietta: è il cancello `test_lista_proiezione_campo_sorgente`, e fa rosso su un test che non c'entra |
| **P-5** | 🔴 **tre** contro-pezzi, non due — e un quarto che non è della NC | anche `fn_assign_numero_fattura` **respinge** rate su totale ≤ 0. E il fondo fattura più una rata negativa contano lo stesso credito **due volte** al livello rata: è il **punto cieco della rata**, che c'è già oggi su ogni documento a rata unica pagato «senza rata» — **Q-A**, e P-5 non parte prima |

### 4-bis.1 Fatti del §1 che non reggono

| Il brief dice | Verificato il 17-09 | Conseguenza |
| --- | --- | --- |
| `chk_fatture_scadenze_importo_pos`: «dal nome, importo positivo» | `CHECK ((importo >= 0))` — **lo zero è ammesso** | il predicato nuovo di P-5 **non può** essere `importo <> 0`: lo zero è raggiungibile dal generatore (base 0,01 su due rate → una rata a 0,00 per arrotondamento). Il modello lo ammette, quindi è un caso |
| «le altre sei sorelle hanno `registro_id` dal 20260831» | `registro_id` sta su `fatture`, `ddt`, `ordini`, `resi` (20260831-07/10/14). `contratti`, `preventivi`, `offerte_commerciali` **non ce l'hanno**. E **nessuna** delle sei viste lo espone, nemmeno come id | Q-1 è su **tre** sorelle, non sei (→ Q-E) |
| «il cliente paga la NC» è già un caso **ammesso col secondo tempo** (riga su documento, senza rata) | `trgfn_vendite_contabili_righe_guard_rata` **esce subito** su `scadenza_id IS NULL`; un guard di capienza a livello documento **non esiste** (in `pagamenti` la parola compare in una sola funzione, quella della rata) | oggi il pagamento di una NC entra **in silenzio**: né segnalazione né forzatura. Non è un argomento contro P-5, è l'argomento **per**: finché la NC non ha una rata, la sua capienza non esiste |
| P-5: «due contro-pezzi» | sono **tre**: `fn_assign_numero_fattura`, condizione 4 — *«presenti N rate su un totale a pagare non positivo»* → numerazione **respinta** (pgTAP `test-numerazione-guard-coerenza-v1`, test 6) | una NC con rata, oggi, **non si numera** |
| `fatture_scadenze`: RLS «via testata» | ✅, e le policy sono **due**: `rls_fatture_scadenze_ef_whitelist` (OPERATORE, tutti i comandi) e `rls_fatture_scadenze_ba_ownership` (CLIENTE_PORTALE, lettura) | la vista P-2 serve **anche il portale** (brief madre §3.3, `GET /api/portale/scadenze/`) senza una riga in più |
| P-2: «appoggiarsi a `vw_fatture_lista` … i nomi restano canonici da soli» | `EXPLAIN` di `fatture_scadenze JOIN vw_fatture_lista`: entra la CTE `fwd` di `vw_documento_lineage` con l'`Append` su preventivi/offerte/ordini/… anche senza proiettare una colonna di lineage | i JOIN si **scrivono** (uno INNER, il resto LEFT). I nomi canonici li tiene il pgTAP, non l'impilamento |

Altri fatti verificati che il brief non nomina e che entrano nel piano:

- `ix_vendite_movimenti_scadenza_id` e `ix_vendite_contabili_righe_scadenza_id`
  esistono, parziali `WHERE scadenza_id IS NOT NULL` → il nucleo di P-3 su una
  pagina è un index scan, non una scansione;
- `pagamenti.vendite_movimenti`, `vendite_contabili_righe`, `vendite_contabili`
  hanno la RLS (una policy ciascuna, `20260915-31/32`) → il nucleo, INVOKER,
  somma ciò che l'operatore vede — esattamente come `fn_get_saldo_rata` oggi;
- **lettori di `fatture_scadenze`** (censiti da `pg_proc`/`pg_views` e dal
  backend): `fn_get_saldo_rata`, `trgfn_vendite_contabili_righe_guard_rata`,
  `script.fn_check_scadenza_di_fattura`, `fn_assign_numero_fattura`,
  `fn_genera_scadenze_fattura`, `fn_imposta_data_documento_lotto`,
  `vw_rate_fuori_capienza`; a BE `vendite_repository.list_fattura_scadenze`
  (drawer **e contesto PDF**) e `pagamenti_repository` (righe,
  `list_rate_con_saldo`). È l'elenco da rileggere per P-5;
- `pagamenti.rate_fuori_capienza` (lista id 52) espone `fattura_numero` = il
  **contatore nudo** più anno e serie: la stessa ambiguità di D19-a su una
  lista che esiste già (→ P-1-bis);
- il BE legge `vw_fatture_lista` con `SELECT v.*` (`fatture_repository`,
  righe 172-178): la colonna nuova di P-1 arriva al frontend senza BE — la
  frase del brief è vera, verificata sull'asterisco.

### 4-bis.2 P-1 — `vw_fatture_lista`: piano

- `CREATE OR REPLACE VIEW … WITH (security_invoker=on)`, **append** di
  `numero_documento`, `registro_codice`, `registro_descrizione`, un
  `LEFT JOIN vendite.registri_fatturazione reg ON reg.id = f.registro_id`.
  `numero_documento` è `NULL` sulla non numerata, mai `''`: è già la regola
  della fn (caso 1), non serve scriverla di nuovo.
- pgTAP `test-vw-fatture-lista.sql`: `plan(8)` → `plan(11)` — i tre nomi entrano
  nell'insieme dei «mancanti» (test 2); `numero_documento IS NULL` sulla bozza
  della fixture esistente (test 6 ne costruisce già una senza numero); una
  fattura **numerata costruita** (numero + serie scritti dalla fixture) rende
  «`numero - serie`»; il LEFT su un `registro_id` NULL non toglie la riga
  (stessa fixture: la bozza non ha registro).
- **P-1-bis, stesso giro**: `vw_rate_fuori_capienza` riceve in coda
  `numero_documento` dalla stessa fn (append: la vista ammette solo l'append).
  Il CSV di id 52 prende una colonna `fattura_numero_documento`, `attivo=f`
  finché il BE non la proietta (la lista ha `vista_sql = NULL`).
- ⚠️ Q-E: le tre sorelle che un registro **ce l'hanno** (`vw_ddt_lista`,
  `vw_ordini_lista`, `vw_resi_lista`) ricevono lo stesso blocco `registro_*`
  nello stesso giro — tre changeSet in più e tre pgTAP da toccare. Non è
  simmetria per la simmetria: chi scriverà l'ottava copia la copia da una delle
  quattro, e oggi tre su quattro non hanno il registro. Su
  contratti/preventivi/offerte **non c'è niente da aggiungere** e va detto
  nel changeSet, così nessuno lo cerca.
- ⭐ Bonus per il BE/FE, fuori dal brief ma a costo zero lato DB: la lista
  `vendite.fatture` (id 48, `vista_sql = vw_fatture_lista`, BE `v.*`) può far
  puntare la colonna «Numero» a `numero_documento` con un edit del CSV.

### 4-bis.3 P-2 — `vendite.vw_fatture_scadenze_lista`: piano

- Vista d'identità, `security_invoker=on`, **una riga per rata**, nessun saldo,
  nessuno scope. JOIN scritti: `fatture_scadenze sc JOIN fatture f` (INNER: la
  FK è NOT NULL), `JOIN nature_doc_fiscale` (INNER: NOT NULL + FK, come la
  sorella), tutto il resto LEFT — stati, tipo, registro, BA → soggetto_ruolo →
  soggetto, emittente (`ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id`,
  unico per `uq_emittenti_fiscali_ruolo`: non moltiplica), valuta.
  ⛔ Niente `utility`, niente `sorgente`, niente lineage: non sono della rata.
- Colonne: quelle del §4.2, con la chiave che si chiama **`scadenza_id`** — è
  il vocabolario di `pagamenti` (`vw_rate_fuori_capienza`,
  `list_rate_con_saldo`, il `context` di `E_RATA_NON_TROVATA`, il `modelValue`
  di `RataSelect`). `<ListaConfigurabile>` ha `dataKey` di default `id`: il
  FE passa `dataKey="scadenza_id"`, non si duplica la colonna.
- Indici: non se ne aggiungono **a priori**. Il filtro per cliente passa da
  `ix_fatture_ba_data (billing_account_id, data)`; `uq_fatture_scadenze_nr`
  copre `fattura_id` in testa. ⚠️ Il filtro per **numero esatto** invece
  **non ha un indice**: `uq_fatture_numero` è `(registro_id, anno,
  COALESCE(serie,''), numero)` e un `WHERE numero = 101` senza registro non lo
  usa — è una scansione di `fatture` (una riga per documento). Per un picker
  regge; se il piano di C dirà il contrario, un indice parziale su `(numero)
  WHERE numero IS NOT NULL` è una riga, e si aggiunge **allora**, col piano
  in mano.
- pgTAP nuovo `db/pgtap/vendite/test-vw-fatture-scadenze-lista-v1.sql`, sullo
  stampo di `test-vw-fatture-lista.sql`: reloption presente; colonne; **nessun
  fan-out** (tante righe quante rate visibili); un solo INNER dimostrabile
  oltre alla FK della rata; fixture: una rata su fattura numerata e una su bozza
  (`numero_documento` NULL, `registro_*` NULL, la riga c'è); e il perimetro
  **attraverso** la vista — come operatore fuori whitelist la rata non si vede,
  ed è la policy della tabella che morde (stesso stampo del test 8 della
  sorella: le righe sono esattamente quelle visibili su `fatture_scadenze`).
- Doc: `manual/vw_fatture_scadenze_lista.md` breve, che **rimanda** alla guida
  dei pagamenti per i saldi — la vista non ne ha, e va detto lì.

### 4-bis.4 P-3 — la terza forma: un nucleo set-based, tre porte

Né (a) né (b) da sole: (a) non serve lo scadenzario, (b) da sola è una seconda
formula. La forma che le tiene insieme è **un nucleo e tre porte**, e la
formula è scritta **una volta**:

```text
pagamenti.fn_get_saldi_rate(p_scadenza_ids bigint[] DEFAULT NULL,
                            p_escludi_contabile_riga_id bigint DEFAULT NULL)
    RETURNS TABLE(scadenza_id, saldo, in_lavorazione, incassato, has_movimenti)
    LANGUAGE sql STABLE                       ← il NUCLEO: la formula di oggi, set-based

pagamenti.fn_get_saldo_rata(p_scadenza_id, p_escludi)     ← porta 1: firma e RETURNS invariati,
    = guard + SELECT dal nucleo con ARRAY[p_scadenza_id]      NOT FOUND → E_RATA_NON_TROVATA,
                                                              resta VOLATILE (il ramo d'errore scrive)

pagamenti.vw_saldi_rate  (security_invoker=on)             ← porta 2: SELECT * FROM nucleo(NULL, NULL)
                                                              = tutte le rate visibili, la forma dello scadenzario

JOIN LATERAL pagamenti.fn_get_saldi_rate(ARRAY[sc.scadenza_id])   ← porta 3: la pagina, dal BE
```

- **Il nucleo** parte da `fatture_scadenze` (`WHERE p_ids IS NULL OR id = ANY(p_ids)`)
  e fa due `LEFT JOIN` su due aggregati `GROUP BY scadenza_id` — movimenti
  attivi (con `incassato` = `SUM … FILTER` sui centri non-cassa, e
  `has_movimenti` = «il gruppo esiste») e righe postabili sotto testata non
  finale — con la stessa esclusione `p_escludi_contabile_riga_id` di oggi in
  entrambi. Una rata **senza movimenti torna lo stesso** (LEFT), con
  `has_movimenti = false`: senza questo la `LATERAL` del picker perderebbe le
  rate mai toccate.
- **Perché `LANGUAGE sql STABLE`**: è inlinabile. Con l'array della pagina il
  filtro si spinge dentro gli aggregati (index scan sui due parziali); con
  `NULL` la vista è due hash aggregate su tutta la tabella, che è il costo
  onesto dello scadenzario. ⚠️ `fn_get_saldo_rata` resta **non** STABLE per la
  ragione già scritta nel suo COMMENT (il ramo d'errore scrive nel registro):
  il nucleo può esserlo perché **non solleva mai** — una rata invisibile è zero
  righe, e a dire `E_RATA_NON_TROVATA` è la porta 1.
- **Comportamento invariato**, e lo prova il pgTAP: `test-abbinamento-rata.sql`
  (18 asserzioni, fra cui saldo/in_lavorazione/incassato su rata costruita) e
  `test-fn-get-saldo-fattura-tre-numeri.sql` restano com'erano e devono restare
  verdi. Nuovo `db/pgtap/pagamenti/test-fn-get-saldi-rate-v1.sql`: le tre porte
  danno gli **stessi numeri** sulla stessa rata costruita; `NULL` = tutte le
  visibili; un array = solo quelle; `p_escludi` sul nucleo; rata senza
  movimenti presente con `has_movimenti = false`; rata fuori perimetro →
  zero righe dal nucleo e `E_RATA_NON_TROVATA` dalla porta 1.
- Nessun codice errore nuovo. `vw_rate_fuori_capienza` continua a chiamare la
  porta 1 in `LATERAL` sul suo insieme già filtrato: non c'è ragione di
  toccarla qui.
- ⚠️ La forma «`residuo · in_lavorazione · incassato`» del §2.7 **non cambia**:
  il nucleo non aggiunge una quarta colonna derivata (`spazio`). Chi vuole lo
  spazio fa `saldo - in_lavorazione`, com'è scritto nel COMMENT — e la domanda
  su quale dei due sia «aperta» è Q-B.
- 🔵 Se Q-A si chiude con l'imputazione (opzione γ), è una **rev del nucleo**:
  una sede sola, ed è la ragione per cui il contenitore si fa adesso e la
  semantica si decide dopo.

### 4-bis.5 P-4 — seed `pagamenti.rate`: piano

- `lista_definizione.csv`: id **68** (il primo libero dopo 67, `amm.processi`
  66 e `vendite.lotto_gruppi` 67 — ⚠️ il numero libero scade subito),
  `schema_dati = pagamenti`, `vista_sql = NULL` (i saldi non stanno nella vista,
  e con `vista_sql` valorizzata il trigger `a10_valida_campo_sorgente` li
  rifiuterebbe), `multi_emittente = f`, **`attivo = f`** — come nacque
  `vendite.fatture` (48): si accende col BE.
- `lista_colonna.csv`: generato con `gen_seed_lista.py --codice pagamenti.rate
  --vista vendite.vw_fatture_scadenze_lista` **a P-2 applicata** (lo script
  legge la vista), poi curato: le tre colonne dei saldi aggiunte a mano
  (`ordinabile = f`, per la ragione del §4.4 — revisabile il giorno che il BE
  ordinerà passando dalla porta 2); **tutte** le righe con `campo_sorgente`
  nascono `attivo = f` (la regola del cancello, non una prudenza); `ba_codice`,
  `emittente`, `stato_fattura` a priorità bassa (si ritirano per prime).
- `lista_preset.csv` + `lista_preset_colonna.csv`: preset `rate_default`, sistema,
  `ordinamento_default = [{"col":"data_scadenza","dir":"asc"}]` — è **qui** che
  vive l'ASC del §4.4, e il presidio `default_rotti` di `--verifica-ordinamento`
  pretende che quella colonna sia `ordinabile = t` e in whitelist BE. Dichiarare
  nel brief BE: whitelist = le colonne `ordinabile = t` del seed, e
  `--verifica-ordinamento pagamenti.rate` verde nello stesso commit.
- ⛔ `lista_definizione_perimetro_emittente.csv` **non** si tocca: la lista non
  è multi-emittente, il perimetro è la RLS.

### 4-bis.6 P-5 — tre contro-pezzi, e il quarto che non è della NC

**Sul modello, la decisione di Tid regge — e regge meglio di come il brief la
motiva.** L'argomento non è «capita che il cliente paghi la NC»: è che una
riga contabile **senza rata non incontra nessuna capienza** (§4-bis.1, terza
riga). La rimessa che compensa — *100 sulla fattura, −20 sulla nota di
credito* — oggi si registra sulla NC solo come riga di documento, cioè
**senza il guard di D14-c**; con una rata sulla NC quella riga passa dal
guard come tutte le altre, e «il cliente paga la NC» (+15 su −20) è il caso
che il guard **segnala** invece di lasciar entrare in silenzio. P-5 non allarga
il modello: **chiude un buco che il modello ha già**.

I contro-pezzi, e sono **tre**:

| # | Dove | Oggi | Cosa cambia |
| --- | --- | --- | --- |
| 1 | `fn_genera_scadenze_fattura` | base < 0 → zero rate + log `W_SCADENZE_TOTALE_NEGATIVO` | base < 0 → **una** rata, `importo = totale_a_pagare` (negativo), data → Q-C; il log **resta** (→ Q-D). Il ramo sta **prima** del loop: il loop continua a vedere solo basi positive, e il suo guard sull'ultima rata (`v_importo < 0`) non cambia |
| 2 | `chk_fatture_scadenze_importo_pos` = `importo >= 0` | vieta il negativo, ammette lo zero | si **toglie**. Non si sostituisce con `<> 0` (lo zero è raggiungibile) né con un CHECK sul segno (attraversa due tabelle). La coerenza di segno **è già presidiata** dal punto 3: una rata di segno sbagliato rompe `somma rate = totale a pagare` |
| 3 | `fn_assign_numero_fattura`, condizioni 3 e 4 | «documento da incassare» = `> 0`; «non positivo non si rateizza» = `<= 0` | condizione 3 su `<> 0` (piano assente / somma diversa), condizione 4 su `= 0` (rate su un documento a totale zero). ⭐ **D-D resta**: *«zero e negativo sono documenti legittimi»* — cambia solo che il negativo ha un piano, come il positivo |

E le conseguenze da censire, col censimento fatto:

- `vw_rate_fuori_capienza`: il `WHERE` è **un intervallo a estremi fissi**
  (`saldo < 0 OR saldo > importo`) — esattamente la trappola del §5 del brief
  madre che D14-c ha sciolto sul guard e **non** sulla vista. Su una rata
  negativa **entrambi** i motivi escono sbagliati (un +15 su −20 dà
  `SOVRA_INCASSATA`, un rimborso di 30 dà `MOVIMENTO_CONTRARIO`). Si riscrive
  nella forma di D14-c: motivo `SOVRA_INCASSATA` se `sign(saldo) <> sign(importo)
  AND saldo <> 0` (ha attraversato lo zero), altrimenti `MOVIMENTO_CONTRARIO`
  se `abs(saldo) > abs(importo)`; il `WHERE` è l'unione dei due. Sulle rate
  positive è **identica** a oggi (i test 13 e 14 di `test-abbinamento-rata`
  restano verdi); il vocabolario resta a due valori — su una NC
  `SOVRA_INCASSATA` significa «sovra-rimborsata», e a dirlo è l'etichetta FE,
  non un terzo codice;
- `fn_genera_scadenze_lotto`: non cambia (filtra sullo stato, chiama la
  per-fattura); `fn_imposta_data_documento_lotto`: non cambia, e **rigenera**
  la rata della NC quando la data si sposta, come per le altre;
- pgTAP: `test-genera-scadenze-fattura-v1` test 13 («base < 0: zero rate»)
  diventa «una rata negativa, log non critico»; `test-fatture-log-error-code`
  test 9 resta se Q-D dice «il log resta»; `test-numerazione-guard-coerenza-v1`
  test 6 si riscrive (rate su totale **zero** → respinta) e ne nasce uno
  (NC con una rata = totale → **ammessa**); nuovo `test-nc-rata-unica-v1.sql`
  che **costruisce** la NC: una rata negativa, numerazione che passa, rimborso
  −20 accettato, +15 segnalato con `E_RIGA_CONTABILE_CAPIENZA_SUPERATA`,
  motivi di `vw_rate_fuori_capienza` sul segno negativo;
- BE/FE, da elencare nel piano gemello: `list_fattura_scadenze` alimenta
  **anche il contesto PDF** — il modello della NC stamperebbe un blocco
  scadenze con un importo negativo (va deciso a parole, non nascosto);
  `RataSelect` «di troppo» (già in §3.4 del piano); `ScadenzeSintesi` è
  temporale e regge; SDI `DatiPagamento` è ⏸️ e il builder fa `abs()`
  (D-NC-2). ⚠️ `fn_prepare_sdi_payload` **non** legge le rate (censimento):
  niente da fare lì.

**Il pregresso: niente backfill** (→ Q-F). Le NC già `DEFINITIVA` senza rata
sono fermate due volte — `E_SCADENZE_FATTURA_BLOCCATA` nella fn e
`E_FATTURA_SATELLITE_CONGELATO` dal trigger sulla tabella — e l'unico varco è la
GUC di manutenzione `zeroerp.maintenance_reset_lotto_draft`, nata per il reset
del lotto. Non siamo in produzione: quelle NC sono dati di prova, e un
changeSet che attraversa un congelamento fiscale con una GUC di manutenzione è
un precedente che non vale la pena scrivere per dei dati di prova. Su un DB da
zero non ce n'è nessuna. Se serve allinearle su dev, è SQL a mano, non un
changeSet.

#### 🔴 Il quarto pezzo: il punto cieco della rata (Q-A)

Non è della nota di credito, e P-5 lo rende **visibile** invece di crearlo.

Il fondo fattura scrive la propria riga contabile **sul documento sorgente
senza rata** (`fn_sync_contabili_fondo_fattura`: `fattura_id =
fattura_sorgente_id`, `scadenza_id` NULL, centro `is_fondo_fattura`), e il guard
della rata la lascia passare apposta (*«è il caso della riga del fondo, che
salda per trasferimento»*). Al posting quella riga diventa un movimento
**senza rata**: `fn_get_saldo_fattura` lo vede (somma per `fattura_id`),
`fn_get_saldo_rata` **no** (somma per `scadenza_id`).

Con P-5, una NC di minimo con utility — che `fn_fondo_fattura_proponibile`
trasforma in fondo **da sola**, col segno del suo `totale_a_pagare` — avrebbe:
a livello documento residuo **0** (regolata per trasferimento sulla fattura
successiva), a livello rata residuo **−20** (la rata non ha visto niente). Il
picker direbbe «−20 da rimborsare», il guard di capienza **accetterebbe** il
rimborso (verso giusto, non supera), e il cliente avrebbe il credito **due
volte**: in cassa e sulla fattura dopo.

⭐ **Ma il difetto non nasce con P-5.** Una fattura positiva a rata unica pagata
con una riga «senza rata» — che D16 ammette (*«fattura sì, rata no»*) e che il
lookup produce — ha oggi `saldo_fattura = 0` e `saldo_rata = 100`.
`RataSelect` la mostra con residuo 100, il picker di C la elencherà come
aperta, e uno scadenzario la solleciterebbe. Finché la domanda era «quale
fattura?» il livello rata non lo guardava nessuno; D19 dice che la domanda vera
è «quale rata?», e a quel livello **la somma delle rate non è il documento**
ogni volta che esiste un movimento senza rata.

Tre strade, e la scelta è di modello:

| | Strada | Cosa comporta | Giudizio |
| --- | --- | --- | --- |
| **α** | accettare il punto cieco e **dichiararlo**: la vista P-2 porta anche il residuo di documento accanto a quello di rata, e il picker mostra entrambi | zero cambi di regola; l'operatore vede «rata 100 · documento 0» e capisce | onesto, ma il doppio credito di P-5 resta possibile: la vista **mostra**, il guard **non sa** |
| **β** | un default a DB: `scadenza_id` si riempie da solo quando il documento ha **esattamente una** rata (trigger `a05_…`, prima del guard `a10` — ⛔ se girasse dopo, il guard vedrebbe NULL e la capienza salterebbe proprio sulla riga che deve vedere) | copre fondo, riga manuale e NC in un colpo; ⚠️ ma la riga del fondo passerebbe allora dal guard di capienza **dentro** `fn_ricalcola_totali_fattura`, che è percorso vivo della pipeline e *logga, non solleva*: serve un'esenzione o `forzata`, e su un documento a più rate non risolve niente | risolve il caso di P-5 e basta; sposta il problema sui documenti a più rate |
| **γ** ⭐ | **imputazione derivata**: nel nucleo di P-3 i movimenti (e le righe postabili) **senza rata** di un documento si imputano alle sue rate in ordine di `data_scadenza`, fino a capienza, con il segno del documento. Nessuno scrive niente: è D2 (*«lo stato della rata è derivato, mai scritto»*) applicato fino in fondo | `Σ saldi rate = saldo documento` **sempre**, per costruzione; il fondo sulla NC azzera la sua unica rata; la fattura a rata unica pagata «senza rata» esce dal picker; il guard di capienza, che legge il nucleo, **vede** ciò che il documento sa. Costo: una window function nel nucleo (cumulato delle rate per documento contro il non-imputato del documento), scritta una volta | la forma che un ERP dà a questa domanda da sempre; è una **rev del nucleo**, non un cantiere |

Raccomando **γ**, e propongo di farla come **seconda rev del nucleo**, dopo
che P-3 è applicata col comportamento di oggi e i suoi pgTAP verdi: così la
prima rev prova che il contenitore è fedele e la seconda prova la regola nuova,
e un rosso dice quale delle due ha sbagliato. ⛔ **P-5 non parte prima di
Q-A**: senza, consegna il doppio credito.

### 4-bis.7 Domande per Tid

| | Domanda | La mia proposta |
| --- | --- | --- |
| **Q-A** ✅ | Il punto cieco della rata (§4-bis.6): α, β o γ? **Blocca P-5**, tocca P-3 (una rev) | ✅ **γ — decisa da Tid il 2026-09-17**: imputazione derivata nel nucleo, come seconda rev dopo P-3 |
| **Q-B** ✅ | Il filtro «solo aperte» e il predicato «selezionabile» nel picker: `saldo <> 0` (residuo, brief madre §3.4 «si guarda il residuo») o `saldo − in_lavorazione <> 0` (lo spazio, che è ciò che il guard confronta)? Se il picker propone il residuo su una rata già tutta dichiarata in un'altra bozza, il DB la rifiuta al Salva | ✅ **Tid, 2026-09-17**: «aperta» = `saldo <> 0`; «selezionabile» e **importo proposto** = `saldo − in_lavorazione`. Nessuna quarta colonna a DB: si calcola. ⚠️ Da riportare nel piano BE/FE (§4.2 e §5.2 di quel piano dicono `residuo <> 0` per la selezionabilità) |
| **Q-C** ✅ | La data dell'unica rata della NC: `fattura.data` (brief) o il primo offset del termine di pagamento, `fine_mese` compreso? | ✅ **Tid, 2026-09-17: il termine** — la rata resta figlia del termine (lo snapshot in `meta` dice il vero), una NC «da regolare a 30 giorni» è una cosa reale, e `fattura.data` sarebbe una seconda regola; chi vuole «subito» dà alla NC un termine immediato, che è un dato. Nello snapshot entra `rata_unica_credito: true` |
| **Q-D** ✅ | Il log `W_SCADENZE_TOTALE_NEGATIVO` su base negativa: resta (riformulato: «generata una rata di credito») o cade? | ✅ **Tid, 2026-09-17: resta**, riformulato — *«a volte è un fondo configurato male, e la differenza la vede una persona»* è ancora vero, e un W_ che sparisce toglie un occhio. Il codice non cambia (⛔ i `W_` restano `W_`); cambia il testo del messaggio nel diario |
| **Q-E** ✅ | `registro_*` anche su `vw_ddt_lista`, `vw_ordini_lista`, `vw_resi_lista` nello stesso giro (3 changeSet, 3 pgTAP)? | ✅ **Tid, 2026-09-17: sì** — stesso blocco su tutte le sorelle che un registro ce l'hanno, e una riga nel changeSet che dice perché le altre tre non lo avranno mai |

✅ **Tutte e sei chiuse il 2026-09-17**: il piano di §4-bis.8 non ha più passi in attesa. Sviluppo avviato lo stesso giorno (registro in §9).
| **Q-F** ✅ | Pregresso NC senza rata: confermi **niente backfill** (SQL a mano su dev se serve)? | ✅ **sì — Tid, 2026-09-17**: non c'è produzione |

### 4-bis.8 Ordine dei changeSet e dei pgTAP

Data `20260917`, NN dal primo libero (`-01` è già preso da `vw_partite_merce`,
non ancora committato): numerazione **globale per data**, si assegna al momento
di scrivere. Nessun `runOnChange` in `20_code`; `validCheckSums: ANY` al plurale.

| # | Fase | ChangeSet | pgTAP | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | `20_code/vendite` | `update-vw-fatture-lista-numero-documento-registro` | `test-vw-fatture-lista.sql` 8 → 11 | — |
| 1-bis | `20_code/vendite` ×3 | `update-vw-{ddt,ordini,resi}-lista-registro` | tre `has_column` nei rispettivi presidi | Q-E |
| 1-ter | `20_code/pagamenti` | `update-vw-rate-fuori-capienza-numero-documento` (append) + riga CSV id 52 `attivo=f` | `has_column` in `test-abbinamento-rata` | — |
| 2 | `20_code/vendite` | `create-vw-fatture-scadenze-lista` | nuovo `test-vw-fatture-scadenze-lista-v1.sql` | — |
| 3 | `20_code/pagamenti` | `create-fn-get-saldi-rate` (nucleo) | nuovo `test-fn-get-saldi-rate-v1.sql` | — |
| 4 | `20_code/pagamenti` | `update-fn-get-saldo-rata-su-nucleo` (porta 1, firma invariata) | `test-abbinamento-rata`, `test-fn-get-saldo-fattura-tre-numeri` **invariati e verdi** | 3 |
| 5 | `20_code/pagamenti` | `create-vw-saldi-rate` (porta 2) | nel file di 3 | 3 |
| 6 | `80_data/sql/ui` | `lista_definizione.csv` (68, `attivo=f`), `lista_colonna.csv` (tutte `attivo=f`), `lista_preset.csv` + `lista_preset_colonna.csv` (ASC su `data_scadenza`) | `test-liste-preset-default-v1`; `gen_seed_lista.py --verifica-ordinamento pagamenti.rate` (KO atteso finché il BE non ha la whitelist: si dichiara) | 2 applicata |
| 7 | `20_code/pagamenti` | `update-fn-get-saldi-rate-imputazione` (γ) | rev del file di 3: la fattura a rata unica pagata senza rata esce a residuo 0; la NC col fondo idem; `Σ rate = documento` su un piano a tre rate con un acconto senza rata | **Q-A** |
| 8 | `00_schema/vendite` | `drop-check-fatture-scadenze-importo-pos` | — | Q-A, Q-C, Q-D, Q-F |
| 9 | `20_code/vendite` | `update-fn-genera-scadenze-fattura-rata-unica-credito` | `test-genera-scadenze-fattura-v1` test 13 riscritto; `test-fatture-log-error-code` test 9 | 8 |
| 10 | `20_code/vendite` | `update-fn-assign-numero-fattura-rate-su-credito` | `test-numerazione-guard-coerenza-v1` test 6 riscritto + uno nuovo | 8 |
| 11 | `20_code/pagamenti` | `update-vw-rate-fuori-capienza-forma-d14c` | `test-abbinamento-rata` 13-14 invariati; i due motivi sul negativo nel nuovo `test-nc-rata-unica-v1.sql` | 7, 9 |
| 12 | doc | `manual/vw_fatture_scadenze_lista.md`, `manual/fn_get_saldi_rate.md` (rimandano alla guida dei pagamenti), `manual/fn_get_saldo_rata.md` (una riga: «è la porta 1 del nucleo»), `manual/fatture_scadenze.md` (il segno, dopo P-5), `guide/gestione-dei-pagamenti.md` §base dei saldi (le tre porte) | — | ogni passo |

I passi 1-6 non aspettano nessuno e si possono scrivere subito; 7-11 aspettano
le risposte di §4-bis.7. Ogni passo: SQL **estratto** con `updateSQL` e provato
in `BEGIN/ROLLBACK`, pgTAP lanciato da Tid, brief aggiornato nello stesso giro.

### 4-bis.9 Stato dello sviluppo (2026-09-17, sera) — ✅ lato DB chiuso

✅ **Tutto scritto, applicato e verde.** Tid ha applicato su dev in due passate
(`databasechangelog`: `20260917-02 … -10` alle 15:04, `-11 … -14` alle 15:23),
poi il migrate coi seed `ui`; **pgTAP come `zeroerp_app` verdi e baseline
senza regressione** (Tid, 17-09 sera). Prima dell'apply i pgTAP erano stati
provati in transazione ritirata come owner (struttura, non permessi).

⭐ **Le tre fixture nuove sono state RIFATTE la sera stessa** (rev «il mondo si
costruisce, non si cerca», guida pgtap-come-si-scrive-un-test §79): la prima
stesura pescava un billing account / una terna emittente-utility-BA fra i dati
**esistenti**, che su un database ricostruito dai changelog (`zeroerp_ci`) sono
a **zero** — la fixture usciva vuota e le asserzioni confrontavano NULL, con
copertura pari a zero (la stessa forma già in `baseline-rossi-ci.tsv` come
`ERRORE_FIXTURE` per `test-numerazione-guard-coerenza-v1`). Ora i tre file
costruiscono un'azienda col suo operatore (`dbops.fn_pgtap_crea_emittente_operatore`)
**prima** del contesto e un cliente fatturabile (`dbops.fn_pgtap_crea_cliente_ba`)
nel contesto; `test-vw-fatture-scadenze-lista-v1` ha due rate e non una, perché
con l'azienda costruita «1 = 1» non distinguerebbe una vista fedele da un JOIN
che moltiplica per uno. I piani non cambiano (17 · 12 · 8).

| # | ChangeSet | pgTAP | Stato |
| --- | --- | --- | --- |
| 1 | `20260917-02-update-vw-fatture-lista-numero-documento-registro` | `test-vw-fatture-lista` 8 → **11** (NULL sulla bozza, «numero - serie» sulla numerata costruita, l'insieme esatto delle sorelle col registro) | ✅ applicato, verde come app |
| 1-bis | `-03/-04/-05 update-vw-{ddt,ordini,resi}-lista-registro` | il test 11 qui sopra (insieme = `ddt, fatture, ordini, resi`, nei due versi) | ✅ applicati |
| 1-ter | fuso nel passo 11 (stessa vista): `numero_documento` su `vw_rate_fuori_capienza` + riga CSV **766** su lista 52, `attivo=f` | test 12 di `test-nc-rata-unica-v1` | ✅ |
| 2 | `-06-create-vw-fatture-scadenze-lista` | **nuovo** `test-vw-fatture-scadenze-lista-v1` (8) | ✅ applicato, 8/8 come app su dbdev **e** su `zeroerp_ci` (fixture costruita, sera) |
| 3 | `-07-create-fn-get-saldi-rate` (rev 1: il contenitore) | **nuovo** `test-fn-get-saldi-rate-v1` (17) | ✅ applicato, 17/17 come app su dbdev **e** su `zeroerp_ci` (fixture costruita, sera) |
| 4 | `-08-update-fn-get-saldo-rata-su-nucleo` | `test-abbinamento-rata` (18) **invariato e verde**; `test-fn-get-saldo-fattura-tre-numeri` invariato | ✅ applicato |
| 5 | `-09-create-vw-saldi-rate` | test 17 del file di 3 | ✅ applicato |
| 6 | CSV `ui`: `lista_definizione` **68** (`attivo=f`), `lista_colonna` **750-765** (tutte `attivo=f`), `lista_preset` 68 (`data_scadenza ASC`), `lista_preset_colonna` | `test-liste-preset-default-v1` salta le liste spente; `--verifica-ordinamento` idem: si arma quando il BE la accende | ✅ applicato col migrate (mirror `runOnChange`) |
| 7 | `-10-update-fn-get-saldi-rate-imputazione` (γ) | test 7-16 del file di 3 | ✅ applicato, verde come app (fixture rifatta) |
| 8 | `-11-drop-chk-fatture-scadenze-importo-pos` (`00_schema`) | `test-nc-rata-unica-v1` test 7 (una rata di segno sbagliato si scrive, e la numerazione la ferma) | ✅ applicato |
| 9 | `-12-update-fn-genera-scadenze-fattura-rata-unica-credito` | `test-genera-scadenze-fattura-v1` test 13 riscritto (16/16); `test-fatture-log-error-code` test 9 **invariato** (il W_ resta) | ✅ applicato |
| 10 | `-13-update-fn-assign-numero-fattura-rate-su-credito` | `test-numerazione-guard-coerenza-v1` test 6 riscritto (9/9) | ✅ applicato |
| 11 | `-14-update-vw-rate-fuori-capienza-forma-d14c` | **nuovo** `test-nc-rata-unica-v1` (12); `test-abbinamento-rata` 13-14 invariati | ✅ applicato, 12/12 come app su dbdev **e** su `zeroerp_ci` (fixture costruita, sera) |
| 12 | doc: `manual/vw_fatture_scadenze_lista.md`, `manual/fn_get_saldi_rate.md`, `manual/vw_saldi_rate.md` (nuove); `manual/fn_get_saldo_rata.md`, `manual/vw_rate_fuori_capienza.md`, `manual/fatture_scadenze.md`, `guide/gestione-dei-pagamenti.md` (rev) | — | ✅ |

⛔ **I tre pgTAP nuovi erano rossi su `zeroerp_ci` — e la CI non li conosceva
(sera, corsa di Tid contro `baseline-rossi-ci.tsv`).** `ERRORE_FIXTURE` ×2
(saldi, NC) e `ASSERZIONE` (vista rate). Causa una sola: le fixture
**cercavano** l'azienda invece di costruirla — ricopiate da
`test-abbinamento-rata` e `test-numerazione-guard-coerenza-v1`, che nel
registro della CI sono **già `ERRORE_FIXTURE` per lo stesso motivo**: su un
database ricostruito dai changelog `billing_account`, `emittenti_fiscali`,
`emittenti_fiscali_utilities` e `user_emittenti_fiscali` sono a **zero**
(verificato sullo scratch). Riscritte sui BB della guida (§«Il mondo si
costruisce, non si cerca»): `dbops.fn_pgtap_crea_emittente_operatore()`
**prima** del contesto, `dbops.fn_pgtap_crea_cliente_ba()` **nel** contesto; la
NC scrive anche la riga `emittenti_fiscali_utilities` (2 dec, `HALF_UP`) che il
ricalcolo totali pretende. Provate come `zeroerp_app` in transazione ritirata su
**entrambi** i database: 8/8 · 17/17 · 12/12. ⚠️ La prova «come owner» del
pomeriggio non poteva vederlo: l'owner salta la RLS e dbdev ha le anagrafiche.
✅ **E i sei file da cui la forma veniva sono stati riscritti nello stesso
giro** (decisione di Tid, sera): `test-abbinamento-rata` (18),
`test-fn-get-or-create-vendite-contabile` (9), `test-fn-posta-contabile` (20),
`test-numerazione-guard-coerenza-v1` (9), `test-genera-scadenze-fattura-v1`
(16), `test-vw-fatture-lista` (11) — tutti sui BB, provati come `zeroerp_app`
in transazione ritirata su dbdev **e** su `zeroerp_ci`, nessun residuo. Tre
cose emerse riscrivendo: (a) `fn_get_or_create_vendite_contabile` col lotto
vuole un lotto **dell'emittente** (livello 2 della sede unica; `codice` ed
`emittente_soggetto_ruolo_id` sono NOT NULL — il ripiego «crea un lotto senza»
non poteva mai passare); (b) in `test-genera-scadenze-fattura-v1` lo `skip`
del test 4 sparisce: la fattura oltre la soglia **nasce** in uno stato con
`congela_fiscale` (scelto dal contratto, non dal nome), senza attraversare la
matrice degli stati — e il creatore applicativo `fn_get_or_create_fattura_header`
non serviva, il generatore legge solo la testata; (c) dove passa
`fn_ricalcola_totali_fattura` la riga `emittenti_fiscali_utilities` la scrive
il test. ⏳ Le sei righe di `baseline-rossi-ci.tsv` **rientrano alla prossima
corsa della CI** e le toglie `scripts/pgtap-baseline-ci-rientrati.sh` da quel
log — non da qui.

**Scostamenti dal piano, emersi sviluppando** (tutti nei changeSet, qui in una riga):

- ⛔ **Il nucleo NON accetta «NULL = tutte le rate»**: l'array è obbligatorio.
  Provato con `EXPLAIN`: `p IS NULL OR x = ANY(p)` si piega a `Index Cond`
  con un array costante, ma con `ARRAY[sc.id]` in `LATERAL` (o un parametro
  plpgsql in piano generico) il ramo `IS NULL` non si piega e l'`OR` diventa una
  scansione intera dei movimenti **per rata** — sul percorso del guard di
  capienza. `vw_saldi_rate` passa `ARRAY(SELECT id FROM fatture_scadenze)`.
  ⇒ Per il BE: la porta 3 è **una chiamata con l'array della pagina**, non una
  `LATERAL` per riga.
- ⚠️ **L'ordine dei fatti conta** (imputazione): un acconto senza rata già
  imputato alla rata 1 occupa il suo spazio, e una riga diretta sulla rata 1 che
  arriva dopo trova quel che resta — il guard la respinge coi numeri. È «ciò che
  vedi è ciò che vale»: il picker mostra i numeri del nucleo e il guard accetta
  esattamente quelli. Dichiarato nel `-10`, nella guida e nel pgTAP.
- `vw_rate_fuori_capienza`: i **candidati** includono i documenti con movimenti
  senza rata (altrimenti l'imputazione avrebbe aperto un buco nell'elenco), e il
  saldo arriva dal nucleo in una chiamata invece che in `LATERAL` per rata.
- Snapshot in testata sulla NC: `numero_rate = 1` (il piano **applicato**) +
  `rata_unica_credito = true`; il termine resta in `termine_pagamento_id`.
- `test-numerazione-guard-coerenza-v1` test 6: il messaggio è ora «…su un totale
  a pagare **zero**».

**Per il BE, in aggiunta al §5** (dalle decisioni Q-A/Q-B e da ciò che il DB
ha scritto):

- la vista P-2 ha la chiave **`scadenza_id`** (non `id`): `dataKey="scadenza_id"`
  su `<ListaConfigurabile>`; la selezionabilità e l'importo proposto usano
  **`saldo − in_lavorazione`** (Q-B), «aperta» resta `saldo <> 0`;
- il seed `pagamenti.rate` nasce **tutto spento** (definizione e colonne): si
  accende nello stesso commit della proiezione, con `WHITELIST_BE` in
  `gen_seed_lista.py` e `--verifica-ordinamento pagamenti.rate` verde. Le
  colonne `ordinabile = t` del seed: `numero_documento` (ordinare per
  `(numero, serie)`, non per il testo), `data`, `ragione_sociale_completa`,
  `numero_rata`, `data_scadenza`, `importo`, `totale_doc`; i tre saldi `f`;
- la riga **766** (`fattura_numero_documento` su `pagamenti.rate_fuori_capienza`)
  è `attivo=f`: si accende quando `_RIGA…`/il repository della lista 52 proietta
  `numero_documento` dalla vista (che ora ce l'ha);
- la NC ha una rata: `RataSelect` «di troppo» → «da rimborsare» per natura
  (piano BE/FE §3.4), e il contesto PDF della NC ora riceve una rata negativa
  da `list_fattura_scadenze` — va deciso a parole nel template.

## 5. Cosa deve fare il backend *(solo l'elenco: il piano è loro)*

- **B** ✅ (17/09): **sette** colonne in `_RIGA_COLONNE` (le cinque previste — `fattura_numero_documento` dalla fn sede unica, `fattura_data`, `fattura_totale_doc`, `fattura_registro_codice`, `scadenza_importo` — più `fattura_natura_doc_codice_interno/descrizione`: la natura si segnala, D19-e) + `LEFT JOIN registri_fatturazione` e `nature_doc_fiscale`; tre presidi sul DB provvisto.
- **C** (dopo P-2/P-4): `GET /pagamenti/rate/` paginata in `saldi_service`; whitelist di ordinamento chiavata sul `campo_sorgente`; saldi in `LATERAL` sulla pagina (P-3 quando c'è).
- **D** (dopo C): `POST /pagamenti/distinte/{id}/righe/da-rate/` — fan-out per riga, `falliti[]` con l'errore intero (`ErrorTranslator.to_api_error`), `forzata`/`motivo_forzatura` per riga.
- **A** (dopo P-1): niente da fare, la lista passa `v.*`.

## 6. Cosa deve fare il frontend *(solo l'elenco)*

- **A**: opzione del `FatturaLookup` a tre righe (documento · registro · data · totale · natura / cliente · id fiscale) — e la natura è un **Tag**, non testo.
- **B** ✅ (17/09): tabella righe con documento (Tag natura via il BB nuovo `NaturaDocTag`) e «Rata n · scadenza»; blocco «Destinazione» in sola lettura nel form (creazione e modifica) + `SaldoPanel` RATA/DOCUMENTO con `escludiRigaId`; `RataSelect` con l'importo della rata; etichetta della rata in una sede (`useEtichettePagamenti().rata`).
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
| **2026-09-17** (sera, ancora) | ✅ **Sei pgTAP di pagamenti/vendite riscritti sui BB** (Tid: «puoi correggere anche questi»): abbinamento-rata, get-or-create-contabile, posta-contabile, numerazione-guard-coerenza, genera-scadenze-fattura (lo skip del test 4 sparisce), vw-fatture-lista. Provati come app su dbdev e scratch: 18 · 9 · 20 · 9 · 16 · 11. Sei righe di `baseline-rossi-ci.tsv` da togliere dalla prossima corsa CI. Dettaglio in §4-bis.9 |
| **2026-09-17** (sera, poi) | 🔴→✅ **Tre pgTAP nuovi rossi su `zeroerp_ci`** (la CI non li conosceva): fixture che cercavano l'azienda, ricopiate da test già `ERRORE_FIXTURE` nel registro della CI. Riscritte sui BB (`fn_pgtap_crea_emittente_operatore` + `fn_pgtap_crea_cliente_ba`, NC con `emittenti_fiscali_utilities` costruita), provate come `zeroerp_app` su dbdev e scratch: 8/8 · 17/17 · 12/12. Dettaglio e residuo in §4-bis.9 |
| **2026-09-17** (notte) | ✅ **Migrate completo (seed `ui` compreso), pgTAP come app verdi, baseline senza regressione** — Tid. Lato DB **chiuso**. Le tre fixture nuove rifatte sul modello «il mondo si costruisce, non si cerca» (§4-bis.9): su `zeroerp_ci` le anagrafiche sono a zero e una fixture che «cerca» esce vuota. Il brief resta in `work-in-progress/` per A-D (BE/FE) |
| **2026-09-17** (sera) | ✅ **Lato DB consegnato e applicato su dev** (Tid, 15:04 e 15:23). Q-A…Q-F decise da Tid una alla volta (γ · spazio = saldo − in_lavorazione · data dal termine · il W_ resta · registro sulle tre sorelle · niente backfill). 13 changeSet `20260917-02…-14`: P-1 (+3 sorelle), P-2, P-3 (nucleo + porta 1 + porta 2, poi la rev γ), P-5 (drop CHECK, generatore, numerazione, `vw_rate_fuori_capienza` in forma D14-c + `numero_documento`), seed `ui` 68/750-765 + 766 tutti spenti. pgTAP: `test-fn-get-saldi-rate-v1` (17), `test-vw-fatture-scadenze-lista-v1` (8), `test-nc-rata-unica-v1` (12), `test-vw-fatture-lista` 8→11, due test riscritti. Due scostamenti di rilievo: l'array del nucleo è **obbligatorio** (EXPLAIN: l'`OR IS NULL` non si piega in LATERAL) e **l'ordine dei fatti conta** nell'imputazione. Stato e note per il BE in §4-bis.9 |
| **2026-09-17** | 🔎 **Risposta del DB** (§4-bis). Sei fatti del §1 corretti su `pg_catalog`: il CHECK è `>= 0` (lo zero è ammesso), le sorelle col registro sono **tre** e nessuna vista lo espone, una riga senza rata **non incontra nessuna capienza** (il guard esce su `scadenza_id IS NULL`), P-5 ha un **terzo** contro-pezzo (`fn_assign_numero_fattura` respinge rate su totale ≤ 0), la RLS delle rate ha anche la policy del portale, e impilare P-2 su `vw_fatture_lista` trascina la CTE del lineage (`EXPLAIN`). Piano: P-1/P-2/P-4 come chiesto (P-2 coi JOIN scritti, P-4 spento); P-3 in **terza forma** — un nucleo set-based `fn_get_saldi_rate` e tre porte; P-5 confermata sul modello ma **bloccata da Q-A**: il **punto cieco della rata** (i movimenti senza rata non arrivano a `fn_get_saldo_rata`; col fondo fattura una NC con rata conterebbe il credito due volte) — tre strade, raccomandata **γ** (imputazione derivata nel nucleo). Sei domande in §4-bis.7. Nessun changeSet scritto |
| **2026-09-17** (2) | ✅ **B committato** dopo la rilettura critica (piano, registro 17/09-2): un BB nuovo (`NaturaDocTag`), l'etichetta della rata in una sede, `useSaldi` con lettore e capacità in una riga sola, sei classi morte sanate. §5/§6 aggiornati |
| **2026-09-17** | ➕ **P-6** (§4.6), dal pezzo B scritto lo stesso giorno: l'esclusione «prima di sé» esiste solo sulla rata; sul documento il pannello la dichiara non applicata |
| **2026-09-15** | 📝 Brief scritto (BE/FE), dopo la decisione di Tid in chat: i quattro pezzi accettati; sulla nota di credito «una rata sola, segnalata nel picker». Fatti verificati sulla doc auto-gen: NC senza rate per costruzione (base < 0), CHECK sull'importo positivo. D19 riportata nel brief madre §2-bis |
