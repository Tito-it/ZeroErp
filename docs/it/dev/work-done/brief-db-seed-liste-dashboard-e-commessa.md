# Brief BE → DB — seed liste configurabili: 3 dashboard + drawer commessa (8° lotto)

> ✅ **CHIUSO il 2026-08-03**, stesso giorno della richiesta. Il team DB ha
> seedato le **6 liste (38-43)** con 51 colonne, e il BE/FE ha convertito i
> `.vue` nella stessa giornata: **il Gruppo A è a 30/34**, e i 4 file rimasti
> sono i cassetti fermi per decisione (§8 punto 4 del piano), non debito.
>
> **La promessa della passata BE ha retto**: tutte e sei le liste sono nate
> verdi al PRIMO passaggio del presidio, senza un giro di ritorno. Registro a
> **43/43**.
>
> Tre scelte del DB che divergono dal brief e sono **migliori** di quanto
> proposto:
>
> - `codice` come identificatore su aperto e backlog, non la prima colonna: la
>   convenzione dice «la prima», ma la regola vera è «quella che l'operatore
>   non deve poter nascondere», e su un elenco di documenti è il codice;
> - lista 38 **senza** ordinamento di apertura: il brief offriva `id asc`, ma
>   `id` non è colonna seedata e il preset avrebbe puntato a qualcosa che nel
>   catalogo non c'è. Vuoto = ordine storico `ca.id`, che è già il default
>   della funzione;
> - il presidio del DB sa ora leggere una whitelist che vive in una **funzione
>   DB** (`fn_list_commessa_attivita`), la prima del progetto.
>
> ⚠️ **Un difetto trovato registrando le liste, e corretto**: il presidio
> Python ne vedeva solo 2 su 6. La regex cercava `codice="..."` con `[^>]*`
> fra tag e attributo, ma un `>` vive dentro `v-if="documentiCount > 0 || …"`
> e la ricerca si fermava lì — il presidio **taceva proprio sulle liste appena
> convertite**, che è il caso per cui esiste.
>
> ---
>
> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-08-03.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** la richiesta di seed (`ui.lista_definizione` + `ui.lista_colonna` +
> preset) per le **6 liste** che chiudono il Gruppo A del binario liste
> configurabili: le 5 liste delle 3 dashboard vendite (decisione 2 del
> 2026-08-02: «sì, come le altre — ma per ultime»; ora sono le ultime) e la
> lista del `CommessaGestioneDrawer` (il cablaggio `order_by`→fn che la
> bloccava è fatto, in arrivo col prossimo push su `dev/backend-tid`).
> **La passata BE è già fatta**: ogni colonna proposta `ordinabile=t` qui sotto
> ha la voce di whitelist **già nel codice** — nessuna freccia nascerà morta.
> **Correlati:** piano-migrazione-primevue-5.md §8-bis/§9.

---

## 0. Cosa NON serve al DB

Nessuna migration su funzioni o viste: l'ordinamento di tutte e 6 le liste vive
nel BE Python (whitelist nei repository), tranne la commessa dove è **dentro**
`vendite.fn_list_commessa_attivita` (già a 8 parametri, `20260802-26` — nessun
altro intervento). Servono **solo i seed**.

Le colonne **checkbox di selezione** (emissione mirata nei gruppi, approvazione
righe nel drawer commessa) **non vanno a catalogo**: sono chrome del building
block FE (estensione `<ListaConfigurabile>` in corso, regola del 2 — 2ª
occorrenza), come la colonna di espansione.

---

## 1. `CommessaGestioneDrawer` — lista attività commessa

- **Codice proposto:** `vendite.commesse_attivita`
- **`.vue`:** `vendite/components/CommessaGestioneDrawer.vue` (drawer, master-detail)
- **Whitelist (nella fn, `20260802-26`):** id, data_attivita, competenza_mese,
  segment_key, quantita, prezzo_snapshot, stato_approvazione, stato_emissione.
  `id` è in whitelist ma non a video: va bene così (il presidio interseca col
  catalogo).
- **Preset:** nessun ordinamento esplicito = ordine storico `ca.id` (è il
  default della fn: `p_order_by` NULL). Se il preset deve dichiarare qualcosa,
  `id asc`. Pagina: 25.

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| data_attivita | data_attivita | date | date_short | **t** | |
| competenza_mese | competenza_mese | date | date_short | **t** | |
| segment_key | segment_key | string | | **t** | |
| quantita | quantita | numeric | | **t** | |
| prezzo_snapshot | prezzo_snapshot | numeric | | **t** | cella FE custom (lucchetto/riallineo) |
| stato_approvazione | stato_approvazione | string | | **t** | Tag FE |
| stato_emissione | stato_emissione | string | | **t** | Tag FE |
| azioni | | azione | | f | |

---

## 2. Situazione aperta — documenti

- **Codice proposto:** `vendite.dash_aperto_documenti`
- **`.vue`:** `vendite/views/SituazioneApertaView.vue`
- **Whitelist:** `VenditeRepository.DASH_APERTO_SORT_COLUMNS` — estesa il
  2026-08-03 con `stato_codice` (nucleo *stato*, era scoperto) + `area`/`fase`
  (simmetria col gemello backlog).
