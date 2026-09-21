# Brief DB — anagrafiche di magazzino: il guard sul padre dell'ubicazione, tre codici, tre liste

> **Destinatario:** team DB (`dev/db-tid`). **Chi scrive:** BE/FE, 2026-09-21.
> **Origine:** [piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md](piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config.md)
> §7 — magazzini, ubicazioni e lotti escono dal pannello config e hanno
> endpoint e drawer propri (decisione **B** di Tid, 2026-09-20). Nessun DDL di
> tabella: tutto ciò che serve c'è già. Restano una regola del modello che oggi
> nessuno fa rispettare (R-1, **decisa da Tid il 2026-09-21: «ora»**), tre codici
> per i 404 delle tre anagrafiche (R-2) e tre liste a catalogo (R-3, dato non
> DDL: le righe le genera BE/FE, l'apply del mirror `ui` è di Tid).
> **Stato:** ✅ **lato DB APPLICATO il 2026-09-21** (§5): R-1 con le due decisioni
> di Tid del §4-bis (lock su `magazzino_id`, anti-ciclo), R-2 sei codici con le
> frasi; pgTAP verde come app (12/13 + lo skip del 10, che si accende quando il
> job genera il lock — vedi §6). **Resta**: il commit; il trigger di lock su dev
> (job delle 21:00 o `CALL`); R-3 (righe del BE non ancora arrivate: apply del
> mirror `ui` + il nome di `magazzino.lotti` nel pgTAP delle liste globali).
> R-2 è pronto per i tre dettagli del BE.

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

## 4-bis. Risposte del team DB (2026-09-21) — ✅ D1 e D2 decise da Tid

Letto il modello vivo (`ubicazioni`, la policy `rls_ubicazioni_ef_whitelist`, i
trigger montati, i CSV dei codici e dei lock) prima di scrivere. Tre cose che il
brief non vedeva, due delle quali cambiano la forma di R-1:

| # | Il brief diceva | Sul modello | Deciso |
| --- | --- | --- | --- |
| **D1** | «vale anche sull'`UPDATE OF magazzino_id`: spostare un'ubicazione lasciandole il padre vecchio è lo stesso difetto dall'altro verso» — chiuso guardando il *padre* | un'ubicazione che cambia magazzino porta con sé anche i **figli** (resterebbero nel magazzino vecchio col padre in quello nuovo: il guard sul padre non li vede) e il **registro** (`movimenti.ubicazione_id` accanto a `movimenti.magazzino_id`: le righe storiche direbbero «ubicazione di B in un movimento di A»). `magazzino_id` è identità, come `magazzini.codice` (lockata) e `ordini.billing_account_id` (`E_ORD_CLIENTE_IMMUTABILE`) | ✅ **Lock**: una riga in `dbops/automation_lock_columns.csv`, codice `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE` (`CONFLITTO_STATO`, la frase dice cosa fare: disattivare e crearne una nel magazzino giusto). Il guard resta solo su `INSERT OR UPDATE OF parent_id`. ⚠️ Il trigger di lock lo genera l'automazione: in CI `ci_apply`, su dev il job `automations_lock_columns` (21:00) o `CALL maintenance.proc_automations_lock_columns_job()` |
| **D2** | «un padre uguale a sé stesso è un ciclo di lunghezza uno: lo stesso guard lo rifiuta con lo stesso codice» | su `UPDATE OF parent_id` la FK e il `require_active_parent` lasciano passare A→B→A di **qualsiasi** lunghezza: la gerarchia non aveva nessun presidio (lo diceva anche il manuale della tabella). E «appartiene al magazzino X, non a X» è una frase falsa per un ciclo dentro lo stesso magazzino | ✅ **Nello stesso guard, codice separato** `E_MAG_UBICAZIONE_PADRE_CICLICO` (`DATO_ERRATO`, campo `parent_id`): risalita degli antenati con l'array dei visitati, solo in `UPDATE` (in `INSERT` la riga nuova non è in nessuna catena; `id` è `IDENTITY BY DEFAULT`, quindi in un `BEFORE INSERT` `NEW.id` c'è già e `parent_id = id` si vede) |
| — | (niente) | il guard è `INVOKER` e legge il padre sotto RLS via magazzino: un padre di **un altro emittente non risolve**, mentre la FK — che la RLS non la vede — passerebbe | si rifiuta anche allora, con `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO` e la frase che lo dice («non è visibile con i permessi di chi sta operando»): **fail-closed**, come `trgfn_trasferimenti_guard_stesso_emittente` |

