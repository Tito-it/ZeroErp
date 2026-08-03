# Brief BE → DB — l'emittibilità della commessa: renderla visibile e sbloccabile

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** 15 attività di giugno stanno nella card «Da emettere» della dashboard
competenza e **non sono fatturabili da nessun verbo**, perché la loro commessa è
rimasta in `BOZZA`. La lista promette un lavoro che il motore non può fare, e
dall'interfaccia non esiste modo di sbloccarla.
**Decisione presa da Tid** (2026-08-04): i dati sporchi non sono il problema
(siamo in test) — **è un buco di modello e va chiuso**. E le attività bloccate
vanno **segnalate, non nascoste**: sono lavoro reale.
**Correlati:**
[vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) ·
[vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) ·
[fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) ·
[transizioni_stati_commessa](/dbzero/vendite/tabelle/transizioni_stati_commessa) ·
[fn_available_actions_commessa](/dbzero/script/funzioni/fn_available_actions_commessa)

---

## 1. Il fatto, misurato

Tid ha chiesto l'emissione mirata sul gruppo
`ORDINE_VENDITA:019eb2ac-3058-704a-91ee-e15247e85145`, competenza giugno 2026.
Il job **141** è finito `FATTO`, con `lane: 0`, `lotti: []`, `falliti: 0`,
`per_motivo: {}`. Nessun errore, nessuna fattura.

La riga c'era ed era a posto:

| | |
| --- | --- |
| `commesse_attivita` 69 | `NON_EMESSA` + `APPROVATA`, `tipo_doc_fiscale_id = 1`, competenza `2026-06-01` |
| commessa 108 (`CMM-20260610175449872-e059eb`) | stato **`BOZZA`** → `stati_commessa.emittibile = **false**` |

`fn_list_emittibili_lane` richiede `sc.emittibile = true`: nessuna terna, nessun
lotto. Corretto, e completamente muto.

**Non è un caso isolato** (query sul DB di sviluppo):

| Stato commessa | `emittibile` | Commesse | Attività pronte | Competenze |
| --- | :---: | ---: | ---: | --- |
| `BOZZA` | false | **5** | **15** | giugno 2026 |
| `PRONTA_FATTURAZIONE` | true | 3 | 38 | giugno → agosto 2026 |

Sono le commesse 66, 103, 104, 107, 108, create fra il 5 e il 10 giugno. La
causa è databile: il ponte `_rendi_commessa_emittibile` — che dopo un push
riuscito approva le righe e porta la testata a `PRONTA_FATTURAZIONE` — è entrato
col commit `09df3dd35` **il 10 giugno**. Quelle commesse nascono da push
precedenti. È pregresso, non un difetto attivo del ponte.

---

## 2. I due buchi

### 2.1 La dashboard e il motore non applicano lo stesso filtro

`vw_dash_competenza_attivita` esclude solo le commesse `ANNULLATA`:

```sql
WHERE ... AND (sc.codice_interno)::text <> 'ANNULLATA'::text
  AND (ca.stato_emissione)::text <> 'ANNULLATA'::text
  AND (((ca.stato_approvazione)::text <> 'RIFIUTATA') OR (ca.stato_emissione = 'EMESSA'))
```

Nessun riferimento a `sc.emittibile`, che è invece il criterio della discovery.
Lo stadio `DA_EMETTERE` guarda solo la riga (`stato_emissione <> 'EMESSA'`), mai
la testata. Quindi la card mostra come emettibile ciò che non lo è.

### 2.2 Una commessa bloccata non ha via d'uscita

La transizione esiste ed è attiva, ma è dichiarata **non manuale**:

| da | a | `meta` |
| --- | --- | --- |
| `BOZZA` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |
| `APERTA` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |
| `IN_ESECUZIONE` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |

Risultato su `script.fn_available_actions_commessa(108)`:

```json
{"stato_codice": "BOZZA", "is_emittibile": false, "can_change_state": true,
 "available_actions": [{"key": "annulla", "target_state": "ANNULLATA", ...}]}
```

**Una sola azione: annullare.** Se il ponte automatico non scatta — push
fallito, dato caricato per altra via, o come qui una commessa più vecchia del
ponte — la commessa resta bloccata per sempre e l'unica uscita offerta è
distruggere il lavoro. Questo è il buco di modello.

---

## 3. Cosa chiediamo

### 3.1 🔴 La vista espone l'emittibilità della testata

Una colonna in `vw_dash_competenza_attivita`, propagata poi in
`vw_dash_competenza_gruppi` (dove entra nella `GROUP BY` insieme al gruppo, o
come `bool_and`/`bool_or` secondo la vostra preferenza):

| Colonna | Tipo | Da |
| --- | --- | --- |
| `commessa_emittibile` | `boolean` | `stati_commessa.emittibile` della testata |

**Segnalare, non nascondere** (decisione Tid): quelle 15 attività sono lavoro
reale e toglierle dalla card le renderebbe invisibili invece che bloccate. Col
flag, la lista marca la riga e ne spiega il motivo, e il verbo «Fattura questo»
può nascere già disabilitato invece di partire e non fare nulla.

Se preferite esporre lo `stato_commessa` (testo) al posto del solo booleano,
per noi va bene: ci serve poter dire *perché* è bloccata, non solo *che* lo è.

### 3.2 🔴 `BOZZA|APERTA|IN_ESECUZIONE → PRONTA_FATTURAZIONE` diventi manuale

Nel seed di `transizioni_stati_commessa`, `meta` con la stessa forma delle altre
azioni manuali (è il contratto che `fn_available_actions_commessa` già legge):

