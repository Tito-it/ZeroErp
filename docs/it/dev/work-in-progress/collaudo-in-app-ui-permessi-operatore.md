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
> **Stato**: ✏️ scritto il 2026-09-25, da eseguire.
> **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **super admin** o un operatore con `TUTTO` su Amministrazione
> software, per aprire il pannello. Il pannello si prova **su altri** operatori.
> **Dove**: Amministrazione software → Operatori → kebab di riga → *Permessi*
> (drawer dedicato), oppure il tab *Permessi* del drawer operatore. Sono lo
> stesso componente: basta una strada, l'altra si guarda solo al §5.

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
```

ℹ️ Le tabelle `config.user_override_*` non hanno RLS: la `dbshell` nuda le
legge per intero.

---

## 1. Il pannello mostra tutte le voci

Apri il pannello sull'**operatore vuoto**.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Guarda le tre tabelle | **Tutte** le voci, non tabelle vuote: al 2026-09-25 sono **14** aree, **35** azioni, **12** oggetti. Conta contro i lookup, non contro questo numero, se nel frattempo il catalogo è cresciuto | Se una tabella è vuota o corta, il catalogo non arriva: è il difetto che il cantiere doveva togliere |
| **1.2** | Colonna *Stato* | Ogni riga dice **«Ereditato»**, nessuna «Override» | — |
| **1.3** | Colonna *Ereditato* | Aree: **«default (nessun profilo)»** con livello bloccato; azioni: negate; oggetti: **«dall'area …»** | Se compare un nome di profilo su un operatore senza profilo, l'endpoint legge il binding sbagliato |
| **1.4** | Scrivi nella ricerca delle azioni (es. `lott`) e degli oggetti | La lista si stringe **localmente**, senza chiamate e senza paginatore | — |
| **1.5** | Cerca un paginatore | ⛔ **Nessuno**: è voluto (analisi §7.2). Con la lista paginata il salvataggio cancellerebbe gli override delle altre pagine | Se c'è, fermati: è il difetto più grave del cantiere |

---

## 2. 🔴 Il salvataggio scrive solo gli override veri

Sempre sull'**operatore vuoto**. Prima di iniziare, la query di controllo deve
dare `0 · 0 · 0`.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | Imposta un override su **una** area (es. Vendite → Lettura), premi *Salva* delle aree | Notifica di successo; la riga passa a **«Override»** | — |
| **2.2** | ⛔ Query di controllo | **`1 · 0 · 0`**. Non 14 | Se sono 14, il salvataggio materializza anche le righe «ereditate»: **ogni** operatore con profilo cambierebbe comportamento (analisi §7.5). Fermati |
| **2.3** | Imposta un override su **una** azione, *Salva* delle azioni | Query: **`1 · 1 · 0`**. Le aree non si toccano | Se le aree tornano a 0, un salvataggio ha riscritto la collezione dell'altro |
| **2.4** | Idem su **un** oggetto | Query: **`1 · 1 · 1`** | — |
| **2.5** | Chiudi e riapri il pannello | I tre override ci sono ancora, stato «Override» | — |

---

## 3. «Torna al profilo» e l'avviso del doppione

Apri il pannello sull'**operatore con profilo**.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Colonna *Ereditato* delle aree | Il livello del profilo **con il suo nome** (es. «Profilo reparto Amministrazione»), non «dal reparto» | Nome assente o sbagliato: vedi il brief pgTAP, è proprio la cosa che deve presidiare |
| **3.2** | Imposta su un'area un override **uguale** all'ereditato | Compare l'**avviso**: *«Ripete il valore ereditato: non serve, e da ora questa voce non seguirà più il profilo.»* | Senza avviso, il doppione che congela l'utente torna invisibile |
| **3.3** | Premi il pulsante **reset** della riga (tooltip *«Togli l'override…»*), poi *Salva* | La riga torna **«Ereditato»**; la query di controllo **scende di uno** | Se la riga resta scritta con lo stesso valore, «torna al profilo» sta scrivendo invece di cancellare |
| **3.4** | Apri il pannello sugli operatori **9** e **6** | Gli override aree che ripetono il profilo mostrano **già** l'avviso (casi veri, non costruiti) | — |

⚠️ La 3.4 **non** chiede di togliere quei doppioni: se toglierli è una
decisione di Tid. Il collaudo prova solo che il pannello li fa vedere.

---

## 4. Gli oggetti ereditano dall'area

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Operatore **con profilo**, nessun override sull'area: guarda un oggetto di quell'area | Ereditato = livello dell'area, etichetta **«dall'area …»** | — |
| **4.2** | Metti un override sull'**area** (senza salvare), riguarda lo stesso oggetto | L'etichetta diventa **«dall'override sull'area»** e il livello segue | Se resta il livello del profilo, la riga oggetto legge la sorgente sbagliata |

---

## 5. Sola lettura e super admin

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **5.1** | Apri il pannello in **sola lettura** (utente con `LETTURA` su Amministrazione software, o drawer aperto in consultazione) | ⛔ **Nessun** controllo premibile: né livelli, né reset, né *Salva* | Un pannello di sicurezza modificabile in sola lettura è il caso peggiore |
| **5.2** | Apri il pannello su un **super admin** | Il messaggio *«Gli amministratori hanno accesso totale…»* | — |
| **5.3** | Apri lo stesso operatore dall'**altra** strada (kebab ↔ tab del drawer) | Stesse righe, stessi stati | — |

---

## 6. Esito

| Esito | Allora |
| --- | --- |
| Tutto verde | Si segna qui la data. Quando il pgTAP del [brief DB](brief-db-pgtap-permessi-ereditati.md) è applicato, analisi e piano vanno in `work-done/` |
| Rosso al §1.5 o al §2 | ⛔ Difetto funzionale, non grafico: si apre prima di qualunque altra cosa |
| Rosso altrove | Si annota la riga e il comportamento visto; il fix va nel piano |

🧹 **Pulizia**: togli gli override creati sull'operatore vuoto al §2 (reset +
*Salva* sulle tre tabelle, query a `0 · 0 · 0`).
