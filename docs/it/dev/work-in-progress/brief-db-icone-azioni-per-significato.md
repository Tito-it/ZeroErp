# Brief DB — Le azioni disponibili portano un significato, non un glifo

> **Chi scrive:** sessione backend/frontend (`dev/backend-tid`), 2026-09-27.
> **A chi:** Tid (decisione, §3), poi team DB (§4) e frontend (§5).
> **Origine:** [censimento-icone-per-significato.md](censimento-icone-per-significato.md),
> approvato da Tid il 2026-09-27. Nel frontend ogni icona è ora una costante
> con nome di significato. Il presidio `frontend/src/core/icone.spec.js` fa
> fallire la CI se compare un `'pi pi-...'` scritto a mano.
>
> **In una riga:** le azioni disponibili dei documenti arrivano dal DB con il
> **glifo** già scelto (`'pi pi-...'`). È l'unico punto dell'app in cui il segno
> non passa dalle costanti, e il frontend non può tenerlo coerente.

---

## 1. Il punto di partenza — letto il 2026-09-27

Fatti datati, letti dalla doc `docs/it/dbzero/` e dal codice frontend.

* **Le funzioni `script.fn_available_actions_*`** restituiscono per ogni azione
  un campo `icon`: lotto, ordine, offerta, preventivo, contratto, DDT, reso,
  commessa e documento interno. Il valore arriva:
  * per la maggior parte da `meta->>'icon'` delle matrici di transizione
    (es. `config.stati_doc_fiscale_transizioni.meta`, vedi
    `fn_available_actions_lotto.md:79`);
  * in alcuni casi da letterali scritti nella funzione:
    * `'pi pi-print'`, la ristampa del lotto;
    * `'pi pi-clone'`, `crea_revisione` in offerta e preventivo;
    * i `VALUES` di `fn_available_actions_documento_interno`, per esempio
      `'pi pi-undo'`.
* **Il backend** le passa senza toccarle.
* **Il frontend** le rende così come arrivano: `useDrawerActions.js`,
  `icon: action.icon`.
* ⚠️ **`frontend/src/vendite/composables/useLottoAzioni.js`** (`LOTTO_AZIONE_ICONA`)
  è una **copia a mano** dei valori del DB, e serve al kebab della lista lotti.
  È l'unica eccezione dichiarata nel presidio frontend.

## 2. Perché è un difetto

1. **Lo stesso verbo ha due segni.** Il verbo «numera» del lotto:
   * nella lista lotti porta `MANAGE_ICONS.NUMERA` (`pi-hashtag`, decisione T4
     di Tid);
   * nella barra del drawer e nel kebab porta `pi-verified`, che arriva dal DB.

   Prima del censimento era peggio: nella lista c'era un lucchetto.

   Stesso difetto per `riporta_a_draft`: il DB manda `pi-undo`, cioè
   `MANAGE_ICONS.UNDO` (storna un fatto registrato), mentre il gesto ha già
   la sua costante `MANAGE_ICONS.RIPORTA_A_BOZZA` (`pi-backward`), che il
   frontend usa per l'evento di giornale. Il verbo nel kebab e nel drawer
   porta proprio il segno che la costante esclude. La mappa verbo→icona
   deve coprire anche questo caso.
2. **I glifi del DB non seguono le regole del censimento.** `crea_revisione`
   porta `pi-clone`, che nel frontend è `STATUS_ICONS.MULTIPLI` («più di uno»),
   non «nuova revisione».
3. **Una correzione di segno oggi richiede un changeSet** e non la vede nessun
   test: né il lint né il presidio frontend guardano i dati.

## 3. Decisione per Tid

**D-1 — Che cosa manda il DB al posto del glifo.**

| Opzione | Come funziona | Pro | Contro |
| --- | --- | --- | --- |
| **A (proposta)** | Il DB **non manda l'icona**. Il frontend la ricava dal `codice` dell'azione con una mappa `verbo → MANAGE_ICONS.*` in `core/`. Un verbo senza voce prende un ripiego visibile | Il verbo **è** già il significato: nessun secondo nome da tenere allineato. La presentazione esce dal DB. Il presidio frontend copre tutto | Un verbo nuovo a DB vuole la sua riga nella mappa frontend (altrimenti mostra il ripiego) |
| B | Il DB manda una **chiave di significato** (`'icona': 'NUMERA'`), che il frontend risolve in `MANAGE_ICONS` | Configurabile da DB senza deploy frontend | Due vocabolari da tenere allineati (chiavi DB e costanti frontend). Una chiave sbagliata dà un'icona vuota, senza errore |

Con A, un test frontend può fissare che ogni verbo noto abbia la sua voce.

## 4. Richiesta al team DB (dopo D-1)

**Con A:**

1. Togliere `icon` dall'output delle `fn_available_actions_*` e i letterali
   `'pi pi-...'` dalle funzioni.
2. Togliere `icon` da `meta` delle matrici di transizione. Prima va fatto
   l'**inventario completo** dei valori seedati (la doc `dbzero` non li riporta
   tutti), da consegnare al frontend: è la base della mappa.
3. Aggiornare la doc delle funzioni e i pgTAP che verificano `icon`.

**Con B:** stessi punti, ma `icon` diventa `icona_chiave` con valori presi da
`MANAGE_ICONS`. L'elenco delle chiavi valide va dato dal frontend.

## 5. Ricaduta sul frontend (dopo il DB)

* **Mappa `verbo → icona`** in `core/`, per opzione A, e `useDrawerActions` che
  la legge.
* **`LOTTO_AZIONE_ICONA`** in `useLottoAzioni.js` si ritira: legge la stessa
  mappa.
* **Presidio:** si toglie l'eccezione in `icone.spec.js`.

⛔ Fino ad allora il frontend **non** cambia `LOTTO_AZIONE_ICONA` da solo:
separerebbe il kebab della lista dalla barra del drawer.
