"""Read-only report projection and dependency-free XLSX/print exports."""
from html import escape
from io import BytesIO
import re
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape as xml_escape


PERFORMANCE_COLUMNS = [
    ('first_name', 'نام', False), ('last_name', 'نام خانوادگی', False),
    ('phone', 'شماره تماس', False), ('call_share', 'سهم تماس', True),
    ('message_share', 'سهم پیام', True), ('gross_earnings', 'کارکرد ناخالص', True),
    ('opening_balance', 'مانده انتقالی', True), ('tax', 'مالیات', True),
    ('deductions', 'کسورات تا پایان دوره', True), ('paid_in_period', 'پرداخت دوره', True),
    ('balance', 'مانده', True),
    ('iban', 'شماره شبا', False), ('previous_payments', 'واریزی قبل از دوره', True),
    ('payable', 'قابل پرداخت پیش از پرداخت دوره', True), ('settlement_status', 'وضعیت مانده', False),
]
EVENT_COLUMNS = [
    ('document_id', 'شناسه سند', False), ('first_name', 'نام', False),
    ('last_name', 'نام خانوادگی', False), ('phone', 'شماره تماس', False),
    ('event_kind', 'نوع رویداد', False), ('amount_toman', 'مبلغ خالص کسورات', True),
    ('event_at', 'زمان رویداد به وقت تهران', False),
    ('bank_reference', 'مرجع بانکی', False), ('confirmed_by', 'شناسه مدیر', False),
    ('transaction_id', 'شناسه تراکنش', False), ('reverses', 'سند اصلی برگشت', False),
]
TITLES = {
    'performance': 'گزارش کارکرد مشاوران', 'deductions': 'گزارش مالیات و کسورات',
    'payments': 'گزارش پرداخت‌ها', 'balances': 'گزارش مانده بدهی به مشاوران',
    'settlements': 'گزارش اسناد تسویه و برگشت',
}


def project_report(kind, report, events=None, start=None, end=None, generated_at=''):
    if kind in ('payments', 'settlements'):
        columns = EVENT_COLUMNS
        rows = events or []
        summary = [('مجموع مبالغ خالص', sum(row['amount_toman'] for row in rows))]
    else:
        columns = PERFORMANCE_COLUMNS
        if kind == 'deductions':
            keys = {'first_name', 'last_name', 'phone', 'tax', 'deductions', 'paid_in_period', 'previous_payments'}
            columns = [column for column in columns if column[0] in keys]
        rows = report['results']
        if kind == 'balances':
            rows = [row for row in rows if row['balance'] > 0]
        summary = [(label, sum(row[key] for row in rows)) for key, label in (
            ('call_share', 'مجموع سهم تماس'), ('message_share', 'مجموع سهم پیام'),
            ('gross_earnings', 'مجموع کارکرد'), ('deductions', 'مجموع کسورات تا پایان دوره'),
            ('paid_in_period', 'مجموع پرداخت دوره'), ('balance', 'مجموع مانده'))]
    projected_rows = [{key: row.get(key) for key, _, _ in columns} for row in rows]
    statuses = {'settled': 'مانده تسویه‌شده', 'partial': 'پرداخت جزئی', 'unpaid': 'دارای مانده'}
    for row in projected_rows:
        if 'settlement_status' in row:
            row['settlement_status'] = statuses.get(row['settlement_status'], '')
    return {
        'title': TITLES[kind], 'currency': 'toman', 'tax_status': 'pending',
        'generated_at': generated_at, 'start': str(start) if start else '',
        'end': str(end) if end else '',
        'columns': [{'key': key, 'label': label, 'numeric': numeric} for key, label, numeric in columns],
        'rows': projected_rows,
        'summary': [{'label': label, 'amount': amount} for label, amount in summary],
        'note': 'مبالغ به تومان است. مالیات در انتظار تعیین است. تراکنش‌های قدیمی w شامل هزینه سالانه نیز هستند. کسورات تا پایان دوره شامل پرداخت قبل و داخل دوره است.',
    }


def column_name(index):
    name = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def clean_xml(value):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', '', str(value))


def worksheet_xml(rows, numeric_columns=()):
    cells = []
    for row_index, row in enumerate(rows, 1):
        values = []
        for col_index, value in enumerate(row, 1):
            reference = '{}{}'.format(column_name(col_index), row_index)
            style = 1 if row_index == 1 else (2 if col_index - 1 in numeric_columns else 0)
            if value is None:
                values.append('<c r="{}" s="{}"/>'.format(reference, style))
            elif type(value) is int and row_index > 1:
                values.append('<c r="{}" s="{}"><v>{}</v></c>'.format(reference, style, value))
            else:
                values.append('<c r="{}" s="{}" t="inlineStr"><is><t xml:space="preserve">{}</t></is></c>'.format(
                    reference, style, xml_escape(clean_xml(value))))
        cells.append('<row r="{}">{}</row>'.format(row_index, ''.join(values)))
    width = max((len(row) for row in rows), default=1)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0" rightToLeft="1"><pane ySplit="1" topLeftCell="A2" state="frozen" activePane="bottomLeft"/></sheetView></sheetViews>'
            '<cols><col min="1" max="{}" width="25" customWidth="1"/></cols>'
            '<sheetData>{}</sheetData><autoFilter ref="A1:{}{}"/>'
            '</worksheet>').format(width, ''.join(cells), column_name(width), len(rows))


