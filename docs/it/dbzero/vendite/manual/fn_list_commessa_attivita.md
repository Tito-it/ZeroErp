## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
> • [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)  
>
### 🎯 Scopo Principale
(latest review 26-02-2026)  
Restituisce il dettaglio righe di una commessa (`commesse_attivita`) con filtri opzionali e paginazione, per uso backend in consultazione e pre-validazione dei flussi di emissione.

---

### Regole principali

* Funzione read-only (`STABLE`).
* `p_commessa_id` obbligatorio (`> 0`).
* Errore esplicito se la commessa non esiste.
* Filtri opzionali:
  * `p_stato_emissione`
  * `p_stato_approvazione`
  * `p_competenza_mese` (normalizzato al primo giorno del mese)
  * `p_tipo_movimento` (dal 20-08-2026) — `NORMALE` | `RETTIFICA` | `ONERE`;
    `NULL`/vuoto = tutti i movimenti.
    ⚠️ Un valore **fuori vocabolario solleva** `E_PARAMETRO_INVALIDO`, non filtra
    a vuoto: una lista vuota si legge come *«non c'è niente»*, cioè il difetto si
    traveste da dato. È la stessa classe della «freccia che non ordina».
    ℹ️ Tollera spazi e minuscole (`upper(btrim(...))`), come `p_order_by` e
    `p_order_dir`: il vocabolario resta chiuso, ma una lista non deve dipendere
    da uno spazio di troppo.
    ⚠️ I tre valori sono una **lettura** del vocabolario: a enforcarlo è il
    `CHECK chk_commesse_attivita_tipo_movimento` sulla tabella, che resta l'unica
    difesa vera. Non esiste una tabella-vocabolario per `tipo_movimento`.

> ⭐ **`p_tipo_movimento` è il NONO argomento, in coda dopo `p_order_dir`** — non
> accanto agli altri tre filtri, dove starebbe meglio a leggersi.
>
> È una scelta, non una svista: **una firma più ordinata non vale la
> ricostruzione della catena di chi la chiama.** Appeso in fondo e con un
> `DEFAULT`, ogni chiamata **posizionale** esistente continua a funzionare
> identica — i primi otto argomenti restano dove sono e il nono si omette.
> Il pgTAP lo presidia (`test-fn-list-commessa-attivita-provenienza-v1`, test 28):
> se un domani qualcuno infilasse un parametro in mezzo, quella riga diventerebbe
> rossa.
>
> ℹ️ **La posizione serve ai chiamanti, non alla logica**: nell'elenco dei filtri
> qui sopra `p_tipo_movimento` è il quarto perché è così che si legge il
> comportamento; nella firma è l'ultimo perché è così che non si rompe niente.
>
> ⚠️ È comunque un `DROP + CREATE`: aggiungere un parametro a una funzione
> **non la sostituisce**, ne crea un **overload** — e con otto parametri
> opzionali le due firme renderebbero ambigua ogni chiamata. La `RETURNS TABLE`
> invece non cambia.
* Paginazione:
  * `p_limit` default `1000`, massimo `10000`
  * `p_offset` minimo `0`
* Ordinamento (dal 02-08-2026, esteso il 16 e il 20-08-2026):
  * `p_order_by` — nome della colonna, **whitelist chiusa** di 16 voci:
    `data_attivita`, `competenza_mese`, `segment_key`, `quantita`,
    `prezzo_snapshot`, `stato_approvazione`, `stato_emissione` (più `id`);
    `fatturata_il`, `fattura_numero` (16-08); `tipo_movimento`,
    `articolo_codice`, `articolo_descrizione`, `sorgente_etichetta` (era
    `sorgente_codice` fino al 21-10-2026), `sorgente_documento_numero`,
    `gruppo_key` (20-08).
  * `p_order_dir` — `asc` (default) o `desc`.
  * ⚠️ **La whitelist e il catalogo `ui.lista_colonna` si muovono insieme.** Una
    colonna dichiarata a catalogo con `ordinabile = t` su un nome che questa
    mappa non conosce **non** produce una freccia inerte: fa **rompere la
    lista** al primo click, perché il ramo qui sotto è fail-loud e deve
    restarlo. Chi aggiunge una colonna a catalogo aggiunge il nome qui nello
    stesso giro.
  * `NULL`/vuoto ⇒ **ordine storico `ca.id`**: chi non chiede niente ottiene
    esattamente il risultato di prima.
  * Un nome fuori whitelist **solleva** `E_PARAMETRO_INVALIDO`: non ripiega sul
    default. Un ripiego silenzioso restituirebbe un ordine che nessuno ha
    chiesto, e a video sembrerebbe funzionare.
  * Tiebreak `ca.id` sempre in coda all'`ORDER BY`: senza, due righe con la
    stessa chiave possono scambiarsi di posto fra una pagina e l'altra, e
    l'operatore vede una riga due volte o mai.