Altre tre note, minori:

- **Ordine dei `BEFORE … a10` su `ubicazioni`**: il trigger si chiama
  `trg_ubicazioni_a10_parent_guard_ins_upd` (non `…guard_parent…`) perché deve
  venire **dopo** `trg_ubicazioni_a10_lock_columns_upd` (`l` < `p`): prima
  l'immutabilità di `magazzino_id`, poi la validità del padre nuovo — conta solo
  per un `UPDATE` che cambia le due colonne insieme, ma è la frase che l'operatore
  legge. Letto sul DB: `… < lock_columns_upd < movimenti_* < parent_guard_ins_upd < …`.
- **R-2**: il brief nominava solo `codici_errore.csv`; le **frasi** stanno in
  `messaggi_errore.csv` (id 1105-1110). ⚠️ Per il BE: `CODICE_NON_MODIFICABILE`,
  che il piano §4.1 mappa per `magazzini.codice`, è **`obsoleto_dal 2026-08-05`**
  nel catalogo (eppure lo usano ancora 25 lock, quello compreso) — non è di questo
  brief, ma chi lo traduce lo sappia.
- **R-3, una trappola**: `lotti` non ha RLS. Se la lista `magazzino.lotti` nasce
  con `perimetro_emittente = f` (globale), il nome va **nell'elenco** di
  `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` (test 6) — il
  19-09 il cantiere osservabilità l'ha saltato: verde sul BE, rosso in CI. Quando
  le righe arrivano nel CSV, il team DB aggiunge il nome nello stesso giro.

## 5. As-built DB (2026-09-21)

| Pezzo | File |
| --- | --- |
| Guard + trigger | `db/changelog/migrations_v2/20_code/magazzino/20260921-14-create-trgfn-ubicazioni-guard-parent-mctit.yaml` — `magazzino.trgfn_ubicazioni_guard_parent()`, `trg_ubicazioni_a10_parent_guard_ins_upd` (`BEFORE INSERT OR UPDATE OF parent_id`); preCondition «nessuna riga cattiva» (`expectedResult: 0`: padre di altro magazzino o `parent_id = id`) |
| Codici (6) | `80_data/sql/config/codici_errore.csv`: `E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO`, `E_MAG_UBICAZIONE_PADRE_CICLICO` (`DATO_ERRATO`), `E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE` (`CONFLITTO_STATO`), `E_MAG_MAGAZZINO_NON_TROVATO`, `E_MAG_UBICAZIONE_NON_TROVATA`, `E_MAG_LOTTO_NON_TROVATO` (`NON_TROVATO`) |
| Frasi (6) | `80_data/sql/config/messaggi_errore.csv`, id 1105-1110 |
| Lock (D1) | `80_data/sql/dbops/automation_lock_columns.csv`: `magazzino.ubicazioni.magazzino_id → E_MAG_UBICAZIONE_MAGAZZINO_IMMUTABILE` |
| Presidio | `db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql` (plan 13; il 10 fa `skip()` dichiarato finché il lock non è generato) |
| Doc | `docs/it/dbzero/magazzino/manual/trgfn_ubicazioni_guard_parent.md` (nuovo); `manual/ubicazioni.md` (la nota «nulla impedisce un ciclo» sostituita dalla regola) |

