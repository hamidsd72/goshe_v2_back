"""Parsian sample format: IBAN,rial,first name,last name,حقوق, + CRLF."""
import re


def normalize_iban(value):
    return ''.join((value or '').split()).upper()


def valid_iranian_iban(value):
    value = normalize_iban(value)
    if not re.fullmatch(r'IR[0-9]{24}', value):
        return False
    return int(value[4:] + '1827' + value[2:4]) % 97 == 1


def bank_row(row, current_balance):
    """Cap a historical report's balance by today's outstanding balance."""
    iban = normalize_iban(row['iban'])
    amount = min(row['balance'], current_balance) * 10
    errors = []
    if row.get('iban_ambiguous'):
        errors.append('چند شماره شبای متفاوت برای مشاور ثبت شده است.')
    elif not valid_iranian_iban(iban):
        errors.append('شماره شبای ایران معتبر نیست.')
    if type(amount) is not int or amount <= 0:
        errors.append('مانده قابل پرداخت باید مثبت و صحیح باشد.')
    names = [row['first_name'].strip(), row['last_name'].strip()]
    if any(not name or any(character == ',' or ord(character) < 32 or ord(character) == 127
                           for character in name) for name in names):
        errors.append('نام و نام خانوادگی باید کامل و فاقد کاما یا نویسه کنترلی باشند.')
    return {
        'user_id': row['user_id'], 'iban': iban,
        'first_name': names[0], 'last_name': names[1],
        'amount_rial': amount, 'errors': errors,
    }


def render_bank_file(rows):
    if not rows or any(row['errors'] for row in rows):
        raise ValueError('Only validated, nonempty bank rows can be exported.')
    return ''.join('{iban},{amount_rial},{first_name},{last_name},حقوق,\r\n'.format(**row)
                   for row in rows).encode('utf-8')
