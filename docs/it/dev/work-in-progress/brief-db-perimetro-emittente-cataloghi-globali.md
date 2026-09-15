# Brief DB — I cataloghi globali che il seed non dichiara: `perimetro_emittente = false` manca a cinque liste

> Chi scrive: backend (`dev/backend-tid`), 2026-09-15.
> Origine: collaudo in-app di «Esegui ora» ([piano-be-fe-avvio-manuale-di-un-processo.md](../work-done/piano-be-fe-avvio-manuale-di-un-processo.md)
> §4.4.2). Aprendo *Processi automatici* con **«Tutti gli emittenti»** nella
> combo, la lista è sbarrata dal cancello di perimetro («Scegli un emittente
> per continuare») — su un registro che un emittente non ce l'ha.
>
> **In una riga:** cinque righe nel CSV
> `80_data/sql/ui/lista_definizione_perimetro_emittente.csv`, dove oggi ce
> n'è una sola. Nessuna colonna, nessuna funzione, nessun changeSet nuovo
> oltre al seed. Più **cinque domande** su liste che una dimensione emittente
> ce l'hanno (§5).

---

## 1. Il fatto, misurato il 2026-09-15 (dbdev, `fn_resolve_lista_config` via API)

Con un token **senza** `emittente_attivo_id` (la combo su «Tutti gli
emittenti»), super admin:

| Lista | `perimetro_emittente` | `multi_emittente` | `richiede_scelta_emittente` |
| --- | --- | --- | --- |
| `amm.processi` | true (default) | false | **true — sbarrata** |
| `anagrafiche.operatori` | true (default) | false | **true — sbarrata** |
| `anagrafiche.emittenti_fiscali` | true (default) | false | **true — sbarrata** |
| `ui.lista_definizione` | true (default) | false | **true — sbarrata** |
| `storico.audit_log` | true (default) | false | **true — sbarrata** |
| `vendite.famiglie_documento` | **false** (seed) | false | false — si entra |

Il super admin deve scegliere un emittente per vedere **l'elenco degli
emittenti**. La misura serve a trovare l'errore, non a disegnare: la regola è
già scritta, e sta nel commento della colonna stessa.

## 2. La regola c'è già: è il commento di `ui.lista_definizione.perimetro_emittente`

`00_schema/ui/20260902-01`, testuale: *«su un catalogo GLOBALE — le famiglie
di documento, **le liste tecniche di ui**, **i vocabolari di config** — non
c'è nessun emittente da dire, quindi il suo `false` è letteralmente vero e
l'effetto è sbagliato: la schermata chiede di scegliere un emittente prima di
entrare, e sbarra la strada proprio a chi ha lo scope più largo»*.

Il commento nomina **tre** famiglie; il seed (`20260902-02`,
`lista_definizione_perimetro_emittente.csv`) ne dichiara **una**: la riga
`vendite.famiglie_documento,false`. Le liste tecniche di `ui` e il registro dei
processi sono rimaste al default `true`, che è il verso prudente per una lista
**nuova** — non per una la cui natura è già stata scritta.

Il backend lo sa da mesi, ma nella sede sbagliata per questo effetto:
`apps/core/tests/test_perimetro_emittente_copertura.py::_ESENZIONI` motiva
l'assenza del cancello **sull'endpoint** (`AdminAPIView`) e per `amm.processi`
scrive *«registro di catalogo, senza perimetro emittente»*, per tre `ui.*`
*«nessun `emittente_fiscale_id` in tabella»*. Ma il cancello **del pannello**
lo calcola `richiede_scelta_emittente(...)` dai flag del seed
(`perimetro_emittente.py`, ramo 2: «la lista non ha un perimetro → non c'è
niente da scegliere»), e il seed dice il contrario del registro. Due sedi che
dicono due cose: la differenza si vede solo su «Tutti gli emittenti».

## 3. Cosa si chiede — cinque righe di seed

In `80_data/sql/ui/lista_definizione_perimetro_emittente.csv`, accanto a
`vendite.famiglie_documento`:

| `codice` | `perimetro_emittente` | Perché (verificato sul dbdev il 15-09: nessuna colonna `emittente_fiscale_id`) |
| --- | --- | --- |
| `amm.processi` | false | `dbops.processi` è catalogo del software: le righe valgono identiche su ogni installazione. Le identità un emittente ce l'hanno, ma stanno nel **dettaglio**, non nella lista |
| `ui.lista_definizione` | false | catalogo delle liste |
| `ui.lista_colonna` | false | catalogo delle colonne |
| `ui.lista_colonna_permesso` | false | grant per colonna/profilo |
| `storico.audit_log` | false | diario delle modifiche ai dati: le colonne a catalogo sono `timestamp, tabella, tipo_operazione, user_modifica, dettaglio` — nessuna dimensione emittente sulla riga |

Tutte e cinque hanno `multi_emittente = false`, quindi il CHECK
`chk_ui_lista_definizione_perimetro_coerente` (`perimetro OR NOT multi`) è
soddisfatto. ⚠️ Non si tocca `multi_emittente`: dichiararle `true` vanterebbe
una capacità che non hanno, e `dbops.vw_liste_multi_emittente_non_certificate`
le intercetterebbe — è la strada breve che il commento della colonna ha già
rifiutato.

## 4. Cosa NON si chiede

* Nessuna modifica a `fn_resolve_lista_config`: legge già la colonna e la
  porta nell'envelope (`perimetro_emittente`, `COALESCE(…, true)`).
* Nessun cambio al default `true` della colonna: una lista nuova nasce **con**
  perimetro e la globalità si dichiara — è giusto così, ed è il motivo per cui
  la richiesta è un seed e non un DDL.
* Nessuna riga per le liste di **dominio** (`vendite.*`, `catalogo.*`,
  `pratiche.*`): lì il perimetro esiste e il cancello è voluto.

## 5. Domande al DB — le liste amministrative che una dimensione emittente ce l'hanno

Sono sbarrate allo stesso modo, ma per loro `perimetro_emittente = false`
sarebbe **falso**, quindi non le metto in §3. Vanno decise una per una:

| Lista | Il fatto | La domanda |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | **è** l'elenco degli emittenti | scegliere un emittente per vedere gli emittenti è una domanda senza risposta — ma la riga *ha* un emittente (se stessa). `perimetro = false` perché la riga **è** il perimetro? |
| `anagrafiche.emittente_billing_account` | mappa BA → emittente | come sopra: la colonna emittente è il contenuto della lista |
| `anagrafiche.operatori` | l'operatore ha uno scope di emittenti (n:m) | quale ramo di `richiede_scelta_emittente` è quello giusto? Oggi il super admin non entra senza scegliere |
| `config.email_log` | ha `emittente_fiscale_id` | è il candidato naturale a `multi_emittente = true` con la colonna esposta (certificazione P-4), non a `perimetro = false` |
| `ui.lista_preset` | ha `emittente_fiscale_id`; `_ESENZIONI` dice che la colonna «Riferimento» lo mostra per riga (P-2c) | idem: è «so dire da quale emittente arriva ogni riga» — cioè `multi_emittente`, da certificare |

⚠️ Queste cinque restano fuori dal seed finché non c'è una risposta: una riga
`false` messa «per far entrare» sarebbe la stessa strada breve di §3, con
l'altro flag.

## 6. Come si verifica che è arrivato

Le sei righe di §1 rilette con lo stesso token senza emittente: le cinque di
§3 devono rispondere `richiede_scelta_emittente = false`. Lato BE, dopo
l'apply, un presidio piccolo e senza DB in
`test_perimetro_emittente_copertura`: ogni voce di `_ESENZIONI` la cui ragione
dichiara «senza perimetro» / «nessun `emittente_fiscale_id`» deve avere la
riga `false` nel CSV — così registro e seed non possono più dire due cose.
Lo scrive il backend a seed applicato.
