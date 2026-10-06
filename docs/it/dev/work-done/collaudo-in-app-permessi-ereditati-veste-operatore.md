# Collaudo in-app · L'ereditato dei permessi e la veste operatore

> **Cos'è.** Il copione della validazione a video, da tenere aperto accanto
> all'applicazione e da spuntare. Il *perché* di ogni scelta sta nel
> [brief](brief-db-pgtap-permessi-ereditati.md): §3 e §3-bis per i
> difetti, §4 per le decisioni D-1 → D-3, §5.1 e §7 per le due consegne.
> Qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Cosa è cambiato, in tre righe:**
>
> - **D-1**: i permessi da operatore contano **solo** i profili della veste
>   `OPERATORE`. Un operatore che ha anche una veste cliente non si porta più
>   il profilo `PORTALE` di quella veste;
> - **D-2**: l'ereditato è calcolato **a DB**, dalla stessa funzione che usano i
>   resolver. La colonna «ereditato» del pannello e il permesso applicato non
>   possono più divergere;
> - **D-3**: a parità di veste vince il **reparto** sul profilo di veste
>   (priorità AD_HOC 1, REPARTO 2, PORTALE 3).
>
> **Stato**: ✅ **ESEGUITO E VERDE il 2026-10-06** (Tid). Scritto il 2026-09-25.
> **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **super admin** per aprire il pannello e interrogare i
> permessi degli altri, più le credenziali dell'operatore **`pochi`** per il §2.
> **Dove**: Amministrazione software → Operatori → kebab di riga → *Permessi*.

---

## ⛔ Prima di cominciare

| | Cosa | Perché conta |
| --- | --- | --- |
| **Backend ricaricato** | `kill -HUP` sul master gunicorn | Il backend di sviluppo non ha l'autoreload: senza, il pannello legge ancora la query vecchia e il collaudo prova il codice di prima |
| **L'operatore multi-veste** | **`pochi`** (`auth_user_id` **6**): vesti `OPERATORE` e `SHOP_CUSTOMER`, reparto Marketing | È il caso del brief §3: il profilo del cliente shop entrava nei suoi permessi da operatore |
| **Un operatore «normale»** | Un operatore con **una sola** veste e un reparto con profilo (es. `auth_user_id` **9**) | Il controllo di non-regressione: per lui non deve cambiare niente |
| **Il super admin multi-veste** | **`tid`** (`auth_user_id` **1**): `OPERATORE` + `CLIENTE_PORTALE`, profilo AD_HOC super admin | Il bypass non deve risentire della veste in più |

📌 *Fatto datato (2026-09-25, `dbdev`), non motivo:* per `pochi`, il profilo
*«Profilo standard cliente shop»* (`PORTALE`, `LETTURA`) e il *«Profilo reparto
Marketing»* (`REPARTO`, `TUTTO`) coprono **entrambi** `vendite` e `pagamenti`.
Su `vendite` c'è un override `TUTTO`; su `pagamenti` nessun override. Prima del
cambio `pagamenti` risultava `LETTURA`: vinceva il profilo da cliente shop.

La query di controllo, da tenere pronta in `dbshell`:

```sql
-- L'ereditato che il pannello deve mostrare per l'operatore in prova
SELECT af.codice, e.livello, e.profilo_tipo, e.profilo_descrizione
  FROM script.fn_get_permessi_ereditati_aree(:id) e
  JOIN config.aree_funzionali af ON af.id = e.area_id
 ORDER BY af.codice;
```

ℹ️ Le tabelle del giro (profili, binding, identità, risorse umane) non hanno
RLS: la `dbshell` nuda le legge per intero.

---

## 1. Il pannello di `pochi` non mostra più il profilo da cliente

Apri il pannello permessi su **`pochi`**.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Colonna *Ereditato* delle aree, riga **Pagamenti** | **Tutto**, fonte **«Profilo reparto Marketing»** | Se dice *Lettura* / *«Profilo standard cliente shop»*, D-1 non è arrivata al pannello: controlla il `kill -HUP`, poi la query di controllo. Se la query dice `TUTTO` e il video no, il difetto è nel backend |
| **1.2** | Scorri **tutta** la colonna *Ereditato* (aree e azioni) | ⛔ **Nessuna** riga ha come fonte *«Profilo standard cliente shop»* | Una sola riga basta: il profilo di un'altra veste sta ancora entrando nei permessi da operatore |
| **1.3** | Riga **Vendite** | Stato **«Override»** (`TUTTO`), ereditato **Tutto** dal reparto, e l'**avviso** del doppione («ripete il valore ereditato») | Senza avviso: prima l'ereditato poteva dire *Lettura* dal profilo shop, e il doppione non si vedeva. Se l'avviso manca ancora, l'ereditato non è quello nuovo |
| **1.4** | Confronta la colonna con la query di controllo (`:id = 6`) | Stesse aree, stessi livelli, stessi nomi di profilo. Le aree che la query non restituisce sono a *«default (nessun profilo)»* | Una differenza qui è un difetto del backend: la colonna legge proprio quella funzione |

