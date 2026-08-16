# Lista attività di commessa — tre informazioni che si fermavano al database

> **Cos'è.** La sede DB della richiesta che il BE ha mandato il **2026-08-16**:
> la riga della lista attività di commessa deve portare a valle **quando** è
> stata portata in fattura, **quale** fattura, e **quale** documento di origine.
> Tutte e tre nascono da `vendite.fn_list_commessa_attivita`, quindi un
> intervento solo — come chiedeva la richiesta.
>
> **Stato**: ⚠️ **scritto, da applicare** — due changeSet `20260816-03` e `-04`.
> Provato in transazione annullata.

---

## 1. Cosa esce dalla funzione adesso

Sette colonne nuove, la firma **invariata** (nessun overload: verificato che
resti una sola definizione).

| Colonna | Da dove | Nota |
| --- | --- | --- |
| `fatturata_il` | `vendite.fatture_righe.data_insert` | il momento in cui la riga è stata **portata** in fattura |
| `fattura_id`, `fattura_numero`, `fattura_stato` | `fatture_righe → fatture → stati_doc_fiscale` | su cosa navigare, e cosa dire all'operatore prima di aprirlo |
| `sorgente_uid` | `commesse_attivita.sorgente_uid` | c'era già in tabella, **non usciva** |
| `sorgente_area` | `config.sorgenti.area` | quello che il BB del frontend chiama «area» |
| `sorgente_documento_id` | `vendite.fn_get_sorgente_documento_id` | l'id numerico, risolto |

Ordinamento: la whitelist accetta due nomi nuovi, **`fatturata_il`** — che è la
domanda da cui nasce la richiesta, «fatturata ieri o tre mesi fa» — e
`fattura_numero`.

---

## 2. ⭐ «Fatturata il»: il dato vero esiste, e non è `data_update`

La richiesta metteva le mani avanti: *«se esiste il dato vero è quello che
vogliamo, altrimenti prendiamo l'approssimazione e l'etichetta lo dirà»*.

**Esiste**: `vendite.fatture_righe.data_insert`, la nascita della riga di
fattura. È un fatto che nessuna modifica successiva all'attività può spostare.

✅ **E la differenza è già visibile.** Sulle 37 righe di commessa già fatturate,
**10 hanno `ca.data_update` diverso da `fr.data_insert`**. Oggi lo scarto è di
**0,4 secondi** — stesso giro di fatturazione, statement diversi — quindi
nessuno se ne accorgerebbe; ma è la prova che le due colonne non sono la stessa
cosa. Basta un riallineamento di prezzo dopo la fatturazione e `data_update`
diventa quella data, mentre l'etichetta continuerebbe a dire «fatturata il».

---

## 3. 🔴 Il documento di origine: **nessuna** riga ha un id numerico

La richiesta diceva: *«l'area è derivabile da `config.sorgenti.area`, l'id no —
la riga porta solo `sorgente_uid`»*. La misura dice che è peggio, e in un modo
che cambia la soluzione.

```text
vendite.commesse_attivita, 2026-08-16

  88 righe con sorgente   →   88 hanno un UUID in `sorgente_uid`
  di cui: 44 PREVENTIVO (key_selector = uid)   ← atteso
          43 ORDINE_VENDITA + 1 DDT (key_selector = id)   ← NON atteso
```

La normalizzazione a `id::text` che fa `fn_link_commessa_sorgente` vale per la
tabella dei **legami** (`commesse_sorgenti`), non per questa colonna: qui il
documento è identificato dal suo uid, sempre.

⚠️ **Ne discende che la traduzione via tabella di destinazione non è il ramo
raro: è l'unico ramo che il dato percorre.** La prima stesura di
`fn_get_sorgente_documento_id` trattava «id numerico» come caso principale e
sarebbe tornata `NULL` su tutte e 88 le righe — cioè un'azione «apri documento»
che non si accende mai, **senza nessun errore**. L'ha scoperta il dry-run, non
il ragionamento.

