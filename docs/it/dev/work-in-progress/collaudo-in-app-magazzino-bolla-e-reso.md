# Collaudo in-app · Magazzino: la merce esce con la bolla e rientra col reso

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il piano: il *perché* sta in
> [piano-be-fe-magazzino-lotto-3.md](piano-be-fe-magazzino-lotto-3.md) (giri A1 … C2) e nei due
> brief DB chiusi
> [brief-db-magazzino-lotto-3-scarico-da-ddt.md](../work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md)
> (D-L3-a … D-L3-k) e
> [brief-db-magazzino-lotto-3-bis-carico-da-reso.md](../work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md)
> (D-3b-a … D-3b-h). Qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se
> non succede**.
>
> **Perché esiste.** I Lotti 3 e 3-bis sono chiusi a codice su tutti i lati: DB
> applicato e verde (28/29-09), BE/FE fatti il 2026-10-13 con test sul DB vero
> (emissione con e senza merce, prelievo da lotto, rientro dal prelievo scelto,
> blocchi). Ma **nessun test monta i drawer**: la sezione Prelievi, la sezione
> Rientri, i motivi dei pulsanti e la tendina del magazzino reggono sui **nomi**
> dei campi. Un nome sbagliato non fa fallire niente: lascia una sezione che non
> compare, o un pulsante spento che sembra una regola. E nessuna bolla ha ancora
> **mosso merce a video**.
>
> **Stato**: ✏️ scritto il 2026-10-14, da eseguire.
> **Ambiente**: sviluppo (`dbdev`). **Utente**: un operatore con Vendite (DDT, resi)
> e Magazzino in scrittura, e le azioni di processo `emetti_ddt`, `conferma_reso`,
> `blocca_merce`. ⚠️ **Non il super admin** per il §8: passa senza azioni, e i casi
> dei permessi verrebbero verdi per costruzione.
> **Dove**: Vendite → *DDT*, *Resi*, *Offerte*; Magazzino → *Magazzini*, *Inventari*,
> *Disponibilità*, *Movimenti*.

---

## ⛔ Prima di cominciare

Il dato del copione va **costruito**. Letto su `dbdev` il 2026-10-14: due magazzini,
`TEST` (azienda 32, con scaffali, due ubicazioni) ed `EMITEST` (azienda 44,
**predefinito**, con scaffali acceso ma **nessuna ubicazione**); cinque articoli
gestiti a magazzino, **nessuno** a lotti o a seriali; **nessun movimento** sul
registro, nessun blocco. Il copione si fa nell'azienda con cui lavori (qui la 44).

| | Cosa | Perché conta |
| --- | --- | --- |
| **Predefinito senza scaffali** | `EMITEST`: spegni «usa ubicazioni» (il registro è vuoto, si può). Se non si lascia spegnere, crea un magazzino nuovo senza scaffali e fallo predefinito | Il §1 è il caso semplice: senza scaffali l'articolo semplice si preleva **da solo**. Oggi `EMITEST` chiederebbe uno scaffale senza averne |
| **Magazzino con scaffali** | Un secondo magazzino della **stessa** azienda, con «usa ubicazioni» acceso e due ubicazioni `UX`, `UY` | Il trasferimento (§2) e gli scaffali (§3.4) |
| **Articolo gestito, semplice** | Uno dei cinque gestiti, senza lotto né seriale | La bolla base |
| **Articolo a lotti** | «Gestito a magazzino» + «Richiede lotto», e **due** lotti (`L1`, `L2`) da «Gestisci lotti» | Il §3.1, il §5.2 |
| **Articolo a seriali** | «Gestito a magazzino» + «Richiede Seriale», e **due** seriali: ⚠️ non c'è una schermata che li crea (gli asset non hanno scrittore dall'app), quindi via SQL, sotto | Il §3.3 |
| **Articolo non gestito** | Uno qualunque senza «Gestito a magazzino» | Il §1.4: la bolla si emette come prima |
| **Kit** | Un kit il cui padre **non** è gestito e i componenti sì | Il §3.5. Se non ce n'è uno pronto, salta il caso e annotalo |
| **Giacenza** | Un **inventario** per magazzino che carica: semplice 10, lotti 5 su `L1` + 5 su `L2`, i due seriali; sul magazzino con scaffali, semplice 10 in `UX` | È il copione del Lotto 2 ([collaudo-in-app-magazzino-inventario-e-rettifica](collaudo-in-app-magazzino-inventario-e-rettifica.md) §1): se il carico non riesce, **fermati lì** |
| **Cliente** | Un cliente dell'azienda, con una bolla di vendita **consegnata** per il §5 (la fai al §1, e la porti a Consegnata) | Il reso nasce da una bolla consegnata |
| **Operatori** | Uno **senza** `emetti_ddt`, uno **senza** `blocca_merce`, uno **senza** `conferma_reso` (anche lo stesso profilo, a turno) | Il §8 |