def render_xlsx(report):
    columns = report['columns']
    rows = [[column['label'] for column in columns]]
    rows += [[row.get(column['key']) for column in columns] for row in report['rows']]
    numeric = [index for index, column in enumerate(columns) if column['numeric']]
    summary = [['عنوان', 'مقدار'], ['گزارش', report['title']], ['واحد', 'تومان'],
               ['شروع', report['start']], ['پایان', report['end']],
               ['زمان تهیه به وقت تهران', report['generated_at']], ['وضعیت مالیات', 'pending'],
               ['فیلترها', report.get('filter_description', '')], ['توضیح', report['note']]]
    summary += [[item['label'], item['amount']] for item in report['summary']]
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', """<?xml version="1.0" ?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
        """)
        archive.writestr('_rels/.rels', """<?xml version="1.0" ?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
        """)
        archive.writestr('xl/workbook.xml', """<?xml version="1.0" ?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="گزارش" sheetId="1" r:id="rId1"/>
    <sheet name="خلاصه" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
        """)
        archive.writestr('xl/_rels/workbook.xml.rels', """<?xml version="1.0" ?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
        """)
        archive.writestr('xl/styles.xml', """<?xml version="1.0" ?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font>
      <sz val="11"/>
      <name val="Arial"/>
    </font>
    <font>
      <b/>
      <sz val="11"/>
      <color rgb="FFFFFFFF"/>
      <name val="Arial"/>
    </font>
  </fonts>
  <fills count="3">
    <fill>
      <patternFill patternType="none"/>
    </fill>
    <fill>
      <patternFill patternType="gray125"/>
    </fill>
    <fill>
      <patternFill patternType="solid">
        <fgColor rgb="FF3C0B64"/>
        <bgColor indexed="64"/>
      </patternFill>
    </fill>
  </fills>
  <borders count="1">
    <border/>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1">
      <alignment horizontal="right" wrapText="1"/>
    </xf>
    <xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>
        """)
        archive.writestr('xl/worksheets/sheet1.xml', worksheet_xml(rows, numeric))
        archive.writestr('xl/worksheets/sheet2.xml', worksheet_xml(summary, (1,)))
    return output.getvalue()


def render_print_html(report):
    def display(value):
        if value is None:
            return '—'
        return escape(format(value, ',') if type(value) is int else str(value))
    headers = ''.join('<th>{}</th>'.format(escape(column['label'])) for column in report['columns'])
    body = ''.join('<tr>{}</tr>'.format(''.join(
        '<td><bdi class="{}" dir="{}">{}</bdi></td>'.format(
            'iban' if column['key'] == 'iban' else '',
            'ltr' if column['numeric'] or column['key'] in (
                'phone', 'iban', 'event_at', 'bank_reference', 'document_id', 'confirmed_by', 'transaction_id', 'reverses') else 'auto',
            display(row.get(column['key']))) for column in report['columns']))
        for row in report['rows'])
    if not body:
        body = '<tr><td colspan="{}">رکوردی یافت نشد.</td></tr>'.format(len(report['columns']))
    summary = ' | '.join('{} {} تومان'.format(escape(item['label']), display(item['amount'])) for item in report['summary'])
    return ('<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">'
            '<title>{title}</title><style>'
            '@page{{size:A3 landscape;margin:12mm}}body{{font:12px Arial,sans-serif;color:#222}}'
            'h1{{font-size:20px;color:#3c0b64}}p{{line-height:1.9}}table{{border-collapse:collapse;width:100%;table-layout:auto;font-size:11px}}'
            'th,td{{border:1px solid #aaa;padding:6px;text-align:right;overflow-wrap:anywhere}}'
            'th{{background:#eee}}.iban{{white-space:nowrap;font:10px monospace}}thead{{display:table-header-group}}tr{{break-inside:avoid}}'
            '</style></head><body><h1>{title}</h1><p>بازه <bdi dir="ltr">{start}</bdi> تا <bdi dir="ltr">{end}</bdi> | زمان تهیه <bdi dir="ltr">{generated}</bdi></p>'
            '<p>{filters}</p><p>{note}</p><p>{summary}</p><table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>'
            '</body></html>').format(title=escape(report['title']), start=escape(report['start'] or 'ابتدای سوابق'),
                                     end=escape(report['end'] or 'آخرین سوابق'), generated=escape(report['generated_at']),
                                     filters=escape(report.get('filter_description', '')),
                                     note=escape(report['note']), summary=summary, headers=headers, body=body)
