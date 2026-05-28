# Template offerta commerciale iniziale

## Scopo

Template HTML iniziale per la generazione PDF di un'**offerta commerciale**
tramite il context builder `OFFERTA_COMMERCIALE`. Da copiare in
`documenti.template_documenti_versioni.html_template` come prima versione
PUBBLICATA per la coppia (sorgente=`OFFERTA_COMMERCIALE`, tipo output=
`OFFERTA_COMMERCIALE`, emittente).

## Contesto

Il template usa solo il document context preparato dal backend
(`apps.vendite.services.offerta_document_context_builder.OffertaDocumentContextBuilder`).
Non esegue query, chiamate esterne o logica business.

Shape del context (versione 1, [vedi sorgente](../../../../../backend/apps/vendite/services/offerta_document_context_builder.py)):

- `offerta` — testata: `codice`, `validita_dal/al`, `data_emissione`,
  `stato.{codice,descrizione}`, `emittente_fiscale.{codice,descrizione}`,
  `utility_ref.{codice,descrizione}`, `listino.{codice,descrizione,versione_codice}`,
  `pricing.{modalita,tipo_variazione_globale,valore_variazione_globale}`,
  `revisione_numero`, `contratto.{id,numero}` (popolato dopo push), `meta`.
- `cliente` — `billing_account_id/codice`, `denominazione`, `id_fiscale`.
- `utility` — dettaglio utility 1:1 dell'offerta (tipo_utenza, classe_utenza,
  parametri).
- `eccezioni` — lista delle **deviazioni negoziate** dal listino base:
  `tipo_eccezione` ∈ {OVERRIDE, ESCLUSIONE, AGGIUNTA}, `articolo_codice/descrizione`,
  `is_composito`, `prezzo_unitario` (decimale 6 cifre stringa), `quantita`,
  `qta_operativa`, `uom_codice`, `tipo_erogazione`, `periodicita`, `ordine`,
  `attivo`, `componenti[]` (BoM annidato sui compositi).
- `_meta` — `context_version`, `context_code=OFFERTA_COMMERCIALE`,
  `righe_source=OFFERTE_ECCEZIONI`, `locale`.

> **Confine v1**: il documento mostra **solo le eccezioni**, non il listino
> effettivo completo. Per i prezzi non elencati si applica il listino base
> alle condizioni standard (l'estensione "listino effettivo" richiedera' una
> fn DB dedicata di preview, fase 2).

## Template HTML

