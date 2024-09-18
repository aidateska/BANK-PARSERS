import pdfplumber
import re

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------
def extract_text_from_pdf(pdf_path):
    text = ''
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + '\n'
    except FileNotFoundError:
        return None
    return text

def extract_account_info(text):
    account_info = {
        "account_holder": "",
        "account_holder_id": "",
        "account_holder_address": "",
        "account_number": "",
        "statement_period": "",
        "bank_name": "Rabobank",
        "bank_address": "Croeselaan 18 3521 CB Utrecht The Netherlands",
        "bank_reg_no": "30046259",
        "bank_vat_code": "NL001797931B01",
        "bank_registration_date": "",
        "bank_bic": "RABONL2U",
        "initial_balance": "",
        "closing_balance": ""
    }

    lines = text.split('\n')
    
    if len(lines) > 6:
        
        account_info["account_holder"] = lines[5].strip().split(' ')[0] + ' ' + ' '.join(lines[5].strip().split(' ')[1:]).split(' ')[1]
    
    if len(lines) > 7:
        
        account_info["account_holder_address"] = lines[6].strip()

    if len(lines) > 9:
        
        initial_balance_line = lines[8].strip()
        statement_start_date_match = re.search(r'(\d{2}-\d{2}-\d{4})', initial_balance_line)
        if statement_start_date_match:
            statement_start_date = statement_start_date_match.group(1)
            account_info["initial_balance"] = re.search(r'([\d.,]+) CR', initial_balance_line).group(1).replace('.', '').replace(',', '.')
            account_info["statement_period"] = f"{statement_start_date} - {statement_end_date}" if 'statement_end_date' in locals() else statement_start_date
        
    if len(lines) > 11:
        
        closing_balance_line = lines[10].strip()
        statement_end_date_match = re.search(r'(\d{2}-\d{2}-\d{4})', closing_balance_line)
        if statement_end_date_match:
            statement_end_date = statement_end_date_match.group(1)
            account_info["closing_balance"] = re.search(r'([\d.,]+) CR', closing_balance_line).group(1).replace('.', '').replace(',', '.')
            if 'statement_period' not in account_info or not account_info["statement_period"]:
                account_info["statement_period"] = f"{statement_start_date} - {statement_end_date}"
        
    if len(lines) > 12:
        
        account_number_match = re.search(r'(NL\d{2} RABO \d{4} \d{4} \d{2})', lines[12].strip())
        if account_number_match:
            account_info["account_number"] = account_number_match.group(1)

    return account_info

def parse_transactions(text):
    transactions = []
    transaction_id = 1

    transaction_line_pattern = re.compile(r'^(\d{2}-\d{2})\s+(.*?)\s+([\d.,]+)$')
    verwerkingsdatum_pattern = re.compile(r'Verwerkingsdatum:\s*(\d{2}-\d{2}-\d{4})')

    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        match = transaction_line_pattern.match(line)
        if match:
            date = match.group(1)
            beneficiary = match.group(2).strip()
            amount_str = match.group(3).replace('.', '').replace(',', '.')
            amount = float(amount_str)

            amount_position = line.rfind(match.group(3))
            
            details = []
            transaction_date = ''

            i += 1
            while i < len(lines) and not transaction_line_pattern.match(lines[i].strip()):
                detail_line = lines[i].strip()

                if verwerkingsdatum_pattern.search(detail_line):
                    transaction_date = verwerkingsdatum_pattern.search(detail_line).group(1)
                else:
                    details.append(detail_line)
                i += 1

            if not transaction_date:
                transaction_date = date

            details_text = ' | '.join(details)
            details_end_position = len(line) - len(details_text) - 1

            indicator = 'dbit' if amount_position > details_end_position else 'crdt'

            transactions.append({
                'transaction_id': f'{transaction_id:03}',
                'date': transaction_date,
                'beneficiary': beneficiary,
                'details': ' | '.join(details),
                'amount': f'{amount:.2f}',
                'balance': '',
                'cdt_dbt_ind': indicator
            })
            
            transaction_id += 1
        else:
            i += 1
    
    return transactions

def extract_pdf_data(pdf_file):
    try:
        text = extract_text_from_pdf(pdf_file)
        if text is None:
            return None
        
        account_info = extract_account_info(text)
        transactions = parse_transactions(text)

        data = {
            "account_holder": account_info.get('account_holder', ''),
            "account_holder_id": account_info.get('account_holder_id', ''),
            "account_holder_address": account_info.get('account_holder_address', ''),
            "account_number": account_info.get('account_number', ''),
            "statement_period": account_info.get('statement_period', ''),
            "bank_name": account_info.get('bank_name', 'Rabobank'),
            "bank_address": account_info.get('bank_address', 'Croeselaan 18 3521 CB Utrecht The Netherlands'),
            "bank_reg_no": account_info.get('bank_reg_no', '30046259'),
            "bank_vat_code": account_info.get('bank_vat_code', 'NL001797931B01'),
            "bank_registration_date": account_info.get('bank_registration_date', ''),
            "bank_bic": account_info.get('bank_bic', 'RABONL2U'),
            "transactions": transactions,
            "initial_balance": account_info.get('initial_balance', ''),
            "closing_balance": account_info.get('closing_balance', '')
        }

        return data

    except FileNotFoundError:
        return None
    except Exception:
        return None

# -------------------- FUNCTION FOR EXTRACTING PDF DATA --------------------

# Automatically trigger processing when this script is run directly
if __name__ == "__main__":
    from common_script import process_files
    process_files(extract_pdf_data)