I due seriali (da `dbdev`, come proprietario; sostituisci il codice dell'articolo):

```sql
INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
SELECT a.id, s.seriale,
       (SELECT id FROM config.stati_assets     WHERE codice_interno = 'ASSET_ST_IN_STOCK'),
       (SELECT id FROM config.assets_ownership WHERE codice_interno = 'ASSET_OWNED'),
       (SELECT emittente_fiscale_id FROM magazzino.magazzini WHERE codice = 'EMITEST')
  FROM catalogo.articoli a
 CROSS JOIN (VALUES ('SN-COLL-001'), ('SN-COLL-002')) AS s(seriale)
 WHERE a.codice = '<codice articolo a seriali>';
```

⚠️ Il §0 si fa **una volta**: i casi successivi consumano la giacenza. Dove un caso
dice «entro la giacenza», guarda prima la Disponibilità.

---

## 1. La bolla semplice esce

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | DDT → «Nuovo», causale di vendita | Alla creazione «**Magazzino di partenza**» si riempie da solo col predefinito (segnaposto *«Il predefinito dell'azienda, se non lo scegli»*). La tendina propone **solo** i magazzini dell'azienda della bolla | Campo vuoto = il default del DB (`trgfn_ddt_default_magazzino`) non arriva al dettaglio. Magazzino di un'altra azienda in tendina = il lookup non filtra su `emittente_fiscale_id` |
| **1.2** | Riga con l'articolo **semplice**, 3 pezzi | Sotto le righe compare la sezione «**Prelievi**»; la voce dice «**Automatico all'emissione**» | Sezione assente = il drawer non legge `muove_merce` dalla situazione dei prelievi |
| **1.3** | «Emetti» | Bolla **Emessa**. Disponibilità: il semplice scende di 3. Movimenti: **uno** scarico (`SCARICO_VEN`) della bolla | Emessa senza movimento = il cambio di stato non passa dal verbo (`fn_cambia_stato_ddt`): fermati, è il cuore di A1 |
| **1.4** | Nuova bolla con un solo articolo **non gestito** → «Emetti» | Si emette come prima; **nessuna** sezione Prelievi, **nessun** movimento | — |
| **1.5** | Nuova bolla: semplice **oltre** la giacenza → guarda «Emetti» | «Emetti» **spento**, tooltip *«La merce da spedire non è disponibile a magazzino in quantità sufficiente.»*; la bolla resta in bozza | Acceso e poi errore generico = il motivo fisico non arriva nella capability |
| **1.6** | Su una bolla in bozza svuota «Magazzino di partenza» → guarda «Emetti» | Spento con *«La bolla non indica il magazzino di partenza: senza, la merce non si può scaricare.»* | — |
| **1.7** | La bolla del §1.3, emessa | «Magazzino di partenza» **spento** | Modificabile = il campo manca da `CAMPI_FORM_TESTATA_*` |
| **1.8** | (Facoltativo) bolla con causale **Conto visione** e l'articolo semplice → «Emetti» | Si emette, **nessun** movimento: la merce presso terzi non muove (D-L3-g, buco dichiarato) | Uno scarico = la mappatura delle causali non è quella del seed |
| **1.9** | Porta la bolla del §1.3 a **Consegnata** | Nessun movimento in più (la vendita scarica all'emissione) | Serve al §5 |

---

## 2. Il trasferimento fra magazzini

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | Nuova bolla, causale «**Trasferimento**» | Compare «**Magazzino di arrivo**», obbligatorio; la sua tendina **non** propone il magazzino di partenza | Campo assente = il form non legge `causale_magazzino` della causale |
| **2.2** | Torna a una causale di vendita | «Magazzino di arrivo» **sparisce e si svuota** | Resta valorizzato nascosto = il salvataggio lo manda e il DB rifiuta |
| **2.3** | Di nuovo «Trasferimento», senza arrivo → «Emetti» | Spento con *«La bolla di trasferimento non indica il magazzino di arrivo.»* | — |
| **2.4** | Partenza il predefinito, arrivo quello **con scaffali**, 2 pezzi del semplice → «Emetti» | Emessa. Movimenti: **solo** l'uscita (`TRASF_OUT`) dalla partenza. L'arrivo **non** sale ancora: la merce è in viaggio | Entrata subito = l'entrata non aspetta il `CONSEGNATO` (D-L3-c) |
| **2.5** | Nella sezione Prelievi della bolla emessa | «**Scaffale di arrivo**» si sceglie anche ora (fino alla consegna): scegli `UY`. Niente aggiunte né cestini sui prelievi | Spento = il guard o la capability chiudono anche l'arrivo. Tendina vuota in sola lettura = il difetto corretto dalla revisione del 13-10 è tornato |
| **2.6** | Porta la bolla a **Consegnata** | Movimenti: l'entrata (`TRASF_IN`) nel magazzino di arrivo, in `UY`. Disponibilità: −2 in partenza, +2 in arrivo | Nessuna entrata = fermati e segnala |
| **2.7** | Bolla consegnata: riapri i Prelievi | Anche lo scaffale di arrivo è **spento** | — |

---

## 3. I prelievi: lotti, seriali, scaffali, kit

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Bolla con l'articolo **a lotti**, 7 pezzi | La voce è «**Da completare**», `0 di 7`; «Aggiungi prelievo» propone come quantità **quella che manca** e chiede il **Lotto**. Prelievo 5 da `L1`, poi 2 da `L2` → «**Completo**» | Nessun campo Lotto = la voce non legge `requires_lotto`. Quantità proposta sbagliata = residuo calcolato male |
| **3.2** | Guarda «Emetti» **prima** di completare (con il solo `L1`) | Spento con *«Una o più righe non hanno prelievi che ne coprano la quantità…»* | — |
| **3.3** | Un secondo prelievo da `L1` sulla stessa riga | Rifiuto che dice di **aumentarne la quantità** (posizione ripetuta) | Errore generico = il vincolo non è tradotto dal service |
| **3.4** | Prelievo che porta la riga **oltre** la sua quantità | Tag «**Oltre la riga**», non «Da completare» | «Da completare» con l'aggiunta ancora aperta = il difetto dei tre stati è tornato |
| **3.5** | Completa a 7 → «Emetti» | Movimenti: **due** scarichi, uno per lotto (5 da `L1`, 2 da `L2`) | Uno scarico senza lotto = la sorgente non è il prelievo (D-L3-d) |
| **3.6** | Bolla con l'articolo **a seriali**, 1 pezzo | Nel prelievo **niente quantità**: si sceglie il **Seriale** fra i due del §0 | Tendina vuota = il lookup degli asset non trova l'azienda del magazzino |
| **3.7** | Bolla dal magazzino **con scaffali**, articolo **semplice** | La voce **non** è più automatica: chiede lo **Scaffale** | «Automatico» = la situazione non legge `usa_ubicazioni` del magazzino |
| **3.8** | Bolla con il **kit** | Una voce **per componente** gestito (tag «componente del kit»), nessuna per il padre | Voce del padre = la regola del kit (D-L3-f) non arriva |
| **3.9** | Bolla senza magazzino di partenza, con una riga gestita | La sezione dice *«Scegli prima il magazzino di partenza: lotti, seriali e scaffali dipendono da lui.»* | — |

---

## 4. L'annullo storna

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Annulla una bolla **emessa** che ha mosso merce (non quella del §1.9) | La giacenza **torna su**. Movimenti: uno storno (`STORNO_POS`) per ogni scarico, che punta al suo originale | Annullata senza storno = l'annullo non passa dal verbo |
| **4.2** | Annulla una bolla emessa **senza** merce | Si annulla, nessun movimento | — |

---

## 5. Il reso

Dalla bolla **consegnata** del §1.9, e da una bolla a lotti consegnata (quella del §3.5,
portata a Consegnata).

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **5.1** | Reso dalla bolla del §1.9, 1 pezzo | «**Magazzino di rientro**» proposto **dalla bolla**, modificabile in bozza; la sezione «**Rientri**» con la voce «Automatico alla conferma» | Campo vuoto = il default del reso (`trgfn_resi_default_magazzino`) non arriva |
| **5.2** | Reso dalla bolla **a lotti**, 3 pezzi | La voce propone il **prelievo d'origine** («Da quale prelievo della bolla», lotto scritto accanto, «usciti N»); con un solo prelievo la scelta è già fatta | Nessuna scelta = la voce non legge i prelievi d'origine |
| **5.3** | La riga era uscita da **due** lotti: rientro di 2 da `L1` e lascia scoperto 1 → guarda «Conferma» | Spenta col motivo dei rientri incompleti, **coi numeri**: *«Riga N del reso: indicati 2 pezzi su 3. Indica quali lotti o seriali rientrano, e dove.»* (N = il numero della riga) | Acceso = il motivo non arriva. Frase coi segnaposti `{0}`, `{1}`, `{2}` = i `valori` non arrivano: la capability non porta `reasons` (`20261014-07` non applicato?), o il FE non lo legge (`testoMotivi`) |
| **5.4** | Completa (1 da `L2`) → «Conferma» | Movimenti: carichi `CARICO_RESO_VEN` sui lotti scelti; Disponibilità: `L1` +2, `L2` +1 | Conferma senza carico = la conferma non passa dal verbo (`fn_conferma_reso`) |
| **5.5** | Reso confermato | Magazzino di rientro **spento**; righe e rientri in sola lettura | — |
| **5.6** | Reso con magazzino di rientro **con scaffali** | Lo scaffale si chiede, e la voce non è più automatica | — |
| **5.7** | Rientro che supera l'uscito del suo lotto (contando gli altri resi della bolla) | «Conferma» spenta col motivo, **coi numeri**: *«Riga N del reso: rientrerebbero X pezzi di un lotto o seriale da cui ne erano usciti Y…»* | Segnaposti al posto dei numeri = come al §5.3 |
| **5.8** | Annulla il reso confermato del §5.4 | La giacenza riscende: storno (`STORNO_NEG`) dei carichi | Nessuno storno = l'annullo non passa dal verbo (`fn_annulla_reso`) |
| **5.9** | (Facoltativo) dalla bolla del §5.1 genera la **ri-consegna** ed emettila | Scarica di nuovo la merce rientrata col reso: la giacenza torna a quella di prima del reso | Scarico che porta sotto zero = il reso non aveva ricaricato (l'errore che il 3-bis chiude) |

---

## 6. I blocchi

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **6.1** | Disponibilità → per magazzino → kebab della riga del semplice | «**Blocca merce**» c'è (con `blocca_merce` sul profilo) | — |
| **6.2** | «Blocca merce»: 2 pezzi, «Per chi» un cliente → «Blocca» | Toast *«Merce bloccata»*; la colonna «Blocchi» sale, «Bloccata» +2, il disponibile −2 | — |
| **6.3** | Di nuovo, senza soggetto né nota | Il messaggio chiede **per chi**, col campo «**Nota**» acceso in rosso | Testo crudo del vincolo = il CHECK `per_chi` non è tradotto |
| **6.4** | Una bolla che vorrebbe scaricare anche i pezzi bloccati | «Emetti» spento col motivo della disponibilità | Emessa = il disponibile non tiene conto dei blocchi |
| **6.5** | Popover dei blocchi («Promesse aperte in uscita») | «**Libera**» c'è **solo** sui blocchi manuali. «Libera» → *«Liberare 2 pezzi bloccati?»* → toast *«Blocco liberato»*; il disponibile torna su | — |

---

## 7. Nello stesso giro: l'offerta

Non è magazzino, ma è il giro C2 dello stesso piano.

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **7.1** | Offerta in **bozza**: cambia il cliente → Salva | Il cliente si cambia; la utility segue il cliente e resta **spenta**; dopo il salvataggio la scheda di fornitura mostra il contatore **nuovo** | Scheda vecchia = il form manda la scheda e la riscrive |
| **7.2** | Offerta **emessa** | Cliente spento | — |
| **7.3** | (Da API) eccezione su un'offerta emessa | Il messaggio delle righe «non è più in bozza», non un errore generico | — |

---

## 8. Chi può che cosa

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **8.1** | Operatore **senza** `emetti_ddt` → «Emetti» su una bolla | *«Non hai i permessi»* (o il pulsante assente) | Emessa = il guard del verbo non morde: fermati e segnala |
| **8.2** | Operatore **senza** `blocca_merce` → Disponibilità | «Blocca merce» **non** c'è; «Libera» nemmeno | — |
| **8.3** | Operatore **senza** `conferma_reso` → «Conferma» su un reso | *«Non hai i permessi»* | — |
| **8.4** | Operatore di **un'altra azienda** | Non vede bolle, resi e magazzini di questa; la tendina dei magazzini non li propone | Se li vede, la RLS non è quella attesa |

---

## 9. 🔴 I punti già noti, da confermare a video

| | Cosa | Dove sta scritto |
| --- | --- | --- |
| **Motivi del reso** | Chiuso lato DB (`20261014-07` applicato e pgTAP verde): la «Conferma» porta `reasons` coi `valori`, come la «Emetti» della bolla. Si conferma a video al §5.3 e al §5.7. | [brief-db-reso-motivi-conferma-con-valori](../work-done/brief-db-reso-motivi-conferma-con-valori.md) (archiviato, il collaudo è passato qui) |
| **Bolle senza merce** | Il permesso all'emissione di una bolla che **non** muove merce lo controlla il backend, non il verbo (D-L3-e affinata, limite dichiarato) | brief del Lotto 3, §9 (28-09) |
| **Merce presso terzi** | Conto visione, riparazione, conto lavoro non muovono (§1.8): decisione a sé | D-L3-g |
| **Merce in viaggio** | Nessuna vista la mostra fra il §2.4 e il §2.6: nasce col suo lettore (P-13.2) | [piano §5](piano-be-fe-magazzino-lotto-3.md) |
| **Seriali** | Nessuna schermata li crea: il §0 li inserisce in SQL | brief tutte-le-scritture-dal-verbo §1, D-L2-l |

---

## 10. Registro

| Data | Cosa |
| --- | --- |
| **2026-10-14** | ✏️ Stesura, dall'elenco breve del piano BE/FE (§4, blocchi A, B, C) più i casi del modello che l'elenco non aveva: l'entrata del trasferimento al consegnato (§2.4-2.6), gli storni (§4, §5.8), la ri-consegna (§5.9), le causali che non muovono (§1.8). Dati di partenza letti su `dbdev`. Tutto a codice, **niente visto a video** |
| **2026-10-14** | Assorbito il collaudo del brief-db-reso-motivi-conferma-con-valori (archiviato): §5.3 e §5.7 ora attendono i numeri nel tooltip, §9 aggiornato |
