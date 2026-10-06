# Brief DB — Il riepilogo permessi diventa la lista operatori, con i permessi aperti

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§5), che **attende** la consegna DB.
> **Decisioni:** di Tid, 2026-10-06 (§2).
> **Stato:** ✏️ scritto, da passare al team DB.

## 1. Perché

La vista *Amministrazione software → Riepilogo permessi* è una matrice operatori × aree:
una colonna per area funzionale, generata a runtime. Con 14 aree non entra più nella
pagina e va scrollata in orizzontale. È anche fuori standard: una `DataTable` registrata
come eccezione, senza paginazione, kebab, esportazione né personalizzazione delle colonne.

Lato backend il motivo è lo stesso: la query costruisce con un f-string una subquery
`fn_resolve_livello_area(au.id, '<schema_db>')` **per ogni area**, su **tutti** gli
operatori in una volta.

Si passa alla forma standard:

* **una riga per operatore**: le colonne della lista Operatori, più una colonna
  **Override** col numero di override dell'operatore;
* sotto ogni riga, un'**espansione sempre aperta** con le aree come chip compatte:
  `Anagrafiche · Tutto · 3 ⚠`, cioè il livello effettivo, il numero di override
  nell'area e il triangolo se il tetto d'area ne ferma qualcuno. È la stessa lettura
  dell'elenco delle aree nel pannello permessi, e i due devono dire la stessa cosa;
* il **kebab** di riga: *Permessi*, che apre il drawer dei permessi, e *Modifica operatore*.

## 2. Le decisioni (Tid, 2026-10-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-1 | Lista nuova, o la lista Operatori? | **Il catalogo `anagrafiche.operatori`** (lista 28), con la stessa sorgente dati. Il riepilogo diventa «la lista operatori con i permessi aperti». Una seconda lista sugli stessi operatori sarebbe una copia destinata a divergere. |
| D-2 | Il numero conta tutti gli override o solo quelli in vigore? | **Quelli scritti**, a prescindere da `valido_dal`/`valido_al`. Come il badge del pannello. |
| D-3 | Il triangolo del tetto nelle chip? | **Sì.** |
| D-4 | Sede unica a DB per il conteggio degli override (§3.1), letta da lista, espansione e pannello? | **Sì**: building block unico (regola del 2). |

## 3. Richiesta

### 3.1 Una sede per «quali override ha un operatore, area per area»

Il numero serve in **tre** posti: la colonna della lista (il totale), le chip
dell'espansione (per area) e il badge del pannello (per area, oggi calcolato a video).
Sono tre letture della stessa regola. Per questo propongo una **sede unica a DB** e
non tre conteggi.

> ✅ Building block per **regola del 2**, confermato da Tid il 2026-10-06 (D-4). La
> forma qui sotto è una proposta, e la scelta finale spetta al team DB.

Forma proposta: una vista (o funzione) che dà **una riga per override scritto**, con la
sua area:

| colonna | da dove |
| --- | --- |
| `auth_user_id` | la tabella di override |
| `area_id` | `user_override_aree.area_id`; per un'azione `azioni_processo.area_id`; per un oggetto `area_model_overrides.area_id` (la FK composita garantisce che l'oggetto sia a catalogo) |
| `tipo` | `AREA` / `AZIONE` / `OGGETTO` |

**Perimetro del conteggio**: deve coincidere con ciò che il pannello mostra, altrimenti
lista e pannello danno due numeri diversi per lo stesso operatore.

* Aree **attive**.
* Azioni **attive**: il pannello mostra solo quelle (`listAzioniProcesso` filtra
  `ap.attivo`).
* Oggetti: tutti quelli a catalogo, **riservati compresi**. Il pannello mostra anche i
  riservati che hanno già un override, così restano visibili e si possono togliere.

📌 *Fatto da verificare, non motivo:* un override su un'azione **non attiva** oggi
resta scritto ma il pannello non lo mostra. Se il team DB ritiene che vada contato,
lo dichiari: allora il pannello si allinea e lo mostra, non il contrario.

### 3.2 Il riepilogo per area, per un insieme di operatori

```text
script.fn_get_permessi_riepilogo_aree(p_auth_user_ids integer[])
RETURNS TABLE (auth_user_id integer, area_id integer,
               livello config.livello_accesso,   -- effettivo dell'area
               override_count integer,           -- da §3.1, per (utente, area)
               voci_limitate integer)            -- azioni + oggetti fermati dal tetto
```