```jsonc
{
  "manuale":  true,
  "action_key": "rendi_pronta",
  "label_key":  "vendite.commesse.azione_rendi_pronta",
  "severity":   "success",
  "icon":       "pi pi-check-circle",
  "requires_confirm": true
}
```

Il ponte automatico **resta**: questa è la via di servizio per quando non
scatta, non un'alternativa al processo.

### 3.3 🟠 Un check che eviti di sostituire un buco con un altro

Rendere manuale la transizione senza guard permetterebbe di portare «pronta» una
commessa senza nulla di approvato — e il verbo di fatturazione fallirebbe di
nuovo, solo un passo più in là. Chiediamo la funzione pura, sul modello di
`fn_check_commessa_chiudibile` / `_annullabile` che avete già scritto il
2026-07-24:

```
script.fn_check_commessa_pronta_fatturazione(p_commessa_id) → jsonb  -- [] = lecito
```

Verdetto su: almeno una riga `APPROVATA` + `NON_EMESSA` con
`tipo_doc_fiscale_id NOT NULL`; commessa con emittente e utility valorizzati.
Usata **sia** da `fn_available_actions_commessa` (per `enabled` + `reasons`)
**sia** dal guard di transizione — una sola sede, come per le sorelle.

La composizione esatta dei motivi decidetela voi: il vincolo che ci interessa è
che il bottone e il guard leggano **lo stesso** verdetto.

### 3.4 🟢 pgTAP

| # | Scenario | Atteso |
| --- | --- | --- |
| 1 | Commessa `BOZZA` con righe approvate | `available_actions` contiene `rendi_pronta` **abilitata** |
| 2 | Commessa `BOZZA` senza righe approvate | `rendi_pronta` presente ma `enabled: false` + motivo |
| 3 | Transizione eseguita al netto del check | commessa `PRONTA_FATTURAZIONE`, `emittibile = true` |
| 4 | Guard e capability sullo stesso caso | **stesso verdetto** (nessuna divergenza) |
| 5 | Vista: commessa `BOZZA` con righe da emettere | riga presente con `commessa_emittibile = false` |

---

## 4. Cosa NON chiediamo

- **Nessuna correzione dei 5 dati di giugno**: sono di test, e una volta esposto
  il verbo si sbloccano dall'interfaccia. Se preferite comunque una migrazione
  dati, per noi è indifferente — ma non serve a chiudere il buco.
- **Nessun nuovo stato**: la transizione esiste già, cambia solo la sua
  dichiarazione a dato.
- **Nessuna modifica al ponte automatico** post-push: funziona, e resta la via
  normale.

---

## 5. Cosa abbiamo già fatto noi (BE), oggi

Il silenzio del giro mirato era la metà nostra del problema, ed è **chiusa**
(commit sul ramo BE, suite 3526 verdi):

1. Un'emissione mirata che non produce **nemmeno un lotto** ora **fallisce** con
   `E_FATTURAZIONE_GIRO_NESSUN_LOTTO` invece di registrare `FATTO`. Il perimetro
   mirato è **nominale**: «zero lotti su N gruppi chiesti» è una richiesta non
   soddisfatta, non un giro senza lavoro. Il giro di **massa** a vuoto resta un
   successo — lì «questo mese non c'era nulla» è legittimo, e il cron lo produce
   di routine.
2. Il messaggio dice **perché**, per ciascun gruppo. Sul caso di Tid:

   > *Nessun lotto prodotto: il gruppo richiesto non è fatturabile.
   > CMM-20260610175449872-e059eb: la commessa è in stato BOZZA, che non ammette
   > fatturazione (1 attività pronta in attesa).*

   La diagnosi (`CommesseRepository.diagnostica_gruppi`) **descrive fatti**
   (stato testata + conteggi righe per stato); non riproduce il criterio di
   ammissibilità, che resta di `fn_list_emittibili_lane`. Se ritenete che debba
   scendere a DB come funzione, siamo d'accordo: ditecelo e ve la passiamo.
3. Il fallimento è dichiarato **deterministico**, quindi la coda va in ERRORE
   subito invece di ripetere il giro 5 volte con backoff. Effetto collaterale
   utile: anche i payload malformati (`E_FATTURAZIONE_GIRO_PAYLOAD`), che oggi
   venivano ritentati 5 volte, ora falliscono al primo colpo.

Resta scoperto un caso che **dipende da voi**: l'emissione **parziale** (3
gruppi chiesti, 2 serviti). Oggi non sappiamo quali gruppi siano finiti in quale
terna, perché `fn_list_emittibili_lane` aggrega per `(emittente, tipo_doc,
utility)` e i gruppi si perdono nell'aggregazione. Se la lane potesse
restituire anche `gruppi_coperti text[]`, l'esito potrebbe dire «2 su 3, il
terzo no perché…». **Non è urgente** e non blocca nulla: valutatelo insieme al
resto.

---

## 6. Definizione di «fatto»

- [ ] `commessa_emittibile` (o `stato_commessa`) esposto dalle due viste;
- [ ] transizione `→ PRONTA_FATTURAZIONE` manuale con `meta` completo;
- [ ] `fn_check_commessa_pronta_fatturazione` come sede unica di capability+guard;
- [ ] pgTAP §3.4 verdi;
- [ ] FE: riga bloccata segnalata in dashboard + verbo «Rendi pronta» sul drawer
      commessa (nostra metà, parte a prerequisiti pronti);
- [ ] le 5 commesse di giugno sbloccate dall'interfaccia da Tid, e le 15 attività
      fatturate — è la prova che il giro si chiude.
