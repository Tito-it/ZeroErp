# Brief DB — anagrafiche di magazzino: il guard sul padre dell'ubicazione, tre codici, tre liste

> **Destinatario:** team DB (`dev/db-tid`). **Chi scrive:** BE/FE, 2026-09-21.
> **Origine:** [piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md](piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md)
> §7 — magazzini, ubicazioni e lotti escono dal pannello config e hanno
> endpoint e drawer propri (decisione **B** di Tid, 2026-09-20). Nessun DDL di
> tabella: tutto ciò che serve c'è già. Restano una regola del modello che oggi
> nessuno fa rispettare (R-1, **decisa da Tid il 2026-09-21: «ora»**), tre codici
> per i 404 delle tre anagrafiche (R-2) e tre liste a catalogo (R-3, dato non
> DDL: le righe le genera BE/FE, l'apply del mirror `ui` è di Tid).
> **Stato:** 🔵 da applicare. R-1 non blocca il BE/FE (il picker filtra intanto);
> R-2 blocca i tre dettagli; R-3 blocca le tre liste.

---

## R-1 🟠 — `ubicazioni.parent_id` deve stare nello stesso magazzino

**Il fatto.** `magazzino.ubicazioni` ha `parent_id → ubicazioni.id` (gerarchia:
area → corsia → scaffale…) e `magazzino_id`. I trigger presenti sono
`trgfn_child_requires_active_parent` (il padre deve essere **attivo**) e i
`block_deact`: nessuno chiede che il padre sia **dello stesso magazzino**. Un
`INSERT` con `parent_id` di un altro magazzino passa. Fino a oggi nessuno
scriveva ubicazioni se non dal pannello config (id a mano): la regola non aveva
un chiamante. Con il drawer ne ha uno, e il picker FE propone solo le ubicazioni
del magazzino — ma «lo filtra il FE» è la seconda sede di una regola del modello,
e un client qualunque non la vede.

**Che cosa si chiede.** Un guard `BEFORE INSERT OR UPDATE OF parent_id,
magazzino_id` su `magazzino.ubicazioni`, fase `_a10_`, nome secondo convenzione
(`trg_ubicazioni_a10_guard_parent_stesso_magazzino_ins_upd`): se `NEW.parent_id
IS NOT NULL` e il padre ha `magazzino_id <> NEW.magazzino_id` → solleva
**`E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`**, classe `DATO_ERRATO`, `campo =
parent_id` nel `context`, `VARIADIC` con i due codici di magazzino (la frase
nomina il dato: *«L'ubicazione padre %s appartiene al magazzino %s, non a %s»*).
⚠️ Vale anche sull'`UPDATE OF magazzino_id`: spostare un'ubicazione di magazzino
lasciandole il padre vecchio è lo stesso difetto dall'altro verso. Un padre
uguale a sé stesso (`parent_id = id`) è un ciclo di lunghezza uno: se non lo
presidia già nulla, lo stesso guard lo rifiuta con lo stesso codice.

**Codice nuovo, non riuso** di `E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO`: quello è
sollevato da `fn_scrivi_movimento` (passo 8) su `ubicazione_id` di un movimento;
qui la condizione è un'altra e il campo è un altro (`parent_id`). Riusarlo
aggiungerebbe una famiglia al rubinetto degli accumulatori.

**pgTAP** (`db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql`, dal
template, come app con contesto operatore): due magazzini dello stesso
emittente da `dbops.fn_pgtap_crea_magazzino`, un'ubicazione in A, un
`INSERT` in B con `parent_id` di A → `throws_ok` con `P0001` e il codice; il caso
buono (padre in B) passa; `UPDATE magazzino_id` verso A col padre di B → rifiuto.

## R-2 🔴 — tre codici `NON_TROVATO`

Verificato il 2026-09-20 nel modulo generato: esistono `E_MAG_DOCUMENTO_NON_TROVATO`
(documento interno) e `E_MAG_MAGAZZINO_NON_VALIDO`, nessuno per le tre
anagrafiche. Sul dettaglio `GET /magazzino/magazzini/<id>/` (e figli) chi chiede è
una persona con un id nell'URL e la riga **non c'è** (inesistente, o fuori dal
perimetro RLS: stesso 404 per convenzione no-leak) — è la definizione della
classe. `_magazzino_o_400` del documento interno resta com'è: lì il magazzino è
un **dato di form** (`E_VALIDAZIONE` col campo), non una risorsa indirizzata.

| Codice | Classe | Note (per il CSV) |
| --- | --- | --- |
| `E_MAG_MAGAZZINO_NON_TROVATO` | `NON_TROVATO` | dettaglio/PATCH di un magazzino: non esiste o è fuori dal perimetro dell'operatore (RLS: la riga non c'è, stesso 404 di un id inesistente). Nasce il 2026-09-21 (brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici, R-2) |
| `E_MAG_UBICAZIONE_NON_TROVATA` | `NON_TROVATO` | dettaglio/PATCH di un'ubicazione sotto `magazzini/<id>/ubicazioni/<uid>/`: non esiste, o non è di quel magazzino, o il magazzino è fuori perimetro. Idem |
| `E_MAG_LOTTO_NON_TROVATO` | `NON_TROVATO` | dettaglio/PATCH di un lotto: non esiste (nessuna RLS: un lotto è dell'articolo). Idem |

Lato BE, allo stesso giro: `genera_error_policies` e i tre ripieghi senza `%s`
in `error_messages_fallback.py` (`feedback_ripiego_ogni_codice_vivo`). ⚠️ Non
rigenerare col DB avanti rispetto a git: prima il CSV mergiato, poi il modulo.

## R-3 🟡 — tre liste a catalogo (dato, non DDL)

`ui.lista_definizione` + `lista_colonna` per `magazzino.magazzini`,
`magazzino.ubicazioni`, `magazzino.lotti` — righe generate da BE/FE con
`scripts/gen_seed_lista.py` (id oltre il massimo fra CSV e DB), riviste a mano
(`formato = date_short` su `data_arrivo`/`data_scadenza`, `etichetta_i18n_key`
su ogni colonna, `sensibile` dove serve), poi **apply del mirror `ui`: Tid**, come
per le liste 70-77 del Lotto 2. Le colonne per lista stanno nel piano §4-6; le
righe CSV arrivano nel commit del Pezzo B/C/D.

## R-4 🟡 — `config.titoli_cortesia`: che cosa farne

Solo `id`, `descrizione`, `descrizione_breve` — senza `codice`/`codice_interno`
ne' `attivo`. `fn_get_lookup_codici` la rifiuta
(`E_LOOKUP_STRUTTURA_TABELLA_INVALIDA`), quindi il 21-09 e' uscita dalla
whitelist del lookup e dal registro del pannello config, dove era dichiarata e
rispondeva 500. **Nessun consumatore** nel BE ne' nel FE. Due strade, decisione
vostra: le si da' `codice` + `attivo` (e rientra nei vocabolari), oppure e' un
dato morto e si ritira come gli altri (analisi-software-per-dati-morti).

## Ai team, per chiudere

- **DB**: R-1 (guard + codice + pgTAP), R-2 (tre righe in `codici_errore.csv`), R-4 (una decisione).
- **Tid**: apply del mirror `ui` quando le righe di R-3 sono nel CSV.
- **BE/FE**: ✅ Pezzo A fatto il 21-09 (non dipendeva da questo brief); B/C/D
  dopo R-2 e R-3 applicati e verificati sul DB vivo.