**Provato** con l'SQL **estratto** dallo YAML + le 13 righe dei CSV rese come
`INSERT` + il lock nella forma che genera `fn_run_automations_lock_columns`, in
`BEGIN … ROLLBACK` sul DB di sviluppo come **owner**: preCondition a 0,
`plpgsql_check` senza rilievi, ordine dei trigger come atteso, **12/13**. Il 13°
è il test 4 (padre di un'altra azienda): come owner la RLS non filtra, il padre si
vede e viene rifiutato per magazzino diverso — rosso atteso, frase diversa; come
app (`PGTAP_RUNNER` default) la lettura dà NULL e la frase è quella «non è
visibile». Due mutazioni accendono solo il test giusto: senza la risalita degli
antenati cade il 6, senza il check `parent_id = id` cade il 5.

**Passi di Tid**, in ordine (✅ 1 e 3 fatti il 21-09 mattina): (1) `make db-migrate`; (2) il lock su dev:
`CALL maintenance.proc_automations_lock_columns_job()` (o attendere le 21:00);
(3) `scripts/testpgtap.sh magazzino/test-ubicazioni-guard-parent-v1.sql` come
app (atteso 13/13, il 10 non più skip) e la baseline di `magazzino` +
`dbops/test-riferimenti-morti-v1`; (4) rigenerare la doc auto-gen
(`funzioni/trgfn_ubicazioni_guard_parent.md` include il manuale); (5) commit.
Poi, quando arrivano le righe di R-3: apply del mirror `ui` e il nome di
`magazzino.lotti` nell'elenco del pgTAP delle liste globali.

## 6. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-21 | Brief scritto dal BE/FE (R-1, R-2, R-3). |
| 2026-09-21 (notte) | ✅ **Lato DB scritto**: D1 (lock su `magazzino_id` al posto del ramo `UPDATE OF magazzino_id`) e D2 (anti-ciclo, codice separato) decise da Tid sulla raccomandazione; `20260921-14` + 6 codici + 6 frasi + 1 lock + pgTAP (13) + due manuali. Provato con l'SQL estratto in transazione ritirata, 12/13 come owner (il 13° è il caso RLS, verde solo come app). Da applicare (§5). |
| 2026-09-21 (mattina dopo) | ✅ **APPLICATO** da Tid (`20260921-14` EXECUTED 10:42, CSV via mirror). Primo giro del pgTAP come app: 11 ok, 1 skip, **test 4 rosso per un refuso di stile** — il guard scriveva `e'` nella frase «non e' visibile…» mentre le frasi del catalogo (e il test) usano `è`. La sostanza era verde: sotto RLS il padre dell'altra azienda non si vede (l'id al posto del codice nella frase) e il rifiuto è fail-closed. Corretto nello YAML (non pushato) e riallineato il dev con l'SQL estratto + `md5sum = NULL` sulla riga di `databasechangelog`, checksum ricalcolato dal migrate successivo. Ora: **12/13 + skip del 10**. ⏳ Il trigger di lock su `magazzino_id` **non è ancora generato** su dev (job `automations_lock_columns` delle 21:00, o `CALL maintenance.proc_automations_lock_columns_job()`): quando c'è, il 10 diventa un'asserzione vera (13/13). Restano commit e R-3. |

## Ai team, per chiudere

- **DB**: ✅ R-1 (guard + due codici + lock + pgTAP), ✅ R-2 (sei righe fra codici e
  frasi). Resta: il nome di `magazzino.lotti` nel pgTAP delle liste globali quando
  le righe di R-3 arrivano.
- **Tid**: apply (§5, cinque passi); apply del mirror `ui` quando le righe di R-3
  sono nel CSV.
- **BE/FE**: parte dal Pezzo A del piano (non dipende da questo brief); B/C/D
  dopo R-2 e R-3 applicati e verificati sul DB vivo. ⚠️ Per il traduttore dei
  DB-errors delle ubicazioni: **tre** codici, non uno — i due del guard (campo
  `parent_id`) e quello del lock su `magazzino_id` (che il PATCH non dovrebbe
  nemmeno mandare: la colonna non è nel form).