### Perché una funzione e non una join

La tabella di destinazione cambia con la sorgente (`config.sorgenti.target_table`,
un `regclass`): in una query set-based servirebbe un `LEFT JOIN` per ogni dominio
possibile — quindici, di cui tre usati — e ognuno diventerebbe una riga da
mantenere quando nasce un dominio nuovo. La funzione legge la destinazione dal
catalogo, come fa già `fn_link_commessa_sorgente`.

⚠️ **E non solleva**, al contrario di quella: lì un legame irrisolvibile è un
errore perché si sta **scrivendo**; qui si sta rispondendo a una **lista**, e una
sorgente non risolta deve solo far sparire l'azione — come per le voci manuali,
che un documento a monte non ce l'hanno. *Fail-closed dove si scrive, silenzioso
ma visibile dove si guarda.*

✅ Verificato dopo la correzione: **88 su 88** risolvono.

---

## 4. ⚠️ Due scelte che non si vedono dal risultato

**1. Il booleano `fatturata` NON deriva dalla join.** Resta l'`EXISTS` su
`vendite.attivita_fatturabili`, che **non ha RLS**, mentre `vendite.fatture` e
`fatture_righe` ce l'hanno. Derivarlo dalla join lo renderebbe **falso** per chi
non vede la fattura: una riga fatturata si presenterebbe come da fatturare.

Così invece chi non vede la fattura legge `fatturata = true` con le colonne del
documento a `NULL`: **sa che è fatturata e sa di non poterci navigare**. Il flag
resta dov'era, il link no.

**2. Il legame con la fattura si prende con un `LATERAL` ordinato + `LIMIT 1`.**
Oggi il rapporto attività → riga di fattura è 1:1 (misurato: nessuna riga con più
di una `attivita_fatturabili`), ma *«oggi è 1:1»* è una fotografia, non un
vincolo. Con una join nuda, il giorno di una fatturazione parziale la lista
**raddoppierebbe le righe** — un difetto che si manifesta come dati sbagliati e
non come errore.

---

## 5. Verificato

In transazione annullata, sulla commessa che ha righe già fatturate:

```text
FIRME: 1                          ← nessun overload, la firma è identica
fatturata=true  il=2026-06-20 00:31:09  fattura=210/1/DEFINITIVA
sorgente=ORDINE_VENDITA  area=ORDINI  doc_id=100
RISOLTI: 88 su 88 righe con sorgente
ORDER BY fatturata_il: ammesso
```

---

## 6. 📮 Per il BE

* la firma **non cambia**: le chiamate esistenti continuano a funzionare, le
  sette colonne sono additive;
* `sorgente_documento_id` è `NULL` quando la sorgente non si risolve **o quando
  il documento non è visibile a chi chiede** (RLS): in entrambi i casi l'azione
  «apri» va nascosta, che è il comportamento già previsto per le voci manuali;
* se al frontend serve anche l'`uid` — per esempio per una rotta che usa la
  chiave nativa — c'è: esce grezzo in `sorgente_uid`.

---

## 7. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-16 | ⭐ **Scritti i due changeSet** (`-03` la risoluzione della sorgente polimorfa, `-04` la lista). **«Fatturata il» ha un dato vero** — `fatture_righe.data_insert` — e non è `data_update`: 10 righe su 37 già divergono. 🔴 **La misura ha smentito l'ipotesi sul documento di origine**: non «metà delle righe non ha un id» ma **nessuna** — 88 su 88 hanno un UUID, ordini e DDT compresi, perché la normalizzazione a `id::text` vale per `commesse_sorgenti` e non per `commesse_attivita`. La prima stesura sarebbe tornata NULL su tutto senza dare errore. ⚠️ Due scelte non visibili dal risultato: `fatturata` resta calcolato sulla tabella **senza RLS** (altrimenti chi non vede la fattura leggerebbe «da fatturare» una riga fatturata) e il legame passa da un `LATERAL` ordinato, perché l'1:1 di oggi è una fotografia |