* **Una riga per (operatore, area attiva)**, anche senza override (`override_count = 0`).
* Il **livello** è quello effettivo dell'area, cioè la catena di `fn_resolve_livello_area`.
* Le **voci limitate** si contano da `fn_get_permessi_effettivi_azioni` (`limitata_da_area`,
  solo azioni attive) e `fn_get_permessi_effettivi_oggetti` (`limitato_da_area`). Sono le
  sedi uniche del tetto, e qui **non si ricalcola** niente.
* **Super admin** e **veste spenta** rispondono come rispondono le funzioni del tetto.
  Il riepilogo non aggiunge rami suoi: il bypass e il fail-closed stanno dove stanno.
* Riceve un **array di id**: il backend chiede solo le righe della **pagina** (25-50
  operatori), non tutti come oggi.
* `STABLE`. Il contesto GUC è quello delle funzioni del tetto, chiamate oggi dal
  pannello per un operatore diverso da chi guarda: va verificato che valga anche qui.

### 3.3 La colonna del catalogo

In `ui/lista_colonna.csv`, lista **28** (`anagrafiche.operatori`):

| campo | valore |
| --- | --- |
| `codice` / `campo_sorgente` | `override_count` |
| `etichetta` | `Override` |
| `etichetta_estesa` | `Override dei permessi scritti per l'operatore (aree, azioni e oggetti)` |
| `tipo_colonna` / `tipo_dato` / `formato` | `informazione` / `numeric` / `number` |
| `allineamento` | `right` |
| `ordinabile` / `filtrabile` / `esportabile` / `ricercabile_full` | `t` / `f` / `t` / `f` |
| `etichetta_i18n_key` | `amministrazione.col_override` (la chiave la aggiunge il FE) |
| `ordine_default` | dopo `unita_organizzativa_nome` (30), prima di `emittenti_descrizione` (40) |

Modello: la colonna `operatori_count` della lista reparti (id 969). Se esistono preset
della lista 28, la colonna va nei preset di default: la decisione è del team DB, che
conosce la forma di casa.

## 4. Test (pgTAP)

* §3.1: un operatore con un override per tipo, più un'azione **non attiva** con override
  e un oggetto **riservato** con override. I conteggi devono rispettare il perimetro di §3.1.
* §3.2:
  * una riga per area attiva anche a zero override;
  * il `livello` coincide con `fn_resolve_livello_area` per ogni (utente, area);
  * `voci_limitate` coincide con il conteggio fatto direttamente sulle due funzioni del
    tetto (area `BLOCCATO` + override azione abilitata ⇒ 1);
  * un super admin e una veste spenta rispondono come le funzioni del tetto;
  * un array vuoto dà zero righe.

## 5. Dopo la consegna: BE/FE (dev/backend-tid)

Si fa solo **dopo** l'applicazione a DB.

* **BE, lista operatori:**
  * la `SELECT` di `list_operatori` proietta `override_count` (totale da §3.1);
  * la colonna entra nella whitelist di ordinamento.
* **BE, riepilogo:** l'endpoint `permessi-riepilogo` legge
  `fn_get_permessi_riepilogo_aree(ids)` per gli id richiesti, cioè le righe della pagina.
  La query con un f-string per area si **toglie**.
* **FE, `PermessiRiepilogoView`:**
  * `ListaConfigurabile codice="anagrafiche.operatori"` con lo store della lista operatori;
  * slot `row-expansion` con le chip, espansione pilotata e **tutta aperta** a ogni
    caricamento («Comprimi tutte» resta l'azione di testata);
  * kebab `#actions` con *Permessi* e *Modifica operatore*;
  * la `DataTable` esce dal registro delle eccezioni (`datatable.baseline.json`).
* **I filtri del riepilogo** (emittente, reparto, super admin) devono esistere nella
  lista operatori. Quelli che mancano entrano nella sua whitelist. Va controllato il
  filtro emittente: oggi legge `config.user_emittenti_fiscali`, mentre lo scope dichiarativo è
  `fn_get_user_emittenti_scope`.
* **Pannello:** il badge per area legge lo stesso numero (§3.1) invece di ricontarlo a
  video (D-4).
* **i18n:** `amministrazione.col_override` in it/en.
* **Test:**
  * BE: proiezione e ordinamento di `override_count`, riepilogo per id;
  * FE: espansione aperta al caricamento, chip con numero e triangolo, kebab.
