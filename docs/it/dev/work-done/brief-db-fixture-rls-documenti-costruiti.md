# Brief DB — I test RLS dei documenti costruiscono il loro documento

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-07. **A chi:** Tid.
> **Origine:** [brief-db-veste-utilizzabile](brief-db-veste-utilizzabile.md) §7.4: la
> correzione delle fixture-operatore ha lasciato un debito che non era di quel cantiere.
> Figlio del cantiere «fixture che costruiscono»
> ([migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md)
> §3 D7; giro 2 in
> [work-done](brief-db-fixture-che-costruiscono-giro-2.md)).
> ✅ **CHIUSO il 2026-10-07, spostato in `work-done/`.** Tre giri, tutti verdi (Tid:
> apply di `20261007-23 → -26` e corse). I sette file `rls/` del censimento (§2)
> costruiscono il loro documento, e con loro quattro builder nuovi in `dbops`. Il debito
> che resta — le copie a mano di ordine, preventivo, commessa e attività negli altri
> pgTAP — torna nel documento principale,
> [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md)
> §3 D7.

## 1. Il difetto

Sette pgTAP `rls/` **cercano** nel DB il documento su cui provare la policy
(«la prima commessa / ordine / preventivo / fattura con un emittente», `LIMIT 1`) e
«l'altro emittente» come il primo diverso trovato. Quindi:

* su `zeroerp_ci` costruito da zero non trovano niente: `prereq` è falso e i casi
  finiscono nel soft-skip. **In CI la copertura è zero**;
* su dbdev provano un documento qualunque, che cambia nel tempo: il verde dipende dai
  dati di oggi;
* i due emittenti sono diversi per fortuna, non per costruzione.

