## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_guard_fatturazione_immediata_immutabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — il legame documento → commessa
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo del documento
>
> Approfondimento funzioni:
>
> * [vendite.fn_commessa_viva_di_sorgente](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente) — in quale commessa aperta sta il documento
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — la porta che scrive il legame
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — il flag è parte della sua chiave di dedup
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza
> * [Fatturazione](/guide/fatturazione) — le due corsie

---

### 🎯 Scopo Principale

Impedisce la modifica di `fatturazione_immediata` su un documento che sta in una commessa **aperta**. È montata su preventivi, ordini, contratti e bolle di vendita.

Il flag decide su quale **corsia** finisce il lavoro:

| Valore | Corsia | `tipo_lotto` | Arriva a |
| --- | --- | --- | --- |
| `true` | immediata | `GIORNALIERO` | `DEFINITIVA` (numera da sola) |
| `false` | differita | `MASSIVO` | `EMESSA` (la numerazione è un atto separato) |

Viene letto **una sola volta**, dal push verso la commessa. Da quel momento in poi, finché la
commessa è aperta, è **inerte**. Conta solo la commessa **aperta**: il legame verso una commessa
chiusa o annullata resta come storia, e il documento torna da mandare — il suo flag torna una
scelta da fare.

---

### Perché serve un guard su un valore già inerte

Senza il guard il campo resterebbe **modificabile a video senza produrre alcun effetto**, che è il
peggiore dei casi: *sembra* funzionare. Tre ragioni rendono il flag inerte dopo il push:

1. **È nella chiave di dedup della commessa.** `fn_get_or_create_commessa` identifica la commessa
   per cliente, utility, tipo, politica di fatturazione, `fatturazione_immediata`, emittente e
   periodo di competenza. Cambiarlo sul documento **non sposta** le righe già spinte: quelle stanno
   in una commessa nata con il vecchio valore.
2. **Un documento sta in una sola commessa aperta.** Finché la sua commessa è aperta, rispingerlo
   verso una commessa di corsia diversa darebbe `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` (la porta,
   `vendite.fn_link_commessa_sorgente`).
3. **Anche potendo, si sposterebbe l'intera commessa**, che raccoglie più documenti (`ROOT` più N
   `COLLEGATO`): trascinerebbe con sé documenti che nessuno ha chiesto di spostare.

> **Il caso «cambio idea dopo» non è scoperto**: lo gestisce l'**emissione mirata per gruppo
> fatturabile**, che fattura esattamente le righe di quel documento senza toccare il resto della
> commessa. Sono due strumenti distinti: il flag è *instradamento automatico* deciso a monte,
> l'emissione mirata è un *atto puntuale dell'operatore*.

---

### Regole

* **Solo cambi reali.** Il trigger è armato con un `WHEN` che lo fa scattare solo quando il valore
  cambia davvero (`IS DISTINCT FROM`, perché sui preventivi la colonna può essere vuota).
  Riscrivere lo **stesso** valore passa: serve alla ri-accettazione di un preventivo, che riscrive
  il flag invariato.
* **Chirurgico sulla colonna.** `BEFORE UPDATE OF fatturazione_immediata`: non interferisce con le
  altre modifiche del documento.
* **Generico per tipo.** Il tipo arriva dal primo argomento del trigger come **`codice_interno`**
  (immutabile), mai come id.
* **Fail-loud sulla configurazione.** Argomento mancante o tipo inesistente → errore. Un guard che
  non sa che cosa protegge non deve poter passare inosservato.
* **Nessun filtro su `attivo`** nella lettura del tipo: il legame documento → commessa esiste anche
  se il tipo venisse disattivato, e va protetto lo stesso.

---

### La domanda «in quale commessa aperta?» ha una sede sola

Il guard non cerca il legame da sé: chiede a
[`vendite.fn_commessa_viva_di_sorgente`](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente) la
commessa aperta del documento, passandogli il tipo e **tutte e due** le chiavi del documento, il suo
`id` e il suo `uid`. Il legame in `commesse_sorgenti` ne tiene una sola, quella che il
`key_selector` del tipo dichiara (`uid` per preventivi e offerte, `id` per ordini, contratti e
bolle), e la regola d'incontro la trova senza che il guard debba leggere il `key_selector`.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_FATT_IMMEDIATA_NON_MODIFICABILE` | il documento sta in una commessa aperta |
| `E_PARAMETRO_INVALIDO` | il primo argomento del trigger manca o è vuoto (trigger mal configurato) |
| `E_CODICE` | il `codice_interno` non è in `config.sorgenti` |

Il contesto dell'errore include tabella, id e uid del documento, tipo, commessa, valore attuale e
valore richiesto: serve a capire *dove* è finito il documento senza doverlo cercare a mano.

---

### Perimetro: perché non sui consumi

`vendite.attivita_consumi` **non ha il flag** e quindi non ha il guard. Un consumo è una
**misura**, non un accordo commerciale: la corsia la decide il **contratto** che lo governa. Un flag
sulla singola lettura creerebbe lo stesso interruttore in due posti, con la possibilità che dicano
cose opposte e nessuna regola su chi vince.

---

### Note di migrazione

* 2026-07-27 — nasce con l'emissione della fattura per documento (brief-db-emissione-fattura-per-documento-sorgente, parte B, D-7); i consumi restano fuori (D-6).
* 2026-10-12 — conta solo la commessa aperta: prima bastava una qualunque riga in
  `commesse_sorgenti`, perché il legame era «per sempre» (brief-db-annullo-a-valle-riapre-a-monte, D-14).
* 2026-11-07 — il legame tiene la chiave nelle colonne tipizzate del modello, e il guard passa id e
  uid del documento; prima componeva da sé la chiave canonica in testo secondo il `key_selector`, e
  sollevava `E_SORG_CONF` su un selettore fuori dominio (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