- **Preset:** `anzianita_giorni desc` (replica il default FE corrente e
  l'ordine storico BE «in essere da»). Pagina: 25.

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| anzianita_giorni | anzianita_giorni | numeric | | **t** | «Aperto da N gg» |
| area | area | string | | **t** | Tag FE |
| codice | codice | string | | **t** | |
| cliente_display | cliente_display | string | | **t** | |
| fase | fase | string | | **t** | Tag FE |
| stato_codice | stato_codice | string | | **t** | Tag FE |
| valore_totale | valore_totale | numeric | currency_eur | **t** | |
| unita_totali | unita_totali | numeric | | f | non in whitelist |
| motivo_fermo | motivo_fermo | string | | f | non in whitelist |
| azioni | | azione | | f | |

---

## 3. Backlog — documenti fermi

- **Codice proposto:** `vendite.dash_backlog_documenti`
- **`.vue`:** `vendite/views/DashboardBacklogView.vue`
- **Whitelist:** `VenditeRepository.DASH_BACKLOG_SORT_COLUMNS` — estesa il
  2026-08-03 con `classe`.
- **Preset:** `anzianita_giorni desc` (default FE corrente). Pagina: 25.

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| anzianita_giorni | anzianita_giorni | numeric | | **t** | «Fermo da N gg» |
| classe | classe | string | | **t** | Tag FE (3 valori) |
| area | area | string | | **t** | Tag FE |
| codice | codice | string | | **t** | |
| cliente_display | cliente_display | string | | **t** | |
| valore_fermo | valore_fermo | numeric | currency_eur | **t** | |
| unita_ferme | unita_ferme | numeric | | f | non in whitelist |
| motivo_fermo | motivo_fermo | string | | f | non in whitelist |
| azione | azione | string | | f | testo «azione consigliata»; non in whitelist |
| stato_codice | stato_codice | string | | **t** | Tag FE |
| azioni | | azione | | f | |

⚠️ Attenzione ai due nomi vicini: `azione` è una colonna **dato** (il
suggerimento operativo della classe), `azioni` è la colonna di tipo `azione`.

---

## 4. Competenza — errori vivi

- **Codice proposto:** `vendite.dash_competenza_errori`
- **`.vue`:** `vendite/views/DashboardCompetenzaView.vue` (prima delle 3 tabelle)
- **Whitelist:** `VenditeRepository.DASH_COMPETENZA_ERRORI_SORT_COLUMNS` —
  **nuova** (2026-08-03): era l'unica lista dash senza ordinamento, ora la
  catena view→service→repo c'è, con `NULLS LAST` (metà della union ha i campi
  documento NULL per costruzione).
- **Preset:** `data_evento desc` (default storico BE: eventi recenti prima).
  Pagina: **10** (la sezione usa il passo compatto).

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| tipo_evento | tipo_evento | string | | **t** | Tag FE |
| lotto_codice | lotto_codice | string | | **t** | NULL sugli errori-fattura |
| fattura_numero | fattura_numero | numeric | | **t** | label FE componibile anno/serie/numero |
| error_code | error_code | string | | **t** | |
| messaggio | messaggio | string | | f | testo libero, non in whitelist |
| data_evento | data_evento | datetime | datetime_short | **t** | |

(nessuna colonna azioni: la lista è sola consultazione)

---

## 5. Competenza — gruppi fatturabili

- **Codice proposto:** `vendite.dash_competenza_gruppi`
- **`.vue`:** `vendite/views/DashboardCompetenzaView.vue` (card «Da emettere»)
- **Whitelist:** `VenditeRepository.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS`
  (7 voci, già completa — nessuna estensione necessaria).
- **Preset:** `valore desc` (default FE corrente: i gruppi più pesanti prima).
  Pagina: 25.
- La **checkbox** dell'emissione mirata NON va a catalogo (chrome BB, §0).

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| riferimento | riferimento | string | | **t** | |
| tipo_gruppo | tipo_gruppo | string | | **t** | Tag FE |
| cliente_display | cliente_display | string | | **t** | |
| commessa_codice | commessa_codice | string | | **t** | |
| n_attivita | n_attivita | numeric | | **t** | |
| valore | valore | numeric | currency_eur | **t** | |
| data_attivita_max | data_attivita_max | date | date_short | **t** | «Periodo» |
| azioni | | azione | | f | |

---

## 6. Competenza — drill-down per commessa (DEC-4)

- **Codice proposto:** `vendite.dash_competenza_commesse`
- **`.vue`:** `vendite/views/DashboardCompetenzaView.vue` (drill-down stadio)
- **Whitelist:** `VenditeRepository.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS`
  (5 voci, già completa).
- **Preset:** `valore_tot desc` (default FE corrente). Pagina: 25.

| codice | campo_sorgente | tipo | formato | ordinabile | note |
| --- | --- | --- | --- | --- | --- |
| commessa_codice | commessa_codice | string | | **t** | |
| cliente_display | cliente_display | string | | **t** | |
| n_attivita | n_attivita | numeric | | **t** | |
| valore_tot | valore_tot | numeric | currency_eur | **t** | |
| valore_fatturato_tot | valore_fatturato_tot | numeric | currency_eur | f | non in whitelist |
| data_attivita_max | data_attivita_max | date | date_short | **t** | «Periodo» |
| n_in_ritardo | n_in_ritardo | numeric | | f | non in whitelist; badge FE |
| azioni | | azione | | f | |

---

## 7. Nota sulla grana attività (perché NON c'è una settima lista)

Il drill-down a grana attività della Lente 1 è stato sostituito dal drill-down
per commessa (DEC-4): l'endpoint `/dashboard-competenza/attivita/` resta vivo
ma non alimenta più una tabella della dashboard. Il conteggio «23 colonne» del
piano per `DashboardCompetenzaView` erano le 3 tabelle sommate.

## 8. Dopo il seed

Come per il 7° lotto: al seed pushato, il BE/FE converte i `.vue` e aggiunge le
righe al registro `_LISTE` del presidio (`test_liste_configurabili_seed.py`).
Le colonne marcate «non in whitelist» qui sopra nascono `ordinabile=f`: se una
di esse dovesse diventare ordinabile in futuro, prima la voce BE, poi il
ribaltone del flag — mai `t` con la speranza.
