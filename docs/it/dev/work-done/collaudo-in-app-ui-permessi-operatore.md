# Collaudo in-app · La UI dei permessi di un operatore

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano: il *perché* di ogni scelta sta
> in [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §7 e
> in [piano-be-fe-ui-permessi-operatore.md](piano-be-fe-ui-permessi-operatore.md).
> Qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** Il codice è fatto dal 2026-09-05 (endpoint
> `permessi-ereditati`, BB `MatriceOverride`, tab convertito), ma il repo non ha
> una suite FE: la verifica del pannello è solo a video. E il difetto più
> pericoloso, cioè un salvataggio che scrive 61 override invece di uno, **a
> video non si vede**: si prova con un `count(*)` sul database.
>
> **Stato**: ✅ **ESEGUITO E VERDE il 2026-10-06** (Tid), su tutte le righe. Scritto il
> 2026-09-25; riscritto il 2026-10-04 sul restyle per area e sul tetto d'area
> ([brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) §7), e il
> 2026-10-06 sulle due modifiche nate durante il collaudo (§7).
> **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **super admin** o un operatore con `TUTTO` su Amministrazione
> software, per aprire il pannello. Il pannello si prova **su altri** operatori.
> **Dove**: Amministrazione software → Operatori → kebab di riga → *Permessi*
> (drawer dedicato), oppure il tab *Permessi* del drawer operatore. Sono lo
> stesso componente: basta una strada, l'altra si guarda solo al §5.
>
> **Com'è fatto il pannello** (dal 2026-10-04): l'**elenco delle aree** a sinistra
> (livello, numero di override dell'area, triangolo se il tetto ferma qualche voce)
> e l'area scelta a destra, con il suo livello, i **suoi** oggetti e le **sue**
> azioni. Un **solo Salva**, nel footer del drawer, che manda le sole sezioni
> modificate. Lo scope emittenti fiscali **non** è qui: sta nella scheda *Dati* del
> drawer operatore (§7).

---

## ⛔ Prima di cominciare

| | Cosa | Perché conta |
| --- | --- | --- |
| **Operatore «vuoto»** | Un operatore **senza override e senza profilo** (se non c'è, crealo e non assegnargli un reparto con profilo) | È il caso che prima mostrava tre tabelle vuote |
| **Operatore con profilo** | Un operatore in un reparto **con profilo** (es. *Profilo reparto Amministrazione*) | Serve a vedere l'ereditato col nome del profilo |
| **Casi veri di doppione** | Gli operatori con `auth_user_id` **9** e **6** hanno override aree che ripetono il profilo (5 dei 6 override aree, al 2026-09-25) | Sono la prova §3 senza doverli costruire |
| **La query di controllo** | Tienila pronta in `dbshell` (sotto) | Il §2 si giudica da lì, non dal video |

```sql
-- Righe di override scritte per l'operatore in prova
SELECT (SELECT count(*) FROM config.user_override_aree    WHERE auth_user_id = :id) AS aree,
       (SELECT count(*) FROM config.user_override_azioni  WHERE auth_user_id = :id) AS azioni,
       (SELECT count(*) FROM config.user_override_oggetti WHERE auth_user_id = :id) AS oggetti;

-- Il catalogo contro cui contare le voci del §1.1
SELECT (SELECT count(*) FROM config.aree_funzionali      WHERE attivo)        AS aree,
       (SELECT count(*) FROM config.azioni_processo      WHERE attivo)        AS azioni,
       (SELECT count(*) FROM config.area_model_overrides WHERE NOT riservato) AS oggetti;
```

ℹ️ Le tabelle `config.user_override_*` non hanno RLS: la `dbshell` nuda le
legge per intero.

---

## 1. Il pannello mostra tutte le voci

Apri il pannello sull'**operatore vuoto**, *Solo con override* spento.

| | Cosa fare | Cosa deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **1.1** | Conta le aree a sinistra; poi clicca le aree una per una e somma oggetti e azioni a destra | **Tutte** le voci del catalogo (seconda query sopra): al 2026-09-25 erano **14** aree, **35** azioni, **12** oggetti. Si conta contro il catalogo, non contro questi numeri | Un'area che manca a sinistra, o un'area senza voci a destra mentre il catalogo ne ha: il catalogo non arriva | ✅ |
| **1.2** | Colonna *Stato*, area per area | Ogni riga dice **«Ereditato»**, nessuna «Override» | — | ✅ |
| **1.3** | Colonna *Ereditato* | Aree: **«default (nessun profilo)»** con livello bloccato; azioni: negate; oggetti: **«dall'area …»** | Se compare un nome di profilo su un operatore senza profilo, l'endpoint legge il binding sbagliato | ✅ |
| **1.4** | Scrivi nella ricerca (es. `lott`) | La vista si stringe **localmente**, senza chiamate e senza paginatore: a sinistra restano le sole aree che contengono la voce | — | ✅ |
| **1.5** | Cerca un paginatore | ⛔ **Nessuno**: è voluto (analisi §7.2). Con la lista paginata il salvataggio cancellerebbe gli override delle altre pagine | Se c'è, fermati: è il difetto più grave del cantiere | ✅ |

---

## 2. 🔴 Il salvataggio scrive solo gli override veri

Sempre sull'**operatore vuoto**. Prima di iniziare, la query di controllo deve
dare `0 · 0 · 0`. Ogni *Salva* è quello del footer.

| | Cosa fare | Cosa deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **2.1** | Imposta un override sul livello di **una** area (es. Vendite → Lettura), *Salva* | Notifica di successo; la riga passa a **«Override»** | — | ✅ |
| **2.2** | ⛔ Query di controllo | **`1 · 0 · 0`**. Non 14 | Se sono 14, il salvataggio materializza anche le righe «ereditate»: **ogni** operatore con profilo cambierebbe comportamento (analisi §7.5). Fermati | ✅ |
| **2.3** | Imposta un override su **una** azione, *Salva* | Query: **`1 · 1 · 0`**. Le aree non si toccano | Se le aree tornano a 0, un salvataggio ha riscritto la collezione dell'altro | ✅ |
| **2.4** | Idem su **un** oggetto | Query: **`1 · 1 · 1`** | — | ✅ |
| **2.5** | Chiudi e riapri il pannello | I tre override ci sono ancora, stato «Override» | — | ✅ |

ℹ️ Nel collaudo del 2026-10-06 gli override di azione e oggetto sono stati scritti
**prima** di quello d'area, sotto un'area *Bloccato*: la query ha dato `0 · 1 · 1`, e il
pannello li ha mostrati limitati dal tetto (§5-bis). La prova sostanziale è la stessa:
nessuna riga «ereditata» scritta.

---

## 3. «Torna al profilo» e l'avviso del doppione

Apri il pannello sull'**operatore con profilo**.

| | Cosa fare | Cosa deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **3.1** | Colonna *Ereditato* del livello d'area | Il livello del profilo **con il suo nome** (es. «Profilo reparto Amministrazione»), non «dal reparto» | Nome assente o sbagliato: vedi il brief pgTAP, è proprio la cosa che deve presidiare | ✅ |
| **3.2** | Imposta su un'area un override **uguale** all'ereditato | Compare l'**avviso**: *«Ripete il valore ereditato: non serve, e da ora questa voce non seguirà più il profilo.»* | Senza avviso, il doppione che congela l'utente torna invisibile | ✅ |
| **3.3** | Premi il pulsante **reset** della riga (tooltip *«Togli l'override…»*), poi *Salva* | La riga torna **«Ereditato»**; la query di controllo **scende di uno** | Se la riga resta scritta con lo stesso valore, «torna al profilo» sta scrivendo invece di cancellare | ✅ |
| **3.4** | Apri il pannello sugli operatori **9** e **6** | Gli override che ripetono il profilo mostrano **già** l'avviso (casi veri, non costruiti) | — | ✅ |

⚠️ La 3.4 **non** chiede di togliere quei doppioni: se toglierli è una
decisione di Tid. Il collaudo prova solo che il pannello li fa vedere.

ℹ️ **Anche sugli oggetti l'avviso è giusto** (verificato il 2026-10-06 su `pochi`,
override `TUTTO` su `anagrafiche.cliente` con Anagrafiche `TUTTO` dal profilo). Un
override d'oggetto uguale all'area oggi non fa niente, e se l'area **scende** il tetto
lo porta giù con lei; ma se l'area **sale**, l'override la ferma al suo livello.
Quindi «non seguirà più il profilo» vale anche qui, in salita.

---

## 4. Gli oggetti ereditano dall'area

| | Cosa fare | Cosa deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **4.1** | Operatore **con profilo**, nessun override sull'area: guarda un oggetto di quell'area | Ereditato = livello dell'area, etichetta **«dall'area …»** | — | ✅ |
| **4.2** | Metti un override sul livello dell'**area** (senza salvare), riguarda lo stesso oggetto | L'etichetta diventa **«dall'override sull'area»** e il livello segue | Se resta il livello del profilo, la riga oggetto legge la sorgente sbagliata | ✅ |

---

## 5. Sola lettura e super admin

| | Cosa fare | Cosa deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **5.1** | Apri il pannello in **sola lettura** (utente con `LETTURA` su Amministrazione software, o drawer aperto in consultazione) | ⛔ **Nessun** controllo premibile: né livelli, né reset, né *Salva* | Un pannello di sicurezza modificabile in sola lettura è il caso peggiore | ✅ |
| **5.2** | Apri il pannello su un **super admin** | Il messaggio *«Gli amministratori hanno accesso totale… il pannello è in sola lettura»*, e il pannello **è** in sola lettura come al 5.1: tendine, reset e *Salva* spenti; elenco, ricerca e filtro attivi (§7) | Un pannello modificabile su un super admin promette un effetto che non c'è: il flag scavalca la catena | ✅ |
| **5.3** | Apri lo stesso operatore dall'**altra** strada (kebab ↔ tab del drawer) | Stesse righe, stessi stati | — | ✅ |

---

## 5-bis. La forma per area e il tetto (2026-10-04)

| | Fai | Deve succedere | Se non succede | Esito |
| --- | --- | --- | --- | --- |
| **5b.1** | Apri il pannello | **Nessuna** scheda interna (lo scope emittenti è nei *Dati*, §7). A sinistra tutte le aree attive (contale contro il catalogo), ognuna col suo livello; a destra la prima | Un'area mancante a sinistra non si può più configurare | ✅ |
| **5b.2** | Clicca un'altra area | A destra il suo livello, i **suoi** oggetti e le **sue** azioni, nient'altro | Se compaiono azioni di un'altra area, il raggruppamento legge il campo sbagliato | ✅ |
| **5b.3** | Accendi *Solo con override* | A sinistra restano le sole aree con almeno un override (il numero accanto: livello, oggetti e azioni insieme); a destra le sole righe con override | — | ✅ |
| **5b.4** | Cerca il nome di un'azione | Resta solo l'area che la contiene, e a destra quell'azione | — | ✅ |
| **5b.5** | Cambia un livello senza salvare | Il nome dell'area a sinistra diventa **arancio**; il Salva del footer si accende | Se il Salva resta spento, la fotografia non vede la modifica | ✅ |
| **5b.6** | Cambia un'azione **e** il livello della stessa area, poi *Salva* una volta | Una sola notifica; query di controllo di §2: aree e azioni salite di uno, oggetti fermi | Se gli oggetti cambiano, il Salva manda anche una sezione non modificata | ✅ |
| **5b.7** | 🔴 **Tetto**: su un'area metti *Bloccato* e su una sua azione *Abilitata*, **senza salvare** | Sotto la tendina dell'azione, in arancio: *«Limitata dall'area… (anteprima: non ancora salvato)»*; a sinistra il triangolo d'avviso sull'area (tooltip *«Voci limitate dall'area: n»*) | Senza etichetta il pannello dice «abilitata» su un'azione che il DB nega | ✅ |
| **5b.8** | *Salva* | L'etichetta resta **senza** «anteprima» (ora viene dal DB); l'override resta scritto (stato «Override») | Se l'etichetta sparisce, anteprima e DB non danno lo stesso esito: confrontare con `tettoArea.spec.js` | ✅ |
| **5b.9** | Riporta l'area a *Tutto*, *Salva* | L'etichetta sparisce: l'override dormiente torna valido da solo | — | ✅ |
| **5b.10** | Lo stesso con un oggetto: area *Lettura*, oggetto *Tutto* | *«Vale "Lettura": limitato dall'area…»* | — | ✅ |
| **5b.11** | Sola lettura (§5.1) | Elenco delle aree, ricerca e filtro **funzionano** (sono navigazione); tendine, reset e Salva no | Se l'elenco non risponde, in sola lettura si vede una sola area | ✅ |
| **5b.12** | Restringi la finestra sotto i 1024px | L'elenco delle aree va **sopra** il dettaglio, niente scroll orizzontale | — | ✅ |

---

## 6. Esito

✅ **Tutto verde il 2026-10-06** (Tid). Verde lo stesso giorno anche
[collaudo-in-app-permessi-ereditati-veste-operatore.md](collaudo-in-app-permessi-ereditati-veste-operatore.md);
il pgTAP del [brief DB](brief-db-pgtap-permessi-ereditati.md) era applicato dal
2026-09-25. Quindi questo collaudo, l'altro, l'analisi, il piano e il
[brief del tetto d'area](brief-db-permessi-tetto-area.md) sono passati in `work-done/`.

| Esito | Allora |
| --- | --- |
| Tutto verde | Si segna qui la data, e analisi e piano vanno in `work-done/` (fatto il 2026-10-06) |
| Rosso al §1.5 o al §2 | ⛔ Difetto funzionale, non grafico: si apre prima di qualunque altra cosa |
| Rosso altrove | Si annota la riga e il comportamento visto; il fix va nel piano |

🧹 **Pulizia**: togli gli override creati sull'operatore vuoto al §2 (reset +
*Salva*, query a `0 · 0 · 0`). Il 2026-10-06 è stato tolto a mano anche l'override
`anagrafiche → LETTURA` scritto su `tid` (super admin) prima del blocco del §7:
dormiente, ma sarebbe diventato vero il giorno in cui `tid` avesse perso il flag.

---

## 7. Le due modifiche nate dal collaudo (2026-10-06, Tid)

| Modifica | Perché | Dove |
| --- | --- | --- |
| **Lo scope emittenti fiscali esce dal pannello e va nella scheda *Dati*** del drawer operatore (sotto *Unità organizzativa*, solo in modifica) | È il **perimetro** dell'operatore (quale emittente vede), come il reparto è la sua collocazione; non è una regola su area, oggetto o azione. E nei *Dati* c'era già, in sola lettura: si vedeva lì e si cambiava altrove | `OperatoreDrawer.vue`: una fotografia sua e il suo endpoint; il Salva manda lo scope solo se cambiato, e se i dati passano e lo scope no i dati restano salvati. Il pannello non ha più schede interne. Dal kebab *Permessi* lo scope non si cambia più |
| **Su un super admin il pannello è in sola lettura** | Il flag scavalca la catena: un override scritto lì non ha effetto. Durante il collaudo un override `LETTURA` su Anagrafiche messo a `tid` non ha cambiato niente, e il pannello modificabile diceva il contrario. Per assegnare permessi si spegne prima il flag (conta quello **salvato**) | `OperatorePermessiTab.vue` (`isReadonly` comprende `isSuperAdmin`) e il messaggio `admin_full_access`. Strada facendo: le tre `MatriceOverride` ora ricevono la sola lettura **esplicita** — prima leggevano solo quella iniettata, e il reset restava premibile se la sola lettura arrivava come prop |

Test: `OperatoreDrawer.spec.js` (scope: solo scope cambiato, scope rifiutato dopo i
dati, scope non modificabile) e `OperatorePermessiTab.spec.js` (8: super admin in sola
lettura ma navigabile).