La forma giusta c'è già: `rls/test-rls-resi-ef-whitelist-write` costruisce due aziende
(A possiede il documento, B è l'estranea) e il documento di A **prima** del
`FORCE ROW LEVEL SECURITY`, da owner senza policy; se qualcosa non si costruisce, il
file va rosso.

Gli operatori di questi file vengono già dalla madre (`fn_pgtap_crea_operatore_umano`,
fatto il 2026-10-07): qui si tocca solo il **documento**.

## 2. Censimento

| File | Cerca | Builder | Giro |
| --- | --- | --- | --- |
| `fatture-ef-whitelist-functional` | una fattura | `fn_pgtap_crea_fattura` ✅ esiste | 1 |
| `ddt-ef-whitelist-write` | BA, soggetto, articolo, emittenti; ordine → DDT | `fn_pgtap_crea_mondo_cliente` + `fn_pgtap_crea_ddt` ✅ esistono | 1 |
| `ordini-multipolicy` | un ordine | ⛔ manca `fn_pgtap_crea_ordine` | 2 |
| `preventivi-ef-whitelist-write` | un preventivo | ⛔ manca `fn_pgtap_crea_preventivo` | 2 |
| `commesse-ef-whitelist-write` | una commessa con attività | ⛔ manca `fn_pgtap_crea_commessa` | 3 |
| `fatture-satelliti-functional` | una fattura con righe e riepiloghi IVA | `fn_pgtap_crea_fattura` + righe nel test | 3 |
| `viste-fattura-invarianza` | un emittente con fatture con righe; tre viste di competenza | catena commessa → attività → fattura (modello: `vendite/test-vw-dash-competenza-v1`) | 3 |

Regola del 2 sui builder mancanti: oggi scrivono a mano un ordine **54** pgTAP, un
preventivo **40**, una commessa **36**. Una copia in più non si scrive: i tre builder
nascono in `dbops` (changeSet + manuale), sulla forma di `fn_pgtap_crea_fattura`
(mondo cliente + testata nello stato scelto, righe al test, esce `IMMEDIATE`).
⚠️ Le altre ~130 copie **non** migrano qui: restano debito di D7, censito sopra.

## 3. Regole del giro

* Il documento si costruisce **prima** dell'`ALTER ... FORCE`: dopo, la fixture
  sarebbe filtrata dalla policy che deve provare.
* `fn_pgtap_crea_mondo_cliente` senza contesto **apre** il contesto sull'operatore che
  costruisce (`app.ruolo_applicativo`, `app.current_user_id`). Questi file simulano
  l'identità caso per caso: finita la costruzione, le due GUC si **svuotano**, così ogni
  caso parte da «nessuno» e dichiara chi è.
* L'altra azienda si costruisce con `fn_pgtap_crea_emittente_operatore()`, mai pescata.
* Un documento costruito non garantisce un esito: i guard `IMMEDIATE` che i file non
  esercitavano possono emergere. Un rosso lì è un guard vero da guardare, non un
  difetto della fixture.

## 4. Giri

1. **fatture-ef, ddt**: solo pgTAP, builder esistenti. ✅ verde.
2. **ordini, preventivi**: changeSet dei due builder, manuale, poi i due file. ✅ verde.
3. **commesse, fatture-satelliti, viste-fattura**: builder della commessa e dell'attività, poi i tre file. ✅ verde.

Ogni giro: guardrail del preambolo, prova di Tid, nota qui sotto.

## 5. Consegne

### Giro 1 (2026-10-07) — ✅ verde (Tid)

* `fatture-ef-whitelist-functional`: B con `fn_pgtap_crea_emittente_operatore()`, A e la
  fattura con `fn_pgtap_crea_fattura`, GUC svuotate, poi il resto invariato. Caso **0**
  nuovo (la fixture è quella promessa), `plan` 7 → 8. Via `_flags`/`prereq` e il ramo
  «NOT prereq OR» delle sette asserzioni: niente più soft-skip. Corretto anche l'indice in
  testa, che contava 1..6 su sette casi.
* `ddt-ef-whitelist-write`: B come sopra, A con `fn_pgtap_crea_mondo_cliente`, la bolla
  con `fn_pgtap_crea_ddt(..., 'VENDITA')`, GUC svuotate. Caso **0** nuovo (la bolla ha
  l'emittente di A), `plan` 3 → 4. Sparisce la costruzione ordine → DDT dentro
  `EXCEPTION WHEN OTHERS THEN NULL`, che inghiottiva qualunque rifiuto della fixture, e
  torna `SET CONSTRAINTS ALL IMMEDIATE` in testa.
* Guardrail del preambolo: verde.
* ⚠️ Da guardare alla corsa: è la prima volta che questi due file girano su un documento
  costruito in `DRAFT` invece che su uno pescato. Un rosso al caso 0 è la fixture; un
  rosso ai casi 1-3 è la policy.

### Giro 2 (2026-10-07) — ✅ verde (Tid: apply e corsa)

**Due builder nuovi** in `dbops`, sulla forma di `fn_pgtap_crea_fattura`:

| changeSet | Funzione | Firma |
| --- | --- | --- |
| `20261007-23` | `dbops.fn_pgtap_crea_ordine` | `(p_etichetta text = 'pgTAP', p_stato_codice_interno = 'DRAFT')` |
| `20261007-24` | `dbops.fn_pgtap_crea_preventivo` | idem, sugli stati del preventivo |

* Il mondo viene da `fn_pgtap_crea_mondo_cliente`; l'emittente è scritto esplicito (quello
  che il guard emittente/BA pretende); la valuta è la prima del catalogo, esplicita, come
  nella fattura (la catena di default non regge su un DB da zero). Numero, registro e
  `fatturazione_trigger` li assegnano i trigger del dominio. Il preventivo ha istanza e
  utility del BA e una validità di 30 giorni da oggi.
* Il guard sullo stato gira **prima** di costruire: uno stato sbagliato non lascia un
  mondo a metà.
* Tornano tutte le chiavi, `uid` compreso (serve a chi lega un documento a valle).
* Manuali: `docs/it/dbzero/dbops/manual/fn_pgtap_crea_ordine.md`, `…/fn_pgtap_crea_preventivo.md`.
  Guida pgTAP: due righe nella tabella dei builder.
* Presidi: `db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` e
  `…/test-fn-pgtap-crea-preventivo-v1.sql`, 7 casi ciascuno (firma, testata, emittente
  del BA, numerazione dal dominio, stato scelto, seconda chiamata nella stessa azienda,
  stato inesistente).

**I due file RLS**, come il giro 1: B con `fn_pgtap_crea_emittente_operatore()`, A e il
documento col builder nuovo, GUC svuotate, caso **0** sulla fixture, niente soft-skip.
`ordini-multipolicy` `plan` 5 → 6; `preventivi-ef-whitelist-write` `plan` 4 → 5 (via
anche i quattro rami `ELSE v_n := …` che fingevano l'esito atteso).

**Prova prima dell'apply** (2026-10-07, `zeroerp_ci` costruito da zero, come owner, in
transazione ritirata): SQL **estratto** dai due YAML, poi le chiamate. Ordine dal nulla:
numerato, con registro, `fatturazione_trigger = CONFERMATO` risolto dal dominio, emittente
e cliente coerenti, contesto aperto. Seconda chiamata `CONFERMATO`: stessa azienda, cliente
nuovo. Preventivo: numero `PRV…` dal dominio, validità 30 giorni, istanza coerente; `EMESSO`
rispettato. Stati inesistenti: rifiutati per nome. `COMMENT` entrati; i `DROP` del rollback
funzionano con la firma dichiarata; dopo il `ROLLBACK`, zero residui. Guardrail del
preambolo: verde. ⚠️ Non eseguiti: i due presidi e i due file RLS (pgTAP: li lancia Tid,
dopo l'apply, perché chiamano i builder nuovi).

⏳ **Da fare per Tid**: apply di `20261007-23` e `-24`; poi i quattro file:
`dbops/test-fn-pgtap-crea-ordine-v1`, `dbops/test-fn-pgtap-crea-preventivo-v1`,
`rls/test-rls-ordini-multipolicy`, `rls/test-rls-preventivi-ef-whitelist-write`.

### Giro 3 (2026-10-07) — ✅ verde (Tid: apply e corse)

**Due builder nuovi**, che questa volta **compongono le madri del dominio** invece di
scrivere testate: per la commessa e le sue attività le madri esistono.

| changeSet | Funzione | Cosa fa |
| --- | --- | --- |
| `20261007-25` | `dbops.fn_pgtap_crea_commessa(p_etichetta)` | mondo + `vendite.fn_get_or_create_commessa` (`p_force_new`), competenza nel mese corrente; codice, emittente e stato dalla madre |
| `20261007-26` | `dbops.fn_pgtap_crea_commessa_attivita(p_commessa_id, p_prezzo_snapshot = 10)` | articolo costruito (`fn_pgtap_crea_articolo`) + `vendite.fn_upsert_commessa_attivita`: `APPROVATA`/`NON_EMESSA`, sorgente la commessa, istanza del BA, competenza della commessa |

* ⚠️ Rispetto al §2, **un builder in più** (l'attività). La ragione è sul modello: un'attività
  non è «una riga del test» come quelle della fattura, ma una scrittura con una ventina di
  argomenti e un articolo da costruire, ricopiata a mano in 32 pgTAP (fatto datato
  2026-10-07). Il caso del test resta fuori: emissione e legame con la fattura.
* **Il legame attività fatturabile → riga di fattura lo scrive il backend**
  (`pipeline_repository.py`), non una funzione del DB: il test che ne ha bisogno
  (viste-fattura) lo fa con lo stesso `UPDATE`, dichiarandolo. Se un giorno nasce la
  funzione DB, la fixture la chiama.
* Manuali in `dbops/manual`, due righe nella guida pgTAP, presidi
  `dbops/test-fn-pgtap-crea-commessa-v1.sql` (6 casi) e
  `dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` (6 casi; il 5 prova che
  **l'emissione prende** le attività del builder).

**I tre file RLS:**

* `commesse-ef-whitelist-write`: commessa di A con un'attività; caso **0**; il caso 4 passa
  da «> 0 righe» a «= 1» (la fixture è nota); `plan` 5 → 6.
* `fatture-satelliti-functional`: fattura di A in `DRAFT` con **due** righe scritte dal
  test (con una sola il «tutto-o-niente» non distinguerebbe «tutte» da «almeno una») e il
  riepilogo da `vendite.fn_ricalcola_riepilogo_iva_fattura`; caso **0**; spariscono
  `prereq` e `prereq_write` (la scrivibilità è per costruzione); `plan` 12 → 13.
* `viste-fattura-invarianza`: la catena intera — commessa, attività, emissione, fattura
  dello stesso cliente con la sua riga, legame — poi l'operatore umano con whitelist A.
  ⭐ **Caso 0 nuovo**: senza RLS l'operatore vede l'attività **con** la fattura agganciata.
  Prima il test 2 (il solo che conta) passava come 0 = 0 su un DB vuoto. `plan` 4 → 5.

**Prova prima dell'apply** (2026-10-07, `zeroerp_ci` da zero, owner, transazione
ritirata). Prima un **prototipo** della catena intera con le madri, poi l'SQL **estratto**
dai due YAML e la stessa catena sui builder:

* commessa `BOZZA`, codice dalla madre, emittente del BA, competenza del mese, contesto
  aperto; seconda chiamata: stessa azienda, cliente nuovo;
* due attività (prezzo 10 e 25), `APPROVATA`/`NON_EMESSA`, istanza e competenza giuste;
* l'emissione produce 2 attività fatturabili;
* nel prototipo: fattura e riga, legame, riepilogo IVA (1 riga), la vista di competenza
  vede l'attività **con** fattura, il lineage ha il suo arco;
* commessa inesistente rifiutata per nome; `COMMENT` entrati; `DROP` del rollback con la
  firma dichiarata; zero residui.

Guardrail del preambolo: verde. ⚠️ Non eseguiti: i due presidi e i tre file RLS (pgTAP,
dopo l'apply).

⭐ **Primo risultato della fixture costruita (corsa di Tid, 2026-10-07)**: in
`viste-fattura` il test 4 era rosso, 232 archi del lineage senza RLS e 204 con. **Non è
un difetto della policy né della fixture: era l'asserzione a essere sbagliata.**
`vw_documento_lineage_archi` non ha un filtro di emittente suo (è `security_invoker`, e il
suo perimetro **è** la RLS delle tabelle di base, tutte con la RLS attiva: per
l'applicazione il grafo è già nel perimetro, nessuna fuga). Da owner, col `FORCE` sulla
sola `fatture_righe`, spariscono gli archi verso le fatture delle **altre** aziende: è la
RLS che lavora. Riscontro (dbdev, sola lettura, fatto datato): senza fixture la vista ha
231 archi, di cui 28 passano da `fatture_righe` (G 26, N 1, S 1); la fixture aggiunge l'arco
G di A → 232; con la RLS armata restano 232 − 28 = 204. Prima il file era verde perché
pescava l'emittente che su dbdev possiede tutte quelle fatture: un verde dovuto ai dati.
**Correzione**: il test 4 misura gli archi **dei documenti di A** (la commessa e la
fattura costruite), cioè «armare la RLS non fa sparire i propri archi»; il caso 0 pretende
che quell'arco esista. ✅ Verde al rilancio.

✅ Apply di `20261007-25`/`-26` e corsa dei cinque file: verdi (Tid, 2026-10-07).

## 6. Stato di chiusura (2026-10-07)

**Fatto**

* I sette file `rls/` del §2 costruiscono il loro documento (due aziende: A lo possiede,
  B è l'estranea), prima del `FORCE`, e non hanno più soft-skip: se la fixture non si
  costruisce vanno rossi. Ognuno ha un caso **0** sulla fixture.
* Quattro builder nuovi in `dbops`, ciascuno con manuale, riga nella guida pgTAP e pgTAP di
  presidio: `fn_pgtap_crea_ordine` (`-23`), `fn_pgtap_crea_preventivo` (`-24`),
  `fn_pgtap_crea_commessa` (`-25`), `fn_pgtap_crea_commessa_attivita` (`-26`). Gli ultimi
  due compongono le **madri** del dominio.
* Due asserzioni che passavano **per i dati** sono emerse e sono state corrette: i rami
  `ELSE v_n := …` di preventivi (scrivevano l'esito atteso quando mancava la fixture) e il
  test 4 di viste-fattura (il lineage misurato sul grafo intero, §5 giro 3).

**Resta, fuori da qui** (portato in §3 D7 del documento principale)

* Le copie a mano negli altri pgTAP (fatto datato 2026-10-07): un ordine in **54** file,
  un preventivo in **40**, una commessa in **36**, un'attività in **32**. Ora c'è la sede
  dove portarle; si migrano per famiglia, con il lotto 4 (`vendite`) di D7.
* Il legame attività fatturabile → riga di fattura lo scrive solo il backend: i test che
  ne hanno bisogno lo emulano con lo stesso `UPDATE`. Se nasce una funzione DB per quel
  passo, le fixture la chiamano.

---
{% include-markdown "signature-core.md" %}