⚠️ Il collaudo **non** chiede di togliere l'override su Vendite: se toglierlo
è una decisione di Tid.

---

## 2. Il permesso applicato è quello che il pannello mostra

Il pannello dice cosa `pochi` **eredita**; qui si prova che è anche ciò che
**ottiene**.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | Da super admin: `GET /api/v1/core/users/6/permessi-effettivi/` | Area `pagamenti`: `livello = "TUTTO"`, `has_profilo_reparto = true` | `LETTURA` qui con `TUTTO` nel pannello: i resolver e il pannello divergono, cioè il difetto che il pgTAP deve impedire. Fermati |
| **2.2** | Entra come **`pochi`**, veste **operatore** | Il menu mostra Pagamenti con le voci di scrittura | — |
| **2.3** | Apri una pagina di Pagamenti e avvia una **modifica** o una **creazione** (senza salvare, se non serve) | L'azione è **permessa**: nessun *«Permesso negato»* | Con `LETTURA` l'azione sarebbe negata: il profilo shop vince ancora nella risoluzione vera |

---

## 3. La veste cliente di `pochi` resta com'era

D-1 tocca **solo** i permessi da operatore: la veste shop ha i suoi.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Entra come **`pochi`** dallo **shop** | Lo shop funziona come prima: ordini e pagamenti propri **in lettura** | Se lo shop perde l'accesso, il filtro di veste è finito anche sulla catena del cliente: è fuori dal perimetro del cambio, e va segnalato al team DB |

---

## 4. Non-regressione: operatore normale e super admin

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Pannello sull'operatore **9** | Colonna *Ereditato* uguale a prima: livelli e nomi del profilo del suo reparto. Gli override che ripetono il profilo mostrano l'avviso, come nel collaudo del pannello §3.4 | Per un operatore a una sola veste senza profilo di veste non deve cambiare niente: una differenza è una regressione |
| **4.2** | Query di controllo con `:id = 9` contro il pannello | Coincidono | — |
| **4.3** | Pannello su **`tid`** | Il messaggio *«Gli amministratori hanno accesso totale…»* | La veste `CLIENTE_PORTALE` in più non deve togliere il bypass |
| **4.4** | Da **`tid`**, veste operatore, apri un'area qualunque | Accesso totale, come prima | — |

---

## 5. Cosa questo collaudo non può mostrare, e dove è provato

Due casi del modello non hanno oggi un soggetto su `dbdev`. Non si costruiscono
qui a mano: sono **provati costruendoli** nel pgTAP
`db/pgtap/script/test-fn-get-permessi-ereditati-v1.sql`.

| Caso | Perché non si vede a video | Dove è provato |
| --- | --- | --- |
| **D-3**: un profilo `PORTALE` legato alla veste `OPERATORE` (profilo base per tutti gli operatori) contro il `REPARTO` sulla stessa area | 📌 *Fatto datato (2026-09-25):* nessun binding di veste `OPERATORE` in `dbdev`. Costruirlo cambierebbe i permessi di **tutti** gli operatori per la durata della prova | Test 22 → 25 (il 25 asserisce le priorità: lo spareggio casuale non si vede da un esito) |
| **Messaggio di diniego** quando l'area è coperta **solo** dal profilo di un'altra veste: ora *«Il reparto non ha ancora un profilo permessi configurato.»* invece di *«Permesso negato»* | 📌 *Fatto datato:* le aree del profilo shop di `pochi` sono coperte anche dal suo reparto | Test 18 → 21 (resolver) e il test Django `test_has_profilo_true` (la query del messaggio legge la funzione dell'ereditato) |

---

## 6. Esito

| Esito | Allora |
| --- | --- |
| Tutto verde | ✅ **2026-10-06**: fatto. Si segna qui la data, e questo documento va in `work-done/` accanto al brief. Se è verde anche il [collaudo del pannello](collaudo-in-app-ui-permessi-operatore.md), analisi e piano della UI permessi vanno in `work-done/` |
| Rosso al §1 o al §2 | ⛔ Difetto funzionale su una schermata di sicurezza: si apre prima di qualunque altra cosa. Prima si guarda la query di controllo, per capire se il difetto sta a DB o nel backend |
| Rosso al §3 | Fuori dal perimetro del cambio, ma causato da lui: brief al team DB |
| Rosso al §4 | Regressione: si annota la riga e il comportamento visto |