```html
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Offerta {{ offerta.codice or offerta.id }}</title>
  <style>
    @page {
      size: A4;
      margin: 18mm 16mm 18mm 16mm;

      @bottom-left {
        content: "Zero ERP - Template demo offerta commerciale";
        color: #6b7280;
        font-size: 8pt;
      }

      @bottom-right {
        content: "Pagina " counter(page) " di " counter(pages);
        color: #6b7280;
        font-size: 8pt;
      }
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: #1f2937;
      font-family: "DejaVu Sans", Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.45;
    }

    .document { width: 100%; }

    .header {
      display: table;
      width: 100%;
      padding-bottom: 14px;
      border-bottom: 2px solid #111827;
    }

    .brand,
    .doc-title {
      display: table-cell;
      vertical-align: top;
    }

    .brand { width: 52%; }

    .brand-mark {
      display: inline-block;
      min-width: 36px;
      min-height: 36px;
      padding: 8px 10px;
      background: #111827;
      color: #ffffff;
      font-size: 15pt;
      font-weight: 700;
      letter-spacing: 0;
      text-align: center;
    }

    .brand-name {
      margin-top: 8px;
      font-size: 12pt;
      font-weight: 700;
    }

    .brand-meta {
      margin-top: 2px;
      color: #6b7280;
      font-size: 8.5pt;
    }

    .doc-title {
      width: 48%;
      text-align: right;
    }

    h1 {
      margin: 0;
      color: #111827;
      font-size: 22pt;
      font-weight: 700;
      letter-spacing: 0;
    }

    .doc-number {
      margin-top: 6px;
      font-size: 11pt;
      font-weight: 700;
    }

    .doc-revision {
      margin-top: 2px;
      color: #6b7280;
      font-size: 9pt;
    }

    .status-pill {
      display: inline-block;
      margin-top: 8px;
      padding: 3px 8px;
      border: 1px solid #9ca3af;
      border-radius: 999px;
      color: #374151;
      font-size: 8pt;
      text-transform: uppercase;
    }

    .section { margin-top: 18px; }

    .two-columns {
      display: table;
      width: 100%;
      table-layout: fixed;
    }

    .column {
      display: table-cell;
      width: 50%;
      vertical-align: top;
    }

    .column + .column { padding-left: 18px; }

    .label {
      margin-bottom: 4px;
      color: #6b7280;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
    }

    .box {
      min-height: 62px;
      padding: 10px 12px;
      border: 1px solid #d1d5db;
      border-radius: 4px;
      background: #ffffff;
    }

    .box-strong {
      font-size: 11pt;
      font-weight: 700;
    }

    .muted { color: #6b7280; }

    .facts {
      width: 100%;
      border-collapse: collapse;
    }

    .facts th,
    .facts td {
      padding: 5px 0;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
    }

    .facts th {
      width: 42%;
      color: #6b7280;
      font-size: 8.5pt;
      font-weight: 700;
    }

    .facts td { text-align: right; }

    .table-title {
      margin: 22px 0 8px;
      color: #111827;
      font-size: 11pt;
      font-weight: 700;
    }

    .table-subtitle {
      margin: 0 0 8px;
      color: #6b7280;
      font-size: 8.5pt;
    }

    table.lines {
      width: 100%;
      border-collapse: collapse;
      page-break-inside: auto;
    }

    table.lines thead { display: table-header-group; }

    table.lines tr {
      page-break-inside: avoid;
      page-break-after: auto;
    }

    table.lines th,
    table.lines td {
      padding: 7px 6px;
      border-bottom: 1px solid #e5e7eb;
      vertical-align: top;
    }

    table.lines th {
      background: #f3f4f6;
      color: #374151;
      font-size: 8pt;
      font-weight: 700;
      text-align: left;
      text-transform: uppercase;
    }

    .num {
      text-align: right;
      white-space: nowrap;
    }

    .row-description { font-weight: 700; }

    .row-note {
      margin-top: 2px;
      color: #6b7280;
      font-size: 8.5pt;
    }

    .tipo-pill {
      display: inline-block;
      margin-left: 6px;
      padding: 1px 6px;
      border-radius: 999px;
      font-size: 7.5pt;
      font-weight: 700;
      text-transform: uppercase;
      vertical-align: middle;
    }

    .tipo-pill.override   { background: #fef3c7; color: #92400e; }
    .tipo-pill.aggiunta   { background: #dcfce7; color: #166534; }
    .tipo-pill.esclusione { background: #fee2e2; color: #991b1b; }

    .componenti {
      margin: 6px 0 0 14px;
      padding-left: 10px;
      border-left: 2px solid #e5e7eb;
      color: #4b5563;
      font-size: 8.5pt;
    }

    .componenti-row { padding: 1px 0; }

    .conditions {
      margin-top: 24px;
      padding-top: 12px;
      border-top: 1px solid #d1d5db;
      color: #4b5563;
      font-size: 8.5pt;
    }
  </style>
</head>
<body>
  <main class="document">
    <header class="header">
      <div class="brand">
        <div class="brand-mark">ZE</div>
        <div class="brand-name">
          {{ offerta.emittente_fiscale.descrizione or "Emittente fiscale demo" }}
        </div>
        <div class="brand-meta">
          {% if offerta.emittente_fiscale.codice %}
            Codice emittente: {{ offerta.emittente_fiscale.codice }}
          {% else %}
            Dati emittente/asset da collegare nelle prossime iterazioni
          {% endif %}
        </div>
      </div>

      <div class="doc-title">
        <h1>OFFERTA COMMERCIALE</h1>
        <div class="doc-number">N. {{ offerta.codice or ("ID " ~ offerta.id) }}</div>
        {% if offerta.revisione_numero and offerta.revisione_numero > 1 %}
          <div class="doc-revision">Revisione {{ offerta.revisione_numero }}</div>
        {% endif %}
        <div class="status-pill">
          {{ offerta.stato.descrizione or offerta.stato.codice or "stato non indicato" }}
        </div>
      </div>
    </header>

    <section class="section two-columns">
      <div class="column">
        <div class="label">Cliente</div>
        <div class="box">
          <div class="box-strong">{{ cliente.denominazione or "Cliente non indicato" }}</div>
          {% if cliente.id_fiscale %}
            <div class="muted">{{ cliente.id_fiscale }}</div>
          {% endif %}
          {% if cliente.billing_account_codice %}
            <div class="muted">Billing account: {{ cliente.billing_account_codice }}</div>
          {% elif cliente.billing_account_id %}
            <div class="muted">Billing account ID: {{ cliente.billing_account_id }}</div>
          {% endif %}
        </div>
      </div>

      <div class="column">
        <div class="label">Dati offerta</div>
        <div class="box">
          <table class="facts">
            <tbody>
              <tr>
                <th>Data emissione</th>
                <td>{{ offerta.data_emissione or "-" }}</td>
              </tr>
              <tr>
                <th>Validita</th>
                <td>{{ offerta.validita_dal or "-" }} - {{ offerta.validita_al or "aperto" }}</td>
              </tr>
              <tr>
                <th>Utility</th>
                <td>{{ offerta.utility_ref.descrizione or offerta.utility_ref.codice or "-" }}</td>
              </tr>
              <tr>
                <th>Modalita pricing</th>
                <td>{{ offerta.pricing.modalita or "-" }}</td>
              </tr>
              {% if offerta.contratto.id %}
                <tr>
                  <th>Contratto generato</th>
                  <td>{{ offerta.contratto.numero or offerta.contratto.id }}</td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="section two-columns">
      <div class="column">
        <div class="label">Listino e condizioni</div>
        <div class="box">
          <table class="facts">
            <tbody>
              <tr>
                <th>Listino</th>
                <td>{{ offerta.listino.codice or offerta.listino.descrizione or "-" }}</td>
              </tr>
              <tr>
                <th>Versione</th>
                <td>{{ offerta.listino.versione_codice or "-" }}</td>
              </tr>
              <tr>
                <th>Variazione globale</th>
                <td>
                  {% if offerta.pricing.tipo_variazione_globale %}
                    {{ offerta.pricing.tipo_variazione_globale }} {{ offerta.pricing.valore_variazione_globale or "" }}
                  {% else %}
                    -
                  {% endif %}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="column">
        <div class="label">Dati utility</div>
        <div class="box">
          {% if utility %}
            <table class="facts">
              <tbody>
                <tr>
                  <th>Tipo utenza</th>
                  <td>{{ utility.get("tipo_utenza_descrizione") or utility.get("tipo_utenza_codice") or "-" }}</td>
                </tr>
                <tr>
                  <th>Classe utenza</th>
                  <td>{{ utility.get("classe_utenza_descrizione") or utility.get("classe_utenza_codice") or "-" }}</td>
                </tr>
                <tr>
                  <th>Parametro</th>
                  <td>{{ utility.get("param_1_num") or utility.get("param_2_txt") or "-" }}</td>
                </tr>
              </tbody>
            </table>
          {% else %}
            <span class="muted">Nessun dettaglio utility disponibile.</span>
          {% endif %}
        </div>
      </div>
    </section>

    <section class="section">
      <div class="table-title">Condizioni economiche — deviazioni dal listino</div>
      <div class="table-subtitle">
        Le voci elencate rappresentano le sole eccezioni negoziate rispetto al
        listino di riferimento. Per le voci non elencate si applicano le
        condizioni standard del listino indicato.
      </div>
      <table class="lines">
        <thead>
          <tr>
            <th style="width: 6%;">#</th>
            <th>Articolo</th>
            <th class="num" style="width: 12%;">Q.ta</th>
            <th class="num" style="width: 12%;">UoM</th>
            <th class="num" style="width: 18%;">Prezzo</th>
            <th class="num" style="width: 14%;">Erogazione</th>
          </tr>
        </thead>
        <tbody>
          {% for r in eccezioni %}
            <tr>
              <td>{{ r.get("ordine") or loop.index }}</td>
              <td>
                <div class="row-description">
                  {{ r.get("articolo_descrizione") or r.get("articolo_codice") or "Eccezione offerta" }}
                  {% set tipo = r.get("tipo_eccezione") %}
                  {% if tipo %}
                    <span class="tipo-pill {{ tipo|lower }}">{{ tipo }}</span>
                  {% endif %}
                </div>
                {% if r.get("articolo_codice") and r.get("articolo_descrizione") %}
                  <div class="row-note">Codice: {{ r.get("articolo_codice") }}</div>
                {% endif %}
                {% if r.get("periodicita") or r.get("tipo_erogazione") %}
                  <div class="row-note">
                    {{ r.get("tipo_erogazione") or "" }}
                    {% if r.get("periodicita") %} - {{ r.get("periodicita") }}{% endif %}
                  </div>
                {% endif %}

                {% if r.get("is_composito") and r.get("componenti") %}
                  <div class="componenti">
                    <strong>Componenti BoM:</strong>
                    {% for c in r.get("componenti") %}
                      <div class="componenti-row">
                        - {{ c.get("componente_descrizione") or c.get("componente_codice") or "componente" }}
                        {% if c.get("quantita") %} x {{ c.get("quantita") }}{% endif %}
                        {% if c.get("uom_codice") %} {{ c.get("uom_codice") }}{% endif %}
                        {% if c.get("prezzo_unitario") %} @ {{ c.get("prezzo_unitario") }}{% endif %}
                      </div>
                    {% endfor %}
                  </div>
                {% endif %}
              </td>
              <td class="num">{{ r.get("qta_operativa") or r.get("quantita") or "-" }}</td>
              <td class="num">{{ r.get("uom_codice") or "-" }}</td>
              <td class="num">
                {% if r.get("tipo_eccezione") == "ESCLUSIONE" %}
                  <span class="muted">esclusa</span>
                {% else %}
                  {{ r.get("prezzo_unitario") or "-" }}
                {% endif %}
              </td>
              <td class="num">{{ r.get("tipo_erogazione") or "-" }}</td>
            </tr>
          {% else %}
            <tr>
              <td colspan="6" class="muted">
                Nessuna eccezione negoziata: si applicano integralmente le
                condizioni standard del listino indicato.
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="conditions">
      <strong>Note demo.</strong>
      Template HTML di prova per stampa offerta commerciale. Il contenuto usa
      solo il document context `OFFERTA_COMMERCIALE` e non esegue query o
      chiamate esterne. La validita' della presente offerta e' quella indicata
      nell'intestazione; salvo accettazione entro la data di scadenza, le
      condizioni qui riportate decadono.
    </section>
  </main>
</body>
</html>
```

## Configurazione iniziale lato app

1. **Modelli Documenti → Nuovo template**:
   - Sorgente: `OFFERTA_COMMERCIALE`
   - Tipo output: `OFFERTA_COMMERCIALE`
   - Emittente fiscale: quella desiderata
   - `context_builder_code`: `OFFERTA_COMMERCIALE`
   - `is_default`: vero
   - `file_name_pattern` (esempio): `offerta-{offerta[codice]}.pdf`
2. **Nuova versione → BOZZA**: incollare l'HTML qui sopra.
3. **Pubblicare** la versione: da quel momento l'emissione dell'offerta
   (BOZZA → EMESSA) genera il PDF usando questo template; l'anteprima in
   BOZZA mostra lo stesso layout.

## Aggancio asset (opzionale, fase successiva)

Il template di esempio non referenzia ancora asset emittente (logo, firma).
Quando saranno caricati gli asset per l'emittente, sostituire il blocco
`.brand-mark` con un `<img>` che punti all'asset (es. `LOGO`) per la stampa
finale.