* Il tipo dell'origine arriva con una join su `config.sorgenti`, evitando risoluzioni N+1 lato backend.

> ⚠️ **Perché l'ordinamento sta qui e non nel backend.** `ORDER BY` e
> `LIMIT/OFFSET` vivono nella stessa funzione: ordinare a valle ordinerebbe **la
> pagina già estratta**, non la lista. Sarebbe un ordinamento che sembra
> funzionare e mente — peggio di una colonna non ordinabile, perché non ripiega:
> risponde sbagliato. È il motivo per cui `CommessaGestioneDrawer` non era
> convertibile a `<ListaConfigurabile>` prima di questa revisione.
>
> ℹ️ L'`ORDER BY` non è parametrizzabile, quindi la query passa da `format()`.
> È sicuro perché l'espressione **non viene mai dal parametro**: viene da un
> `CASE` chiuso che mappa nome → espressione. I valori restano parametri.
>
> ⚠️ **`NULLS LAST` esplicito in entrambi i versi** (dal 16-08-2026). La nota
> precedente — «nessun `NULLS LAST`: tutte le colonne ordinabili sono `NOT
> NULL`» — è **superata**: da agosto la whitelist contiene colonne nullable
> (`fatturata_il`, `sorgente_documento_numero`), e sul `DESC` il default di
> PostgreSQL mette i `NULL` in **testa**. Chi ordina per una colonna vuole
> vedere per prime le righe che quel valore ce l'hanno; scriverlo per entrambi
> i versi evita che l'ordinamento si comporti in due modi a seconda della
> freccia.

---

### Output

Elenco righe `commesse_attivita` della commessa con i principali campi operativi:

* identificativi (`id`, `commessa_id`, `segment_key`)
* dati di competenza/quantita`/prezzo
* stati (`stato_approvazione`, `stato_emissione`)
* classificazione sorgente (`sorgente_tipo_id`, `sorgente_codice_interno`,
  `sorgente_uid`, `sorgente_apribile`, `sorgente_etichetta`) — vedi sotto
  «Il tipo dell'origine»
* legame con la fattura (`fatturata`, `fatturata_il`, `fattura_id`,
  `fattura_numero`, `fattura_stato`) — dal 16-08-2026
* `meta` e `data_update`

#### Il tipo dell'origine (dal 21-10-2026)

Tre colonne dicono **di che tipo è il documento d'origine** e come trattarlo,
e ognuna risponde a una domanda sola:

| Colonna | A che cosa serve |
| --- | --- |
| `sorgente_codice_interno` | **aprire** il documento: è il nome del tipo (`DDT_VENDITA`, `FATTURA`…), lo stesso con cui il frontend sceglie la pagina |
| `sorgente_apribile` | **se** il documento si apre: alcuni tipi una pagina non ce l'hanno |
| `sorgente_etichetta` | **mostrarlo** all'utente («DDT», «Fattura»…): è la colonna «Tipo origine» della lista, e anche la chiave per ordinarla |

> ⚠️ **Perché non `codice`.** Fino al 21-10-2026 usciva `sorgente_codice`, cioè
> `config.sorgenti.codice`: è il nome che l'operatore può cambiare. Un
> documento che si apre da un valore modificabile smette di aprirsi il giorno
> in cui qualcuno lo rinomina. `codice_interno` è l'unico protetto dal lock.
> Oggi sulle sorgenti seminate i due valori coincidono, ed è il motivo per cui
> il pgTAP costruisce una sorgente rinominata invece di guardare quelle che ci
> sono (`test-fn-list-commessa-attivita-sorgente-codice-interno-v1`).
>
> ℹ️ `sorgente_etichetta` è **l'ultima** colonna della `RETURNS TABLE`: è
> arrivata dopo, ed è stata messa in coda per non spostare le altre.

#### La provenienza della riga (dal 20-08-2026)

Cinque colonne che rispondono a **da dove viene questa riga**, ed è la domanda
con cui nasce la fattura: il documento si separa per **gruppo fatturabile**, una
fattura per documento sorgente.

| Colonna | Cosa dice |
| --- | --- |
| `tipo_movimento` | `NORMALE` / `RETTIFICA` / `ONERE`. Prima una rettifica si distingueva **solo** perché la quantità è negativa |
| `articolo_codice`, `articolo_descrizione` | di cosa parla la riga: prima usciva il solo `articolo_id` uuid |
| `sorgente_documento_numero` | il numero che l'operatore legge (`DDT0010839`), accanto all'id nudo |
| `gruppo_key` | l'unità con cui nasce la fattura, da `vendite.fn_build_gruppo_fatturabile_key` |

> 🔴 **Perché sono cinque e non quattro.** Le righe `RETTIFICA` e `ONERE` sono
> **senza documento sorgente per progetto** — `fn_accredita_riga_reso` le scrive
> con la sorgente a `NULL`, e il `CHECK` sulla tabella impone la coppia
> tutta-vuota o tutta-piena. Misurato il 20-08-2026: **9 righe su 98**, cioè il
> **100%** delle righe di nota di credito. Su quelle, `sorgente_documento_numero`
> è vuoto — proprio dove la colonna serviva.
>
> `gruppo_key` risponde comunque, e risponde la cosa giusta: su una riga senza
> sorgente vale `MAN:<commessa_id>`, cioè **il gruppo «oneri di commessa»**, che
> è davvero il contenitore da cui quella riga verrà fatturata. Le due colonne
> rispondono a due domande diverse — *«da quale documento discende»* e *«in che
> gruppo verrà fatturata»* — che sulle righe normali coincidono e sulle
> sourceless no.
>
> ⭐ **E non è un difetto del documento**: `fn_build_fattura_key` porta la
> **natura**, quindi una rettifica non finisce nella fattura ordinaria in nessun
> caso. Il gruppo è l'unità dell'**emissione mirata**, non del documento.

> ℹ️ `sorgente_documento_id` e `sorgente_documento_numero` arrivano da **una
> sola** chiamata a [`vendite.fn_get_sorgente_documento_ref`](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref),
> che dal 20-08-2026 sostituisce `fn_get_sorgente_documento_id`: due funzioni
> gemelle avrebbero voluto due letture per riga e due copie della stessa regola
> di risoluzione polimorfa.
>
> ⚠️ Entrambe sono `NULL` anche quando il documento **esiste ma non è visibile**
> a chi chiede (RLS): l'azione «apri» va nascosta, e il numero non si mostra.

---

### Esempio d'uso

```sql
-- Con ordinamento esplicito (la lista attività della commessa apre così:
-- `data_attivita desc`, come dichiara il preset di `ui.lista_preset`).
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_stato_approvazione => NULL,
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 200,
  p_offset => 0,
  p_order_by => 'data_attivita',
  p_order_dir => 'desc'
);

-- Senza i due parametri il comportamento è quello storico (`ORDER BY ca.id`):
-- i chiamanti che non ordinano non sono stati toccati dalla revisione 08-2026.
SELECT * FROM vendite.fn_list_commessa_attivita(p_commessa_id => 12345);
```

---

{% include-markdown "signature-core.md" %}
